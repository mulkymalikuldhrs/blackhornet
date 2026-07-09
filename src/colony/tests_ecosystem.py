"""Tests for Colony Ecosystem: Radar, MeshBus, SelfNest."""

from __future__ import annotations

import asyncio
import os
import sys
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


class TestColonyEcosystemTypes(unittest.TestCase):
    """Type definitions from colony_ecosystem.py."""

    def test_radar_discovery_method_enum(self):
        from src.colony_types.colony_ecosystem import RadarDiscoveryMethod
        vals = [m.value for m in RadarDiscoveryMethod]
        self.assertIn("lan_broadcast", vals)
        self.assertIn("dht", vals)
        self.assertIn("rendezvous", vals)
        self.assertIn("static_peer", vals)

    def test_radar_signal_type_enum(self):
        from src.colony_types.colony_ecosystem import RadarSignalType
        self.assertEqual(RadarSignalType.ANNOUNCE.value, "announce")
        self.assertEqual(RadarSignalType.PING.value, "ping")
        self.assertEqual(RadarSignalType.PONG.value, "pong")
        self.assertEqual(RadarSignalType.BYE.value, "bye")

    def test_colony_identity_defaults(self):
        from src.colony_types.colony_ecosystem import ColonyIdentity
        identity = ColonyIdentity(name="test-colony")
        self.assertEqual(identity.name, "test-colony")
        self.assertTrue(identity.colony_id)
        self.assertTrue(identity.instance_id)
        self.assertGreater(identity.first_seen, 0)

    def test_radar_signal_serialization(self):
        from src.colony_types._pydantic_compat import model_dump, model_validate
        from src.colony_types.colony_ecosystem import ColonyIdentity, RadarSignal, RadarSignalType
        identity = ColonyIdentity(name="sender")
        signal = RadarSignal(
            signal_type=RadarSignalType.ANNOUNCE,
            sender=identity,
            payload={"msg": "hello"},
        )
        data = model_dump(signal)
        restored = model_validate(RadarSignal, data)
        self.assertEqual(restored.signal_type.value, "announce")
        self.assertEqual(restored.payload["msg"], "hello")
        self.assertEqual(restored.sender.name, "sender")

    def test_mesh_message_defaults(self):
        from src.colony_types.colony_ecosystem import MeshMessage
        msg = MeshMessage(topic="test", sender_id="agent-1", sender_colony="colony-1")
        self.assertEqual(msg.topic, "test")
        self.assertEqual(msg.hop_count, 0)
        self.assertEqual(msg.max_hops, 5)
        self.assertEqual(msg.priority, 5)

    def test_nest_config_defaults(self):
        from src.colony_types.colony_ecosystem import NestConfig
        config = NestConfig(name="test-nest")
        self.assertEqual(config.name, "test-nest")
        self.assertEqual(config.auto_restart, True)
        self.assertEqual(config.health_check_interval, 30)
        self.assertIn("python3", config.dependencies)

    def test_nest_status_report(self):
        from src.colony_types.colony_ecosystem import NestStatusReport
        report = NestStatusReport(nest_id="n1", name="test", status="running")
        self.assertEqual(report.status, "running")
        self.assertEqual(report.restart_count, 0)
        self.assertEqual(report.peers_connected, 0)


class TestRadarProtocol(unittest.TestCase):
    """ColonyRadar — discovery protocol tests."""

    def test_radar_init(self):
        from src.colony.radar import ColonyRadar, RadarConfig
        from src.colony_types.colony_ecosystem import ColonyIdentity
        identity = ColonyIdentity(name="test-radar")
        config = RadarConfig(identity=identity)
        radar = ColonyRadar(config)
        self.assertEqual(radar.peer_count, 0)

    def test_radar_get_peers_empty(self):
        from src.colony.radar import ColonyRadar, RadarConfig
        from src.colony_types.colony_ecosystem import ColonyIdentity
        radar = ColonyRadar(RadarConfig(identity=ColonyIdentity(name="empty")))
        self.assertEqual(radar.get_peers(), [])

    def test_radar_static_peers_config(self):
        from src.colony.radar import RadarConfig
        from src.colony_types.colony_ecosystem import ColonyIdentity, RadarDiscoveryMethod
        config = RadarConfig(
            identity=ColonyIdentity(name="static-test"),
            discovery_methods=[RadarDiscoveryMethod.STATIC_PEER],
            static_peers=["http://peer1:8080", "http://peer2:8080"],
        )
        self.assertEqual(len(config.static_peers), 2)

    def test_radar_rendezvous_config(self):
        from src.colony.radar import RadarConfig
        from src.colony_types.colony_ecosystem import ColonyIdentity, RadarDiscoveryMethod
        config = RadarConfig(
            identity=ColonyIdentity(name="rendezvous-test"),
            discovery_methods=[RadarDiscoveryMethod.RENDEZVOUS],
            rendezvous_url="http://rendezvous:3117",
        )
        self.assertEqual(config.rendezvous_url, "http://rendezvous:3117")

    def test_radar_stats(self):
        from src.colony.radar import ColonyRadar, RadarConfig
        from src.colony_types.colony_ecosystem import ColonyIdentity
        radar = ColonyRadar(RadarConfig(identity=ColonyIdentity(name="stats")))
        stats = radar.get_stats()
        self.assertIn("running", stats)
        self.assertIn("peers", stats)
        self.assertIn("methods", stats)
        self.assertFalse(stats["running"])

    def test_peer_join_leave_callbacks(self):
        from src.colony.radar import ColonyRadar, RadarConfig
        from src.colony_types.colony_ecosystem import ColonyIdentity
        radar = ColonyRadar(RadarConfig(identity=ColonyIdentity(name="cb")))
        self.assertIsNone(radar._on_peer_join)
        self.assertIsNone(radar._on_peer_leave)
        calls = []

        def on_join(peer):
            calls.append(("join", peer.name))

        def on_leave(peer):
            calls.append(("leave", peer.name))

        radar.on_peer_join(on_join)
        radar.on_peer_leave(on_leave)
        self.assertIsNotNone(radar._on_peer_join)
        self.assertIsNotNone(radar._on_peer_leave)

    def test_radar_multicast_group_default(self):
        from src.colony.radar import MULTICAST_GROUP, MULTICAST_PORT
        self.assertEqual(MULTICAST_GROUP, "239.255.43.21")
        self.assertEqual(MULTICAST_PORT, 43210)


