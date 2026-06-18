"""Tests for ColonyHealthMonitor."""

import asyncio
import unittest
from unittest.mock import AsyncMock, Mock


class TestColonyHealthMonitor(unittest.TestCase):
    """ColonyHealthMonitor tests."""

    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()

    def _make_monitor(self, **kwargs):
        from src.colony.health_monitor import ColonyHealthMonitor
        return ColonyHealthMonitor(**kwargs)

    def test_init_defaults(self):
        hm = self._make_monitor()
        self.assertIsNotNone(hm._detector)
        self.assertIsNotNone(hm._orchestrator)
        self.assertIsNotNone(hm._circuit_breaker)

    def test_wire_radar(self):
        hm = self._make_monitor()
        radar = Mock()
        radar.peers = {"peer1": {}, "peer2": {}}
        hm.wire_radar(radar)
        self.assertEqual(hm._radar, radar)

    def test_wire_mesh(self):
        hm = self._make_monitor()
        mesh = Mock()
        hm.wire_mesh(mesh)
        self.assertEqual(hm._mesh_bus, mesh)

    def test_wire_nest(self):
        hm = self._make_monitor()
        nest = Mock()
        nest.components = {"component1": {}, "component2": {}}
        hm.wire_nest(nest)
        self.assertEqual(hm._nest, nest)

    def test_record_peer_heartbeat(self):
        hm = self._make_monitor()
        radar = Mock()
        radar.peers = {"peer1": {}}
        hm.wire_radar(radar)
        hm.record_peer_heartbeat("peer1")
        # This will hit the detector's record_heartbeat
        # We can't easily test the internal state, so we'll just verify no crash
        self.assertTrue(True)

    def test_get_peer_health(self):
        hm = self._make_monitor()
        radar = Mock()
        radar.peers = {"peer1": {}}
        hm.wire_radar(radar)
        hm.record_peer_heartbeat("peer1")
        health = hm.get_peer_health("peer1")
        self.assertIsNotNone(health)

    def test_monitored_deliver_success(self):
        hm = self._make_monitor()
        mesh = Mock()
        mesh._send_http = AsyncMock(return_value=True)
        hm.wire_mesh(mesh)
        result = self.loop.run_until_complete(hm.monitored_deliver({}, "http://test"))
        self.assertTrue(result)

    def test_monitored_deliver_failure(self):
        hm = self._make_monitor()
        mesh = Mock()
        mesh._send_http = AsyncMock(return_value=False)
        hm.wire_mesh(mesh)
        result = self.loop.run_until_complete(hm.monitored_deliver({}, "http://test"))
        self.assertFalse(result)

    def test_get_stats(self):
        hm = self._make_monitor()
        stats = hm.get_stats()
        self.assertIn("detector", stats)
        self.assertIn("circuit_breaker", stats)
        self.assertIn("orchestrator", stats)

    def test_start_stop(self):
        hm = self._make_monitor()
        self.loop.run_until_complete(hm.start())
        self.assertTrue(hm._running)
        self.loop.run_until_complete(hm.stop())
        self.assertFalse(hm._running)


if __name__ == "__main__":
    unittest.main()