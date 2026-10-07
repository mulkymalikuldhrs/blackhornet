"""Comprehensive end-to-end integration tests for self-healing, self-upgrade,
and immortal capabilities of BlackHornet.

Covers:
  - Self-healing: heartbeat → failure detection → recovery
  - Self-modify: propose → approve → apply → verify
  - Auto-discovery: scan modules → find capabilities
  - Self-prompt: generate adaptive prompts
  - Curiosity drive: knowledge gap exploration
  - Preference learning: user modeling
  - Self-task generation: autonomous task creation
"""

import asyncio
import os
import tempfile
import time
import unittest
from dataclasses import dataclass
from typing import Any, Dict, List
from unittest.mock import MagicMock


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1: Self-Healing Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestPhiAccrualFailureDetector(unittest.TestCase):
    """Test the phi-accrual failure detector."""

    def test_heartbeat_records_health(self):
        from src.core.self_healing import PhiAccrualFailureDetector, FailureLevel
        det = PhiAccrualFailureDetector(threshold=3.0, acceptable_heartbeat_pause=0.1)
        health = det.record_heartbeat("svc-A")
        self.assertEqual(health.component_id, "svc-A")
        self.assertEqual(health.level, FailureLevel.HEALTHY)
        self.assertEqual(health.heartbeats_received, 1)

    def test_phi_increases_with_time_without_heartbeat(self):
        import time as _time
        from src.core.self_healing import PhiAccrualFailureDetector
        det = PhiAccrualFailureDetector(threshold=0.5, acceptable_heartbeat_pause=0.05, min_samples=3)
        for _ in range(5):
            det.record_heartbeat("svc-B")
            _time.sleep(0.06)
        _time.sleep(0.3)
        phi = det.compute_phi("svc-B")
        self.assertGreater(phi, 0.0, "Phi should increase when heartbeat is delayed")

    def test_failed_status_when_phi_exceeds_threshold(self):
        from src.core.self_healing import PhiAccrualFailureDetector, FailureLevel
        det = PhiAccrualFailureDetector(threshold=0.3, acceptable_heartbeat_pause=0.01, min_samples=2)
        for _ in range(3):
            det.record_heartbeat("svc-C")
            time.sleep(0.02)
        time.sleep(0.5)
        health = det.get_health("svc-C")
        self.assertEqual(health.level, FailureLevel.FAILED)

    def test_reset_clears_state(self):
        from src.core.self_healing import PhiAccrualFailureDetector
        det = PhiAccrualFailureDetector()
        det.record_heartbeat("svc-D")
        det.record_heartbeat("svc-D")
        det.reset("svc-D")
        health = det.get_health("svc-D")
        self.assertEqual(health.heartbeats_received, 0)

    def test_is_available_healthy(self):
        from src.core.self_healing import PhiAccrualFailureDetector
        det = PhiAccrualFailureDetector(threshold=3.0, acceptable_heartbeat_pause=0.1)
        det.record_heartbeat("svc-E")
        self.assertTrue(det.is_available("svc-E"))

    def test_get_all_health(self):
        from src.core.self_healing import PhiAccrualFailureDetector
        det = PhiAccrualFailureDetector(acceptable_heartbeat_pause=0.1)
        det.record_heartbeat("svc-1")
        det.record_heartbeat("svc-2")
        all_h = det.get_all_health()
        self.assertIn("svc-1", all_h)
        self.assertIn("svc-2", all_h)


