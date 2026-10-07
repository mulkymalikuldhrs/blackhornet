"""Tests for MemoryFederation ecosystem snapshot persistence."""
from src.bh_types.ecosystem import ConsensusStatus, EcosystemState
from src.colony.orchestrator import (
    EcosystemOrchestrator,
    OrchestratorConfig,
)
from src.memory.memory_federation import MemoryFederation


def make_state(rounds: int = 2) -> EcosystemState:
    state = EcosystemState(consensus_status=ConsensusStatus.REACHED)
    for _ in range(rounds):
        state.increment_debate_round()
    state.append_audit("test.event", rounds=rounds)
    return state


def test_snapshot_ecosystem_persists_state():
    fed = MemoryFederation()
    state = make_state()
    result = fed.snapshot_ecosystem(state)

    assert "snapshot_id" in result
    snapshots = fed.get_ecosystem_snapshots()
    assert len(snapshots) == 1
    data = snapshots[0]["data"]
    assert data["session_id"] == state.session_id
    assert data["debate_rounds"] == 2
    assert data["consensus_status"] == "reached"
    assert len(data["audit_log"]) == 1


def test_snapshot_cap_prunes_oldest():
    fed = MemoryFederation()
    for i in range(25):
        state = make_state(rounds=i)
        state.append_audit("cycle", cycle=i)
        fed.snapshot_ecosystem(state, max_snapshots=20)

    snapshots = fed.get_ecosystem_snapshots(limit=100)
    assert len(snapshots) <= 20


def test_get_ecosystem_snapshots_limit():
    fed = MemoryFederation()
    for i in range(5):
        state = make_state(rounds=i)
        state.append_audit("cycle", cycle=i)
        fed.snapshot_ecosystem(state)

    assert len(fed.get_ecosystem_snapshots(limit=3)) == 3


def test_snapshots_are_federated_memories():
    fed = MemoryFederation()
    fed.snapshot_ecosystem(make_state())

    by_type = fed.get_memories_by_type("ecosystem_snapshot")
    assert len(by_type) == 1
    assert "ecosystem" in by_type[0].tags


def test_get_stats_reports_snapshot_count():
    fed = MemoryFederation()
    fed.snapshot_ecosystem(make_state())
    assert fed.get_stats()["ecosystem_snapshots"] == 1


def test_roundtrip_via_from_dict():
    fed = MemoryFederation()
    state = make_state()
    fed.snapshot_ecosystem(state)
    snapshot = fed.get_ecosystem_snapshots(limit=1)[0]["data"]

    restored = EcosystemState.from_dict(snapshot)
    assert restored.session_id == state.session_id
    assert restored.debate_rounds == state.debate_rounds


def test_sync_from_carries_snapshots():
    fed_a = MemoryFederation()
    fed_b = MemoryFederation()
    fed_a.snapshot_ecosystem(make_state())

    events = fed_b.sync_from(fed_a)
    assert fed_b.get_memories_by_type("ecosystem_snapshot")
    assert any(e.action == "share" for e in events)


class _StubMemory:
    def __init__(self):
        self.calls = []

    def snapshot_ecosystem(self, state):
        self.calls.append(state)


class _BrokenMemory:
    def snapshot_ecosystem(self, state):
        raise RuntimeError("boom")


def _new_orchestrator() -> EcosystemOrchestrator:
    return EcosystemOrchestrator(OrchestratorConfig(colony_id="smoke"))


def test_orchestrator_feeds_snapshot():
    orch = _new_orchestrator()
    stub = _StubMemory()
    orch._memory_system = stub

    orch._feed_ecosystem_snapshot()

    assert len(stub.calls) == 1
    assert stub.calls[0] is orch._ecosystem_state


def test_orchestrator_feed_skips_missing_method():
    orch = _new_orchestrator()
    orch._memory_system = object()  # no snapshot_ecosystem attr
    orch._feed_ecosystem_snapshot()  # must not raise


def test_orchestrator_feed_swallows_errors():
    orch = _new_orchestrator()
    orch._memory_system = _BrokenMemory()
    orch._feed_ecosystem_snapshot()  # must not raise


def test_orchestrator_feed_skips_without_memory_system():
    orch = _new_orchestrator()
    orch._memory_system = None
    orch._feed_ecosystem_snapshot()  # must not raise
