"""Tests for evolution layer (Phase 13.5): SkillLearner, AutoDiscoveryEnhancer, SelfModifyEngine, EvolutionOrchestrator."""

import asyncio
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


class TestSkillLearner(unittest.TestCase):
    """SkillLearner — record, learn, replay command patterns."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _make_learner(self, **kwargs):
        from src.colony.evolution.skill_learner import SkillLearner
        return SkillLearner(**kwargs)

    def test_init_defaults(self):
        sl = self._make_learner()
        stats = sl.get_stats()
        self.assertEqual(stats["total_recorded"], 0)
        self.assertEqual(stats["skills_count"], 0)

    def test_record_success(self):
        sl = self._make_learner()
        sl.record("status", True, {"success": True, "status": "ok"})
        stats = sl.get_stats()
        self.assertEqual(stats["total_recorded"], 1)
        self.assertEqual(stats["skills_count"], 1)

    def test_record_failure_no_skill_creation(self):
        sl = self._make_learner(min_success_threshold=2)
        sl.record("deploy", False, {"success": False, "error": "fail"})
        stats = sl.get_stats()
        self.assertEqual(stats["skills_count"], 0)
        self.assertEqual(stats["total_recorded"], 1)
        sk = sl.learn("deploy")
        self.assertIsNone(sk)

    def test_learn_after_threshold(self):
        sl = self._make_learner(min_success_threshold=2)
        sl.record("ask hello", True, {"success": True, "answer": "hi"})
        sl.record("ask hello", True, {"success": True, "answer": "hi"})
        sk = sl.learn("ask")
        self.assertIsNotNone(sk)
        self.assertEqual(sk.skill_name, "ask")
        self.assertEqual(sk.success_count, 2)

    def test_learned_skills(self):
        sl = self._make_learner(min_success_threshold=1)
        sl.record("status", True, {"success": True})
        sl.record("status", True, {"success": True})
        learned = sl.learned_skills()
        self.assertEqual(len(learned), 1)
        self.assertEqual(learned[0].skill_name, "status")

    def test_get_history(self):
        sl = self._make_learner()
        sl.record("cmd1", True, {"success": True})
        sl.record("cmd2", False, {"success": False})
        history = sl.get_history()
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["command"], "cmd1")

    def test_get_history_success_only(self):
        sl = self._make_learner()
        sl.record("cmd1", True, {"success": True})
        sl.record("cmd2", False, {"success": False})
        history = sl.get_history(success_only=True)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["command"], "cmd1")

    def test_replay_learned_skill(self):
        sl = self._make_learner(min_success_threshold=1)
        sl.record("status", True, {"success": True})
        result = sl.replay("status")
        self.assertTrue(result.success)
        self.assertEqual(result.result["command"], "status")

    def test_replay_unlearned(self):
        sl = self._make_learner()
        result = sl.replay("nonexistent")
        self.assertFalse(result.success)

    def test_forget(self):
        sl = self._make_learner(min_success_threshold=1)
        sl.record("test", True, {"success": True})
        stats_before = sl.get_stats()
        self.assertEqual(stats_before["skills_count"], 1)
        sk = sl.learn("test")
        self.assertIsNotNone(sk)
        sl.forget(sk.id)
        stats_after = sl.get_stats()
        self.assertEqual(stats_after["skills_count"], 0)

    def test_clear_history(self):
        sl = self._make_learner()
        sl.record("a", True, {"success": True})
        sl.record("b", False, {"success": False})
        sl.clear_history()
        self.assertEqual(len(sl.get_history()), 0)

    def test_persist_and_load(self):
        path = os.path.join(self.tmp, "skills.json")
        sl1 = self._make_learner(persist_path=path, min_success_threshold=1)
        sl1.record("status", True, {"success": True})
        sl2 = self._make_learner(persist_path=path, min_success_threshold=1)
        self.assertEqual(sl2.get_stats()["total_recorded"], 1)
        self.assertEqual(sl2.get_stats()["skills_count"], 1)

    def test_max_skills(self):
        sl = self._make_learner(max_skills=3, min_success_threshold=1)
        for i in range(5):
            sl.record(f"cmd{i}", True, {"success": True})
        self.assertLessEqual(sl.get_stats()["skills_count"], 3)

    def test_record_with_tags_and_context(self):
        sl = self._make_learner()
        sl.record("deploy", True, {"success": True}, context={"env": "prod"}, tags=["deploy"], latency_ms=42.0)
        history = sl.get_history()
        self.assertEqual(history[0]["tags"], ["deploy"])
        self.assertEqual(history[0]["context"]["env"], "prod")

    def test_stats_format(self):
        sl = self._make_learner(min_success_threshold=1)
        stats = sl.get_stats()
        self.assertIn("total_recorded", stats)
        self.assertIn("learned_skills_count", stats)
        self.assertIn("history_size", stats)


class TestAutoDiscoveryEnhancer(unittest.TestCase):
    """AutoDiscoveryEnhancer — runtime capability discovery tests."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        import shutil
        self.loop.close()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _make_discovery(self, **kwargs):
        from src.colony.evolution.auto_discovery import AutoDiscoveryEnhancer
        return AutoDiscoveryEnhancer(**kwargs)

    def test_init_defaults(self):
        ad = self._make_discovery()
        stats = ad.get_stats()
        self.assertEqual(stats["total_capabilities"], 0)
        self.assertEqual(stats["total_scans"], 0)

    def test_scan_directory_nonexistent(self):
        ad = self._make_discovery()
        result = self.loop.run_until_complete(ad.scan_directory("/nonexistent_path_xyz"))
        self.assertFalse(result.success)

    def test_scan_directory_empty(self):
        ad = self._make_discovery()
        result = self.loop.run_until_complete(ad.scan_directory(self.tmp))
        self.assertTrue(result.success)
        self.assertEqual(len(result.capabilities), 0)

    def test_scan_directory_with_file(self):
        mod_path = os.path.join(self.tmp, "test_mod.py")
        with open(mod_path, "w") as f:
            f.write("def my_tool():\n    \"\"\"A test tool.\"\"\"\n    pass\n")
        ad = self._make_discovery()
        result = self.loop.run_until_complete(ad.scan_directory(self.tmp))
        self.assertTrue(result.success)
        self.assertGreaterEqual(len(result.capabilities), 1)

    def test_discover_peer_capabilities_from_obj(self):
        peer = type("Peer", (), {"colony_id": "peer-1", "capabilities": ["ping", "scan"]})()
        ad = self._make_discovery()
        caps = ad.discover_peer_capabilities(peer)
        self.assertEqual(len(caps), 2)
        names = [c.name for c in caps]
        self.assertIn("ping", names)
        self.assertIn("scan", names)

    def test_discover_peer_capabilities_from_dict(self):
        peer = {"colony_id": "peer-2", "capabilities": ["echo", "status"]}
        ad = self._make_discovery()
        caps = ad.discover_peer_capabilities(peer)
        self.assertEqual(len(caps), 2)

    def test_get_capabilities_filter_type(self):
        ad = self._make_discovery()
        peer = type("P", (), {"colony_id": "p1", "capabilities": ["scan"]})()
        ad.discover_peer_capabilities(peer)
        caps = ad.get_capabilities(capability_type="skill")
        self.assertGreaterEqual(len(caps), 1)
        caps_tool = ad.get_capabilities(capability_type="tool")
        self.assertEqual(len(caps_tool), 0)

    def test_get_capabilities_filter_source(self):
        ad = self._make_discovery()
        peer = type("P", (), {"colony_id": "p1", "capabilities": ["scan"]})()
        ad.discover_peer_capabilities(peer)
        caps = ad.get_capabilities(source="peer")
        self.assertGreaterEqual(len(caps), 1)
        caps_other = ad.get_capabilities(source="module_scan")
        self.assertEqual(len(caps_other), 0)

    def test_get_stats_format(self):
        ad = self._make_discovery()
        stats = ad.get_stats()
        self.assertIn("total_capabilities", stats)
        self.assertIn("total_scans", stats)
        self.assertIn("radar_wired", stats)

    def test_clear(self):
        ad = self._make_discovery()
        peer = type("P", (), {"colony_id": "p1", "capabilities": ["x"]})()
        ad.discover_peer_capabilities(peer)
        self.assertGreater(ad.get_stats()["total_capabilities"], 0)
        ad.clear()
        self.assertEqual(ad.get_stats()["total_capabilities"], 0)

    def test_wire_radar(self):
        ad = self._make_discovery()
        radar = type("R", (), {})()
        ad.wire_radar(radar)
        self.assertTrue(ad.get_stats()["radar_wired"])

    def test_scan_modules_noop_bad_prefix(self):
        ad = self._make_discovery()
        result = self.loop.run_until_complete(ad.scan_modules(package_prefix="nonexistent_pkg_xyz"))
        self.assertFalse(result.success)

    def test_persist_and_load(self):
        path = os.path.join(self.tmp, "discovery.json")
        ad1 = self._make_discovery(persist_path=path)
        peer = type("P", (), {"colony_id": "p1", "capabilities": ["scan"]})()
        ad1.discover_peer_capabilities(peer)
        ad2 = self._make_discovery(persist_path=path)
        self.assertGreater(ad2.get_stats()["total_capabilities"], 0)


