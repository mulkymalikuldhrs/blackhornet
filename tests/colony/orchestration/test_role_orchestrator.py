"""Tests for OWL/CAMEL-inspired Role Orchestrator."""

import importlib.util
import os
import unittest

_src = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))
_spec = importlib.util.spec_from_file_location(
    'role_orchestrator',
    os.path.join(_src, 'colony', 'orchestration', 'role_orchestrator.py'),
)
_role_orch = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_role_orch)

RoleOrchestrator = _role_orch.RoleOrchestrator
RoleType = _role_orch.RoleType
AgentRole = _role_orch.AgentRole
CollaborationRound = _role_orch.CollaborationRound


class TestRoleOrchestrator(unittest.TestCase):

    def setUp(self):
        self.orch = RoleOrchestrator()

    def test_assign_role(self):
        self.orch.assign_role("agent-1", RoleType.ANALYST, ["python", "sql"])
        self.assertIn("agent-1", self.orch.roles)
        self.assertEqual(self.orch.roles["agent-1"].role, RoleType.ANALYST)

    def test_get_agents_by_role(self):
        self.orch.assign_role("a1", RoleType.CRITIC)
        self.orch.assign_role("a2", RoleType.EXECUTOR)
        self.orch.assign_role("a3", RoleType.CRITIC)
        critics = self.orch.get_agents_by_role(RoleType.CRITIC)
        self.assertEqual(len(critics), 2)
        self.assertEqual({r.agent_id for r in critics}, {"a1", "a3"})

    def test_get_agents_by_role_none(self):
        self.assertEqual(self.orch.get_agents_by_role(RoleType.PLANNER), [])

    def test_run_collaboration_creates_rounds(self):
        self.orch.assign_role("a1", RoleType.RESEARCHER)
        self.orch.assign_role("a2", RoleType.ANALYST)

        def mock_fn(agent_id, task, role):
            return f"{agent_id} working on {task} as {role.value}"

        rounds = self.orch.run_collaboration("test task", mock_fn, max_rounds=2)
        self.assertEqual(len(rounds), 2)
        for r in rounds:
            self.assertIn("a1", r.contributions)
            self.assertIn("a2", r.contributions)
            self.assertIn("test task", r.contributions["a1"])

    def test_collaboration_round_defaults(self):
        r = CollaborationRound(round_num=1)
        self.assertEqual(r.contributions, {})
        self.assertIsNone(r.consensus)

    def test_agent_role_assignment_id_generated(self):
        r = AgentRole(agent_id="x", role=RoleType.PLANNER)
        self.assertTrue(r.assignment_id.startswith("role-"))
        self.assertEqual(len(r.assignment_id), 13)

    def test_agent_role_capabilities_defaults_to_empty(self):
        r = AgentRole(agent_id="y", role=RoleType.EXECUTOR)
        self.assertEqual(r.capabilities, [])

    def test_role_type_values(self):
        self.assertEqual(RoleType.ANALYST.value, "analyst")
        self.assertEqual(RoleType.CRITIC.value, "critic")
        self.assertEqual(RoleType.EXECUTOR.value, "executor")
        self.assertEqual(RoleType.PLANNER.value, "planner")
        self.assertEqual(RoleType.RESEARCHER.value, "researcher")

    def test_multiple_roles_round(self):
        self.orch.assign_role("p1", RoleType.PLANNER)
        self.orch.assign_role("e1", RoleType.EXECUTOR)

        def static_fn(agent_id, task, role):
            return f"{agent_id}:{role.value}"

        rounds = self.orch.run_collaboration("multi", static_fn, max_rounds=1)
        self.assertIn("p1", rounds[0].contributions)
        self.assertIn("e1", rounds[0].contributions)

    def test_empty_orchestrator_rounds(self):
        def fn(agent_id, task, role):
            return "ok"

        rounds = self.orch.run_collaboration("empty", fn, max_rounds=1)
        self.assertEqual(len(rounds), 1)
        self.assertEqual(rounds[0].contributions, {})

    def test_run_collaboration_zero_rounds(self):
        self.orch.assign_role("a1", RoleType.ANALYST)
        rounds = self.orch.run_collaboration("zero", lambda a, t, r: "", max_rounds=0)
        self.assertEqual(rounds, [])


if __name__ == "__main__":
    unittest.main()
