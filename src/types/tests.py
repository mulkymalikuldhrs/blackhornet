"""Tests for src/types — Pydantic v2 models and enums."""

from __future__ import annotations

import os
import sys
import unittest


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


class TestEnums(unittest.TestCase):
    """Enum definitions."""

    def test_agent_type_values(self):
        from src.types.models import AgentType
        self.assertEqual(AgentType.MANUS.value, "manus")
        self.assertEqual(AgentType.COLONY.value, "colony")

    def test_task_status_values(self):
        from src.types.models import TaskStatus
        self.assertEqual(TaskStatus.PENDING.value, "pending")
        self.assertEqual(TaskStatus.COMPLETED.value, "completed")

    def test_task_priority_ordering(self):
        from src.types.models import TaskPriority
        self.assertLess(TaskPriority.LOW, TaskPriority.CRITICAL)
        self.assertEqual(TaskPriority.MEDIUM, TaskPriority.NORMAL)

    def test_autonomy_level(self):
        from src.types.models import AutonomyLevel
        self.assertEqual(AutonomyLevel.L0_READONLY, 0)
        self.assertEqual(AutonomyLevel.L4_DESTRUCTIVE, 4)

    def test_colony_status(self):
        from src.types.models import ColonyStatus
        for s in ("creating", "active", "paused", "terminating", "terminated"):
            self.assertTrue(hasattr(ColonyStatus, s.upper()))

    def test_event_type_values(self):
        from src.types.models import EventType
        self.assertEqual(EventType.HEARTBEAT.value, "heartbeat")
        self.assertEqual(EventType.SECURITY_ALERT.value, "security_alert")

    def test_channel_type_values(self):
        from src.types.models import ChannelType
        self.assertEqual(ChannelType.TELEGRAM.value, "telegram")
        self.assertEqual(ChannelType.SLACK.value, "slack")


class TestAgentModels(unittest.TestCase):
    """AgentSpec, AgentInfo, AgentCapabilities."""

    def test_agent_spec_defaults(self):
        from src.types.models import AgentSpec
        spec = AgentSpec()
        self.assertTrue(spec.agent_id)
        self.assertEqual(spec.autonomy_level.value, 1)

    def test_agent_spec_with_colony(self):
        from src.types.models import AgentSpec
        spec = AgentSpec(colony_id="col-123")
        self.assertEqual(spec.colony_id, "col-123")

    def test_agent_info_defaults(self):
        from src.types.models import AgentInfo, AgentType
        info = AgentInfo(agent_id="a1", agent_type=AgentType.MANUS)
        self.assertEqual(info.agent_id, "a1")
        self.assertEqual(info.health_score, 1.0)
        self.assertEqual(info.tasks_completed, 0)

    def test_agent_capabilities(self):
        from src.types.models import AgentCapabilities
        cap = AgentCapabilities(tools=["search", "code"])
        self.assertIn("search", cap.tools)
        self.assertEqual(cap.max_concurrent_tasks, 3)


class TestTaskModels(unittest.TestCase):
    """Task, TaskResult, TaskDeadline."""

    def test_task_defaults(self):
        from src.types.models import Task, TaskStatus, TaskPriority
        t = Task()
        self.assertTrue(t.task_id)
        self.assertEqual(t.status, TaskStatus.PENDING)
        self.assertEqual(t.priority, TaskPriority.MEDIUM)
        self.assertEqual(t.max_retries, 3)

    def test_task_with_assignment(self):
        from src.types.models import Task
        t = Task(description="test task", assigned_agent="agent-1")
        self.assertEqual(t.assigned_agent, "agent-1")
        self.assertEqual(t.description, "test task")

    def test_task_result_defaults(self):
        from src.types.models import TaskResult
        r = TaskResult(task_id="t1")
        self.assertTrue(r.success)
        self.assertEqual(r.retry_count, 0)

    def test_task_deadline_absolute(self):
        from datetime import datetime, timezone
        from src.types.models import TaskDeadline
        now = datetime.now(timezone.utc)
        d = TaskDeadline(absolute=now)
        self.assertEqual(d.absolute, now)
        self.assertTrue(d.enforced)

    def test_task_deadline_relative(self):
        from src.types.models import TaskDeadline
        d = TaskDeadline(relative_ms=5000)
        self.assertEqual(d.relative_ms, 5000)


