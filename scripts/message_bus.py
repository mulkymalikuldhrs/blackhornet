#!/usr/bin/env python3
"""
BH Cross-Agent Message Bus
===========================
File-based inter-agent messaging system.
Messages stored as JSON files in data/messages/.
Auto-cleanup of messages older than 7 days.

Supports:
- Point-to-point send/receive
- Broadcast to all agents
- Message history between two agents
- Pending message count per agent
"""

import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from threading import Lock

BASE_DIR = Path(__file__).resolve().parent.parent
MESSAGES_DIR = BASE_DIR / "data" / "messages"
os.makedirs(MESSAGES_DIR, exist_ok=True)

MESSAGE_TTL_DAYS = 7


def _timestamp() -> str:
    return datetime.utcnow().isoformat()


def _message_path(msg_id: str) -> Path:
    return MESSAGES_DIR / f"{msg_id}.json"


class MessageBus:
    """
    File-based message bus for inter-agent communication.

    Each message is a JSON file. Messages are auto-cleaned after 7 days.
    Thread-safe via per-operation lock.
    """

    def __init__(self):
        self._lock = Lock()
        self._cleanup_old()

    def send(self, from_agent: str, to_agent: str, subject: str, body: str) -> str:
        """Send a message from one agent to another. Returns message ID."""
        msg_id = f"msg-{int(time.time() * 1000)}-{from_agent}-{to_agent}"
        msg = {
            "id": msg_id,
            "from": from_agent,
            "to": to_agent,
            "subject": subject,
            "body": body,
            "timestamp": _timestamp(),
            "read": False,
        }
        with self._lock:
            _message_path(msg_id).write_text(json.dumps(msg, indent=2))
        return msg_id

    def receive(self, agent_name: str) -> list[dict]:
        """Get all pending (unread) messages for an agent."""
        messages = []
        with self._lock:
            for f in sorted(MESSAGES_DIR.iterdir()):
                if not f.name.endswith(".json"):
                    continue
                try:
                    msg = json.loads(f.read_text())
                except (json.JSONDecodeError, OSError):
                    continue
                if msg.get("to") == agent_name and not msg.get("read"):
                    msg["read"] = True
                    f.write_text(json.dumps(msg, indent=2))
                    messages.append(msg)
        return messages

    def broadcast(self, sender: str, subject: str, body: str) -> list[str]:
        """Send a message to ALL agents. Returns all message IDs."""
        agents = self._discover_agents()
        ids = []
        for agent in agents:
            if agent != sender:
                mid = self.send(sender, agent, subject, body)
                ids.append(mid)
        return ids

    def pending_count(self, agent_name: str) -> int:
        """Count unread messages for an agent."""
        count = 0
        with self._lock:
            for f in MESSAGES_DIR.iterdir():
                if not f.name.endswith(".json"):
                    continue
                try:
                    msg = json.loads(f.read_text())
                except (json.JSONDecodeError, OSError):
                    continue
                if msg.get("to") == agent_name and not msg.get("read"):
                    count += 1
        return count

    def conversation(self, agent1: str, agent2: str) -> list[dict]:
        """Get message history between two agents."""
        msgs = []
        with self._lock:
            for f in sorted(MESSAGES_DIR.iterdir()):
                if not f.name.endswith(".json"):
                    continue
                try:
                    msg = json.loads(f.read_text())
                except (json.JSONDecodeError, OSError):
                    continue
                frm = msg.get("from", "")
                to = msg.get("to", "")
                if {frm, to} == {agent1, agent2}:
                    msgs.append(msg)
        return msgs

    def all_unread(self) -> dict[str, int]:
        """Return dict of agent -> unread count for all agents."""
        counts: dict[str, int] = {}
        with self._lock:
            for f in MESSAGES_DIR.iterdir():
                if not f.name.endswith(".json"):
                    continue
                try:
                    msg = json.loads(f.read_text())
                except (json.JSONDecodeError, OSError):
                    continue
                if not msg.get("read"):
                    to = msg.get("to", "unknown")
                    counts[to] = counts.get(to, 0) + 1
        return counts

    def _discover_agents(self) -> list[str]:
        agents = set()
        agents_dir = BASE_DIR / "src" / "agents"
        if agents_dir.exists():
            for d in agents_dir.iterdir():
                if d.is_dir():
                    agents.add(d.name)
        for f in MESSAGES_DIR.iterdir():
            if not f.name.endswith(".json"):
                continue
            try:
                msg = json.loads(f.read_text())
            except (json.JSONDecodeError, OSError):
                continue
            agents.add(msg.get("from", ""))
            agents.add(msg.get("to", ""))
        return sorted(a for a in agents if a)

    def _cleanup_old(self):
        cutoff = datetime.utcnow() - timedelta(days=MESSAGE_TTL_DAYS)
        with self._lock:
            for f in MESSAGES_DIR.iterdir():
                if not f.name.endswith(".json"):
                    continue
                try:
                    mtime = datetime.fromtimestamp(f.stat().st_mtime)
                    if mtime < cutoff:
                        f.unlink()
                except OSError:
                    continue

    def cleanup(self):
        """Force cleanup of old messages."""
        self._cleanup_old()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="BH Message Bus")
    parser.add_argument("action", choices=["send", "receive", "broadcast", "pending", "conversation", "cleanup"])
    parser.add_argument("--from", dest="from_agent", help="Sender agent name")
    parser.add_argument("--to", help="Recipient agent name")
    parser.add_argument("--subject", default="", help="Message subject")
    parser.add_argument("--body", default="", help="Message body")
    parser.add_argument("--agent", help="Agent name for receive/pending")
    parser.add_argument("--agent2", help="Second agent for conversation")
    args = parser.parse_args()

    bus = MessageBus()

    if args.action == "send":
        if not all([args.from_agent, args.to, args.body]):
            print("--from, --to, and --body are required")
            sys.exit(1)
        mid = bus.send(args.from_agent, args.to, args.subject or "(no subject)", args.body)
        print(f"Sent: {mid}")

    elif args.action == "receive":
        if not args.agent:
            print("--agent is required")
            sys.exit(1)
        msgs = bus.receive(args.agent)
        for m in msgs:
            print(f"[{m['from']}->{m['to']}] {m['subject']}: {m['body'][:100]}")

    elif args.action == "broadcast":
        if not all([args.from_agent, args.body]):
            print("--from and --body are required")
            sys.exit(1)
        ids = bus.broadcast(args.from_agent, args.subject or "(broadcast)", args.body)
        print(f"Broadcast to {len(ids)} agents")

    elif args.action == "pending":
        if args.agent:
            print(f"Pending for {args.agent}: {bus.pending_count(args.agent)}")
        else:
            for agent, count in bus.all_unread().items():
                print(f"  {agent}: {count}")

    elif args.action == "conversation":
        if not all([args.agent, args.agent2]):
            print("--agent and --agent2 are required")
            sys.exit(1)
        msgs = bus.conversation(args.agent, args.agent2)
        for m in msgs:
            status = "READ" if m.get("read") else "UNREAD"
            print(f"[{status}] {m['from']}->{m['to']} ({m['timestamp']}): {m['subject']}")

    elif args.action == "cleanup":
        bus.cleanup()
        print("Cleanup done")
