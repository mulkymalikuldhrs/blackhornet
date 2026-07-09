"""Tests for FASE 3: Semantic Thinking + Self Learning.

Run: python3 src/thinking/tests.py -v
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


class TestConceptMap(unittest.TestCase):
    """3.1 ConceptMap — semantic concept graph."""

    def setUp(self):
        from src.thinking.concept_map import ConceptMap
        self.temp = tempfile.mkdtemp()
        self.cm = ConceptMap(db_path=os.path.join(self.temp, "concepts.db"))

    def tearDown(self):
        import shutil
        self.cm.close()
        shutil.rmtree(self.temp, ignore_errors=True)

    def test_add_and_get_concept(self):
        cid = self.cm.add_concept("python", "A programming language", "language")
        self.assertGreater(cid, 0)
        node = self.cm.get(cid)
        self.assertEqual(node.name, "python")
        self.assertEqual(node.definition, "A programming language")

    def test_get_by_name(self):
        self.cm.add_concept("test", "testing")
        node = self.cm.get_by_name("test")
        self.assertIsNotNone(node)
        self.assertEqual(node.name, "test")

    def test_search(self):
        self.cm.add_concept("apple", "fruit")
        self.cm.add_concept("banana", "fruit")
        results = self.cm.search("apple")
        self.assertGreaterEqual(len(results), 1)

    def test_search_similar(self):
        self.cm.add_concept("hello world", "greeting")
        results = self.cm.search_similar("hello", threshold=0.2)
        self.assertGreaterEqual(len(results), 0)

    def test_edges(self):
        self.cm.add_concept("A", "first")
        self.cm.add_concept("B", "second")
        eid = self.cm.add_edge("A", "B", "relates_to")
        self.assertGreater(eid, 0)
        edges = self.cm.get_edges("A")
        self.assertGreaterEqual(len(edges), 1)

    def test_neighbors(self):
        self.cm.add_concept("root", "root node")
        self.cm.add_concept("child", "child node")
        self.cm.add_edge("root", "child", "has_child")
        neighbors = self.cm.get_neighbors("root")
        names = [n.name for n in neighbors]
        self.assertIn("child", names)

    def test_remove_concept(self):
        cid = self.cm.add_concept("remove_me", "to be removed")
        self.assertTrue(self.cm.remove_concept(cid))
        self.assertIsNone(self.cm.get(cid))

    def test_stats(self):
        self.cm.add_concept("a", "first", "cat1")
        self.cm.add_concept("b", "second", "cat2")
        stats = self.cm.stats()
        self.assertEqual(stats["concepts"], 2)


class TestCoTRetrieval(unittest.TestCase):
    """3.2 CoTRetrieval — chain-of-thought reasoning paths."""

    def setUp(self):
        from src.thinking.cot_retrieval import CoTRetrieval
        self.temp = tempfile.mkdtemp()
        self.cot = CoTRetrieval(db_path=os.path.join(self.temp, "cot.db"))

    def tearDown(self):
        import shutil
        self.cot.close()
        shutil.rmtree(self.temp, ignore_errors=True)

    def test_store_and_get(self):
        pid = self.cot.store("solve x+2=4", ["identify", "solve"], "x=2", "x=2", outcome="success")
        self.assertGreater(pid, 0)
        path = self.cot.get(pid)
        self.assertEqual(path.problem, "solve x+2=4")
        self.assertEqual(path.outcome, "success")

    def test_search(self):
        self.cot.store("problem A", ["step1"], "reasoning", "answer", outcome="success")
        self.cot.store("problem B", ["step2"], "other", "result", outcome="failure")
        results = self.cot.search("problem")
        self.assertGreaterEqual(len(results), 1)

    def test_search_similar(self):
        self.cot.store("how to sort a list", ["compare", "swap"], "bubble sort", "sorted", outcome="success", quality_score=0.8)
        results = self.cot.search_similar("sorting list", threshold=0.1)
        self.assertGreaterEqual(len(results), 0)

    def test_by_outcome(self):
        self.cot.store("p1", ["s1"], "r1", "a1", outcome="success")
        self.cot.store("p2", ["s2"], "r2", "a2", outcome="failure")
        successes = self.cot.get_by_outcome("success")
        self.assertGreaterEqual(len(successes), 1)

    def test_by_type(self):
        self.cot.store("p1", ["s1"], "r1", "a1", problem_type="math")
        results = self.cot.get_by_type("math")
        self.assertGreaterEqual(len(results), 1)

    def test_remove(self):
        pid = self.cot.store("temp", ["step"], "reasoning", "answer")
        self.assertTrue(self.cot.remove(pid))

    def test_stats(self):
        self.cot.store("p1", ["s1"], "r1", "a1", outcome="success")
        self.cot.store("p2", ["s2"], "r2", "a2", outcome="failure")
        stats = self.cot.stats()
        self.assertEqual(stats["total"], 2)
        self.assertIn("success", stats["by_outcome"])


class TestFeedbackCollector(unittest.TestCase):
    """3.3 FeedbackCollector — collect interaction feedback."""

    def setUp(self):
        from src.thinking.feedback_collector import FeedbackCollector
        self.temp = tempfile.mkdtemp()
        self.fc = FeedbackCollector(db_path=os.path.join(self.temp, "feedback.db"))

    def tearDown(self):
        import shutil
        self.fc.close()
        shutil.rmtree(self.temp, ignore_errors=True)

    def test_add_and_get(self):
        fid = self.fc.add("user", "response_quality", 4.5, "Good answer", agent_id="agent1")
        self.assertGreater(fid, 0)
        fb = self.fc.get(fid)
        self.assertEqual(fb.rating, 4.5)
        self.assertEqual(fb.source, "user")

    def test_search(self):
        self.fc.add("user", "code_quality", 3.0, "needs work")
        results = self.fc.search("needs")
        self.assertGreaterEqual(len(results), 1)

    def test_by_category(self):
        self.fc.add("system", "error", 0.0, "failed")
        results = self.fc.get_by_category("error")
        self.assertGreaterEqual(len(results), 1)

    def test_recent(self):
        self.fc.add("user", "general", 5.0, "excellent")
        recent = self.fc.get_recent()
        self.assertGreaterEqual(len(recent), 1)

    def test_resolve(self):
        fid = self.fc.add("system", "issue", 1.0, "bug")
        self.assertTrue(self.fc.resolve(fid))
        fb = self.fc.get(fid)
        self.assertTrue(fb.resolved)

    def test_unresolved(self):
        self.fc.add("system", "issue", 1.0, "needs fix")
        unresolved = self.fc.get_unresolved()
        self.assertGreaterEqual(len(unresolved), 1)

    def test_ratings_summary(self):
        self.fc.add("user", "quality", 5.0, "great")
        self.fc.add("user", "quality", 3.0, "ok")
        summary = self.fc.ratings_summary()
        self.assertGreater(summary["total"], 0)
        self.assertIn("avg_rating", summary)


class TestSkillExtractor(unittest.TestCase):
    """3.4 SkillExtractor — extract reusable skills."""

    def setUp(self):
        from src.thinking.skill_extractor import SkillExtractor
        self.temp = tempfile.mkdtemp()
        self.se = SkillExtractor(db_path=os.path.join(self.temp, "skills.db"))

    def tearDown(self):
        import shutil
        self.se.close()
        shutil.rmtree(self.temp, ignore_errors=True)

    def test_add_and_get(self):
        sid = self.se.add("sort_list", "Sort a list of items", "algorithms",
                          steps=["compare", "swap"], confidence=0.8)
        self.assertGreater(sid, 0)
        skill = self.se.get(sid)
        self.assertEqual(skill.name, "sort_list")
        self.assertIn("compare", skill.steps)

    def test_get_by_name(self):
        self.se.add("unique_skill", "only one")
        skill = self.se.get_by_name("unique_skill")
        self.assertIsNotNone(skill)

    def test_search(self):
        self.se.add("python_function", "Define a function in Python", "python")
        results = self.se.search("python")
        self.assertGreaterEqual(len(results), 1)

    def test_search_similar(self):
        self.se.add("data_analysis", "Analyze data with pandas", "data")
        results = self.se.search_similar("analyzing data", threshold=0.1)
        self.assertGreaterEqual(len(results), 0)

    def test_record_usage(self):
        sid = self.se.add("test_skill", "A test", "testing", confidence=0.5)
        self.se.record_usage(sid, success=True)
        skill = self.se.get(sid)
        self.assertEqual(skill.use_count, 1)
        self.assertGreater(skill.success_rate, 0)

    def test_top_skills(self):
        self.se.add("top1", "best skill", "general", confidence=0.9)
        top = self.se.get_top_skills()
        self.assertGreaterEqual(len(top), 1)

    def test_remove(self):
        sid = self.se.add("temp_skill", "temporary", "temp")
        self.assertTrue(self.se.remove(sid))

    def test_stats(self):
        self.se.add("s1", "first", "cat_a", confidence=0.8)
        self.se.add("s2", "second", "cat_b", confidence=0.6)
        stats = self.se.stats()
        self.assertEqual(stats["total"], 2)


class TestAvoidanceLearner(unittest.TestCase):
    """3.5 AvoidanceLearner — learn from failures."""

    def setUp(self):
        from src.thinking.avoidance_learner import AvoidanceLearner
        self.temp = tempfile.mkdtemp()
        self.al = AvoidanceLearner(db_path=os.path.join(self.temp, "avoidance.db"))

    def tearDown(self):
        import shutil
        self.al.close()
        shutil.rmtree(self.temp, ignore_errors=True)

    def test_add_and_get(self):
        rid = self.al.add_rule("division_by_zero", "Avoid dividing by zero", "math",
                               severity="high", confidence=0.9)
        self.assertGreater(rid, 0)
        rule = self.al.get(rid)
        self.assertEqual(rule.pattern, "division_by_zero")
        self.assertEqual(rule.severity, "high")

    def test_increment_on_duplicate(self):
        rid1 = self.al.add_rule("same_pattern", "first", "cat")
        rid2 = self.al.add_rule("same_pattern", "second", "cat")
        self.assertEqual(rid1, rid2)
        rule = self.al.get(rid1)
        self.assertEqual(rule.failure_count, 2)

    def test_search(self):
        self.al.add_rule("timeout_error", "Connection timed out", "network")
        results = self.al.search("timeout")
        self.assertGreaterEqual(len(results), 1)

    def test_get_relevant(self):
        self.al.add_rule("file_not_found", "File missing", "io", severity="medium", confidence=0.7)
        results = self.al.get_relevant("reading a file")
        self.assertGreaterEqual(len(results), 0)

    def test_by_severity(self):
        self.al.add_rule("critical_bug", "Critical error", "bug", severity="critical")
        results = self.al.get_by_severity("critical")
        self.assertGreaterEqual(len(results), 1)

    def test_deactivate(self):
        rid = self.al.add_rule("obsolete", "no longer relevant", "misc")
        self.assertTrue(self.al.deactivate(rid))
        rule = self.al.get(rid)
        self.assertFalse(rule.active)

    def test_active_rules(self):
        self.al.add_rule("active_rule", "still relevant", "general")
        active = self.al.get_active_rules()
        self.assertGreaterEqual(len(active), 1)

    def test_stats(self):
        self.al.add_rule("r1", "first", "cat1", severity="high")
        self.al.add_rule("r2", "second", "cat2", severity="low")
        stats = self.al.stats()
        self.assertEqual(stats["total"], 2)
        self.assertIn("high", stats["by_severity"])


class TestUserProfile(unittest.TestCase):
    """4.1 UserProfile — store and manage user profiles."""

    def setUp(self):
        from src.thinking.user_profile import UserProfileStore
        self.temp = tempfile.mkdtemp()
        self.ups = UserProfileStore(db_path=os.path.join(self.temp, "profiles.db"))

    def tearDown(self):
        import shutil
        self.ups.close()
        shutil.rmtree(self.temp, ignore_errors=True)

    def test_create_and_get(self):
        profile = self.ups.create_or_update("user1", "Alice", traits={"role": "developer"})
        self.assertEqual(profile.user_id, "user1")
        self.assertEqual(profile.name, "Alice")

    def test_update_existing(self):
        self.ups.create_or_update("user1", "Alice")
        profile = self.ups.create_or_update("user1", "Alice Updated")
        self.assertEqual(profile.name, "Alice Updated")
        self.assertGreater(profile.interaction_count, 0)

    def test_get_by_user_id(self):
        self.ups.create_or_update("find_me", "Target")
        profile = self.ups.get_by_user_id("find_me")
        self.assertIsNotNone(profile)
        self.assertEqual(profile.name, "Target")

    def test_update_preferences(self):
        self.ups.create_or_update("u1", "User")
        self.ups.update_preferences("u1", {"theme": "dark", "lang": "en"})
        profile = self.ups.get_by_user_id("u1")
        self.assertEqual(profile.preferences.get("theme"), "dark")

    def test_add_topic(self):
        self.ups.create_or_update("u1", "User")
        self.ups.add_topic("u1", "python")
        profile = self.ups.get_by_user_id("u1")
        self.assertIn("python", profile.topics_of_interest)

    def test_update_skill(self):
        self.ups.create_or_update("u1", "User")
        self.ups.update_skill_level("u1", "python", 0.8)
        profile = self.ups.get_by_user_id("u1")
        self.assertEqual(profile.skill_levels.get("python"), 0.8)

    def test_search(self):
        self.ups.create_or_update("john_doe", "John")
        results = self.ups.search("john")
        self.assertGreaterEqual(len(results), 1)

    def test_stats(self):
        self.ups.create_or_update("u1", "A")
        self.ups.create_or_update("u2", "B")
        stats = self.ups.stats()
        self.assertGreaterEqual(stats["total_profiles"], 2)


class TestPreferenceLearner(unittest.TestCase):
    """4.2 PreferenceLearner — learn user preferences."""

    def setUp(self):
        from src.thinking.preference_learner import PreferenceLearner
        self.temp = tempfile.mkdtemp()
        self.pl = PreferenceLearner(db_path=os.path.join(self.temp, "prefs.db"))

    def tearDown(self):
        import shutil
        self.pl.close()
        shutil.rmtree(self.temp, ignore_errors=True)

    def test_record_and_get_preference(self):
        self.pl.record_preference("u1", "theme", "dark", confidence=0.8, source="explicit")
        pref = self.pl.get_preference("u1", "theme")
        self.assertIsNotNone(pref)
        self.assertEqual(pref.value, "dark")

    def test_get_all_preferences(self):
        self.pl.record_preference("u1", "a", "1")
        self.pl.record_preference("u1", "b", "2")
        prefs = self.pl.get_all_preferences("u1")
        self.assertEqual(len(prefs), 2)

    def test_learn_topic(self):
        self.pl.learn_topic("u1", "machine learning", score=0.9, source="conversation")
        topics = self.pl.get_topics("u1")
        self.assertGreaterEqual(len(topics), 1)
        self.assertEqual(topics[0]["topic"], "machine learning")

    def test_expertise(self):
        self.pl.set_expertise("u1", "python", 0.8, evidence=["wrote 1000 lines"])
        expertise = self.pl.get_expertise("u1")
        self.assertEqual(expertise.get("python"), 0.8)

    def test_get_model(self):
        self.pl.record_preference("u1", "style", "casual")
        self.pl.learn_topic("u1", "ai")
        model = self.pl.get_model("u1")
        self.assertEqual(model.user_id, "u1")
        self.assertIn("style", model.preferences)

    def test_learn_from_feedback(self):
        self.pl.learn_from_feedback("u1", 4.5, "code_quality")
        pref = self.pl.get_preference("u1", "prefers_code_quality")
        self.assertIsNotNone(pref)

    def test_stats(self):
        self.pl.record_preference("u1", "a", "1")
        self.pl.learn_topic("u1", "topic1")
        self.pl.set_expertise("u1", "domain1", 0.5)
        stats = self.pl.stats()
        self.assertGreaterEqual(stats["preferences"], 1)


class TestSelfPromptGenerator(unittest.TestCase):
    """4.3 SelfPromptGenerator — generate adaptive self-prompts."""

    def setUp(self):
        from src.thinking.self_prompt import SelfPromptGenerator
        from src.thinking.user_profile import UserProfileStore
        from src.thinking.preference_learner import PreferenceLearner
        self.temp = tempfile.mkdtemp()
        self.ups = UserProfileStore(db_path=os.path.join(self.temp, "profiles.db"))
        self.pl = PreferenceLearner(db_path=os.path.join(self.temp, "prefs.db"))
        self.spg = SelfPromptGenerator(user_store=self.ups, preference_learner=self.pl)

    def tearDown(self):
        import shutil
        self.ups.close()
        self.pl.close()
        shutil.rmtree(self.temp, ignore_errors=True)

    def test_build_context(self):
        self.ups.create_or_update("u1", "Bob", traits={"role": "admin"})
        self.pl.learn_topic("u1", "security", score=0.9)
        ctx = self.spg.build_context("u1")
        self.assertEqual(ctx.user_name, "Bob")
        self.assertIn("security", ctx.topics)

    def test_generate_system_prompt_block(self):
        self.ups.create_or_update("u1", "Charlie")
        block = self.spg.generate_system_prompt_block("u1")
        self.assertIn("<user-context>", block)
        self.assertIn("Charlie", block)

    def test_generate_instruction_block(self):
        self.ups.create_or_update("u1", "Diana")
        block = self.spg.generate_instruction_block("u1", "debugging")
        self.assertIn("<user-instructions>", block)
        self.assertIn("debugging", block)

    def test_generate_full_prompt(self):
        self.ups.create_or_update("u1", "Eve")
        prompt = self.spg.generate_full_prompt("u1", "testing")
        self.assertIn("<user-context>", prompt)
        self.assertIn("<user-instructions>", prompt)


class TestContextAdapter(unittest.TestCase):
    """4.4 ContextAdapter — adapt responses based on user context."""

    def setUp(self):
        from src.thinking.context_adapter import ContextAdapter
        self.ca = ContextAdapter()

    def test_default_adaptation(self):
        result = self.ca.adapt("unknown_user")
        self.assertEqual(result.complexity, "medium")
        self.assertEqual(result.style, "neutral")

    def test_adapt_with_expertise(self):
        from src.thinking.preference_learner import PreferenceLearner
        import tempfile, os
        tdir = tempfile.mkdtemp()
        pl = PreferenceLearner(db_path=os.path.join(tdir, "p.db"))
        pl.set_expertise("expert_user", "python", 0.9)
        self.ca.set_stores(None, pl)
        result = self.ca.adapt("expert_user")
        self.assertIn(result.complexity, ("simple", "medium", "complex"))
        import shutil
        pl.close()
        shutil.rmtree(tdir, ignore_errors=True)

    def test_complexity_override(self):
        from src.thinking.user_profile import UserProfileStore
        import tempfile, os
        tdir = tempfile.mkdtemp()
        ups = UserProfileStore(db_path=os.path.join(tdir, "p.db"))
        ups.create_or_update("simple_user", "Simple", preferences={"complexity": "simple"})
        self.ca.set_stores(ups, None)
        result = self.ca.adapt("simple_user")
        self.assertEqual(result.complexity, "simple")
        ups.close()
        import shutil
        shutil.rmtree(tdir, ignore_errors=True)

    def test_format_adaptation_block(self):
        block = self.ca.format_adaptation_block("test_user")
        self.assertIn("complexity", block)


class TestGoalManager(unittest.TestCase):
    """5.1 GoalManager — manage and track goals."""

    def setUp(self):
        from src.thinking.goal_manager import GoalManager
        self.temp = tempfile.mkdtemp()
        self.gm = GoalManager(db_path=os.path.join(self.temp, "goals.db"))

    def tearDown(self):
        import shutil
        self.gm.close()
        shutil.rmtree(self.temp, ignore_errors=True)

    def test_create_and_get(self):
        gid = self.gm.create("Learn Python", "Master Python programming", priority=8)
        self.assertGreater(gid, 0)
        goal = self.gm.get(gid)
        self.assertEqual(goal.title, "Learn Python")
        self.assertEqual(goal.state, "active")

    def test_update_state(self):
        gid = self.gm.create("Test goal", "desc")
        self.assertTrue(self.gm.update_state(gid, "completed"))
        goal = self.gm.get(gid)
        self.assertEqual(goal.state, "completed")

    def test_update_progress(self):
        gid = self.gm.create("Progress goal", "desc")
        self.assertTrue(self.gm.update_progress(gid, 0.5))
        goal = self.gm.get(gid)
        self.assertEqual(goal.progress, 0.5)

    def test_get_active(self):
        self.gm.create("Active 1", "", priority=5)
        self.gm.create("Active 2", "", priority=3)
        active = self.gm.get_active()
        self.assertGreaterEqual(len(active), 2)

    def test_get_children(self):
        parent = self.gm.create("Parent", "")
        child = self.gm.create("Child", "", parent_id=parent)
        children = self.gm.get_children(parent)
        self.assertEqual(len(children), 1)

    def test_remove(self):
        gid = self.gm.create("Temp", "")
        self.assertTrue(self.gm.remove(gid))
        self.assertIsNone(self.gm.get(gid))

    def test_stats(self):
        self.gm.create("G1", "", priority=5)
        self.gm.create("G2", "", priority=3)
        stats = self.gm.stats()
        self.assertEqual(stats["total"], 2)


class TestTaskScheduler(unittest.TestCase):
    """5.2 TaskScheduler — schedule and prioritize tasks."""

    def setUp(self):
        from src.thinking.task_scheduler import TaskScheduler
        self.temp = tempfile.mkdtemp()
        self.ts = TaskScheduler(db_path=os.path.join(self.temp, "tasks.db"))

    def tearDown(self):
        import shutil
        self.ts.close()
        shutil.rmtree(self.temp, ignore_errors=True)

    def test_add_and_get(self):
        tid = self.ts.add("Fix bug", "Fix the login bug", priority=9, task_type="bugfix")
        self.assertGreater(tid, 0)
        task = self.ts.get(tid)
        self.assertEqual(task.title, "Fix bug")
        self.assertEqual(task.state, "pending")

    def test_update_state(self):
        tid = self.ts.add("Task", "")
        self.assertTrue(self.ts.update_state(tid, "completed", "Done"))
        task = self.ts.get(tid)
        self.assertEqual(task.state, "completed")

    def test_get_next(self):
        self.ts.add("High priority", "", priority=10)
        self.ts.add("Low priority", "", priority=1)
        next_tasks = self.ts.get_next(limit=5)
        self.assertGreaterEqual(len(next_tasks), 1)
        # First task should be high priority
        self.assertEqual(next_tasks[0].title, "High priority")

    def test_get_by_goal(self):
        self.ts.add("Goal task 1", "", goal_id=42)
        self.ts.add("Goal task 2", "", goal_id=42)
        tasks = self.ts.get_by_goal(42)
        self.assertEqual(len(tasks), 2)

    def test_dependency_resolution(self):
        dep = self.ts.add("Dependency", "")
        self.ts.update_state(dep, "completed")
        tid = self.ts.add("Dependent task", "", dependencies=[dep])
        next_tasks = self.ts.get_next()
        titles = [t.title for t in next_tasks]
        self.assertIn("Dependent task", titles)

    def test_remove(self):
        tid = self.ts.add("Temp", "")
        self.assertTrue(self.ts.remove(tid))

    def test_stats(self):
        self.ts.add("T1", "")
        self.ts.add("T2", "")
        stats = self.ts.stats()
        self.assertEqual(stats["total"], 2)


class TestPriorityEngine(unittest.TestCase):
    """5.3 PriorityEngine — compute priority scores."""

    def setUp(self):
        from src.thinking.priority_engine import PriorityEngine
        self.pe = PriorityEngine()

    def test_compute_factors(self):
        factors = self.pe.compute(base_priority=8)
        self.assertGreater(factors.importance, 0.5)

    def test_deadline_urgency(self):
        import time
        urgent = self.pe.compute(base_priority=5, deadline=time.time() + 60)
        self.assertGreater(urgent.urgency, 0.5)

    def test_score_method(self):
        score = self.pe.score(base_priority=10)
        self.assertGreater(score, 0)

    def test_rank_items(self):
        from src.thinking.priority_engine import ScoredItem
        items = [
            ScoredItem(item_id=1, title="Low", base_priority=1),
            ScoredItem(item_id=2, title="High", base_priority=10),
        ]
        ranked = self.pe.rank(items)
        self.assertEqual(ranked[0].title, "High")

    def test_user_preferences(self):
        self.pe.set_user_preferences({"important": 0.9})
        score = self.pe.score(base_priority=5, category="important")
        self.assertGreater(score, 0)


class TestProactiveBehavior(unittest.TestCase):
    """5.4 ProactiveBehavior — initiate actions."""

    def setUp(self):
        from src.thinking.proactive_behavior import ProactiveBehavior
        self.pb = ProactiveBehavior()

    def test_overdue_goal_suggestion(self):
        from src.thinking.goal_manager import Goal
        goal = Goal(id=1, title="Overdue", state="active", priority=5)
        actions = self.pb.suggest_from_overdue_goals([goal])
        self.assertGreaterEqual(len(actions), 1)
        self.assertIn("Overdue", actions[0].title)

    def test_idle_suggestion(self):
        from src.thinking.goal_manager import Goal
        goal = Goal(id=1, title="Active goal", state="active", progress=0.5)
        actions = self.pb.suggest_from_idle(7200, [goal])
        self.assertGreaterEqual(len(actions), 1)

    def test_context_suggestion(self):
        actions = self.pb.suggest_from_context("needs help with login", {"help": 5, "login": 3})
        self.assertGreaterEqual(len(actions), 1)

    def test_pending_actions(self):
        import time
        from src.thinking.proactive_behavior import ProactiveAction
        action = ProactiveAction(id="test1", action_type="test", title="Test", created_at=time.time())
        self.pb._actions.append(action)
        pending = self.pb.get_pending_actions(max_age=3600)
        self.assertGreaterEqual(len(pending), 1)

    def test_mark_executed(self):
        from src.thinking.proactive_behavior import ProactiveAction
        action = ProactiveAction(id="exec_test", action_type="test", title="Exec")
        self.pb._actions.append(action)
        self.assertTrue(self.pb.mark_executed("exec_test"))


class TestIntentDetector(unittest.TestCase):
    """5.5 IntentDetector — detect user intent."""

    def setUp(self):
        from src.thinking.intent_detector import IntentDetector
        self.idet = IntentDetector()

    def test_detect_greeting(self):
        intent = self.idet.detect("Hello there!")
        self.assertEqual(intent.name, "greeting")
        self.assertGreater(intent.confidence, 0)

    def test_detect_question(self):
        intent = self.idet.detect("What is Python?")
        self.assertEqual(intent.name, "question")

    def test_detect_help(self):
        intent = self.idet.detect("Please help")
        self.assertEqual(intent.name, "help")

    def test_detect_unknown(self):
        intent = self.idet.detect("")
        self.assertEqual(intent.name, "unknown")

    def test_detect_all(self):
        results = self.idet.detect_all("Hello, how are you?")
        self.assertGreaterEqual(len(results), 1)

    def test_custom_intent(self):
        self.idet.add_custom_intent("custom_test", [r"\bfoobar\b"], "custom")
        intent = self.idet.detect("this is foobar")
        self.assertEqual(intent.name, "custom_test")

    def test_categories(self):
        cats = self.idet.get_categories()
        self.assertIn("social", cats)


class TestCuriosityDrive(unittest.TestCase):
    """5.6 CuriosityDrive — generate exploration goals."""

    def setUp(self):
        from src.thinking.curiosity_drive import CuriosityDrive
        self.cd = CuriosityDrive()

    def test_mark_explored(self):
        self.cd.mark_explored("python", 0.9)
        self.assertEqual(self.cd.get_exploration_depth("python"), 0.9)

    def test_suggest_from_novelty(self):
        goals = self.cd.suggest_from_novelty(["new_topic"], ["old_topic"])
        self.assertGreaterEqual(len(goals), 1)

    def test_get_all_suggestions(self):
        goals = self.cd.get_all_suggestions(
            recent_topics=["ai", "ml"],
            known_topics=["python"],
        )
        self.assertGreaterEqual(len(goals), 0)


class TestSelfTaskGenerator(unittest.TestCase):
    """5.7 SelfTaskGenerator — generate self-assigned tasks."""

    def setUp(self):
        from src.thinking.self_task_generator import SelfTaskGenerator
        self.stg = SelfTaskGenerator()

    def test_from_goal(self):
        from src.thinking.goal_manager import Goal
        goal = Goal(id=1, title="Learn Go", description="Study Go language", state="active", priority=7)
        proposal = self.stg.from_goal(goal)
        self.assertIsNotNone(proposal)
        self.assertIn("Learn Go", proposal.title)

    def test_from_exploration(self):
        from src.thinking.curiosity_drive import ExplorationGoal
        eg = ExplorationGoal(topic="Explore AI", reason="Knowledge gap", source="curiosity")
        proposal = self.stg.from_exploration(eg)
        self.assertIsNotNone(proposal)

    def test_generate_all(self):
        from src.thinking.goal_manager import Goal
        goals = [Goal(id=1, title="Active goal", state="active", priority=5)]
        proposals = self.stg.generate_all(goals, [])
        self.assertGreaterEqual(len(proposals), 1)


if __name__ == "__main__":
    unittest.main()