class TestMeshBus(unittest.TestCase):
    """MeshBus — cross-colony messaging tests."""

    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()

    def _make_bus(self):
        from src.core.event_bus import EventBus
        from src.colony_types.colony_ecosystem import ColonyIdentity
        from src.colony.mesh_bus import MeshBus
        eb = EventBus.get_instance()
        eb.reset()
        eb = EventBus()
        identity = ColonyIdentity(name="mesh-test")
        return MeshBus(eb, identity), eb

    def test_mesh_bus_init(self):
        bus, eb = self._make_bus()
        self.assertFalse(bus._running)
        self.assertEqual(bus.message_count, 0)
        self.assertEqual(bus.peer_count, 0)

    def test_mesh_bus_subscribe(self):
        bus, eb = self._make_bus()
        received = []

        def handler(msg):
            received.append(msg.topic)

        bus.on("test-topic", handler)
        self.assertIn("test-topic", bus._subscribers)
        self.assertEqual(len(bus._subscribers["test-topic"]), 1)

    def test_mesh_bus_unsubscribe(self):
        bus, eb = self._make_bus()

        def handler(msg):
            pass

        bus.on("test", handler)
        bus.off("test", handler)
        self.assertEqual(len(bus._subscribers["test"]), 0)

    def test_mesh_bus_wildcard_subscriber(self):
        bus, eb = self._make_bus()
        received = []

        def handler(msg):
            received.append(msg.topic)

        bus.on("*", handler)
        msg_id = self.loop.run_until_complete(
            bus.publish("any-topic", {"data": 1})
        )
        self.assertTrue(msg_id)
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0], "any-topic")

    def test_mesh_bus_publish_local(self):
        bus, eb = self._make_bus()
        received = []

        def handler(msg):
            received.append(msg.payload)

        bus.on("greeting", handler)
        self.loop.run_until_complete(
            bus.publish("greeting", {"hello": "world"})
        )
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0]["hello"], "world")

    def test_mesh_bus_deduplication(self):
        bus, eb = self._make_bus()

        result = self.loop.run_until_complete(
            bus.receive_message({
                "message_id": "dup-1",
                "topic": "test",
                "sender_id": "a1",
                "sender_colony": "c1",
                "payload": {},
            })
        )
        self.assertEqual(result["status"], "delivered")

        result2 = self.loop.run_until_complete(
            bus.receive_message({
                "message_id": "dup-1",
                "topic": "test",
                "sender_id": "a1",
                "sender_colony": "c1",
                "payload": {},
            })
        )
        self.assertEqual(result2["status"], "duplicate")

    def test_mesh_bus_message_count(self):
        bus, eb = self._make_bus()
        self.assertEqual(bus.message_count, 0)
        self.loop.run_until_complete(bus.publish("t1", {"n": 1}))
        self.loop.run_until_complete(bus.publish("t2", {"n": 2}))
        self.assertEqual(bus.message_count, 2)

    def test_mesh_bus_update_peers(self):
        bus, eb = self._make_bus()
        from src.colony_types.colony_ecosystem import ColonyIdentity
        peer = ColonyIdentity(name="remote-colony", host="10.0.0.5", port=9090)
        bus.update_peers([peer])
        self.assertEqual(bus.peer_count, 1)

    def test_mesh_bus_reply(self):
        bus, eb = self._make_bus()
        from src.colony_types.colony_ecosystem import MeshMessage
        original = MeshMessage(
            topic="query",
            sender_id="requester",
            sender_colony="colony-a",
            correlation_id="corr-1",
        )
        received = []

        def handler(msg):
            received.append(msg.correlation_id)

        bus.on("query.response", handler)
        self.loop.run_until_complete(bus.reply(original, {"answer": 42}))
        self.assertIn("corr-1", received)

    def test_mesh_bus_hop_limit(self):
        bus, eb = self._make_bus()
        from src.colony_types.colony_ecosystem import ColonyIdentity
        bus.update_peers([
            ColonyIdentity(name="far-peer", host="10.0.0.1", port=8080)
        ])

        msg = self.loop.run_until_complete(
            bus.publish("broadcast", {"hop_test": True})
        )
        self.assertTrue(msg)

    def test_mesh_bus_stats(self):
        bus, eb = self._make_bus()
        stats = bus.get_stats()
        self.assertIn("running", stats)
        self.assertIn("peers", stats)
        self.assertIn("messages_sent", stats)

    def test_mesh_bus_request_timeout(self):
        bus, eb = self._make_bus()
        from src.colony_types.colony_ecosystem import ColonyIdentity
        bus.update_peers([
            ColonyIdentity(name="silent-peer", host="10.0.0.9", port=9999)
        ])

        result = self.loop.run_until_complete(
            bus.request("no-response", {}, target_colony="ghost", timeout=0.5)
        )
        self.assertIsNone(result)