class TestRecoveryManager(unittest.TestCase):
    """Test recovery manager with handler dispatch."""

    def test_successful_recovery_resets_detector(self):
        from src.core.self_healing import (
            PhiAccrualFailureDetector, RecoveryManager, RecoveryAction, FailureLevel
        )
        det = PhiAccrualFailureDetector(threshold=0.3, acceptable_heartbeat_pause=0.01, min_samples=2)
        rm = RecoveryManager(det)

        recovered = {"called": False}

        async def handler(cid, action):
            recovered["called"] = True
            return True

        rm.register_handler("web", handler)

        for _ in range(3):
            det.record_heartbeat("web-svc")
            time.sleep(0.02)
        time.sleep(0.5)
        self.assertEqual(det.get_health("web-svc").level, FailureLevel.FAILED)

        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(
            rm.check_and_recover("web-svc", "web", RecoveryAction.RESTART)
        )
        loop.close()
        self.assertTrue(result)
        self.assertTrue(recovered["called"])
        self.assertEqual(det.get_health("web-svc").level, FailureLevel.HEALTHY)

    def test_recovery_blocked_without_handler(self):
        from src.core.self_healing import (
            PhiAccrualFailureDetector, RecoveryManager, RecoveryAction, FailureLevel
        )
        det = PhiAccrualFailureDetector(threshold=0.3, acceptable_heartbeat_pause=0.01, min_samples=2)
        rm = RecoveryManager(det)
        for _ in range(3):
            det.record_heartbeat("svc-X")
            time.sleep(0.02)
        time.sleep(0.5)
        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(
            rm.check_and_recover("svc-X", "unknown_type", RecoveryAction.RESTART)
        )
        loop.close()
        self.assertFalse(result)

    def test_recovery_stats(self):
        from src.core.self_healing import PhiAccrualFailureDetector, RecoveryManager
        det = PhiAccrualFailureDetector()
        rm = RecoveryManager(det)
        rm._recovery_history["svc"] = [
            {"timestamp": time.time(), "action": "restart", "success": True},
            {"timestamp": time.time(), "action": "restart", "success": False},
        ]
        stats = rm.get_recovery_stats()
        self.assertEqual(stats["total_recoveries"], 2)
        self.assertEqual(stats["successful"], 1)


