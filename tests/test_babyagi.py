"""Tests for BabyAGI task-driven autonomous agent loop."""

from __future__ import annotations

from src.agents.babyagi import BabyAGI


class TestBabyAGI:
    def test_create_with_objective(self):
        b = BabyAGI("Build a web app")
        assert b.objective == "Build a web app"

    def test_add_objective_creates_tasks(self):
        b = BabyAGI()
        b.add_objective("Test objective")
        assert len(b._tasks) == 3
        assert b.objective == "Test objective"

    def test_add_task(self):
        b = BabyAGI("Test")
        task = b.add_task("Do something", priority=3)
        assert task.description == "Do something"
        assert task.priority == 3
        assert task.status == "pending"

    def test_prioritize(self):
        b = BabyAGI("Test")
        b.add_task("low", priority=1)
        b.add_task("high", priority=10)
        b.add_task("medium", priority=5)
        b.prioritize()
        # Lower priority number = higher priority
        assert b._tasks[0].priority <= b._tasks[-1].priority

    def test_execute_next(self):
        b = BabyAGI("Test")
        b.add_objective("Execute test")
        task = b.execute_next()
        assert task is not None
        assert task.status == "completed"
        assert task.completed_at > 0

    def test_run_loop(self):
        b = BabyAGI("Loop test")
        b.add_objective("Run loop")
        completed = b.run_loop(max_steps=5)
        assert len(completed) == 5

    def test_status(self):
        b = BabyAGI("Status test")
        status = b.status()
        assert "objective" in status
        assert "pending" in status
        assert "completed" in status
