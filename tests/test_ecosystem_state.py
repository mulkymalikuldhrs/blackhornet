"""Tests for EcosystemState — canonical colony state schema (SAMAN-AI DESIGN.md)."""

from __future__ import annotations

from src.bh_types.ecosystem import ConsensusStatus, EcosystemState


def test_ecosystem_state_defaults() -> None:
    state = EcosystemState()
    assert state.task_queue == []
    assert state.active_agents == []
    assert state.debate_rounds == 0
    assert state.consensus_reached is False
    assert state.consensus_status is ConsensusStatus.PENDING
    assert state.audit_log == []


def test_task_queue_fifo() -> None:
    state = EcosystemState()
    state.enqueue_task("t1")
    state.enqueue_task("t2")
    assert state.dequeue_task() == "t1"
    assert state.dequeue_task() == "t2"
    assert state.dequeue_task() is None
    assert state.task_queue == []


def test_agent_registry() -> None:
    state = EcosystemState()
    state.register_agent("a1")
    state.register_agent("a1")  # idempotent
    assert state.active_agents == ["a1"]
    state.deregister_agent("a1")
    assert state.active_agents == []


def test_debate_round_and_consensus() -> None:
    state = EcosystemState()
    state.increment_debate_round()
    state.increment_debate_round()
    assert state.debate_rounds == 2
    state.set_consensus(True)
    assert state.consensus_reached is True
    assert state.consensus_status is ConsensusStatus.REACHED
    state.set_consensus(False)
    assert state.consensus_reached is False
    assert state.consensus_status is ConsensusStatus.FAILED


def test_audit_log_immutable_entries() -> None:
    state = EcosystemState()
    state.append_audit("debate.completed", round=1, score=0.91)
    assert len(state.audit_log) == 1
    entry = state.audit_log[0]
    assert entry["event"] == "debate.completed"
    assert entry["score"] == 0.91
    assert "timestamp" in entry


def test_roundtrip_to_from_dict() -> None:
    state = EcosystemState()
    state.enqueue_task("t1")
    state.enqueue_task("t2")
    state.register_agent("a1")
    state.increment_debate_round()
    state.set_consensus(True)
    state.append_audit("debate.completed", round=1, score=0.91)

    data = state.to_dict()
    restored = EcosystemState.from_dict(data)

    assert restored.session_id == state.session_id
    assert restored.task_queue == ["t1", "t2"]
    assert restored.active_agents == ["a1"]
    assert restored.debate_rounds == 1
    assert restored.consensus_reached is True
    assert restored.consensus_status is ConsensusStatus.REACHED
    assert len(restored.audit_log) == 1


def test_from_dict_tolerates_bad_status() -> None:
    data = {"consensus_status": "not-a-status"}
    state = EcosystemState.from_dict(data)
    assert state.consensus_status is ConsensusStatus.PENDING