class TestSelfHealingOrchestrator(unittest.TestCase):
    """Test the orchestrator combining detector + recovery."""

    def test_monitor_and_heartbeat(self):
        from src.core.self_healing import SelfHealingOrchestrator, FailureLevel
        orch = SelfHealingOrchestrator({"phi_threshold": 3.0})
        orch.monitor("db", "database")
        health = orch.heartbeat("db")
        self.assertEqual(health.level, FailureLevel.HEALTHY)
        status = orch.get_status()
        self.assertEqual(status["monitored_components"], 1)

    def test_start_stop_loop(self):
        from src.core.self_healing import SelfHealingOrchestrator
        orch = SelfHealingOrchestrator({"check_interval": 0.1})
        orch.monitor("svc", "service")
        loop = asyncio.new_event_loop()
        loop.run_until_complete(orch.start())
        time.sleep(0.2)
        loop.run_until_complete(orch.stop())
        loop.close()
        self.assertFalse(orch._running)

    def test_unmonitor(self):
        from src.core.self_healing import SelfHealingOrchestrator
        orch = SelfHealingOrchestrator()
        orch.monitor("svc", "service")
        orch.unmonitor("svc")
        self.assertEqual(len(orch._monitored), 0)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2: Self-Modify Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestSelfModifyEngine(unittest.TestCase):
    """Test propose → approve → apply → verify flow."""

    def test_propose_creates_pending(self):
        from src.colony.evolution.self_modify import SelfModifyEngine
        engine = SelfModifyEngine(codebase_root="/tmp/test_codebase", require_approval=True)
        proposal = engine.propose_change(
            change_type="refactor",
            file_path="/tmp/test_codebase/src/main.py",
            description="Simplify function",
            original_snippet="def foo():\n    pass",
            proposed_snippet="def foo():\n    return 42",
            rationale="Clearer",
        )
        self.assertEqual(proposal.status, "pending")
        self.assertEqual(proposal.change_type, "refactor")

    def test_approve_then_apply(self):
        from src.colony.evolution.self_modify import SelfModifyEngine
        with tempfile.TemporaryDirectory() as td:
            src_dir = os.path.join(td, "src")
            os.makedirs(src_dir)
            fp = os.path.join(src_dir, "test.py")
            with open(fp, "w") as f:
                f.write("def hello():\n    return 'world'\n")
            engine = SelfModifyEngine(codebase_root=td, require_approval=True, allowed_paths=["src"])
            proposal = engine.propose_change(
                change_type="fix",
                file_path=fp,
                description="Fix return value",
                original_snippet="return 'world'",
                proposed_snippet="return 'hello'",
                rationale="Bug fix",
            )
            self.assertTrue(engine.approve(proposal.id))
            result = engine.apply(proposal.id)
            self.assertTrue(result.success)
            with open(fp) as f:
                content = f.read()
            self.assertIn("return 'hello'", content)

    def test_apply_without_approval_rejected(self):
        from src.colony.evolution.self_modify import SelfModifyEngine
        with tempfile.TemporaryDirectory() as td:
            src_dir = os.path.join(td, "src")
            os.makedirs(src_dir)
            fp = os.path.join(src_dir, "test.py")
            with open(fp, "w") as f:
                f.write("x = 1\n")
            engine = SelfModifyEngine(codebase_root=td, require_approval=True, allowed_paths=["src"])
            proposal = engine.propose_change(
                change_type="fix", file_path=fp, description="test",
                original_snippet="x = 1", proposed_snippet="x = 2", rationale="test",
            )
            result = engine.apply(proposal.id)
            self.assertFalse(result.success)
            self.assertIn("Not approved", result.error)

    def test_low_confidence_rejected(self):
        from src.colony.evolution.self_modify import SelfModifyEngine
        with tempfile.TemporaryDirectory() as td:
            src_dir = os.path.join(td, "src")
            os.makedirs(src_dir)
            fp = os.path.join(src_dir, "test.py")
            with open(fp, "w") as f:
                f.write("x = 1\n")
            engine = SelfModifyEngine(codebase_root=td, require_approval=False, min_confidence=0.8, allowed_paths=["src"])
            proposal = engine.propose_change(
                change_type="fix", file_path=fp, description="test",
                original_snippet="x = 1", proposed_snippet="x = 2", rationale="test",
                confidence=0.3,
            )
            result = engine.apply(proposal.id)
            self.assertFalse(result.success)
            self.assertIn("below minimum", result.error)

    def test_safety_flags_detected(self):
        from src.colony.evolution.self_modify import SelfModifyEngine
        engine = SelfModifyEngine(codebase_root="/tmp")
        big_proposed = "import os\n" * 20
        proposal = engine.propose_change(
            change_type="feature", file_path="/tmp/src/test.py",
            description="big change", original_snippet="import os",
            proposed_snippet=big_proposed, rationale="test",
        )
        self.assertIn("new_imports", proposal.safety_flags)

    def test_reject(self):
        from src.colony.evolution.self_modify import SelfModifyEngine
        engine = SelfModifyEngine(codebase_root="/tmp")
        p = engine.propose_change(
            change_type="refactor", file_path="/tmp/src/x.py",
            description="x", original_snippet="a", proposed_snippet="b", rationale="y",
        )
        self.assertTrue(engine.reject(p.id))
        self.assertEqual(p.status, "rejected")

    def test_apply_nonexistent_proposal(self):
        from src.colony.evolution.self_modify import SelfModifyEngine
        engine = SelfModifyEngine(codebase_root="/tmp")
        result = engine.apply("nonexistent-id")
        self.assertFalse(result.success)

    def test_stats(self):
        from src.colony.evolution.self_modify import SelfModifyEngine
        engine = SelfModifyEngine(codebase_root="/tmp")
        engine.propose_change("refactor", "/tmp/src/a.py", "d", "a", "b", "r")
        stats = engine.get_stats()
        self.assertEqual(stats["total_proposed"], 1)
        self.assertTrue(stats["require_approval"])


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 5: Auto-Discovery Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestAutoDiscovery(unittest.TestCase):
    """Test capability discovery from modules and directories."""

    def test_scan_directory_finds_python_files(self):
        from src.colony.evolution.auto_discovery import AutoDiscoveryEnhancer
        enhancer = AutoDiscoveryEnhancer(auto_persist=False)
        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(
            enhancer.scan_directory(os.path.dirname(os.path.abspath(__file__)))
        )
        loop.close()
        self.assertTrue(result.success)
        self.assertGreater(len(result.capabilities), 0)

    def test_scan_nonexistent_directory(self):
        from src.colony.evolution.auto_discovery import AutoDiscoveryEnhancer
        enhancer = AutoDiscoveryEnhancer(auto_persist=False)
        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(enhancer.scan_directory("/nonexistent/path"))
        loop.close()
        self.assertFalse(result.success)

    def test_discover_peer_capabilities(self):
        from src.colony.evolution.auto_discovery import AutoDiscoveryEnhancer
        enhancer = AutoDiscoveryEnhancer(auto_persist=False)
        peer = {"capabilities": ["translate", "summarize"], "colony_id": "peer-1"}
        caps = enhancer.discover_peer_capabilities(peer)
        self.assertEqual(len(caps), 2)
        names = {c.name for c in caps}
        self.assertIn("translate", names)

    def test_get_capabilities_filtered(self):
        from src.colony.evolution.auto_discovery import AutoDiscoveryEnhancer
        enhancer = AutoDiscoveryEnhancer(auto_persist=False)
        enhancer.discover_peer_capabilities({"capabilities": ["a", "b"], "colony_id": "c1"})
        skills = enhancer.get_capabilities(capability_type="skill")
        self.assertEqual(len(skills), 2)
        tools = enhancer.get_capabilities(capability_type="tool")
        self.assertEqual(len(tools), 0)

    def test_persistence(self):
        from src.colony.evolution.auto_discovery import AutoDiscoveryEnhancer
        with tempfile.TemporaryDirectory() as td:
            pp = os.path.join(td, "caps.json")
            enhancer = AutoDiscoveryEnhancer(persist_path=pp, auto_persist=True)
            enhancer.discover_peer_capabilities({"capabilities": ["x"], "colony_id": "c1"})
            # Create new instance, should load from file
            enhancer2 = AutoDiscoveryEnhancer(persist_path=pp, auto_persist=False)
            caps = enhancer2.get_capabilities()
            self.assertEqual(len(caps), 1)

    def test_clear(self):
        from src.colony.evolution.auto_discovery import AutoDiscoveryEnhancer
        enhancer = AutoDiscoveryEnhancer(auto_persist=False)
        enhancer.discover_peer_capabilities({"capabilities": ["a"], "colony_id": "c1"})
        enhancer.clear()
        self.assertEqual(len(enhancer.get_capabilities()), 0)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 6: Self-Prompt Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestSelfPrompt(unittest.TestCase):
    """Test adaptive prompt generation."""

    def test_build_context_empty(self):
        from src.thinking.self_prompt import SelfPromptGenerator
        gen = SelfPromptGenerator()
        ctx = gen.build_context("user-1")
        self.assertEqual(ctx.user_id, "user-1")
        self.assertEqual(ctx.topics, [])

    def test_generate_system_prompt_block(self):
        from src.thinking.self_prompt import SelfPromptGenerator
        gen = SelfPromptGenerator()
        block = gen.generate_system_prompt_block("user-1")
        self.assertIn("<user-context>", block)
        self.assertIn("</user-context>", block)

    def test_generate_instruction_block(self):
        from src.thinking.self_prompt import SelfPromptGenerator
        gen = SelfPromptGenerator()
        block = gen.generate_instruction_block("user-1", task="Build API")
        self.assertIn("<user-instructions>", block)
        self.assertIn("Build API", block)

    def test_generate_full_prompt(self):
        from src.thinking.self_prompt import SelfPromptGenerator
        gen = SelfPromptGenerator()
        full = gen.generate_full_prompt("user-1", task="Deploy")
        self.assertIn("<user-context>", full)
        self.assertIn("<user-instructions>", full)
        self.assertIn("Deploy", full)

    def test_build_context_with_profile(self):
        from src.thinking.self_prompt import SelfPromptGenerator, PromptContext
        mock_store = MagicMock()
        mock_profile = MagicMock()
        mock_profile.name = "Alice"
        mock_profile.topics_of_interest = ["AI", "ML"]
        mock_profile.preferences = {"theme": "dark"}
        mock_profile.skill_levels = {"python": 0.9}
        mock_profile.interaction_count = 42
        mock_store.get_by_user_id.return_value = mock_profile
        gen = SelfPromptGenerator(user_store=mock_store)
        ctx = gen.build_context("alice")
        self.assertEqual(ctx.user_name, "Alice")
        self.assertIn("AI", ctx.topics)
        self.assertEqual(ctx.expertise["python"], 0.9)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 7: Self-Task Generator Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestSelfTaskGenerator(unittest.TestCase):
    """Test autonomous task generation."""

    def test_from_goal(self):
        from src.thinking.self_task_generator import SelfTaskGenerator
        gen = SelfTaskGenerator()
        goal = MagicMock(state="active", title="Deploy service", description="Deploy to prod",
                         priority=8, category="devops", id=42)
        proposal = gen.from_goal(goal)
        self.assertIsNotNone(proposal)
        self.assertEqual(proposal.task_type, "goal_step")
        self.assertEqual(proposal.priority, 8)

    def test_from_inactive_goal_returns_none(self):
        from src.thinking.self_task_generator import SelfTaskGenerator
        gen = SelfTaskGenerator()
        goal = MagicMock(state="completed")
        proposal = gen.from_goal(goal)
        self.assertIsNone(proposal)

    def test_from_exploration(self):
        from src.thinking.self_task_generator import SelfTaskGenerator
        gen = SelfTaskGenerator()
        exp = MagicMock(topic="Quantum Computing", source="curiosity",
                        reason="Novel topic", priority=6, related_concepts=["qubits"])
        proposal = gen.from_exploration(exp)
        self.assertIsNotNone(proposal)
        self.assertEqual(proposal.task_type, "exploration")

    def test_from_maintenance(self):
        from src.thinking.self_task_generator import SelfTaskGenerator
        gen = SelfTaskGenerator()
        mock_mem = MagicMock()
        mock_mem.stats.return_value = {
            "last_consolidation": time.time() - 10000,
            "last_forgetting": time.time() - 20000,
        }
        proposals = gen.from_maintenance(mock_mem)
        self.assertGreater(len(proposals), 0)
        types = {p.task_type for p in proposals}
        self.assertIn("maintenance", types)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 8: Curiosity Drive Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestCuriosityDrive(unittest.TestCase):
    """Test curiosity-driven exploration goal generation."""

    def test_mark_and_get_depth(self):
        from src.thinking.curiosity_drive import CuriosityDrive
        cd = CuriosityDrive()
        cd.mark_explored("quantum", 0.7)
        self.assertEqual(cd.get_exploration_depth("quantum"), 0.7)
        self.assertEqual(cd.get_exploration_depth("unknown"), 0.0)

    def test_suggest_from_novelty(self):
        from src.thinking.curiosity_drive import CuriosityDrive
        cd = CuriosityDrive()
        goals = cd.suggest_from_novelty(
            recent_topics=["quantum", "neuroscience"],
            known_topics=["quantum"],
        )
        self.assertEqual(len(goals), 1)
        self.assertIn("neuroscience", goals[0].topic)

    def test_suggest_empty_when_all_known(self):
        from src.thinking.curiosity_drive import CuriosityDrive
        cd = CuriosityDrive()
        goals = cd.suggest_from_novelty(
            recent_topics=["quantum"],
            known_topics=["quantum"],
        )
        self.assertEqual(len(goals), 0)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 9: Preference Learner Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestPreferenceLearner(unittest.TestCase):
    """Test user preference learning."""

    def test_record_and_get(self):
        from src.thinking.preference_learner import PreferenceLearner
        with tempfile.TemporaryDirectory() as td:
            db = os.path.join(td, "prefs.db")
            pl = PreferenceLearner(db_path=db)
            pl.record_preference("user-1", "theme", "dark", confidence=0.8, source="test")
            pref = pl.get_preference("user-1", "theme")
            self.assertIsNotNone(pref)
            self.assertEqual(pref.value, "dark")
            self.assertAlmostEqual(pref.confidence, 0.8, places=1)
            pl.close()

    def test_learn_topic(self):
        from src.thinking.preference_learner import PreferenceLearner
        with tempfile.TemporaryDirectory() as td:
            db = os.path.join(td, "prefs.db")
            pl = PreferenceLearner(db_path=db)
            pl.learn_topic("user-1", "machine_learning", 0.9)
            topics = pl.get_topics("user-1")
            self.assertEqual(len(topics), 1)
            self.assertEqual(topics[0]["topic"], "machine_learning")
            pl.close()

    def test_set_expertise(self):
        from src.thinking.preference_learner import PreferenceLearner
        with tempfile.TemporaryDirectory() as td:
            db = os.path.join(td, "prefs.db")
            pl = PreferenceLearner(db_path=db)
            pl.set_expertise("user-1", "python", 0.95)
            expertise = pl.get_expertise("user-1")
            self.assertEqual(expertise["python"], 0.95)
            pl.close()

    def test_learn_from_feedback(self):
        from src.thinking.preference_learner import PreferenceLearner
        with tempfile.TemporaryDirectory() as td:
            db = os.path.join(td, "prefs.db")
            pl = PreferenceLearner(db_path=db)
            pl.learn_from_feedback("user-1", 4.5, "code_quality")
            pref = pl.get_preference("user-1", "prefers_code_quality")
            self.assertIsNotNone(pref)
            self.assertEqual(pref.source, "feedback")
            pl.close()

    def test_get_model(self):
        from src.thinking.preference_learner import PreferenceLearner
        with tempfile.TemporaryDirectory() as td:
            db = os.path.join(td, "prefs.db")
            pl = PreferenceLearner(db_path=db)
            pl.learn_topic("user-1", "ai", 0.8)
            pl.set_expertise("user-1", "python", 0.9)
            pl.record_preference("user-1", "communication_style", "concise")
            model = pl.get_model("user-1")
            self.assertEqual(model.user_id, "user-1")
            self.assertIn("ai", model.learned_topics)
            self.assertEqual(model.communication_style, "concise")
            pl.close()

    def test_stats(self):
        from src.thinking.preference_learner import PreferenceLearner
        with tempfile.TemporaryDirectory() as td:
            db = os.path.join(td, "prefs.db")
            pl = PreferenceLearner(db_path=db)
            pl.record_preference("u1", "k", "v")
            stats = pl.stats()
            self.assertEqual(stats["preferences"], 1)
            pl.close()


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 10: User Profile Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestUserProfile(unittest.TestCase):
    """Test user profile CRUD operations."""

    def test_create_and_get(self):
        from src.thinking.user_profile import UserProfileStore
        with tempfile.TemporaryDirectory() as td:
            db = os.path.join(td, "profiles.db")
            store = UserProfileStore(db_path=db)
            profile = store.create_or_update("alice", name="Alice")
            self.assertEqual(profile.user_id, "alice")
            self.assertEqual(profile.name, "Alice")
            fetched = store.get_by_user_id("alice")
            self.assertIsNotNone(fetched)
            self.assertEqual(fetched.name, "Alice")
            store.close()

    def test_update_increments_count(self):
        from src.thinking.user_profile import UserProfileStore
        with tempfile.TemporaryDirectory() as td:
            db = os.path.join(td, "profiles.db")
            store = UserProfileStore(db_path=db)
            store.create_or_update("bob", name="Bob")
            store.create_or_update("bob", name="Bob")
            profile = store.get_by_user_id("bob")
            self.assertEqual(profile.interaction_count, 1)
            store.close()

    def test_add_topic(self):
        from src.thinking.user_profile import UserProfileStore
        with tempfile.TemporaryDirectory() as td:
            db = os.path.join(td, "profiles.db")
            store = UserProfileStore(db_path=db)
            store.create_or_update("carol", name="Carol")
            store.add_topic("carol", "AI Safety")
            store.add_topic("carol", "Robotics")
            profile = store.get_by_user_id("carol")
            self.assertIn("AI Safety", profile.topics_of_interest)
            self.assertIn("Robotics", profile.topics_of_interest)
            store.close()

    def test_update_skill_level(self):
        from src.thinking.user_profile import UserProfileStore
        with tempfile.TemporaryDirectory() as td:
            db = os.path.join(td, "profiles.db")
            store = UserProfileStore(db_path=db)
            store.create_or_update("dave", name="Dave")
            store.update_skill_level("dave", "rust", 0.7)
            profile = store.get_by_user_id("dave")
            self.assertEqual(profile.skill_levels["rust"], 0.7)
            store.close()

    def test_search(self):
        from src.thinking.user_profile import UserProfileStore
        with tempfile.TemporaryDirectory() as td:
            db = os.path.join(td, "profiles.db")
            store = UserProfileStore(db_path=db)
            store.create_or_update("eve", name="Eve")
            results = store.search("eve")
            self.assertEqual(len(results), 1)
            store.close()

    def test_stats(self):
        from src.thinking.user_profile import UserProfileStore
        with tempfile.TemporaryDirectory() as td:
            db = os.path.join(td, "profiles.db")
            store = UserProfileStore(db_path=db)
            store.create_or_update("u1")
            stats = store.stats()
            self.assertEqual(stats["total_profiles"], 1)
            store.close()


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 11: Cross-Module Integration Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestCrossModuleIntegration(unittest.TestCase):
    """Test end-to-end flows spanning multiple modules."""

    def test_healing_recovery_full_flow(self):
        """Full flow: detect failure → recovery handler → reset → healthy."""
        from src.core.self_healing import (
            SelfHealingOrchestrator, RecoveryAction, FailureLevel
        )
        orch = SelfHealingOrchestrator({
            "phi_threshold": 0.3,
            "check_interval": 0.05,
            "acceptable_pause": 0.01,
        })
        orch.detector.min_samples = 3
        orch.monitor("api", "service")

        async def fake_handler(cid, action):
            return True

        orch.recovery.register_handler("service", fake_handler)

        # Send enough heartbeats to populate stats
        for _ in range(15):
            orch.heartbeat("api")
            time.sleep(0.03)
        # Now stop heartbeats and wait for phi to rise above threshold
        time.sleep(0.8)

        phi = orch.detector.compute_phi("api")
        health = orch.detector.get_health("api")
        self.assertEqual(health.level, FailureLevel.FAILED, f"phi={phi:.3f}")

        # Trigger recovery
        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(
            orch.recovery.check_and_recover("api", "service", RecoveryAction.RESTART)
        )
        loop.close()
        self.assertTrue(result)
        self.assertEqual(orch.detector.get_health("api").level, FailureLevel.HEALTHY)

    def test_user_profile_drives_prompt(self):
        """User profile data flows into prompt generation."""
        from src.thinking.user_profile import UserProfileStore
        from src.thinking.self_prompt import SelfPromptGenerator
        with tempfile.TemporaryDirectory() as td:
            db = os.path.join(td, "profiles.db")
            store = UserProfileStore(db_path=db)
            store.create_or_update("test-user", name="Tester")
            store.add_topic("test-user", "AI")
            store.update_skill_level("test-user", "python", 0.8)
            gen = SelfPromptGenerator(user_store=store)
            block = gen.generate_system_prompt_block("test-user")
            self.assertIn("Tester", block)
            self.assertIn("AI", block)
            store.close()

    def test_curiosity_drives_task_generation(self):
        """Curiosity suggestions feed into task generation."""
        from src.thinking.curiosity_drive import CuriosityDrive
        from src.thinking.self_task_generator import SelfTaskGenerator
        cd = CuriosityDrive()
        goals = cd.suggest_from_novelty(
            recent_topics=["quantum", "bioethics"],
            known_topics=["quantum"],
        )
        gen = SelfTaskGenerator()
        tasks = [gen.from_exploration(g) for g in goals]
        tasks = [t for t in tasks if t is not None]
        self.assertGreater(len(tasks), 0)
        self.assertEqual(tasks[0].task_type, "exploration")

    def test_self_modify_end_to_end(self):
        """Propose → approve → apply → verify content changed."""
        from src.colony.evolution.self_modify import SelfModifyEngine
        with tempfile.TemporaryDirectory() as td:
            fp = os.path.join(td, "src", "app.py")
            os.makedirs(os.path.dirname(fp))
            with open(fp, "w") as f:
                f.write("# v1\ndef run(): pass\n")
            engine = SelfModifyEngine(codebase_root=td, require_approval=True, allowed_paths=["src"])
            prop = engine.propose_change(
                change_type="feature", file_path=fp, description="Add return",
                original_snippet="def run(): pass", proposed_snippet="def run():\n    return 42",
                rationale="Better",
            )
            self.assertTrue(engine.approve(prop.id))
            result = engine.apply(prop.id)
            self.assertTrue(result.success)
            with open(fp) as f:
                content = f.read()
            self.assertIn("return 42", content)
            self.assertIn("# v1", content)  # Original comment preserved


# ═══════════════════════════════════════════════════════════════════════════════
# Runner
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    unittest.main(verbosity=2)
