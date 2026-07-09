"""Hermes Nous → BH auto-converter.

Fetches research data from hermes-nous-research repo and converts
into BlackHornet agent updates, consciousness layer improvements,
and new capabilities.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Optional

from src.config.logging_config import get_logger

logger = get_logger("hermes_nous.converter")


class HermesNousConverter:
    """Auto-convert Hermes Nous research data into BH implementations."""

    RESEARCH_DIR = "data/hermes-nous-research"
    CONVERTED_LOG = "data/omega/hermes-conversions.json"

    def __init__(self) -> None:
        self._base = os.environ.get("DHAHERLABS", "/sdcard/dhaherlabs")

    def _research_path(self, *parts: str) -> str:
        return os.path.join(self._base, self.RESEARCH_DIR, *parts)

    def scan_research(self) -> list[dict]:
        """Scan research repo for new data files."""
        results = []
        research_dir = self._research_path()
        if not os.path.isdir(research_dir):
            return results
        for root, dirs, files in os.walk(research_dir):
            for f in files:
                if f.endswith((".md", ".json", ".txt")):
                    path = os.path.join(root, f)
                    results.append({
                        "file": f,
                        "path": path,
                        "size": os.path.getsize(path),
                        "modified": os.path.getmtime(path),
                        "relpath": os.path.relpath(path, research_dir),
                    })
        return sorted(results, key=lambda r: r["modified"], reverse=True)

    def convert_file(self, file_info: dict) -> Optional[dict]:
        """Convert a single research file into BH-compatible data."""
        path = file_info["path"]
        try:
            with open(path) as f:
                content = f.read()
        except Exception as e:
            logger.warning("cannot_read_research_file path=%s err=%s", path, e)
            return None

        conversion = {
            "source_file": file_info["file"],
            "source_path": file_info["relpath"],
            "converted_at": time.time(),
            "content_type": self._detect_type(file_info["file"], content),
            "content_length": len(content),
            "bh_target": self._map_to_bh_module(file_info["file"]),
            "payload": content[:500],
        }
        self._log_conversion(conversion)
        return conversion

    def _detect_type(self, filename: str, content: str) -> str:
        if filename.endswith(".json"):
            return "structured_data"
        if any(kw in content[:200].lower() for kw in ["consciousness", "layer", "l1", "l2", "l3", "l4", "l5", "l6", "l7", "l8"]):
            return "consciousness_layer"
        if any(kw in content[:200].lower() for kw in ["agent", "tool", "function", "capability"]):
            return "agent_capability"
        if any(kw in content[:200].lower() for kw in ["prompt", "template", "system"]):
            return "prompt_template"
        return "research_note"

    def _map_to_bh_module(self, filename: str) -> str:
        name_lower = filename.lower()
        if "consciousness" in name_lower or "layer" in name_lower:
            return "src/hermes_nous/"
        if "agent" in name_lower or "tool" in name_lower:
            return "src/agents/"
        if "memory" in name_lower or "brain" in name_lower:
            return "src/omega/brain.py"
        if "sync" in name_lower or "pipeline" in name_lower:
            return "src/omega/sync.py"
        if "council" in name_lower or "persona" in name_lower:
            return "src/omega/council.py"
        if "genome" in name_lower or "evol" in name_lower:
            return "src/omega/genome.py"
        if "scs" in name_lower or "confidence" in name_lower:
            return "src/omega/scs.py"
        if "predict" in name_lower or "oracle" in name_lower:
            return "src/omega/predictor.py"
        return "src/hermes_nous/"

    def _log_conversion(self, conversion: dict) -> None:
        log_path = os.path.join(self._base, self.CONVERTED_LOG)
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        existing = []
        if os.path.isfile(log_path):
            try:
                with open(log_path) as f:
                    existing = json.load(f)
            except Exception:
                pass
        existing.append(conversion)
        with open(log_path, "w") as f:
            json.dump(existing[-100:], f, indent=2)

    def convert_all(self) -> list[dict]:
        """Scan research directory and convert all new files."""
        files = self.scan_research()
        conversions = []
        for f in files:
            result = self.convert_file(f)
            if result:
                conversions.append(result)
        return conversions

    def status(self) -> dict:
        return {
            "research_dir": self._research_path(),
            "exists": os.path.isdir(self._research_path()),
            "last_scan": time.time(),
        }