class TestSelfNest(unittest.TestCase):
    """SelfNest — autonomous bootstrap and health tests."""

    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()

    def _make_nest(self, **kwargs):
        from src.colony.nest import SelfNest, NestConfig
        config = NestConfig(name="test-nest", **kwargs)
        return SelfNest(config)

    def test_nest_init(self):
        nest = self._make_nest()
        self.assertFalse(nest._running)
        self.assertEqual(nest.uptime, 0.0)
        self.assertEqual(nest._config.name, "test-nest")

    def test_nest_bootstrap_creates_directories(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            from src.colony.nest import SelfNest, NestConfig
            config = NestConfig(
                name="bootstrap-test",
                data_dir=os.path.join(tmp, "data"),
                log_dir=os.path.join(tmp, "logs"),
            )
            nest = SelfNest(config)
            self.loop.run_until_complete(nest.bootstrap())
            self.assertTrue(os.path.exists(os.path.join(tmp, "data")))
            self.assertTrue(os.path.exists(os.path.join(tmp, "logs")))

    def test_nest_start_stop(self):
        nest = self._make_nest()
        self.loop.run_until_complete(nest.start())
        self.assertTrue(nest._running)
        self.assertGreater(nest.uptime, 0)

        self.loop.run_until_complete(nest.shutdown())
        self.assertFalse(nest._running)

    def test_nest_components_registered_on_start(self):
        nest = self._make_nest()
        self.loop.run_until_complete(nest.start())
        self.assertIn("nest-core", nest._components)
        self.assertIn("health-monitor", nest._components)
        self.assertIn("supervisor", nest._components)
        self.loop.run_until_complete(nest.shutdown())

    def test_nest_register_component(self):
        nest = self._make_nest()
        self.loop.run_until_complete(nest.register_component_async("test-service"))
        self.assertIn("test-service", nest._components)
        self.assertEqual(nest._components["test-service"].status, "stopped")

    def test_nest_health_report(self):
        nest = self._make_nest()
        self.loop.run_until_complete(nest.start())
        report = self.loop.run_until_complete(nest.health_report())
        self.assertEqual(report.nest_id, nest._config.nest_id)
        self.assertEqual(report.name, "test-nest")
        self.assertIn(report.status, ("running", "stopped"))
        self.assertGreaterEqual(report.cpu_pct, 0.0)
        self.assertGreaterEqual(report.memory_mb, 0.0)
        self.assertGreaterEqual(report.disk_pct, 0.0)
        self.loop.run_until_complete(nest.shutdown())

    def test_nest_health_report_without_start(self):
        nest = self._make_nest()
        report = self.loop.run_until_complete(nest.health_report())
        self.assertEqual(report.status, "stopped")
        self.assertEqual(report.uptime, 0.0)

    def test_nest_restart_component(self):
        nest = self._make_nest()
        self.loop.run_until_complete(nest.start())
        self.loop.run_until_complete(nest.register_component_async("worker"))

        success = self.loop.run_until_complete(nest.restart_component("worker"))
        self.assertTrue(success)
        self.assertEqual(nest._components["worker"].restart_count, 1)
        self.loop.run_until_complete(nest.shutdown())

    def test_nest_restart_nonexistent_component(self):
        nest = self._make_nest()
        success = self.loop.run_until_complete(nest.restart_component("ghost"))
        self.assertFalse(success)

    def test_nest_stats(self):
        nest = self._make_nest()
        self.loop.run_until_complete(nest.start())
        stats = nest.get_stats()
        self.assertIn("running", stats)
        self.assertIn("uptime", stats)
        self.assertIn("components", stats)
        self.assertIn("config", stats)
        self.assertTrue(stats["running"])
        self.loop.run_until_complete(nest.shutdown())

    def test_nest_callbacks(self):
        nest = self._make_nest()
        health_changes = []
        crashes = []

        def on_health(report):
            health_changes.append(report.status)

        def on_crash(name):
            crashes.append(name)

        nest.on_health_change(on_health)
        nest.on_crash(on_crash)

        self.loop.run_until_complete(nest.start())
        self.loop.run_until_complete(nest.shutdown())

    def test_nest_double_start(self):
        nest = self._make_nest()
        self.loop.run_until_complete(nest.start())
        self.loop.run_until_complete(nest.start())
        self.assertTrue(nest._running)
        self.loop.run_until_complete(nest.shutdown())

    def test_nest_config_defaults(self):
        nest = self._make_nest(max_restarts_per_hour=5, cooldown_seconds=120)
        self.assertEqual(nest._config.max_restarts_per_hour, 5)
        self.assertEqual(nest._config.cooldown_seconds, 120)


class TestRadarAsync(unittest.TestCase):
    """Async tests for ColonyRadar start/stop."""

    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()

    def test_radar_start_stop(self):
        from src.colony.radar import ColonyRadar, RadarConfig
        from src.colony_types.colony_ecosystem import ColonyIdentity
        from src.colony_types.colony_ecosystem import RadarDiscoveryMethod
        identity = ColonyIdentity(name="async-radar")
        config = RadarConfig(
            identity=identity,
            discovery_methods=[RadarDiscoveryMethod.LAN_BROADCAST],
            announce_interval=9999,
        )
        radar = ColonyRadar(config)
        self.loop.run_until_complete(radar.start())
        self.assertTrue(radar._running)
        self.loop.run_until_complete(radar.stop())
        self.assertFalse(radar._running)

    def test_radar_static_peers_connect(self):
        from src.colony.radar import ColonyRadar, RadarConfig
        from src.colony_types.colony_ecosystem import ColonyIdentity, RadarDiscoveryMethod
        identity = ColonyIdentity(name="static-radar")
        config = RadarConfig(
            identity=identity,
            discovery_methods=[RadarDiscoveryMethod.STATIC_PEER],
            static_peers=["http://nonexistent:9999"],
        )
        radar = ColonyRadar(config)
        self.loop.run_until_complete(radar.start())
        self.assertTrue(radar._running)
        self.loop.run_until_complete(radar.stop())


class TestMeshBusAsyncStartStop(unittest.TestCase):
    """Async start/stop for MeshBus."""

    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()

    def test_mesh_bus_start_stop(self):
        from src.core.event_bus import EventBus
        from src.colony_types.colony_ecosystem import ColonyIdentity
        from src.colony.mesh_bus import MeshBus
        eb = EventBus()
        identity = ColonyIdentity(name="async-mesh")
        bus = MeshBus(eb, identity)
        self.loop.run_until_complete(bus.start())
        self.assertTrue(bus._running)

        self.loop.run_until_complete(bus.stop())
        self.assertFalse(bus._running)

    def test_mesh_bus_delivery_after_start(self):
        from src.core.event_bus import EventBus
        from src.colony_types.colony_ecosystem import ColonyIdentity
        from src.colony.mesh_bus import MeshBus
        eb = EventBus()
        identity = ColonyIdentity(name="delivery-test")
        bus = MeshBus(eb, identity)
        received = []

        def handler(msg):
            received.append(msg.payload.get("value"))

        bus.on("numbers", handler)
        self.loop.run_until_complete(bus.start())
        self.loop.run_until_complete(bus.publish("numbers", {"value": 42}))
        self.assertIn(42, received)
        self.loop.run_until_complete(bus.stop())


class TestEcosystemOrchestrator(unittest.TestCase):
    """EcosystemOrchestrator — control center tests."""

    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()

    def _make_orch(self, **kwargs):
        from src.colony.orchestrator import EcosystemOrchestrator, OrchestratorConfig
        config = OrchestratorConfig(
            colony_id="test-colony",
            colony_name="test-orch",
            **kwargs,
        )
        return EcosystemOrchestrator(config)

    def test_orch_init(self):
        orch = self._make_orch()
        self.assertFalse(orch._running)
        self.assertEqual(orch._config.colony_name, "test-orch")
        self.assertEqual(orch.uptime, 0.0)

    def test_orch_wire(self):
        orch = self._make_orch()
        self.assertIsNone(orch._radar)
        orch.wire(radar="mock-radar", mesh="mock-mesh")
        self.assertEqual(orch._radar, "mock-radar")
        self.assertEqual(orch._mesh_bus, "mock-mesh")

    def test_orch_start_stop(self):
        orch = self._make_orch(auto_sync_docs=False, auto_export_sessions=False)
        self.loop.run_until_complete(orch.start())
        self.assertTrue(orch._running)
        self.assertGreater(orch.uptime, 0)
        self.loop.run_until_complete(orch.stop())
        self.assertFalse(orch._running)

    def test_orch_full_status_without_wiring(self):
        orch = self._make_orch()
        status = self.loop.run_until_complete(orch.full_status())
        self.assertIn("orchestrator", status)
        self.assertIn("radar", status)
        self.assertIn("mesh", status)
        self.assertIn("nest", status)
        self.assertEqual(status["radar"], {})
        self.assertEqual(status["nest"], {})

    def test_orch_full_status_after_start(self):
        orch = self._make_orch(auto_sync_docs=False, auto_export_sessions=False)
        self.loop.run_until_complete(orch.start())
        status = self.loop.run_until_complete(orch.full_status())
        self.assertEqual(status["orchestrator"]["colony_name"], "test-orch")
        self.assertTrue(status["orchestrator"]["uptime"] > 0)
        self.loop.run_until_complete(orch.stop())

    def test_orch_stats(self):
        orch = self._make_orch()
        stats = orch.get_stats()
        self.assertIn("running", stats)
        self.assertIn("colony", stats)
        self.assertIn("components", stats)
        self.assertFalse(stats["running"])

    def test_orch_stats_after_start(self):
        orch = self._make_orch(auto_sync_docs=False, auto_export_sessions=False)
        self.loop.run_until_complete(orch.start())
        stats = orch.get_stats()
        self.assertTrue(stats["running"])
        self.assertEqual(stats["colony"], "test-orch")
        self.loop.run_until_complete(orch.stop())

    def test_orch_status_cache(self):
        orch = self._make_orch()
        self.assertEqual(orch.get_status_cache(), {})
        self.loop.run_until_complete(orch.full_status())
        cache = orch.get_status_cache()
        self.assertIn("orchestrator", cache)

    def test_orch_doc_section_generation(self):
        orch = self._make_orch()
        section = orch._generate_agents_section(agent_count=5, peer_count=3, colony_count=1, uptime=3600)
        self.assertIn("Agents**: 5", section)
        self.assertIn("Peers (Radar)**: 3", section)
        self.assertIn("Colonies**: 1", section)

    def test_orch_soul_section_generation(self):
        orch = self._make_orch()
        status = {
            "orchestrator": {
                "colony_name": "queen",
                "version": "5.0.0",
                "running": True,
                "uptime": 7200,
            },
            "radar": {"peer_count": 7},
            "nest": {
                "components": {"core": "running", "worker": "running", "monitor": "error"},
            },
        }
        section = orch._generate_soul_section(status)
        self.assertIn("queen", section)
        self.assertIn("2/3 healthy", section)
        self.assertIn("Peers discovered: 7", section)


class TestLifecycleRecorder(unittest.TestCase):
    """LifecycleRecorder — colony awareness tests."""

    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()

    def _make_recorder(self, **kwargs):
        from src.colony.lifecycle import LifecycleRecorder
        return LifecycleRecorder(colony_id="test-colony", **kwargs)

    def test_recorder_init(self):
        rec = self._make_recorder()
        self.assertEqual(rec._colony_id, "test-colony")
        self.assertEqual(rec.total_events, 0)
        self.assertIsNone(rec.session_id)

    def test_recorder_start(self):
        rec = self._make_recorder()
        self.loop.run_until_complete(rec.start())
        self.assertIsNotNone(rec.session_id)
        self.assertEqual(rec.total_events, 1)
        self.assertEqual(rec._boot_count, 1)
        self.loop.run_until_complete(rec.stop())

    def test_recorder_record_event(self):
        rec = self._make_recorder()
        self.loop.run_until_complete(rec.start())
        event = self.loop.run_until_complete(
            rec.record("task_completed", {"task_id": "t1"})
        )
        self.assertEqual(event["event_type"], "task_completed")
        self.assertEqual(event["data"]["task_id"], "t1")
        self.assertEqual(rec.total_events, 2)
        self.loop.run_until_complete(rec.stop())

    def test_recorder_event_type_counts(self):
        rec = self._make_recorder()
        self.loop.run_until_complete(rec.start())
        self.loop.run_until_complete(rec.record("boot", {}))
        self.loop.run_until_complete(rec.record("task_completed", {}))
        self.loop.run_until_complete(rec.record("task_failed", {}))
        summary = self.loop.run_until_complete(rec.get_summary())
        self.assertEqual(summary["event_counts"]["boot"], 2)  # start() records boot + manual boot
        self.assertEqual(summary["event_counts"]["task_completed"], 1)
        self.assertEqual(summary["event_counts"]["task_failed"], 1)
        self.loop.run_until_complete(rec.stop())

    def test_recorder_record_task(self):
        rec = self._make_recorder()
        self.loop.run_until_complete(rec.start())
        ev = self.loop.run_until_complete(
            rec.record_task(task_id="t1", task_type="analysis", status="completed")
        )
        self.assertEqual(ev["data"]["task_id"], "t1")
        self.assertEqual(ev["data"]["status"], "completed")
        self.loop.run_until_complete(rec.stop())

    def test_recorder_record_error(self):
        rec = self._make_recorder()
        self.loop.run_until_complete(rec.start())
        ev = self.loop.run_until_complete(
            rec.record_error(error_type="timeout", message="Agent took too long")
        )
        self.assertEqual(ev["event_type"], "error")
        self.assertEqual(ev["data"]["error_type"], "timeout")
        self.loop.run_until_complete(rec.stop())

    def test_recorder_record_milestone(self):
        rec = self._make_recorder()
        self.loop.run_until_complete(rec.start())
        ev = self.loop.run_until_complete(
            rec.record_milestone(name="first_deploy", description="First autonomous deployment")
        )
        self.assertEqual(ev["data"]["milestone"], "first_deploy")
        self.loop.run_until_complete(rec.stop())

    def test_recorder_get_history(self):
        rec = self._make_recorder()
        self.loop.run_until_complete(rec.start())
        self.loop.run_until_complete(rec.record("task_completed", {"id": "t1"}))
        self.loop.run_until_complete(rec.record("task_completed", {"id": "t2"}))
        history = self.loop.run_until_complete(
            rec.get_history(event_type="task_completed", limit=10)
        )
        self.assertGreaterEqual(len(history), 2)
        self.loop.run_until_complete(rec.stop())

    def test_recorder_get_history_filter_source(self):
        rec = self._make_recorder()
        self.loop.run_until_complete(rec.start())
        self.loop.run_until_complete(rec.record("boot", {}, source="test"))
        history = self.loop.run_until_complete(
            rec.get_history(source="test", limit=10)
        )
        self.assertGreaterEqual(len(history), 1)
        for ev in history:
            self.assertEqual(ev["source"], "test")
        self.loop.run_until_complete(rec.stop())

    def test_recorder_get_recent_activity(self):
        rec = self._make_recorder()
        self.loop.run_until_complete(rec.start())
        self.loop.run_until_complete(rec.record("test", {"n": 1}))
        recent = self.loop.run_until_complete(rec.get_recent_activity(seconds=3600))
        self.assertGreater(len(recent), 1)
        self.loop.run_until_complete(rec.stop())

    def test_recorder_get_errors(self):
        rec = self._make_recorder()
        self.loop.run_until_complete(rec.start())
        self.loop.run_until_complete(rec.record("error", {"msg": "err1"}))
        self.loop.run_until_complete(rec.record("error", {"msg": "err2"}))
        errors = self.loop.run_until_complete(rec.get_errors(limit=10))
        self.assertGreaterEqual(len(errors), 2)
        self.loop.run_until_complete(rec.stop())

    def test_recorder_get_milestones(self):
        rec = self._make_recorder()
        self.loop.run_until_complete(rec.start())
        self.loop.run_until_complete(rec.record_milestone("m1", "first"))
        self.loop.run_until_complete(rec.record_milestone("m2", "second"))
        milestones = self.loop.run_until_complete(rec.get_milestones())
        self.assertGreaterEqual(len(milestones), 2)
        self.loop.run_until_complete(rec.stop())

    def test_recorder_double_start(self):
        rec = self._make_recorder()
        self.loop.run_until_complete(rec.start())
        self.loop.run_until_complete(rec.start())
        self.assertEqual(rec._boot_count, 1)
        self.loop.run_until_complete(rec.stop())

    def test_recorder_max_events(self):
        rec = self._make_recorder(max_events=5)
        self.loop.run_until_complete(rec.start())
        for i in range(10):
            self.loop.run_until_complete(rec.record("test", {"i": i}))
        self.assertLessEqual(rec.total_events, 6)  # 1 boot + 10 test, capped at 5+1
        self.loop.run_until_complete(rec.stop())

    def test_recorder_stats(self):
        rec = self._make_recorder()
        self.loop.run_until_complete(rec.start())
        stats = rec.get_stats()
        self.assertIn("colony_id", stats)
        self.assertIn("total_events", stats)
        self.assertIn("event_counts", stats)
        self.assertEqual(stats["colony_id"], "test-colony")
        self.loop.run_until_complete(rec.stop())

    def test_recorder_agent_event(self):
        rec = self._make_recorder()
        self.loop.run_until_complete(rec.start())
        ev = self.loop.run_until_complete(
            rec.record_agent_event(agent_id="agent-1", agent_type="coder", event="spawn")
        )
        self.assertEqual(ev["event_type"], "agent_spawn")
        self.assertEqual(ev["data"]["agent_id"], "agent-1")
        self.loop.run_until_complete(rec.stop())

    def test_recorder_shutdown_records_event(self):
        rec = self._make_recorder()
        self.loop.run_until_complete(rec.start())
        self.loop.run_until_complete(rec.stop())
        self.assertGreaterEqual(rec.total_events, 2)  # boot + shutdown


class TestGraphifySyncBridge(unittest.TestCase):
    """GraphifySyncBridge — colony-to-graph sync tests."""

    def setUp(self):
        import tempfile
        import shutil
        from src.graph.graph_store import GraphStore
        from src.colony.graph_sync import GraphifySyncBridge
        self.temp = tempfile.mkdtemp()
        self.gs = GraphStore(db_path=os.path.join(self.temp, "graph.db"))
        self.bridge = GraphifySyncBridge(self.gs)

    def tearDown(self):
        import shutil
        self.gs.close()
        shutil.rmtree(self.temp, ignore_errors=True)

    def test_bridge_init(self):
        self.assertEqual(self.bridge.sync_report["agents_synced"], 0)
        self.assertEqual(self.bridge.sync_report["edges_created"], 0)

    def test_sync_agent_creates_node(self):
        self.bridge.sync_agent(agent_id="test-agent", name="Test Agent", status="active")
        node = self.gs.find_node("agent:test-agent")
        self.assertIsNotNone(node)
        self.assertEqual(node.node_type, "agent")
        self.assertEqual(node.properties["name"], "Test Agent")
        self.assertEqual(node.properties["status"], "active")

    def test_sync_agent_updates_properties(self):
        self.bridge.sync_agent(agent_id="upd-agent", health=0.5)
        self.bridge.sync_agent(agent_id="upd-agent", health=0.9)
        node = self.gs.find_node("agent:upd-agent")
        self.assertEqual(node.properties["health"], 0.9)

    def test_sync_agent_with_colony(self):
        self.bridge.sync_agent(agent_id="a1", colony="col-alpha")
        agent_node = self.gs.find_node("agent:a1")
        colony_node = self.gs.find_node("colony:col-alpha")
        self.assertIsNotNone(agent_node)
        self.assertIsNotNone(colony_node)
        self.assertEqual(colony_node.node_type, "colony")
        edges = self.gs.get_edges(agent_node.id)
        edge_relations = [e.relation for e in edges]
        self.assertIn("member_of", edge_relations)

    def test_sync_agent_with_capabilities(self):
        self.bridge.sync_agent(agent_id="cap-agent", capabilities=["code", "test"])
        node = self.gs.find_node("agent:cap-agent")
        self.assertEqual(node.properties["capabilities"], ["code", "test"])

    def test_sync_colony(self):
        self.bridge.sync_colony(colony_id="col-test", name="Test Colony", health=0.85, agent_count=3)
        node = self.gs.find_node("colony:col-test")
        self.assertIsNotNone(node)
        self.assertEqual(node.properties["health"], 0.85)
        self.assertEqual(node.properties["agent_count"], 3)

    def test_sync_colony_merges(self):
        self.bridge.sync_colony("col-merge", health=0.5)
        self.bridge.sync_colony("col-merge", health=0.95)
        node = self.gs.find_node("colony:col-merge")
        self.assertEqual(node.properties["health"], 0.95)

    def test_sync_agents_batch(self):
        agents = [
            {"agent_id": "a1", "name": "Agent 1", "status": "active"},
            {"agent_id": "a2", "name": "Agent 2", "status": "idle"},
        ]
        self.bridge.sync_agents_batch(agents)
        self.assertEqual(self.bridge.sync_report["agents_synced"], 2)
        self.assertIsNotNone(self.gs.find_node("agent:a1"))
        self.assertIsNotNone(self.gs.find_node("agent:a2"))

    def test_sync_colonies_batch(self):
        colonies = [
            {"colony_id": "c1", "name": "Colony 1"},
            {"colony_id": "c2", "name": "Colony 2"},
        ]
        self.bridge.sync_colonies_batch(colonies)
        self.assertEqual(self.bridge.sync_report["colonies_synced"], 2)

    def test_sync_lifecycle_event(self):
        event = {
            "id": "evt-001",
            "event_type": "agent_spawn",
            "source": "system",
            "colony_id": "col-test",
            "data": {"agent_id": "a1"},
            "timestamp": 1000.0,
        }
        self.bridge.sync_lifecycle_event(event)
        event_node = self.gs.find_node("event:agent_spawn:evt-001")
        self.assertIsNotNone(event_node)
        self.assertEqual(event_node.properties["event_type"], "agent_spawn")

    def test_sync_lifecycle_event_creates_edges(self):
        self.bridge.sync_agent(agent_id="a1")
        self.bridge.sync_colony(colony_id="col-test")
        event = {
            "id": "evt-002",
            "event_type": "task_completed",
            "colony_id": "col-test",
            "data": {"agent_id": "a1"},
        }
        self.bridge.sync_lifecycle_event(event)
        event_node = self.gs.find_node("event:task_completed:evt-002")
        edges = self.gs.get_edges(event_node.id)
        relations = [e.relation for e in edges]
        self.assertIn("occurred_in", relations)
        self.assertIn("involves", relations)

    def test_sync_no_graph_store(self):
        from src.colony.graph_sync import GraphifySyncBridge
        bridge = GraphifySyncBridge(None)
        bridge.sync_agent("a1")
        self.assertEqual(bridge.sync_report["agents_synced"], 1)

    def test_reset_counts(self):
        self.bridge.sync_agent("a1")
        self.assertGreater(self.bridge.sync_report["agents_synced"], 0)
        self.bridge.reset_counts()
        self.assertEqual(self.bridge.sync_report["agents_synced"], 0)


class TestSessionExporter(unittest.TestCase):
    """SessionExporter — session + memory export tests."""

    def setUp(self):
        import tempfile
        self.temp = tempfile.mkdtemp()
        from src.colony.session_export import SessionExporter
        self.exporter = SessionExporter(export_dir=self.temp, max_exports=10)
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        import shutil
        self.loop.close()
        shutil.rmtree(self.temp, ignore_errors=True)

    def test_exporter_init(self):
        self.assertEqual(self.exporter.export_count, 0)
        self.assertEqual(self.exporter._export_dir, self.temp)

    def test_set_session_start(self):
        self.exporter.set_session_start(1000.0)
        self.assertEqual(self.exporter._session_start, 1000.0)

    def test_export_full_creates_files(self):
        result = self.loop.run_until_complete(
            self.exporter.export_full(colony_id="test")
        )
        self.assertIn("ecosystem", result)
        self.assertIn("session_log", result)
        self.assertIn("auto_todo", result)
        self.assertEqual(self.exporter.export_count, 1)

    def test_export_full_with_status_and_events(self):
        status = {"orchestrator": {"colony_name": "test", "running": True, "version": "1.0"}}
        events = [
            {"event_type": "error", "data": {"message": "test error"}},
            {"event_type": "milestone", "data": {"milestone": "m1", "description": "first"}},
            {"event_type": "task_completed", "data": {"task_id": "t1", "task_type": "test"}},
            {"event_type": "task_failed", "data": {"task_id": "t2", "task_type": "test"}},
        ]
        result = self.loop.run_until_complete(
            self.exporter.export_full(status=status, lifecycle_events=events, colony_id="test")
        )
        self.assertIn("session_log", result)
        self.assertIn("auto_todo", result)

    def test_export_final(self):
        result = self.loop.run_until_complete(
            self.exporter.export_final(colony_id="test")
        )
        self.assertIn("session_final", result)

    def test_export_final_with_events(self):
        events = [
            {"event_type": "milestone", "data": {"milestone": "m1", "description": "done"}},
            {"event_type": "error", "data": {"message": "err"}},
            {"event_type": "task_completed", "data": {"task_id": "t1"}},
        ]
        result = self.loop.run_until_complete(
            self.exporter.export_final(lifecycle_events=events, colony_id="test")
        )
        self.assertIn("session_final", result)

    def test_auto_todo_no_issues(self):
        todo = self.exporter._generate_auto_todo([], {})
        self.assertIn("No pending issues detected", todo)

    def test_auto_todo_with_errors(self):
        events = [{"event_type": "error", "data": {"message": "something broke"}}]
        todo = self.exporter._generate_auto_todo(events, {})
        self.assertIn("something broke", todo)
        self.assertIn("Errors to Resolve", todo)

    def test_auto_todo_with_failed_tasks(self):
        events = [{"event_type": "task_failed", "data": {"task_id": "t1", "task_type": "analysis"}}]
        todo = self.exporter._generate_auto_todo(events, {})
        self.assertIn("analysis", todo)
        self.assertIn("needs retry", todo)

    def test_rotation(self):
        self.exporter._max_exports = 2
        self.loop.run_until_complete(self.exporter.export_full(colony_id="test"))
        self.loop.run_until_complete(self.exporter.export_full(colony_id="test"))
        self.loop.run_until_complete(self.exporter.export_full(colony_id="test"))
        self.assertLessEqual(self.exporter.export_count, 5)

    def test_get_stats(self):
        stats = self.exporter.get_stats()
        self.assertIn("export_count", stats)
        self.assertIn("export_dir", stats)
        self.assertEqual(stats["export_dir"], self.temp)


class TestQueenAgent(unittest.TestCase):
    """QueenAgent — unified command center tests."""

    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()

    def _make_queen(self, **kwargs):
        from src.colony.queen import QueenAgent
        return QueenAgent(**kwargs)

    def test_queen_init(self):
        q = self._make_queen(colony_name="test-queen")
        self.assertEqual(q._colony_name, "test-queen")
        self.assertFalse(q._running)
        self.assertEqual(q._command_count, 0)

    def test_queen_start_stop(self):
        q = self._make_queen(proactive=False)
        self.loop.run_until_complete(q.start())
        self.assertTrue(q._running)
        self.assertGreater(q.uptime, 0)
        self.loop.run_until_complete(q.stop())
        self.assertFalse(q._running)

    def test_queen_help(self):
        q = self._make_queen()
        result = self.loop.run_until_complete(q.command("help"))
        self.assertTrue(result["success"])
        self.assertIn("commands", result)

    def test_queen_help_shortcut(self):
        q = self._make_queen()
        result = self.loop.run_until_complete(q.command("?"))
        self.assertTrue(result["success"])

    def test_queen_unknown_command(self):
        q = self._make_queen()
        result = self.loop.run_until_complete(q.command("nonexistent"))
        self.assertFalse(result["success"])
        self.assertIn("Unknown command", result["error"])

    def test_queen_stats(self):
        q = self._make_queen(proactive=False)
        self.loop.run_until_complete(q.start())
        result = self.loop.run_until_complete(q.command("stats"))
        self.assertTrue(result["success"])
        self.assertEqual(result["colony"], "queen")
        self.assertEqual(result["version"], "5.0.0")
        self.assertTrue(result["running"])
        self.loop.run_until_complete(q.stop())

    def test_queen_stats_no_orchestrator(self):
        q = self._make_queen()
        result = self.loop.run_until_complete(q.command("stats"))
        self.assertFalse(result["orchestrator_wired"])

    def test_queen_status_no_orchestrator(self):
        q = self._make_queen()
        result = self.loop.run_until_complete(q.command("status"))
        self.assertFalse(result["success"])

    def test_queen_graph_no_store(self):
        q = self._make_queen()
        result = self.loop.run_until_complete(q.command("graph"))
        self.assertFalse(result["success"])

    def test_queen_export_no_exporter(self):
        q = self._make_queen()
        result = self.loop.run_until_complete(q.command("export"))
        self.assertFalse(result["success"])

    def test_queen_sync_no_orchestrator(self):
        q = self._make_queen()
        result = self.loop.run_until_complete(q.command("sync"))
        self.assertFalse(result["success"])

    def test_queen_deploy_no_registry(self):
        q = self._make_queen()
        result = self.loop.run_until_complete(q.command("deploy agent=coder count=1"))
        self.assertFalse(result["success"])

    def test_queen_idle_tracking(self):
        q = self._make_queen(idle_timeout=1, proactive=False)
        self.loop.run_until_complete(q.start())
        self.assertFalse(q.is_idle)  # just started
        self.loop.run_until_complete(asyncio.sleep(1.5))
        self.assertTrue(q.is_idle)
        q._last_activity = time.time()
        self.assertFalse(q.is_idle)
        self.loop.run_until_complete(q.stop())

    def test_queen_command_increments_count(self):
        q = self._make_queen(proactive=False)
        self.loop.run_until_complete(q.start())
        self.loop.run_until_complete(q.command("help"))
        self.loop.run_until_complete(q.command("stats"))
        self.assertEqual(q._command_count, 2)
        self.loop.run_until_complete(q.stop())

    def test_queen_get_stats(self):
        q = self._make_queen(proactive=False)
        self.loop.run_until_complete(q.start())
        stats = q.get_stats()
        self.assertIn("commands_processed", stats)
        self.assertIn("idle", stats)
        self.assertTrue(stats["running"])
        self.loop.run_until_complete(q.stop())

    def test_queen_route_task_no_registry(self):
        q = self._make_queen()
        result = self.loop.run_until_complete(q.route_task("do something"))
        self.assertIsNone(result)

    def test_queen_double_start(self):
        q = self._make_queen(proactive=False)
        self.loop.run_until_complete(q.start())
        self.loop.run_until_complete(q.start())
        self.loop.run_until_complete(q.stop())

    def test_queen_status_with_orchestrator(self):
        from src.colony.orchestrator import EcosystemOrchestrator, OrchestratorConfig
        orch = EcosystemOrchestrator(OrchestratorConfig(colony_id="test", colony_name="test"))
        q = self._make_queen(orchestrator=orch, proactive=False)
        self.loop.run_until_complete(q.start())
        result = self.loop.run_until_complete(q.command("status"))
        self.assertTrue(result["success"])
        self.assertIn("data", result)
        self.loop.run_until_complete(q.stop())

    def test_queen_status_subsystem(self):
        from src.colony.orchestrator import EcosystemOrchestrator, OrchestratorConfig
        orch = EcosystemOrchestrator(OrchestratorConfig(colony_id="test", colony_name="test"))
        q = self._make_queen(orchestrator=orch, proactive=False)
        self.loop.run_until_complete(q.start())
        result = self.loop.run_until_complete(q.command("status radar"))
        self.assertTrue(result["success"])
        self.assertEqual(result["subsystem"], "radar")
        self.loop.run_until_complete(q.stop())

    def test_queen_wire(self):
        q = self._make_queen(proactive=False)
        q.wire(voice="mock-voice", mesh_bus="mock-mesh", lifecycle_recorder="mock-lifecycle")
        self.assertEqual(q._voice, "mock-voice")
        self.assertEqual(q._mesh_bus, "mock-mesh")
        self.assertEqual(q._lifecycle_recorder, "mock-lifecycle")

    def test_queen_wire_none(self):
        q = self._make_queen()
        q.wire()
        self.assertIsNone(q._voice)
        self.assertIsNone(q._mesh_bus)
        self.assertIsNone(q._lifecycle_recorder)

    def test_queen_say_no_wiring(self):
        q = self._make_queen(proactive=False)
        self.loop.run_until_complete(q.start())
        self.loop.run_until_complete(q.say("hello"))
        self.assertEqual(q._say_count, 1)
        self.loop.run_until_complete(q.stop())

    def test_queen_broadcast_no_mesh(self):
        q = self._make_queen()
        result = self.loop.run_until_complete(q.command("broadcast hello"))
        self.assertFalse(result["success"])

    def test_queen_voice_no_service(self):
        q = self._make_queen()
        result = self.loop.run_until_complete(q.command("voice"))
        self.assertFalse(result["success"])

    def test_queen_voice_with_mock(self):
        mock_voice = type("MockVoice", (), {
            "enable": lambda self: None,
            "disable": lambda self: None,
            "set_language": lambda self, lang: None,
            "set_wake_word": lambda self, word: None,
            "get_stats": lambda self: {"tts_backend": "mock"},
        })()
        q = self._make_queen()
        q.wire(voice=mock_voice)
        result = self.loop.run_until_complete(q.command("voice"))
        self.assertTrue(result["success"])
        self.assertEqual(result["data"]["tts_backend"], "mock")

    def test_queen_voice_on(self):
        mock_voice = type("MockVoice", (), {
            "_enabled": False,
            "enable": lambda self: setattr(self, "_enabled", True),
            "get_stats": lambda self: {},
        })()
        q = self._make_queen()
        q.wire(voice=mock_voice)
        result = self.loop.run_until_complete(q.command("voice on"))
        self.assertTrue(result["success"])
        self.assertTrue(mock_voice._enabled)

    def test_queen_voice_off(self):
        mock_voice = type("MockVoice", (), {
            "_enabled": True,
            "disable": lambda self: setattr(self, "_enabled", False),
            "get_stats": lambda self: {},
        })()
        q = self._make_queen()
        q.wire(voice=mock_voice)
        result = self.loop.run_until_complete(q.command("voice off"))
        self.assertTrue(result["success"])
        self.assertFalse(mock_voice._enabled)

    def test_queen_voice_lang(self):
        mock_voice = type("MockVoice", (), {
            "_lang": "en",
            "set_language": lambda self, lang: setattr(self, "_lang", lang),
            "get_stats": lambda self: {},
        })()
        q = self._make_queen()
        q.wire(voice=mock_voice)
        result = self.loop.run_until_complete(q.command("voice lang=id"))
        self.assertTrue(result["success"])
        self.assertEqual(mock_voice._lang, "id")

    def test_queen_voice_wake(self):
        mock_voice = type("MockVoice", (), {
            "_wake": "",
            "set_wake_word": lambda self, word: setattr(self, "_wake", word),
            "get_stats": lambda self: {},
        })()
        q = self._make_queen()
        q.wire(voice=mock_voice)
        result = self.loop.run_until_complete(q.command("voice wake=queen"))
        self.assertTrue(result["success"])
        self.assertEqual(mock_voice._wake, "queen")

    def test_queen_broadcast_with_mock_mesh(self):
        received = []
        mock_mesh = type("MockMesh", (), {
            "broadcast": lambda self, sender, channel, content: received.append((sender, channel, content))
        })()
        q = self._make_queen()
        q.wire(mesh_bus=mock_mesh)
        result = self.loop.run_until_complete(q.command("broadcast hello world"))
        self.assertTrue(result["success"])
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0][0], "queen")
        self.assertEqual(received[0][2]["message"], "hello world")

    def test_queen_broadcast_no_message(self):
        mock_mesh = type("MockMesh", (), {
            "broadcast": lambda self, sender, channel, content: None
        })()
        q = self._make_queen()
        q.wire(mesh_bus=mock_mesh)
        result = self.loop.run_until_complete(q.command("broadcast"))
        self.assertFalse(result["success"])

    def test_queen_stats_with_wiring(self):
        q = self._make_queen(proactive=False)
        q.wire(voice="v", mesh_bus="m", lifecycle_recorder="l")
        self.loop.run_until_complete(q.start())
        stats = q.get_stats()
        self.assertTrue(stats["voice_wired"])
        self.assertTrue(stats["mesh_wired"])
        self.assertTrue(stats["lifecycle_wired"])
        self.loop.run_until_complete(q.stop())

    def test_queen_say_with_mock_voice(self):
        said = []
        mock_voice = type("MockVoice", (), {
            "say": lambda self, text: said.append(text)
        })()
        q = self._make_queen(proactive=False)
        q.wire(voice=mock_voice)
        self.loop.run_until_complete(q.start())
        self.loop.run_until_complete(q.say("hello queen"))
        self.assertIn("hello queen", said)
        self.loop.run_until_complete(q.stop())


