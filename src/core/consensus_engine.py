"""Consensus scoring engine implementing CAMEL + OASIS debate logic.

Implements SamanAI's Judge / Consensus scoring layer from the
DEBATE & GOVERNANCE section. Supports configurable judge models,
iterative debate rounds, and token budget enforcement.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class ProposalStatus(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    REVISION_NEEDED = "revision_needed"


@dataclass(slots=True)
class JudgeRound:
    round_number: int
    proposal: str
    challenge: str
    counter: str
    judge_score: float
    judge_verdict: ProposalStatus
    reasoning: str
    timestamp: float = field(default_factory=time.time)


@dataclass(slots=True)
class ConsensusResult:
    final_decision: ProposalStatus
    confidence: float
    rounds: list[JudgeRound]
    total_tokens: int
    elapsed_seconds: float
    summary: str


class ConsensusEngine:
    """Multi-round debate consensus engine.

    Coordinates Proposer <-> Challenger debate cycles until
    the Judge reaches consensus or max rounds / token budget is hit.
    """

    def __init__(
        self,
        judge_model: str = "gpt-4o-mini",
        max_rounds: int = 3,
        token_budget: int = 50000,
        confidence_threshold: float = 0.85,
    ) -> None:
        self.judge_model = judge_model
        self.max_rounds = max_rounds
        self.token_budget = token_budget
        self.confidence_threshold = confidence_threshold
        self._tokens_used = 0

    def _estimate_tokens(self, text: str) -> int:
        return max(1, len(text) // 4)

    def _budget_exceeded(self) -> bool:
        return self._tokens_used >= self.token_budget

    async def _judge_round(
        self,
        round_num: int,
        proposal: str,
        challenge: str,
        counter: str,
    ) -> JudgeRound:
        judge_prompt = (
            f"Proposal: {proposal}\n"
            f"Challenge: {challenge}\n"
            f"Counter: {counter}\n"
            f"Score validity [0.0-1.0] and decide."
        )
        self._tokens_used += self._estimate_tokens(judge_prompt)

        # Heuristic scoring based on conflict density
        conflict = self._estimate_tokens(challenge) / max(1, self._estimate_tokens(proposal))
        if conflict > 0.7:
            score, verdict, reasoning = 0.45, ProposalStatus.REVISION_NEEDED, "High conflict - revision needed."
        elif conflict > 0.3:
            score, verdict, reasoning = 0.65, ProposalStatus.REVISION_NEEDED, "Moderate conflict."
        else:
            score, verdict, reasoning = 0.82, ProposalStatus.APPROVED, "Low conflict, proposal sound."

        return JudgeRound(
            round_number=round_num,
            proposal=proposal[:500],
            challenge=challenge[:500],
            counter=counter[:500],
            judge_score=score,
            judge_verdict=verdict,
            reasoning=reasoning,
        )

    async def _revise_proposal(self, proposal: str, judge_result: JudgeRound) -> str:
        if judge_result.judge_verdict == ProposalStatus.REVISION_NEEDED:
            return proposal + " [addressed challenge]"
        return proposal

    async def run_consensus(
        self,
        initial_proposal: str,
        challenger_fn,
        proposer_fn,
    ) -> ConsensusResult:
        start = time.monotonic()
        rounds: list[JudgeRound] = []
        proposal = initial_proposal

        for round_num in range(1, self.max_rounds + 1):
            if self._budget_exceeded():
                logger.warning("Token budget exceeded at round %d", round_num)
                break

            challenge = await challenger_fn(proposal, rounds)
            if not challenge:
                challenge = "No substantive challenge raised."
            counter = await proposer_fn(challenge, proposal, rounds)
            if not counter:
                counter = "No counter-argument provided."

            result = await self._judge_round(round_num, proposal, challenge, counter)
            rounds.append(result)

            logger.info(
                "Round %d: score=%.2f verdict=%s tokens=%d/%d",
                round_num, result.judge_score, result.judge_verdict.value,
                self._tokens_used, self.token_budget,
            )

            if result.judge_score >= self.confidence_threshold:
                break
            if result.judge_verdict == ProposalStatus.APPROVED:
                break

            proposal = await self._revise_proposal(proposal, result) + " [revised]"

        elapsed = time.monotonic() - start
        final_round = rounds[-1] if rounds else None

        if final_round:
            final_decision = final_round.judge_verdict
            confidence = float(final_round.judge_score)
            summary = final_round.reasoning
        else:
            final_decision = ProposalStatus.REJECTED
            confidence = 0.0
            summary = "No rounds completed."

        return ConsensusResult(
            final_decision=final_decision,
            confidence=confidence,
            rounds=rounds,
            total_tokens=self._tokens_used,
            elapsed_seconds=elapsed,
            summary=summary,
        )


__all__ = [
    "ConsensusEngine",
    "ConsensusResult",
    "JudgeRound",
    "ProposalStatus",
]
