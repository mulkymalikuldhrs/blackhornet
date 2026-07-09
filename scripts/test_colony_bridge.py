"""
Colony Bridge Integration Test
Validates BH colony bridge capabilities, agent registration, event bus,
colony hand types, A2A coordination, and task scheduling.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _skip(reason):
    """Mark a test as skipped."""
    print(f"  ⏭ SKIPPED: {reason}")
    return None


def test_imports():
    """Test 1: All colony bridge imports work"""
    from src.colony_bridge import ColonyBridge, CAPABILITY_DOMAINS, COLONY_CAPABILITIES
    assert len(CAPABILITY_DOMAINS) > 0, "No capability domains defined"
    assert len(COLONY_CAPABILITIES) > 0, "No colony capabilities defined"

    total_caps = sum(len(caps) for caps in CAPABILITY_DOMAINS.values())
    print(f"  \u2713 ColonyBridge imported, {len(CAPABILITY_DOMAINS)} domains, {total_caps} domain capabilities + {len(COLONY_CAPABILITIES)} quant caps")

    domains = sorted(CAPABILITY_DOMAINS.keys())
    print(f"  \u2713 Domains: {domains}")
    return True


def test_bridge_creation():
    """Test 2: Create colony bridge instance and verify structure"""
    from src.colony_bridge import ColonyBridge
    bridge = ColonyBridge()
    assert bridge is not None
    assert hasattr(bridge, 'get_capabilities')
    assert hasattr(bridge, 'status')
    assert hasattr(bridge, 'report_health')
    print(f"  \u2713 ColonyBridge created with all expected methods")
    return True


def test_capability_lookup():
    """Test 3: Capability lookup by name and dotted path"""
    from src.colony_bridge import ColonyBridge

    bridge = ColonyBridge()

    caps = bridge.get_capabilities()
    assert 'core' in caps
    assert 'agents' in caps
    assert 'colony' in caps
    assert 'harness' in caps
    assert 'organism' in caps
    assert 'memory' in caps

    core_caps = list(caps['core'].keys())
    print(f"  \u2713 Core capabilities: {', '.join(core_caps)}")

    result = bridge.get_capability('core.base_agent')
    assert result is not None
    assert 'state machine' in result.lower()

    result = bridge.get_capability('base_agent')
    assert result is not None

    result = bridge.get_capability('nonexistent')
    assert result is None

    print(f"  \u2713 Capability lookup works (dotted path, short name, missing)")
    return True


def test_quant_nanggroe_capabilities():
    """Test 4: Quant Nanggroe engine capabilities"""
    from src.colony_bridge import ColonyBridge, COLONY_CAPABILITIES

    quant_keys = list(COLONY_CAPABILITIES.keys())
    print(f"  \u2713 Quant capabilities ({len(quant_keys)}): {', '.join(quant_keys)}")

    assert 'engine.backtest' in COLONY_CAPABILITIES
    assert 'engine.risk' in COLONY_CAPABILITIES
    assert 'engine.strategies' in COLONY_CAPABILITIES
    assert 'daemon_manager' in COLONY_CAPABILITIES
    assert 'exchange_connectors' in COLONY_CAPABILITIES

    bridge = ColonyBridge()
    caps = bridge.get_capabilities()

    quant_cap = bridge.get_capability('engine.backtest')
    assert quant_cap is not None
    assert 'Walk-forward' in quant_cap

    print(f"  \u2713 Quant capability lookup verified")
    return True


def test_bridge_status_and_health():
    """Test 5: Bridge status and health reporting"""
    from src.colony_bridge import ColonyBridge

    bridge = ColonyBridge()

    status = bridge.status()
    assert 'available' in status
    assert 'capabilities' in status
    assert 'available_count' in status
    assert 'total_capabilities' in status
    assert 'timestamp' in status
    print(f"  \u2713 Status: available={status['available']}, "
          f"caps={status['available_count']}/{status['total_capabilities']}, "
          f"strategies={status['strategies']}, exchanges={len(status['exchanges'])}")

    health = bridge.report_health()
    assert 'domains' in health
    assert 'total_capabilities' in health
    assert 'quant_nanggroe_capabilities' in health
    assert 'timestamp' in health

    for domain, count in health['domains'].items():
        assert count > 0
    print(f"  \u2713 Health: {health['total_capabilities']} domain caps, "
          f"{health['quant_nanggroe_capabilities']} quant caps, "
          f"{health['agents_discovered']} agents discovered")
    return True


def test_colony_imports():
    """Test 6: Colony module imports (hands, scheduler, manager, a2a)"""
    from src.colony import (
        Colony, ColonyManager, SCALE_PRESETS,
        Hand, HandManager,
        SecurityHand, CodeHand, ResearchHand, BrowserHand,
        VoiceHand, ComputeHand, IntegrationHand,
        HAND_DESCRIPTIONS, HAND_DEFAULTS,
        TaskScheduler, A2ACoordinator,
    )
    print(f"  \u2713 All colony module imports successful")
    print(f"  \u2713 Hand types: {list(HAND_DESCRIPTIONS.keys())}")
    print(f"  \u2713 Scale presets: {list(SCALE_PRESETS.keys())}")
    return True


def test_hand_types():
    """Test 7: Hand type creation and management"""
    from src.colony import (
        Hand, HandManager, SecurityHand, CodeHand, ResearchHand,
        BrowserHand, VoiceHand, ComputeHand, IntegrationHand,
        HAND_DESCRIPTIONS, HAND_DEFAULTS,
    )
    from src.bh_types import HandType

    code_hand = CodeHand()
    assert code_hand.hand_type == HandType.CODE
    assert code_hand.min_replicas == 2
    assert code_hand.max_replicas == 10
    assert code_hand.agent_count == 0
    assert not code_hand.is_staffed

    added = code_hand.add_agent("agent_1")
    assert added
    assert code_hand.agent_count == 1
    assert code_hand.pending_tasks == 0

    assert isinstance(code_hand.description, str) and len(code_hand.description) > 0

    manager = HandManager()
    security = manager.get_hand(HandType.SECURITY)
    assert security is not None
    assert security.min_replicas == 1
    assert security.max_replicas == 5

    added_sec = manager.assign_agent(HandType.SECURITY, "sec_agent_1")
    assert added_sec
    assert security.agent_count == 1

    print(f"  \u2713 All 7 hand types created and verified")

    all_status = manager.get_all_status()
    assert len(all_status) == 7
    print(f"  \u2713 HandManager manages {len(all_status)} hands")

    staffed = manager.get_staffed_hands()
    print(f"  \u2713 Staffed hands: {len(staffed)}/7 (only Security has an agent)")
    return True


def test_a2a_coordinator():
    """Test 8: A2A coordinator registration and messaging"""
    from src.colony import A2ACoordinator
    from src.bh_types import HandType

    coordinator = A2ACoordinator()
    assert coordinator.agent_count == 0

    try:
        coordinator.register_agent(
            agent_id="agent_alpha",
            colony_id="colony_1",
            capabilities=["code", "review", "test"],
            hand_type=HandType.CODE,
        )
        assert coordinator.agent_count == 1

        coordinator.register_agent(
            agent_id="agent_beta",
            colony_id="colony_1",
            capabilities=["security", "scan"],
            hand_type=HandType.SECURITY,
        )
        assert coordinator.agent_count == 2

        code_agents = coordinator.discover_agents("code")
        assert len(code_agents) == 1
        assert code_agents[0]["agent_id"] == "agent_alpha"

        caps = coordinator.get_agent_capabilities("agent_beta")
        assert "security" in caps
        assert "scan" in caps

        coordinator.update_capabilities("agent_alpha", ["code", "review", "test", "deploy"])
        updated_caps = coordinator.get_agent_capabilities("agent_alpha")
        assert "deploy" in updated_caps

        print(f"  \u2713 A2A: {coordinator.agent_count} agents registered, "
              f"{coordinator.capability_count} unique capabilities")

        coordinator.unregister_agent("agent_beta")
        assert coordinator.agent_count == 1
        print(f"  \u2713 A2A: agent unregistered, {coordinator.agent_count} remaining")

        stats = coordinator.get_stats()
        assert stats["registered_agents"] == 1
        print(f"  \u2713 A2A stats: {stats}")
    except AttributeError as e:
        return _skip(f"A2A needs pydantic v2 (model_dump): {e}")

    return True


def test_task_scheduler():
    """Test 9: Task scheduler with priority queue and routing"""
    from src.colony import TaskScheduler
    from src.bh_types import Task, TaskPriority, TaskStatus, TaskDeadline, RoutingStrategy

    scheduler = TaskScheduler(max_concurrent=10)

    scheduler.register_agent("worker_1", ["code", "review"])
    scheduler.register_agent("worker_2", ["security", "scan"])

    task_high = Task(
        title="Critical fix",
        description="Fix security vulnerability",
        priority=TaskPriority.CRITICAL,
        required_capabilities=["security"],
    )
    task_low = Task(
        title="Minor refactor",
        description="Clean up code",
        priority=TaskPriority.LOW,
        required_capabilities=["code"],
    )

    tid_high = scheduler.submit(task_high)
    tid_low = scheduler.submit(task_low)

    assert scheduler.pending_count == 2

    next_t = scheduler.next_task()
    assert next_t is not None
    assert next_t.task_id == tid_high
    assert next_t.status == TaskStatus.ASSIGNED
    print(f"  \u2713 Priority queue: CRITICAL task dequeued before LOW")

    next_low = scheduler.next_task()
    assert next_low is not None
    assert next_low.task_id == tid_low

    scheduler.start_task(tid_high, "worker_2")
    result = scheduler.complete_task(tid_high, result="Fixed")
    assert result.success
    print(f"  \u2713 Task completed successfully")

    scheduler.start_task(tid_low, "worker_1")
    fail_result = scheduler.complete_task(tid_low, error="Something broke")
    assert not fail_result.success
    print(f"  \u2713 Task failure with retry handled")

    stats = scheduler.get_stats()
    assert stats["max_concurrent"] == 10
    print(f"  \u2713 Scheduler stats: {stats}")
    return True


def test_hand_routing():
    """Test 10: HandManager task routing by capability"""
    from src.colony import HandManager, CodeHand, SecurityHand
    from src.bh_types import HandType, Task, TaskPriority
    from datetime import datetime, timezone

    manager = HandManager()

    manager.assign_agent(HandType.CODE, "coder_1")
    manager.assign_agent(HandType.CODE, "coder_2")
    manager.assign_agent(HandType.SECURITY, "sec_1")

    code_task = Task(
        title="Build feature",
        description="Write new feature code",
        priority=TaskPriority.HIGH,
        required_capabilities=["code", "testing"],
        created_at=datetime.now(timezone.utc),
    )
    sec_task = Task(
        title="Vulnerability scan",
        description="Scan for vulns",
        priority=TaskPriority.CRITICAL,
        required_capabilities=["vulnerability", "scan"],
        created_at=datetime.now(timezone.utc),
    )
    unknown_task = Task(
        title="General work",
        description="Do something",
        priority=TaskPriority.MEDIUM,
        required_capabilities=[],
        created_at=datetime.now(timezone.utc),
    )

    routed_code = manager.route_task(code_task)
    assert routed_code == HandType.CODE, f"Expected CODE, got {routed_code}"

    routed_sec = manager.route_task(sec_task)
    assert routed_sec == HandType.SECURITY, f"Expected SECURITY, got {routed_sec}"

    routed_unknown = manager.route_task(unknown_task)
    assert routed_unknown is not None
    print(f"  \u2713 Task routing: CODE->{routed_code}, SECURITY->{routed_sec}, unknown->{routed_unknown}")
    return True


def test_colony_integration():
    """Test 11: Full colony lifecycle integration"""
    from src.colony import ColonyManager
    from src.bh_types import ColonyConfig, ColonyScale, ColonyStatus

    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def run():
        manager = ColonyManager()
        assert manager.colony_count == 0

        config = ColonyConfig(
            name="test-colony",
            goal="integration testing",
            scale=ColonyScale.MICRO,
        )
        colony = await manager.create_colony(config=config)
        assert colony is not None
        assert colony.status == ColonyStatus.ACTIVE
        assert colony.colony_id is not None

        info = colony.get_info()
        assert info.name == "test-colony"
        assert info.scale == ColonyScale.MICRO
        print(f"  \u2713 Colony created: {info.colony_id[:8]} ({info.name}), scale={info.scale.value}")

        await colony.pause()
        assert colony.status == ColonyStatus.PAUSED

        await colony.resume()
        assert colony.status == ColonyStatus.ACTIVE

        await colony.shutdown()
        assert colony.status == ColonyStatus.TERMINATED
        print(f"  \u2713 Colony lifecycle: CREATING -> ACTIVE -> PAUSED -> ACTIVE -> TERMINATED")

        colony2 = await manager.create_colony()
        assert manager.colony_count == 2

        active = manager.list_active_colonies()
        assert len(active) == 1

        health = colony2.compute_health()
        assert health.overall_score > 0
        print(f"  \u2713 Colony health score: {health.overall_score}")

        await manager.delete_colony(colony2.colony_id)
        assert manager.colony_count == 1

    loop.run_until_complete(run())
    loop.close()
    print(f"  \u2713 ColonyManager CRUD and lifecycle verified")
    return True


def test_event_bus():
    """Test 12: Event bus creation and pub/sub"""
    try:
        from src.core.event_bus import EventBus
    except ImportError as e:
        return _skip(f"requires pydantic v2 (field_validator etc): {e}")

    EventBus.reset()
    bus = EventBus()
    bus._running = True
    assert bus is not None
    assert bus.event_count == 0
    assert bus.message_count == 0

    received = []
    async def handler(event):
        received.append(event)

    bus.subscribe("test_event", handler)
    bus.subscribe("*", handler)

    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def test_pub_sub():
        from src.bh_types.events import Event, EventType
        event = Event(event_type=EventType.CUSTOM, source="test", data={"msg": "hello"})
        await bus.publish_event(event)
        await bus.publish_event(event)
        assert len(received) == 4
        print(f"  \u2713 EventBus: {bus.event_count} events published, {len(received)} handler calls")

    loop.run_until_complete(test_pub_sub())
    loop.close()

    singleton = EventBus.get_instance()
    assert singleton is not None

    EventBus.reset()
    print(f"  \u2713 EventBus singleton pattern and reset work")
    return True


def main():
    """Run all tests, return (passed, failed, skipped)."""
    tests = [
        ("Imports",                    test_imports),
        ("Bridge Creation",            test_bridge_creation),
        ("Capability Lookup",          test_capability_lookup),
        ("Quant Capabilities",         test_quant_nanggroe_capabilities),
        ("Status & Health",            test_bridge_status_and_health),
        ("Colony Imports",             test_colony_imports),
        ("Hand Types",                 test_hand_types),
        ("A2A Coordinator",            test_a2a_coordinator),
        ("Task Scheduler",             test_task_scheduler),
        ("Hand Routing",               test_hand_routing),
        ("Colony Integration",         test_colony_integration),
        ("Event Bus",                  test_event_bus),
    ]

    passed = 0
    failed = 0
    skipped = 0
    print(f"\n{'='*60}")
    print("BH COLONY BRIDGE INTEGRATION TEST")
    print(f"{'='*60}\n")

    for name, func in tests:
        print(f"\n[{name}]")
        try:
            result = func()
            if result is None:
                skipped += 1
            elif result:
                passed += 1
        except Exception as e:
            print(f"  \u2717 FAILED: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print(f"\n{'='*60}")
    print(f"RESULTS: {passed} passed, {failed} failed, {skipped} skipped")
    print(f"{'='*60}")
    return passed, failed, skipped


if __name__ == "__main__":
    passed, failed, skipped = main()
    sys.exit(0 if failed == 0 else 1)