class TestVoiceService(unittest.TestCase):
    """VoiceService — TTS and wake word tests."""

    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()

    def _make_voice(self, **kwargs):
        from src.colony.voice_service import VoiceService
        return VoiceService(**kwargs)

    def test_voice_init(self):
        v = self._make_voice(language="en", wake_word="queen")
        self.assertEqual(v._language, "en")
        self.assertEqual(v._wake_word, "queen")
        self.assertTrue(v._enabled)
        self.assertEqual(v._say_count, 0)

    def test_voice_init_disabled(self):
        v = self._make_voice(enabled=False)
        self.assertFalse(v._enabled)

    def test_voice_enable_disable(self):
        v = self._make_voice()
        v.disable()
        self.assertFalse(v._enabled)
        v.enable()
        self.assertTrue(v._enabled)

    def test_voice_say_disabled(self):
        v = self._make_voice(enabled=False)
        self.loop.run_until_complete(v.say("hello"))
        self.assertEqual(v._say_count, 0)

    def test_voice_say_enabled(self):
        v = self._make_voice()
        self.loop.run_until_complete(v.say("hello"))
        self.assertEqual(v._say_count, 1)
        self.assertIsNotNone(v._last_say)

    def test_voice_say_multiple(self):
        v = self._make_voice()
        self.loop.run_until_complete(v.say("a"))
        self.loop.run_until_complete(v.say("b"))
        self.loop.run_until_complete(v.say("c"))
        self.assertEqual(v._say_count, 3)

    def test_voice_set_language(self):
        v = self._make_voice()
        v.set_language("id")
        self.assertEqual(v._language, "id")

    def test_voice_set_wake_word(self):
        v = self._make_voice()
        v.set_wake_word("blackhornet")
        self.assertEqual(v._wake_word, "blackhornet")

    def test_voice_wake_trigger_clear(self):
        v = self._make_voice()
        self.assertFalse(v.wake_detected)
        v.trigger_wake_word()
        self.assertTrue(v.wake_detected)
        v.clear_wake()
        self.assertFalse(v.wake_detected)

    def test_voice_interrupt(self):
        v = self._make_voice()
        self.assertFalse(v.interrupt_requested)
        v.request_interrupt()
        self.assertTrue(v.interrupt_requested)
        v.clear_interrupt()
        self.assertFalse(v.interrupt_requested)

    def test_voice_callback(self):
        called = []
        v = self._make_voice(voice_callback=lambda text: called.append(text))
        self.loop.run_until_complete(v.say("hello"))
        self.assertIn("hello", called)

    def test_voice_get_stats(self):
        v = self._make_voice(language="id", wake_word="test")
        stats = v.get_stats()
        self.assertIn("tts_backend", stats)
        self.assertIn("say_count", stats)
        self.assertIn("language", stats)
        self.assertIn("wake_word", stats)
        self.assertEqual(stats["language"], "id")
        self.assertEqual(stats["wake_word"], "test")

    def test_voice_backend_detection(self):
        v = self._make_voice()
        backend = v.tts_backend
        self.assertIn(backend, (None, "espeak-ng", "espeak", "say", "gtts", "log-only"))


