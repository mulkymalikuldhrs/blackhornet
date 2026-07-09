"""Tests for ORCA parallel agent orchestration."""

from __future__ import annotations

from src.agents.orca import OrcaOrchestrator, AgentWorktree


class TestOrcaOrchestrator:
    def test_create_worktree(self):
        o = OrcaOrchestrator()
        wt = o.create_worktree("test-agent", "coder")
        assert wt.name == "test-agent"
        assert wt.agent_type == "coder"
        assert wt.status == "ready"

    def test_list_worktrees(self):
        o = OrcaOrchestrator()
        o.create_worktree("wt1")
        o.create_worktree("wt2")
        assert len(o.list_worktrees()) == 2

    def test_get_worktree(self):
        o = OrcaOrchestrator()
        wt = o.create_worktree("find-me")
        found = o.get_worktree(wt.id)
        assert found is not None
        assert found.name == "find-me"
        assert o.get_worktree("nonexistent") is None

    def test_race(self):
        o = OrcaOrchestrator()
        task = o.race("test prompt", agent_types=["coder", "planner"])
        assert task.status == "completed"
        assert len(task.results) == 2
        assert task.best_result is not None

    def test_fan_out(self):
        o = OrcaOrchestrator()
        results = o.fan_out("fan test", count=3)
        assert len(results) == 3

    def test_task_history(self):
        o = OrcaOrchestrator()
        o.race("task 1")
        o.race("task 2")
        assert len(o.task_history()) == 2

    def test_stats(self):
        o = OrcaOrchestrator()
        stats = o.stats()
        assert "worktrees" in stats
        assert "tasks_completed" in stats
