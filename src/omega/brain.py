"""Second Brain (L0) — permanent awareness. Auto-captures everything. Never forgets."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class BrainEntry:
    id: str
    entry_type: str
    content: str
    project: str
    tags: list[str]
    timestamp: float
    code_snippet: str = ""
    file_path: str = ""
    recall_count: int = 0
    session_id: str = ""


class SecondBrain:
    """L0 Second Brain — auto-captures everything, persists across sessions."""

    BRAIN_PATH: str = "data/omega/second_brain.json"
    SESSION_LOG_PATH: str = "data/omega/session_log.json"

    def __init__(self) -> None:
        self._entries: list[BrainEntry] = []
        self._session_history: list[dict] = []
        self._load()

    def _load(self) -> None:
        path = self._resolve_path(self.BRAIN_PATH)
        if os.path.isfile(path):
            try:
                with open(path) as f:
                    data = json.load(f)
                self._entries = [BrainEntry(**e) for e in data.get("entries", [])]
            except Exception:
                pass

        slog = self._resolve_path(self.SESSION_LOG_PATH)
        if os.path.isfile(slog):
            try:
                with open(slog) as f:
                    self._session_history = json.load(f).get("sessions", [])
            except Exception:
                pass

    def _save(self) -> None:
        path = self._resolve_path(self.BRAIN_PATH)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump({"version": 2, "entries": [asdict(e) for e in self._entries[-500:]]}, f, indent=2)

    def _resolve_path(self, rel: str) -> str:
        base = os.environ.get("DHAHERLABS", "/sdcard/dhaherlabs")
        return os.path.join(base, rel)

    def _new_id(self) -> str:
        return f"br-{int(time.time() * 1000)}-{os.urandom(2).hex()}"

    def auto_capture(self, entry_type: str, content: str, project: str = "blackhornet", tags: Optional[list[str]] = None, code_snippet: str = "", file_path: str = "") -> BrainEntry:
        entry = BrainEntry(
            id=self._new_id(),
            entry_type=entry_type,
            content=content[:500],
            project=project,
            tags=tags or [entry_type, project],
            timestamp=time.time(),
            code_snippet=code_snippet[:2000],
            file_path=file_path,
            session_id=f"s{int(time.time() / 3600)}",
        )
        self._entries.append(entry)
        self._save()
        return entry

    def recall_recent(self, limit: int = 10, entry_type: Optional[str] = None) -> list[dict]:
        entries = self._entries
        if entry_type:
            entries = [e for e in entries if e.entry_type == entry_type]
        for e in entries[-limit:]:
            e.recall_count += 1
        self._save()
        return [{"type": e.entry_type, "content": e.content[:100], "project": e.project, "timestamp": e.timestamp} for e in entries[-limit:]]

    def recall_search(self, query: str) -> list[dict]:
        results = []
        for e in self._entries:
            if query.lower() in e.content.lower() or query.lower() in e.project.lower():
                e.recall_count += 1
                results.append(asdict(e))
        self._save()
        return results[-20:]

    def scan_ecosystem(self) -> dict:
        return {
            "entries_count": len(self._entries),
            "types": {t: sum(1 for e in self._entries if e.entry_type == t) for t in set(e.entry_type for e in self._entries)},
            "projects": {p: sum(1 for e in self._entries if e.project == p) for p in set(e.project for e in self._entries)},
            "timestamp": time.time(),
        }

    def wake_up(self) -> dict:
        return {
            "timestamp": time.time(),
            "iso_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "total_entries": len(self._entries),
            "last_sessions": self._session_history[-3:] if self._session_history else [],
            "top_entries": self.recall_recent(5),
        }

    def log_session(self, summary: str, files_changed: Optional[list[str]] = None, decisions: Optional[list[str]] = None) -> None:
        session = {
            "timestamp": time.time(),
            "iso_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "summary": summary,
            "files_changed": files_changed or [],
            "decisions": decisions or [],
        }
        self._session_history.append(session)
        path = self._resolve_path(self.SESSION_LOG_PATH)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump({"sessions": self._session_history[-100:]}, f, indent=2)