class TestColonyConsciousness(unittest.TestCase):
    """ColonyConsciousness — memory + lifecycle bridge tests."""

    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()

    def _make_consciousness(self, **kwargs):
        from src.colony.consciousness import ColonyConsciousness
        return ColonyConsciousness(**kwargs)

    def _make_mock_lifecycle(self):
        """Return a mock LifecycleRecorder with test events."""
        import time
        class MockLifecycle:
            def __init__(self):
                self._events = [
                    {"id": "e1", "event_type": "boot", "data": {"version": "5.0"}, "source": "system", "timestamp": time.time()},
                    {"id": "e2", "event_type": "task_completed", "data": {"task_id": "t1", "agent_id": "a1"}, "source": "agent", "timestamp": time.time()},
                    {"id": "e3", "event_type": "error", "data": {"message": "timeout"}, "source": "system", "timestamp": time.time()},
                    {"id": "e4", "event_type": "milestone", "data": {"description": "first deploy"}, "source": "queen", "timestamp": time.time()},
                ]
            async def get_history(self, **kw):
                return self._events
            async def get_summary(self):
                return {"total_events": 4, "event_counts": {"boot": 1, "task_completed": 1, "error": 1, "milestone": 1}}
            async def get_milestones(self):
                return [self._events[3]]
        return MockLifecycle()

    def test_consciousness_init(self):
        cc = self._make_consciousness(colony_id="test-colony")
        self.assertEqual(cc._colony_id, "test-colony")
        self.assertFalse(cc._running)
        self.assertEqual(cc._processed_count, 0)

    def test_consciousness_start_stop(self):
        cc = self._make_consciousness(colony_id="test")
        self.loop.run_until_complete(cc.start())
        self.assertTrue(cc._running)
        self.loop.run_until_complete(cc.stop())
        self.assertFalse(cc._running)

    def test_consciousness_process_events_no_subsystems(self):
        cc = self._make_consciousness(colony_id="test")
        events = [{"id": "e1", "event_type": "boot", "data": {}, "source": "system", "timestamp": 0}]
        count = self.loop.run_until_complete(cc.process_events(events))
        self.assertEqual(count, 1)
        self.assertEqual(cc._processed_count, 1)

    def test_consciousness_process_events_empty(self):
        cc = self._make_consciousness()
        count = self.loop.run_until_complete(cc.process_events([]))
        self.assertEqual(count, 0)

    def test_consciousness_process_from_lifecycle(self):
        mock_lc = self._make_mock_lifecycle()
        cc = self._make_consciousness(lifecycle_recorder=mock_lc)
        count = self.loop.run_until_complete(cc.process_events())
        self.assertEqual(count, 4)

    def test_consciousness_process_dedup(self):
        mock_lc = self._make_mock_lifecycle()
        cc = self._make_consciousness(lifecycle_recorder=mock_lc)
        self.loop.run_until_complete(cc.process_events())
        count = self.loop.run_until_complete(cc.process_events())
        self.assertEqual(count, 0)

    def test_consciousness_double_start(self):
        cc = self._make_consciousness()
        self.loop.run_until_complete(cc.start())
        self.loop.run_until_complete(cc.start())
        self.loop.run_until_complete(cc.stop())

    def test_consciousness_self_summary_with_lifecycle(self):
        mock_lc = self._make_mock_lifecycle()
        cc = self._make_consciousness(lifecycle_recorder=mock_lc, colony_id="c1")
        self.loop.run_until_complete(cc.process_events())
        summary = self.loop.run_until_complete(cc.self_summary())
        self.assertEqual(summary["colony_id"], "c1")
        self.assertIn("processed_events", summary)
        self.assertIn("lifecycle", summary)
        self.assertEqual(summary["lifecycle"]["total_events"], 4)
        self.assertIn("milestones", summary)

    def test_consciousness_self_summary_no_lifecycle(self):
        cc = self._make_consciousness()
        summary = self.loop.run_until_complete(cc.self_summary())
        self.assertIn("processed_events", summary)
        self.assertNotIn("lifecycle", summary)

    def test_consciousness_timeline(self):
        mock_lc = self._make_mock_lifecycle()
        cc = self._make_consciousness(lifecycle_recorder=mock_lc)
        self.loop.run_until_complete(cc.process_events())
        events = self.loop.run_until_complete(cc.timeline(hours=48, limit=10))
        self.assertGreaterEqual(len(events), 4)

    def test_consciousness_timeline_no_events(self):
        cc = self._make_consciousness()
        events = self.loop.run_until_complete(cc.timeline(hours=1, limit=10))
        self.assertEqual(len(events), 0)

    def test_consciousness_search_no_memory(self):
        cc = self._make_consciousness()
        results = self.loop.run_until_complete(cc.search_memories("test"))
        self.assertEqual(results, [])

    def test_consciousness_get_stats(self):
        cc = self._make_consciousness(colony_id="c1")
        stats = cc.get_stats()
        self.assertFalse(stats["running"])
        self.assertIn("processed_events", stats)
        self.assertIn("lifecycle_wired", stats)
        self.assertIn("memory_wired", stats)

    def test_consciousness_get_stats_after_start(self):
        cc = self._make_consciousness()
        self.loop.run_until_complete(cc.start())
        stats = cc.get_stats()
        self.assertTrue(stats["running"])
        self.loop.run_until_complete(cc.stop())

    def test_consciousness_process_events_with_memory(self):
        mock_lc = self._make_mock_lifecycle()
        memory_fake = type("FakeMemory", (), {
            "remember": lambda self, k, c: None,
            "store": lambda self, k, c, tags=None, importance=0.5: 1,
            "record_episode": lambda self, agent_id, event_type, summary, outcome="": 1,
        })()
        graph_fake = type("FakeGraph", (), {
            "sync_lifecycle_event": lambda self, e: None,
        })()
        cc = self._make_consciousness(
            lifecycle_recorder=mock_lc,
            memory_system=memory_fake,
            graph_sync=graph_fake,
        )
        count = self.loop.run_until_complete(cc.process_events())
        self.assertEqual(count, 4)

    def test_consciousness_process_increments_count(self):
        cc = self._make_consciousness()
        self.loop.run_until_complete(cc.process_events([
            {"id": "1", "event_type": "boot", "data": {}, "source": "sys", "timestamp": 0},
            {"id": "2", "event_type": "task_completed", "data": {}, "source": "sys", "timestamp": 1},
        ]))
        self.assertEqual(cc._processed_count, 2)