class TestColonyModels(unittest.TestCase):
    """ColonyConfig, ColonyInfo, ColonyHealth."""

    def test_colony_config_defaults(self):
        from src.types.models import ColonyConfig
        c = ColonyConfig()
        self.assertTrue(c.colony_id)
        self.assertEqual(c.scale.value, "medium")
        self.assertEqual(c.max_agents, 50)

    def test_colony_info(self):
        from src.types.models import ColonyInfo, ColonyStatus
        info = ColonyInfo(colony_id="c1", name="test", goal="test goal")
        self.assertEqual(info.status, ColonyStatus.CREATING)

    def test_colony_health(self):
        from src.types.models import ColonyHealth
        h = ColonyHealth(colony_id="c1")
        self.assertEqual(h.overall_score, 1.0)
        self.assertEqual(h.issues, [])


class TestToolModels(unittest.TestCase):
    """ToolSpec, ToolCall, ToolResult."""

    def test_tool_call_to_openai_format(self):
        from src.types.models import ToolCall
        tc = ToolCall(tool_name="search", arguments={"q": "hello"})
        fmt = tc.to_openai_format()
        self.assertEqual(fmt["function"]["name"], "search")

    def test_tool_result_to_message(self):
        from src.types.models import ToolResult
        tr = ToolResult(output="done", success=True)
        msg = tr.to_message()
        self.assertEqual(msg["role"], "tool")
        self.assertEqual(msg["content"], "done")

    def test_tool_result_error_message(self):
        from src.types.models import ToolResult
        tr = ToolResult(success=False, error="oops")
        msg = tr.to_message()
        self.assertIn("Error: oops", msg["content"])


class TestMemoryModels(unittest.TestCase):
    """MemoryPage, TemporalFact, TreeNode, FactQuery."""

    def test_memory_page_defaults(self):
        from src.types.models import MemoryPage
        p = MemoryPage(agent_id="a1", colony_id="c1", session_id="s1")
        self.assertEqual(p.agent_id, "a1")
        self.assertFalse(p.is_compacted)

    def test_temporal_fact(self):
        from src.types.models import TemporalFact
        f = TemporalFact(subject="earth", predicate="orbits", obj="sun")
        self.assertEqual(f.confidence, 1.0)
        self.assertTrue(f.fact_id)

    def test_tree_node(self):
        from src.types.models import TreeNode
        n = TreeNode(path="/root/child")
        self.assertEqual(n.access_count, 0)


