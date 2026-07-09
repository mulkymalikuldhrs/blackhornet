"""
UnifiedMemoryBridge — BH ⇄ Unified Memory Hub.
Menghubungkan BH MemorySystem ke seluruh ekosistem memori.

Usage:
    from memory.unified_bridge import unified_bridge
    unified_bridge.store("code", "wrote function X", project="blackhornet")
    results = unified_bridge.search("function X")
    unified_bridge.sync_all()
"""

from __future__ import annotations

import json
import os
import time
import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

DHAHER = Path(os.environ.get("DHAHERLABS", "/sdcard/dhaherlabs"))
HUB_SCRIPT = DHAHER / "data" / "ecosystem-memory" / "unified-memory-hub.py"


class UnifiedMemoryBridge:
    """
    Jembatan antara BH Memory System dan UNIFIED MEMORY HUB.
    Setiap write ke BH memory otomatis di-copy ke ecosystem memory + omega.
    Setiap query bisa membaca dari SEMUA sumber memori.
    """

    def __init__(self, agent_id: str = "bh-agent"):
        self.agent_id = agent_id
        self._local_cache: list[dict] = []
        self._max_local = 200

    # ── Canonical Store ──────────────────────────────────────────

    def store(
        self,
        entry_type: str,
        content: str,
        project: str = "ecosystem",
        tags: Optional[list[str]] = None,
        code_snippet: str = "",
        file_path: str = "",
        context: str = "",
        confidence: float = 0.5,
        importance: float = 0.5,
    ) -> dict:
        """Simpan memory ke unified store (ecosystem KB + omega brain)."""
        timestamp = time.time()
        entry = {
            "id": hashlib.sha256(f"bh:{timestamp}:{content[:100]}".encode()).hexdigest()[:12],
            "source_system": "bh",
            "entry_type": entry_type,
            "content": content,
            "project": project,
            "tags": sorted(set(tags or [])),
            "timestamp": timestamp,
            "iso_time": datetime.now(timezone.utc).isoformat(),
            "confidence": confidence,
            "importance": importance,
            "recall_count": 0,
            "file_path": file_path,
            "code_snippet": code_snippet[:2000] if code_snippet else "",
            "context": context,
            "session_id": f"s{int(timestamp / 3600)}",
            "source_agent": self.agent_id,
        }

        # Write to ecosystem knowledge-base.json
        self._write_to_ecosystem_kb(entry)

        # Write to omega second_brain.json
        self._write_to_omega_brain(entry)

        # Cache locally
        self._local_cache.append(entry)
        if len(self._local_cache) > self._max_local:
            self._local_cache = self._local_cache[-self._max_local:]

        return entry

    def _write_to_ecosystem_kb(self, entry: dict) -> None:
        kb_path = DHAHER / "data" / "ecosystem-memory" / "knowledge-base.json"
        try:
            with open(kb_path) as f:
                kb = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            kb = {"version": 2, "entries": []}

        kb.setdefault("entries", [])
        kb["entries"].append({
            "id": entry["id"],
            "type": entry["entry_type"],
            "timestamp": entry["iso_time"],
            "project": entry["project"],
            "tags": entry["tags"],
            "content": entry["content"],
            "code_snippet": entry["code_snippet"],
            "file_path": entry["file_path"],
            "context": entry["context"],
            "recall_count": 0,
            "last_recalled": None,
            "session_id": entry["session_id"],
        })
        kb["updated"] = entry["iso_time"]
        kb["entry_count"] = len(kb["entries"])

        kb_path.parent.mkdir(parents=True, exist_ok=True)
        with open(kb_path, "w") as f:
            json.dump(kb, f, indent=2, ensure_ascii=False)

    def _write_to_omega_brain(self, entry: dict) -> None:
        brain_path = DHAHER / "data" / "omega" / "second_brain.json"
        try:
            with open(brain_path) as f:
                brain = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            brain = {"version": 2, "entries": []}

        brain.setdefault("entries", [])
        brain["entries"].append({
            "id": entry["id"],
            "entry_type": entry["entry_type"],
            "content": entry["content"][:500],
            "project": entry["project"],
            "tags": entry["tags"],
            "timestamp": entry["timestamp"],
            "code_snippet": entry["code_snippet"][:2000],
            "file_path": entry["file_path"],
            "recall_count": 0,
            "session_id": entry["session_id"],
        })

        brain_path.parent.mkdir(parents=True, exist_ok=True)
        with open(brain_path, "w") as f:
            json.dump(brain, f, indent=2, ensure_ascii=False)

    # ── Search Across ALL Systems ────────────────────────────────

    def search(self, query: str, limit: int = 20) -> list[dict]:
        """Search across ALL memory systems."""
        results = []
        q = query.lower()

        # 1. Local cache
        for e in self._local_cache:
            if q in e["content"].lower() or any(q in t.lower() for t in e["tags"]):
                e["_match_from"] = "local_cache"
                results.append(e)

        # 2. Ecosystem KB
        kb_path = DHAHER / "data" / "ecosystem-memory" / "knowledge-base.json"
        try:
            with open(kb_path) as f:
                kb = json.load(f)
            for e in kb.get("entries", []):
                if q in e.get("content", "").lower() or any(q in t.lower() for t in e.get("tags", [])):
                    e["_match_from"] = "ecosystem_kb"
                    results.append(e)
        except (FileNotFoundError, json.JSONDecodeError):
            pass

        # 3. Omega brain
        brain_path = DHAHER / "data" / "omega" / "second_brain.json"
        try:
            with open(brain_path) as f:
                brain = json.load(f)
            for e in brain.get("entries", []):
                if q in e.get("content", "").lower() or any(q in t.lower() for t in e.get("tags", [])):
                    e["_match_from"] = "omega_brain"
                    results.append(e)
        except (FileNotFoundError, json.JSONDecodeError):
            pass

        # Deduplicate by content
        seen = set()
        deduped = []
        for e in results:
            key = e.get("content", e.get("id", ""))[:100]
            if key not in seen:
                seen.add(key)
                deduped.append(e)

        # Sort by timestamp desc
        deduped.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
        return deduped[:limit]

    # ── Sync All Systems ─────────────────────────────────────────

    def sync_all(self) -> dict:
        """Trigger unified memory hub sync across all systems."""
        import subprocess
        try:
            result = subprocess.run(
                ["python3", str(HUB_SCRIPT), "sync"],
                capture_output=True, text=True, timeout=60,
            )
            return {"success": True, "output": result.stdout, "errors": result.stderr}
        except Exception as e:
            logger.error(f"Unified sync failed: {e}")
            return {"success": False, "error": str(e)}

    # ── Stats ────────────────────────────────────────────────────

    def get_stats(self) -> dict:
        """Get unified memory statistics."""
        import subprocess
        try:
            result = subprocess.run(
                ["python3", str(HUB_SCRIPT), "catalog"],
                capture_output=True, text=True, timeout=30,
            )
            catalog_path = DHAHER / "data" / "ecosystem-memory" / "unified-catalog.json"
            try:
                with open(catalog_path) as f:
                    return json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                return {"error": "Catalog not available", "raw": result.stdout}
        except Exception as e:
            return {"error": str(e)}


# ── Singleton ──────────────────────────────────────────────────────

_unified_bridge_instance: Optional[UnifiedMemoryBridge] = None


def get_bridge(agent_id: str = "bh-agent") -> UnifiedMemoryBridge:
    global _unified_bridge_instance
    if _unified_bridge_instance is None:
        _unified_bridge_instance = UnifiedMemoryBridge(agent_id)
    return _unified_bridge_instance


unified_bridge = get_bridge()