class TestQueenAgentConsciousness(unittest.TestCase):
    """QueenAgent consciousness command tests."""

    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()

    def _make_queen(self, **kwargs):
        from src.colony.queen import QueenAgent
        return QueenAgent(**kwargs)

    def test_queen_consciousness_no_service(self):
        q = self._make_queen()
        result = self.loop.run_until_complete(q.command("consciousness"))
        self.assertFalse(result["success"])

    def test_queen_consciousness_summary(self):
        from src.colony.consciousness import ColonyConsciousness
        cc = ColonyConsciousness(colony_id="test")
        q = self._make_queen()
        q.wire(consciousness=cc)
        result = self.loop.run_until_complete(q.command("consciousness summary"))
        self.assertTrue(result["success"])
        self.assertEqual(result["data"]["colony_id"], "test")

    def test_queen_consciousness_summary_shortcut(self):
        from src.colony.consciousness import ColonyConsciousness
        cc = ColonyConsciousness(colony_id="c1")
        q = self._make_queen()
        q.wire(consciousness=cc)
        result = self.loop.run_until_complete(q.command("cs summary"))
        self.assertTrue(result["success"])

    def test_queen_consciousness_timeline(self):
        from src.colony.consciousness import ColonyConsciousness
        cc = ColonyConsciousness(colony_id="test")
        q = self._make_queen()
        q.wire(consciousness=cc)
        result = self.loop.run_until_complete(q.command("consciousness timeline"))
        self.assertTrue(result["success"])
        self.assertIn("events", result)

    def test_queen_consciousness_timeline_custom_hours(self):
        from src.colony.consciousness import ColonyConsciousness
        cc = ColonyConsciousness(colony_id="test")
        q = self._make_queen()
        q.wire(consciousness=cc)
        result = self.loop.run_until_complete(q.command("consciousness timeline 48"))
        self.assertTrue(result["success"])
        self.assertEqual(result["hours"], 48)

    def test_queen_consciousness_stats(self):
        from src.colony.consciousness import ColonyConsciousness
        cc = ColonyConsciousness(colony_id="test")
        q = self._make_queen()
        q.wire(consciousness=cc)
        result = self.loop.run_until_complete(q.command("consciousness stats"))
        self.assertTrue(result["success"])
        self.assertIn("processed_events", result["data"])

    def test_queen_consciousness_unknown(self):
        from src.colony.consciousness import ColonyConsciousness
        cc = ColonyConsciousness(colony_id="test")
        q = self._make_queen()
        q.wire(consciousness=cc)
        result = self.loop.run_until_complete(q.command("consciousness blah"))
        self.assertFalse(result["success"])

    def test_queen_help_includes_consciousness(self):
        q = self._make_queen()
        result = self.loop.run_until_complete(q.command("help"))
        help_text = str(result)
        self.assertIn("consciousness", help_text)


