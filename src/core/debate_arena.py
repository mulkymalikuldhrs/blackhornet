"""Debate Arena — Proposer / Challenger / Judge topology.

Implements SamanAI §3.2 DEBATE & GOVERNANCE layer.
Wired to BlackHornet core via ast_sanitizer and council.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Callable, Awaitable

from src.core.ast_sanitizer import SecurityViolationException, sanitize

logger = logging.getLogger(__name__)


class DebateRoundStatus(str, Enum):
    PENDING = "pending"
    CHALLENGED = "challenged"
    JUDGED = "judged"
    BLOCKED = "blocked"


@dataclass(slots=True)
class DebateRound:
    round_number: int
    proposal: str = ""
    challenge: str = ""
    counter: str = ""
    judge_score: float = 0.0
    judge_verdict: str = "pending"
    status: DebateRoundStatus = DebateRoundStatus.PENDING
    sanitized: bool = False
    blocked_reason: str = ""


@dataclass(slots=True)
class DebateResult:
    proposal: str
    rounds: list[DebateRound] = field(default_factory=list)
    final_score: float = 0.0
    final_verdict: str = "pending"
    blocked: bool = False
    blocked_reason: str = ""
    total_rounds: int = 0


class DebateArena:
    """Multi-round debate engine with AST sanitization gate.

    Topology: Proposer → Challenger → Judge → (loop or verdict)
    """

    def __init__(self, max_rounds: int = 3, confidence_threshold: float = 0.85) -> None:
        self.max_rounds = max_rounds
        self.confidence_threshold = confidence_threshold
        self.rounds: list[DebateRound] = []

    def _sanitize(self, text: str, label: str) -> tuple[bool, str]:
        try:
            sanitize(text, language="python")
            return True, ""
        except SecurityViolationException as e:
            return False, e.reason

    async def propose(
        self,
        proposal: str,
        proposer_fn: Optional[Callable[[str], Awaitable[str]]] = None,
    ) -> DebateRound:
        ok, reason = self._sanitize(proposal, "proposal")
        if not ok:
            return DebateRound(
                round_number=len(self.rounds) + 1,
                proposal=proposal[:500],
                status=DebateRoundStatus.BLOCKED,
                blocked_reason=reason,
            )
        refined = await proposer_fn(proposal) if proposer_fn else proposal
        round_obj = DebateRound(
            round_number=len(self.rounds) + 1,
            proposal=refined[:500],
            status=DebateRoundStatus.PENDING,
            sanitized=True,
        )
        self.rounds.append(round_obj)
        return round_obj

    async def challenge(
        self,
        challenge_text: str,
        challenger_fn: Optional[Callable[[str], Awaitable[str]]] = None,
    ) -> DebateRound:
        ok, reason = self._sanitize(challenge_text, "challenge")
        if not ok:
            if self.rounds:
                self.rounds[-1].status = DebateRoundStatus.BLOCKED
                self.rounds[-1].blocked_reason = reason
            return DebateRound(
                round_number=len(self.rounds) + 1,
                challenge=challenge_text[:500],
                status=DebateRoundStatus.BLOCKED,
                blocked_reason=reason,
            )
        refined = await challenger_fn(challenge_text) if challenger_fn else challenge_text
        round_obj = DebateRound(
            round_number=len(self.rounds) + 1,
            proposal=self.rounds[-1].proposal if self.rounds else "",
            challenge=refined[:500],
            status=DebateRoundStatus.CHALLENGED,
            sanitized=True,
        )
        self.rounds.append(round_obj)
        return round_obj

    async def judge(
        self,
        proposal: str,
        challenge: str,
        counter: str = "",
    ) -> DebateRound:
        ok, reason = self._sanitize(proposal, "judge_proposal")
        if not ok:
            return DebateRound(
                round_number=len(self.rounds) + 1,
                status=DebateRoundStatus.BLOCKED,
                blocked_reason=reason,
            )
        conflict = len(challenge) / max(1, len(proposal))
        if conflict > 0.7:
            score, verdict = 0.35, "reject"
        elif conflict > 0.3:
            score, verdict = 0.6, "revise"
        else:
            score, verdict = 0.88, "approve"
        round_obj = DebateRound(
            round_number=len(self.rounds) + 1,
            proposal=proposal[:500],
            challenge=challenge[:500],
            counter=counter[:500],
            judge_score=score,
            judge_verdict=verdict,
            status=DebateRoundStatus.JUDGED,
            sanitized=True,
        )
        self.rounds.append(round_obj)
        return round_obj

    async def run_debate(
        self,
        initial_proposal: str,
        challenger_fn: Optional[Callable[[str], Awaitable[str]]] = None,
        proposer_fn: Optional[Callable[[str], Awaitable[str]]] = None,
    ) -> DebateResult:
        prop_round = await self.propose(initial_proposal, proposer_fn)
        if prop_round.status == DebateRoundStatus.BLOCKED:
            return DebateResult(proposal=initial_proposal, blocked=True, blocked_reason=prop_round.blocked_reason)
        chall_round = await self.challenge(
            f"Challenge to: {prop_round.proposal[:200]}",
            challenger_fn,
        )
        if chall_round.status == DebateRoundStatus.BLOCKED:
            await self.judge(prop_round.proposal, "No challenge raised.")
            return self._build_result()
        await self.judge(prop_round.proposal, chall_round.challenge, "Counter-argument provided.")
        return self._build_result()

    def _build_result(self) -> DebateResult:
        judged = [r for r in self.rounds if r.status == DebateRoundStatus.JUDGED]
        last = judged[-1] if judged else None
        return DebateResult(
            proposal=self.rounds[0].proposal if self.rounds else "",
            rounds=self.rounds,
            final_score=last.judge_score if last else 0.0,
            final_verdict=last.judge_verdict if last else "pending",
            total_rounds=len(self.rounds),
        )


__all__ = ["DebateArena", "DebateRound", "DebateResult", "DebateRoundStatus"]