class TestSelfModifyEngine(unittest.TestCase):
    """SelfModifyEngine — codebase change proposals and application."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.codebase = os.path.join(self.tmp, "codebase")
        os.makedirs(self.codebase)
        os.makedirs(os.path.join(self.codebase, "src"))
        self.test_file = os.path.join(self.codebase, "src", "test_mod.py")
        with open(self.test_file, "w") as f:
            f.write("def old_func():\n    return 1\n")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _make_engine(self, **kwargs):
        from src.colony.evolution.self_modify import SelfModifyEngine
        return SelfModifyEngine(codebase_root=self.codebase, **kwargs)

    def test_init_defaults(self):
        sm = self._make_engine()
        stats = sm.get_stats()
        self.assertEqual(stats["total_proposed"], 0)
        self.assertEqual(stats["total_applied"], 0)

    def test_propose_change(self):
        sm = self._make_engine()
        prop = sm.propose_change(
            change_type="refactor",
            file_path=self.test_file,
            description="Refactor old_func",
            original_snippet="def old_func():\n    return 1",
            proposed_snippet="def new_func():\n    return 2",
            rationale="Modernize",
        )
        self.assertEqual(prop.status, "pending")
        self.assertEqual(prop.change_type, "refactor")
        self.assertIn("old_func", prop.diff)
        self.assertIn("new_func", prop.diff)

    def test_propose_change_disallowed_path(self):
        sm = self._make_engine(allowed_paths=["src"])
        bad_path = os.path.join(self.tmp, "outside", "bad.py")
        with self.assertRaises(ValueError):
            sm.propose_change(
                change_type="refactor",
                file_path=bad_path,
                description="Bad",
                original_snippet="x",
                proposed_snippet="y",
                rationale="Bad",
            )

    def test_approve(self):
        sm = self._make_engine()
        prop = sm.propose_change(
            change_type="refactor",
            file_path=self.test_file,
            description="Test",
            original_snippet="def old_func():\n    return 1",
            proposed_snippet="def new_func():\n    return 2",
            rationale="Test",
        )
        self.assertTrue(sm.approve(prop.id))
        self.assertEqual(sm.get_proposal(prop.id).status, "approved")

    def test_reject(self):
        sm = self._make_engine()
        prop = sm.propose_change(
            change_type="refactor",
            file_path=self.test_file,
            description="Test",
            original_snippet="def old_func():\n    return 1",
            proposed_snippet="def new_func():\n    return 2",
            rationale="Test",
        )
        self.assertTrue(sm.reject(prop.id))
        self.assertEqual(sm.get_proposal(prop.id).status, "rejected")

    def test_apply_without_approval(self):
        sm = self._make_engine(require_approval=True, min_confidence=0.0)
        prop = sm.propose_change(
            change_type="refactor",
            file_path=self.test_file,
            description="Test",
            original_snippet="def old_func():\n    return 1",
            proposed_snippet="def new_func():\n    return 2",
            rationale="Test",
            confidence=0.8,
        )
        result = sm.apply(prop.id)
        self.assertFalse(result.success)
        self.assertIn("Not approved", result.error)

    def test_apply_after_approval(self):
        sm = self._make_engine(require_approval=True, min_confidence=0.0)
        prop = sm.propose_change(
            change_type="refactor",
            file_path=self.test_file,
            description="Test",
            original_snippet="def old_func():\n    return 1",
            proposed_snippet="def new_func():\n    return 2",
            rationale="Test",
            confidence=0.8,
        )
        sm.approve(prop.id)
        result = sm.apply(prop.id)
        self.assertTrue(result.success)
        with open(self.test_file) as f:
            content = f.read()
        self.assertIn("def new_func()", content)
        self.assertNotIn("def old_func()", content)

    def test_apply_below_confidence(self):
        sm = self._make_engine(require_approval=False, min_confidence=0.9)
        prop = sm.propose_change(
            change_type="refactor",
            file_path=self.test_file,
            description="Test",
            original_snippet="def old_func():\n    return 1",
            proposed_snippet="def new_func():\n    return 2",
            rationale="Test",
            confidence=0.5,
        )
        result = sm.apply(prop.id)
        self.assertFalse(result.success)

    def test_apply_nonexistent_file(self):
        sm = self._make_engine(require_approval=False, min_confidence=0.0)
        missing_file = os.path.join(self.codebase, "src", "nonexistent.py")
        prop = sm.propose_change(
            change_type="fix",
            file_path=missing_file,
            description="Test",
            original_snippet="x", proposed_snippet="y",
            rationale="Test",
        )
        result = sm.apply(prop.id)
        self.assertFalse(result.success)

    def test_apply_already_applied(self):
        sm = self._make_engine(require_approval=False, min_confidence=0.0)
        prop = sm.propose_change(
            change_type="refactor",
            file_path=self.test_file,
            description="Test",
            original_snippet="def old_func():\n    return 1",
            proposed_snippet="def new_func():\n    return 2",
            rationale="Test",
        )
        sm.apply(prop.id)
        result = sm.apply(prop.id)
        self.assertFalse(result.success)

    def test_get_proposals_filter(self):
        sm = self._make_engine()
        sm.propose_change("refactor", self.test_file, "A", "x", "y", "r1")
        sm.propose_change("fix", self.test_file, "B", "x", "y", "r2")
        props = sm.get_proposals(change_type="fix")
        self.assertEqual(len(props), 1)
        self.assertEqual(props[0].description, "B")

    def test_get_proposals_limit(self):
        sm = self._make_engine()
        for i in range(5):
            sm.propose_change("refactor", self.test_file, f"P{i}", "x", "y", f"r{i}")
        props = sm.get_proposals(limit=2)
        self.assertLessEqual(len(props), 5)

    def test_safety_flags(self):
        sm = self._make_engine()
        prop = sm.propose_change(
            change_type="refactor",
            file_path=self.test_file,
            description="Large growth",
            original_snippet="x",
            proposed_snippet="x\n" * 100,
            rationale="Test",
        )
        self.assertIn("large_growth", prop.safety_flags)

    def test_stats_format(self):
        sm = self._make_engine()
        sm.propose_change("refactor", self.test_file, "T", "x", "y", "r")
        stats = sm.get_stats()
        self.assertIn("total_proposed", stats)
        self.assertIn("pending_proposals", stats)
        self.assertEqual(stats["pending_proposals"], 1)

    def test_proposal_not_found(self):
        sm = self._make_engine()
        result = sm.apply("nonexistent-id")
        self.assertFalse(result.success)
        self.assertIn("not found", result.error)


class TestEvolutionOrchestrator(unittest.TestCase):
    """EvolutionOrchestrator — wires SkillLearner + Discovery + SelfModify."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        import shutil
        self.loop.close()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _make_orch(self, **kwargs):
        from src.colony.evolution.orchestrator import EvolutionOrchestrator, EvolutionConfig
        cfg = EvolutionConfig(**kwargs)
        return EvolutionOrchestrator(config=cfg)

    def test_init_defaults(self):
        eo = self._make_orch()
        stats = eo.get_stats()
        self.assertFalse(stats["running"])
        self.assertIn("skill_learner", stats)
        self.assertIn("discovery", stats)
        self.assertIn("self_modify", stats)

    def test_start_stop(self):
        eo = self._make_orch()
        self.loop.run_until_complete(eo.start())
        self.assertTrue(eo.get_stats()["running"])
        self.loop.run_until_complete(eo.stop())
        self.assertFalse(eo.get_stats()["running"])

    def test_record_command(self):
        eo = self._make_orch(auto_learn=True, min_skill_confidence=1)
        eo.record_command("status", True, {"success": True})
        self.assertEqual(eo.skill_learner.get_stats()["total_recorded"], 1)

    def test_record_command_disabled(self):
        eo = self._make_orch(auto_learn=False)
        eo.record_command("status", True, {"success": True})
        self.assertEqual(eo.skill_learner.get_stats()["total_recorded"], 0)

    def test_get_learned_skills(self):
        eo = self._make_orch(auto_learn=True, min_skill_confidence=1)
        eo.record_command("test", True, {"ok": True})
        eo.record_command("test", True, {"ok": True})
        learned = eo.get_learned_skills()
        self.assertEqual(len(learned), 1)

    def test_get_discovered_capabilities(self):
        eo = self._make_orch()
        caps = eo.get_discovered_capabilities()
        self.assertIsInstance(caps, list)

    def test_get_proposals(self):
        eo = self._make_orch()
        props = eo.get_proposals()
        self.assertIsInstance(props, list)

    def test_wire(self):
        eo = self._make_orch()
        lifecycle = type("L", (), {})()
        radar = type("R", (), {})()
        eo.wire(lifecycle=lifecycle, radar=radar)
        self.assertTrue(eo.discovery.get_stats()["radar_wired"])

    def test_run_discovery_scan(self):
        eo = self._make_orch(auto_discover=True)
        result = self.loop.run_until_complete(eo.run_discovery_scan())
        self.assertIn("success", result)

    def test_run_discovery_scan_disabled(self):
        eo = self._make_orch(auto_discover=False)
        result = self.loop.run_until_complete(eo.run_discovery_scan())
        self.assertFalse(result["success"])

    def test_get_stats_format(self):
        eo = self._make_orch(auto_learn=True, auto_discover=True)
        stats = eo.get_stats()
        self.assertIn("skill_learner", stats)
        self.assertIn("discovery", stats)
        self.assertIn("self_modify", stats)
        self.assertIn("config", stats)


if __name__ == "__main__":
    unittest.main()