class TestIntelligenceBridge(unittest.TestCase):
    """IntelligenceBridge — unified intelligence routing tests."""

    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()

    def _make_intel(self, **kwargs):
        from src.colony.intelligence import IntelligenceBridge
        return IntelligenceBridge(**kwargs)

    def test_intel_init(self):
        ib = self._make_intel()
        self.assertEqual(ib._ask_count, 0)
        self.assertEqual(ib._think_count, 0)
        self.assertEqual(len(ib._cache), 0)

    def test_intel_ask_no_backend(self):
        ib = self._make_intel()
        result = self.loop.run_until_complete(ib.ask("hello"))
        self.assertFalse(result.success)
        self.assertIn("No LLM router", result.error)

    def test_intel_ask_with_mock_fallback(self):
        called = []
        mock_fb = type("MockFallback", (), {
            "execute": lambda self, prompt, complexity=None: (
                called.append((prompt, complexity)),
                type("FBResult", (), {"success": True, "response": "Hello world", "provider": "mock", "model": "m1", "attempts": 1})()
            )[1]
        })()
        ib = self._make_intel(fallback_chain=mock_fb)
        result = self.loop.run_until_complete(ib.ask("hello"))
        self.assertTrue(result.success)
        self.assertEqual(result.answer, "Hello world")
        self.assertEqual(result.provider, "mock")
        self.assertEqual(len(called), 1)

    def test_intel_ask_with_context(self):
        mock_fb = type("MockFallback", (), {
            "execute": lambda self, prompt, complexity=None: type("R", (), {"success": True, "response": "ok", "provider": "p", "model": "m", "attempts": 1})()
        })()
        ib = self._make_intel(fallback_chain=mock_fb)
        result = self.loop.run_until_complete(ib.ask("test", context={"session": "abc"}))
        self.assertTrue(result.success)

    def test_intel_ask_cached(self):
        mock_fb = type("MockFallback", (), {
            "execute": lambda self, prompt, complexity=None: type("R", (), {"success": True, "response": "cached", "provider": "p", "model": "m", "attempts": 1})()
        })()
        ib = self._make_intel(fallback_chain=mock_fb)
        self.loop.run_until_complete(ib.ask("same query"))
        result = self.loop.run_until_complete(ib.ask("same query"))
        self.assertTrue(result.cached)

    def test_intel_think_no_backend(self):
        ib = self._make_intel()
        result = self.loop.run_until_complete(ib.think("analyze"))
        self.assertFalse(result.success)
        self.assertIn("No fallback chain", result.error)

    def test_intel_think_with_mock(self):
        mock_fb = type("MockFallback", (), {
            "execute": lambda self, prompt, complexity=None: type("R", (), {"success": True, "response": "analysis result", "provider": "p", "model": "m", "attempts": 1})()
        })()
        ib = self._make_intel(fallback_chain=mock_fb)
        result = self.loop.run_until_complete(ib.think("analyze this"))
        self.assertTrue(result.success)
        self.assertIn("analysis", result.answer)

    def test_intel_web_search_no_results(self):
        ib = self._make_intel()
        results = self.loop.run_until_complete(ib.search_web("asdfghjkl12345"))
        self.assertIsInstance(results, list)

    def test_intel_get_providers_no_router(self):
        ib = self._make_intel()
        providers = ib.get_providers()
        self.assertEqual(providers, [])

    def test_intel_get_providers_with_router(self):
        mock_router = type("MockRouter", (), {
            "get_available_providers": lambda self: [{"name": "opencode", "model": "deepseek-v4-flash-free"}]
        })()
        ib = self._make_intel(llm_router=mock_router)
        providers = ib.get_providers()
        self.assertEqual(len(providers), 1)
        self.assertEqual(providers[0]["name"], "opencode")

    def test_intel_stats(self):
        ib = self._make_intel()
        stats = ib.get_stats()
        self.assertIn("ask_count", stats)
        self.assertIn("cache_size", stats)
        self.assertFalse(stats["router_wired"])

    def test_intel_clear_cache(self):
        mock_fb = type("MockFallback", (), {
            "execute": lambda self, prompt, complexity=None: type("R", (), {"success": True, "response": "x", "provider": "p", "model": "m", "attempts": 1})()
        })()
        ib = self._make_intel(fallback_chain=mock_fb)
        self.loop.run_until_complete(ib.ask("q"))
        self.assertEqual(len(ib._cache), 1)
        ib.clear_cache()
        self.assertEqual(len(ib._cache), 0)

    def test_intel_ask_uses_correct_complexity(self):
        used = []
        mock_fb = type("MockFallback", (), {
            "execute": lambda self, prompt, complexity=None: (
                used.append(complexity),
                type("R", (), {"success": True, "response": "ok", "provider": "p", "model": "m", "attempts": 1})()
            )[1]
        })()
        ib = self._make_intel(fallback_chain=mock_fb)
        self.loop.run_until_complete(ib.ask("hello", complexity="simple"))
        self.assertIn("simple", used[0] if used else "")

    def test_intel_think_with_context(self):
        used = []
        mock_fb = type("MockFallback", (), {
            "execute": lambda self, prompt, complexity=None: (
                used.append(prompt),
                type("R", (), {"success": True, "response": "thought", "provider": "p", "model": "m", "attempts": 1})()
            )[1]
        })()
        ib = self._make_intel(fallback_chain=mock_fb, memory_system=True)
        self.loop.run_until_complete(ib.think("deep", context={"goal": "build"}))
        self.assertTrue(any("goal" in p for p in used))