class TestSecurityModels(unittest.TestCase):
    """AuditEntry, AuditEvent, RoleDef, etc."""

    def test_audit_entry_defaults(self):
        from src.types.models import AuditEntry
        e = AuditEntry(agent_id="a1", colony_id="c1", tool_name="ls")
        self.assertTrue(e.approved)
        self.assertTrue(e.entry_id)

    def test_role_def(self):
        from src.types.models import RoleDef
        r = RoleDef(name="admin", allowed_tools=["*"])
        self.assertEqual(r.allowed_tools, ["*"])

    def test_permission_check(self):
        from src.types.models import PermissionCheck
        p = PermissionCheck(tool_name="rm", autonomy_level=4)
        self.assertFalse(p.granted)

    def test_approval_request(self):
        from src.types.models import ApprovalRequest
        r = ApprovalRequest(agent_id="a1", colony_id="c1", justification="need it")
        self.assertIsNone(r.approved)

    def test_escalation_record(self):
        from datetime import datetime, timezone, timedelta
        from src.types.models import EscalationRecord, AutonomyLevel
        rec = EscalationRecord(
            agent_id="a1", colony_id="c1",
            from_level=AutonomyLevel.L0_READONLY,
            to_level=AutonomyLevel.L2_MODERATE,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        self.assertEqual(rec.from_level, 0)
        self.assertEqual(rec.to_level, 2)


class TestA2AModels(unittest.TestCase):
    """A2AMessage, A2AHandshake, A2ACapabilityAd."""

    def test_a2a_message_defaults(self):
        from src.types.models import A2AMessage
        m = A2AMessage(
            sender={"agent_id": "a1"},
            recipient={"agent_id": "a2"},
        )
        self.assertEqual(m.version, "1.0")
        self.assertEqual(m.ttl, 300)

    def test_a2a_handshake(self):
        from src.types.models import A2AHandshake
        h = A2AHandshake(initiator_id="a1", responder_id="a2")
        self.assertEqual(h.state, "init")

    def test_a2a_capability_ad(self):
        from src.types.models import A2ACapabilityAd
        ad = A2ACapabilityAd(agent_id="a1", colony_id="c1", capabilities=["search"])
        self.assertTrue(ad.available)


class TestChannelModels(unittest.TestCase):
    """ChannelMessage, ChannelConfig, InlineKeyboard, etc."""

    def test_channel_message_defaults(self):
        from src.types.models import ChannelMessage, ChannelType
        m = ChannelMessage(channel_type=ChannelType.TELEGRAM)
        self.assertTrue(m.message_id)
        self.assertEqual(m.format.value, "markdown")

    def test_inline_keyboard(self):
        from src.types.models import InlineKeyboard
        k = InlineKeyboard(text="Click", callback_data="cb_1")
        self.assertEqual(k.url, "")

    def test_embed_field(self):
        from src.types.models import EmbedField
        f = EmbedField(name="Title", value="Content", inline=True)
        self.assertTrue(f.inline)


class TestEventModel(unittest.TestCase):
    """Event model."""

    def test_event_defaults(self):
        from src.types.models import Event, EventType
        e = Event(event_type=EventType.SYSTEM)
        self.assertTrue(e.event_id)

    def test_event_with_data(self):
        from src.types.models import Event, EventType
        e = Event(event_type=EventType.ACTION, data={"key": "val"})
        self.assertEqual(e.data["key"], "val")


class TestSkillModel(unittest.TestCase):
    """SkillDef model."""

    def test_skill_def_defaults(self):
        from src.types.models import SkillDef
        s = SkillDef(name="search_skill")
        self.assertEqual(s.version, "1.0.0")
        self.assertEqual(s.autonomy_level.value, 1)


class TestAPIModels(unittest.TestCase):
    """APIError, PaginatedResponse."""

    def test_api_error(self):
        from src.types.models import APIError
        e = APIError(code="NOT_FOUND", message="missing")
        self.assertEqual(e.code, "NOT_FOUND")

    def test_paginated_response(self):
        from src.types.models import PaginatedResponse
        r = PaginatedResponse(items=[1, 2, 3], total=3)
        self.assertEqual(len(r.items), 3)
        self.assertFalse(r.has_next)


class TestTypesInitExports(unittest.TestCase):
    """Verify types/__init__.py exports all expected symbols."""

    def test_all_exported_symbols_importable(self):
        import src.types
        expected = [
            "AgentType", "AgentState", "AutonomyLevel", "ColonyStatus",
            "TaskStatus", "TaskPriority", "ToolCategory", "MemoryTier",
            "HandType", "EventType", "ChannelType", "Task", "TaskResult",
            "ToolCall", "ToolResult", "AgentSpec", "AgentInfo",
            "ColonyConfig", "ColonyInfo", "ColonyHealth",
            "MemoryPage", "TemporalFact", "TreeNode",
            "A2AMessage", "A2AHandshake", "A2ACapabilityAd",
            "SkillDef", "APIError", "PaginatedResponse",
        ]
        for name in expected:
            with self.subTest(symbol=name):
                self.assertTrue(hasattr(src.types, name), f"Missing {name}")


if __name__ == "__main__":
    unittest.main()
