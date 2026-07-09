"""Tests for PlanLayer state machine."""

import unittest

from src.colony.orchestration.plan_layer import PlanLayer, PlanLayerState, PlanTransitionError


class TestPlanLayer(unittest.TestCase):
    def test_starts_idle(self):
        p = PlanLayer(plan_id="plan-1")
        self.assertEqual(p.state, PlanLayerState.IDLE)

    def test_idle_to_planning(self):
        p = PlanLayer(plan_id="plan-1")
        p.plan()
        self.assertEqual(p.state, PlanLayerState.PLANNING)

    def test_planning_to_approved(self):
        p = PlanLayer(plan_id="plan-1")
        p.plan()
        p.approve()
        self.assertEqual(p.state, PlanLayerState.APPROVED)

    def test_approved_to_executing(self):
        p = PlanLayer(plan_id="plan-1")
        p.plan()
        p.approve()
        p.execute()
        self.assertEqual(p.state, PlanLayerState.EXECUTING)

    def test_executing_to_completed(self):
        p = PlanLayer(plan_id="plan-1")
        p.plan()
        p.approve()
        p.execute()
        p.complete("done")
        self.assertEqual(p.state, PlanLayerState.COMPLETED)

    def test_full_lifecycle(self):
        p = PlanLayer(plan_id="plan-1")
        self.assertEqual(p.state, PlanLayerState.IDLE)
        p.plan()
        self.assertEqual(p.state, PlanLayerState.PLANNING)
        p.approve()
        self.assertEqual(p.state, PlanLayerState.APPROVED)
        p.execute()
        self.assertEqual(p.state, PlanLayerState.EXECUTING)
        p.complete({"result": "ok"})
        self.assertEqual(p.state, PlanLayerState.COMPLETED)

    def test_fail_from_planning(self):
        p = PlanLayer(plan_id="plan-1")
        p.plan()
        p.fail("bad plan")
        self.assertEqual(p.state, PlanLayerState.FAILED)

    def test_fail_from_executing(self):
        p = PlanLayer(plan_id="plan-1")
        p.plan()
        p.approve()
        p.execute()
        p.fail("runtime error")
        self.assertEqual(p.state, PlanLayerState.FAILED)

    def test_illegal_transition_raises(self):
        p = PlanLayer(plan_id="plan-1")
        with self.assertRaises(PlanTransitionError):
            p.approve()  # cannot approve from IDLE

    def test_illegal_transition_from_completed(self):
        p = PlanLayer(plan_id="plan-1")
        p.plan()
        p.approve()
        p.execute()
        p.complete()
        with self.assertRaises(PlanTransitionError):
            p.plan()

    def test_illegal_transition_from_failed(self):
        p = PlanLayer(plan_id="plan-1")
        p.plan()
        p.fail()
        with self.assertRaises(PlanTransitionError):
            p.approve()

    def test_is_terminal_completed(self):
        p = PlanLayer(plan_id="plan-1")
        p.plan()
        p.approve()
        p.execute()
        p.complete()
        self.assertTrue(p.is_terminal)

    def test_is_terminal_failed(self):
        p = PlanLayer(plan_id="plan-1")
        p.plan()
        p.fail()
        self.assertTrue(p.is_terminal)

    def test_is_terminal_false_during_lifecycle(self):
        p = PlanLayer(plan_id="plan-1")
        self.assertFalse(p.is_terminal)
        p.plan()
        self.assertFalse(p.is_terminal)
        p.approve()
        self.assertFalse(p.is_terminal)
        p.execute()
        self.assertFalse(p.is_terminal)

    def test_add_step(self):
        p = PlanLayer(plan_id="plan-1")
        step = p.add_step("research")
        self.assertEqual(step.name, "research")
        self.assertEqual(step.status, PlanLayerState.IDLE)
        self.assertEqual(len(p.steps), 1)

    def test_multiple_steps(self):
        p = PlanLayer(plan_id="plan-1")
        p.add_step("research")
        p.add_step("implement")
        p.add_step("test")
        self.assertEqual(len(p.steps), 3)

    def test_summary(self):
        p = PlanLayer(plan_id="plan-1")
        p.plan()
        s = p.summary
        self.assertEqual(s["plan_id"], "plan-1")
        self.assertEqual(s["state"], "PLANNING")
        self.assertFalse(s["is_terminal"])
        self.assertIn("elapsed_seconds", s)

    def test_elapsed_non_negative(self):
        p = PlanLayer(plan_id="plan-1")
        self.assertGreaterEqual(p.elapsed(), 0)

    def test_transition_error_message(self):
        p = PlanLayer(plan_id="plan-1")
        with self.assertRaises(PlanTransitionError) as ctx:
            p.complete("nope")
        self.assertIn("IDLE", str(ctx.exception))
        self.assertIn("COMPLETED", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