class TestQueenAgentIntelligence(unittest.TestCase):
    """QueenAgent ask/think command tests."""

    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()

    def _make_queen(self, **kwargs):
        from src.colony.queen import QueenAgent
        return QueenAgent(**kwargs)

    def test_queen_ask_no_bridge(self):
        q = self._make_queen()
        result = self.loop.run_until_complete(q.command("ask hello"))
        self.assertFalse(result["success"])

    def test_queen_ask_no_query(self):
        mock_intel = type("MockIntel", (), {"ask": lambda self, q, complexity=None, use_cache=True, context=None: type("R", (), {"success": True, "answer": "yes", "provider": "m", "model": "m1", "latency_ms": 10, "cached": False, "error": ""})()})()
        q = self._make_queen()
        q.wire(intelligence=mock_intel)
        result = self.loop.run_until_complete(q.command("ask"))
        self.assertFalse(result["success"])

    def test_queen_ask_with_mock(self):
        mock_intel = type("MockIntel", (), {"ask": lambda self, q, complexity=None, use_cache=True, context=None: type("R", (), {"success": True, "answer": "42", "provider": "mock", "model": "m1", "latency_ms": 5, "cached": False, "error": ""})()})()
        q = self._make_queen()
        q.wire(intelligence=mock_intel)
        result = self.loop.run_until_complete(q.command("ask what is 6*7"))
        self.assertTrue(result["success"])
        self.assertEqual(result["answer"], "42")

    def test_queen_think_no_bridge(self):
        q = self._make_queen()
        result = self.loop.run_until_complete(q.command("think analyze"))
        self.assertFalse(result["success"])

    def test_queen_think_with_mock(self):
        mock_intel = type("MockIntel", (), {"think": lambda self, p, context=None, temperature=0.3: type("R", (), {"success": True, "answer": "analysis complete", "provider": "m", "model": "m1", "latency_ms": 20, "error": ""})()})()
        q = self._make_queen()
        q.wire(intelligence=mock_intel)
        result = self.loop.run_until_complete(q.command("think optimize this"))
        self.assertTrue(result["success"])
        self.assertIn("analysis", result["answer"])

    def test_queen_help_includes_ask(self):
        q = self._make_queen()
        result = self.loop.run_until_complete(q.command("help"))
        help_text = str(result)
        self.assertIn("ask", help_text)
        self.assertIn("think", help_text)


if __name__ == "__main__":
    unittest.main()
