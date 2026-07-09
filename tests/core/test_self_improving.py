"""Tests for SelfImprovingAgent (Hermes Agent closed learning loop)."""

import unittest

from src.core.self_improving import SelfImprovingAgent, Skill


class TestSelfImprovingAgent(unittest.TestCase):
    def test_starts_empty(self):
        agent = SelfImprovingAgent("agent-1")
        self.assertEqual(agent.agent_id, "agent-1")
        self.assertEqual(len(agent.skills), 0)
        self.assertEqual(len(agent.experiences), 0)
        self.assertEqual(agent.improvement_count, 0)

    def test_create_skill_adds_to_skills(self):
        agent = SelfImprovingAgent("agent-1")
        skill = agent.create_skill("parse_json", "Parse JSON safely", "def parse(): pass")
        self.assertEqual(skill.name, "parse_json")
        self.assertIn("parse_json", agent.skills)
        self.assertEqual(agent.improvement_count, 1)

    def test_use_skill_updates_usage_and_success_rate(self):
        agent = SelfImprovingAgent("agent-1")
        agent.create_skill("greet", "Say hello", "def greet(): pass")
        agent.use_skill("greet", success=True)
        agent.use_skill("greet", success=False)
        skill = agent.skills["greet"]
        self.assertEqual(skill.usage_count, 2)
        self.assertEqual(skill.success_rate, 0.5)

    def test_use_skill_unknown_returns_none(self):
        agent = SelfImprovingAgent("agent-1")
        result = agent.use_skill("nope", success=True)
        self.assertIsNone(result)

    def test_record_experience_appends(self):
        agent = SelfImprovingAgent("agent-1")
        agent.record_experience("task1", "action1", "success", "good")
        agent.record_experience("task2", "action2", "failure", "bad")
        self.assertEqual(len(agent.experiences), 2)

    def test_get_top_skills_returns_sorted(self):
        agent = SelfImprovingAgent("agent-1")
        agent.create_skill("a", "desc a", "code a")
        agent.create_skill("b", "desc b", "code b")
        agent.create_skill("c", "desc c", "code c")
        agent.use_skill("a", success=True)
        agent.use_skill("a", success=False)
        agent.use_skill("b", success=True)
        agent.use_skill("b", success=True)
        agent.use_skill("c", success=False)
        top = agent.get_top_skills(2)
        self.assertEqual(len(top), 2)
        self.assertEqual(top[0].name, "b")

    def test_learn_from_failures_suggests_skills(self):
        agent = SelfImprovingAgent("agent-1")
        for _ in range(10):
            agent.record_experience("parsing:json", "decode", "failure", "syntax error")
        suggestions = agent.learn_from_failures(threshold=0.3)
        self.assertTrue(any("parsing" in s for s in suggestions))

    def test_learn_from_failures_below_threshold(self):
        agent = SelfImprovingAgent("agent-1")
        agent.record_experience("task1", "act", "success", "ok")
        suggestions = agent.learn_from_failures(threshold=0.3)
        self.assertEqual(suggestions, [])


if __name__ == "__main__":
    unittest.main()
