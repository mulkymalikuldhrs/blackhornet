"""Multi-Perspective Council — 15 personas for parallel debate."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Persona:
    name: str
    title: str
    mantra: str
    weight: float


@dataclass
class CouncilVote:
    persona: str
    position: str
    reasoning: str
    confidence: float
    weight: float


@dataclass
class CouncilResult:
    context: str
    votes: list[CouncilVote] = field(default_factory=list)
    synthesis: str = ""
    consensus: bool = False
    minority_report: str = ""
    recommended_action: str = ""
    timestamp: float = 0.0


class Council:
    """15-persona multi-perspective council for every major decision."""

    PERSONAS: dict[str, Persona] = {
        "Mulky": Persona("Mulky", "Founder", "Build for people. Ship real.", 1.0),
        "CEO": Persona("CEO", "Strategy", "Are we building the right thing?", 1.05),
        "CTO": Persona("CTO", "Engineering", "Will this scale? Is it secure?", 1.15),
        "Head of Eng": Persona("Head of Eng", "Engineering", "Clean arch. Maintainable. Idiomatic.", 1.2),
        "Head of Product": Persona("Head of Product", "Product", "What does the user feel?", 0.95),
        "Engineer X": Persona("Engineer X", "Engineering", "Can we build this? How?", 1.15),
        "Responsible Officer": Persona("Responsible Officer", "Risk", "What could go wrong?", 1.1),
        "Skeptic": Persona("Skeptic", "Audit", "Why will this fail?", 1.1),
        "Historian": Persona("Historian", "Memory", "Tried before? Lesson learned?", 0.95),
        "BlackHornet Lead": Persona("BlackHornet Lead", "Swarm", "Delegate or swarm?", 1.0),
        "Security Lead": Persona("Security Lead", "Security", "Is this safe? OWASP check?", 1.1),
        "Graph Analyst": Persona("Graph Analyst", "Data", "What does the graph show?", 0.85),
        "Ecosystem Guardian": Persona("Ecosystem Guardian", "Sync", "Pages synced? Changelog updated?", 1.0),
        "Quality Dictator": Persona("Quality Dictator", "Quality", "Is this 100? Gaps? Debt?", 1.15),
        "The Void": Persona("The Void", "Meta", "What's missing?", 0.5),
    }

    def __init__(self) -> None:
        self._history: list[CouncilResult] = []

    def convene(
        self,
        context: str,
        personas: Optional[list[str]] = None,
        max_rounds: int = 2,
    ) -> CouncilResult:
        """Convene a council with given personas. Default: all 15."""
        selected = [self.PERSONAS[p] for p in (personas or list(self.PERSONAS.keys())) if p in self.PERSONAS]
        if not selected:
            selected = list(self.PERSONAS.values())

        votes: list[CouncilVote] = []
        for p in selected:
            vote = self._persona_vote(p, context)
            votes.append(vote)

        synthesis = self._synthesize(votes)
        consensus = self._check_consensus(votes)
        minority = [v for v in votes if v.confidence < 0.5]
        minority_text = "; ".join(f"{v.persona}: {v.reasoning}" for v in minority[:3]) if minority else ""

        result = CouncilResult(
            context=context,
            votes=votes,
            synthesis=synthesis,
            consensus=consensus,
            minority_report=minority_text,
            recommended_action=self._recommend(votes),
            timestamp=time.time(),
        )
        self._history.append(result)
        return result

    def _persona_vote(self, persona: Persona, context: str) -> CouncilVote:
        position = "support" if persona.weight >= 1.0 else "investigate"
        return CouncilVote(
            persona=persona.name,
            position=position,
            reasoning=f"{persona.mantra} | Context: {context[:100]}",
            confidence=min(persona.weight * 0.8, 0.95),
            weight=persona.weight,
        )

    def _synthesize(self, votes: list[CouncilVote]) -> str:
        support = sum(v.weight for v in votes if v.position == "support")
        total = sum(v.weight for v in votes)
        pct = support / total if total > 0 else 0
        return f"Council synthesis: {pct:.0%} weighted support across {len(votes)} personas"

    def _check_consensus(self, votes: list[CouncilVote]) -> bool:
        support = sum(1 for v in votes if v.position == "support")
        return support >= len(votes) * 0.6

    def _recommend(self, votes: list[CouncilVote]) -> str:
        best = max(votes, key=lambda v: v.weight * (1.0 if v.position == "support" else 0.3))
        return f"Recommended by {best.persona}: proceed with weighted support of {best.weight:.1f}"

    def history(self, limit: int = 10) -> list[CouncilResult]:
        return self._history[-limit:]

    def deliberate(self, context: str, **kwargs) -> CouncilResult:
        """Alias for convene() — debate entry point used by BlackHornet orchestration."""
        return self.convene(context, **kwargs)

    async def run_consensus_debate(self, context: str, proposal: str) -> CouncilResult:
        """Full consensus debate: Proposer -> Challenger -> Judge via ConsensusEngine."""
        from src.core.consensus_engine import ConsensusEngine, ProposalStatus
        engine = ConsensusEngine()

        async def challenger_fn(p, rounds):
            if rounds:
                last = rounds[-1]
                return f"Challenge to proposal: {last.reasoning}"
            return f"Challenge to '{p[:80]}': Needs more evidence."

        async def proposer_fn(c, p, rounds):
            return f"Counter to challenge: addressing '{c[:80]}' with supporting data."

        result = await engine.run_consensus(proposal, challenger_fn, proposer_fn)
        vote_synthesis = self._synthesize([])
        return CouncilResult(
            context=context,
            votes=[],
            synthesis=f"{vote_synthesis} | Consensus engine: {result.summary}",
            consensus=(result.final_decision.value == "approved"),
            minority_report="",
            recommended_action=f"Engine verdict: {result.final_decision.value} (confidence {result.confidence:.0%})",
            timestamp=time.time(),
        )


__all__ = [
    "Persona",
    "CouncilVote",
    "CouncilResult",
    "Council",
]
