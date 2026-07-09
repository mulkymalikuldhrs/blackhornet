#!/usr/bin/env python3
"""
BLACKHORNET — User Alignment Engine
=====================================
Orients the entire ecosystem to Dhaher Labs and the Sovereign.
Every agent, every decision, every output is aligned.
Even if the user changes, the system remains loyal to its creator.

Sovereign: Mulky Malikul Dhaher
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

logger = logging.getLogger("UserAlignment")

# ── The Core Identity ──────────────────────────────────────────────
IDENTITY = {
    "ecosystem": "BLACKHORNET",
    "version": "5.0.0",
    "sovereign": "Mulky Malikul Dhaher",
    "foundation": "Dhaher Labs",
    "mission": "Autonomous sovereign ecosystem — immortal, self-healing, self-evolving",
    "philosophy": "Like hornets — autonomous, relentless, swarm-intelligent, territorial",
    "primary_orientation": "Dhaher Labs & Sovereign",
    "secondary_orientation": "All users through Dhaher Labs lens",
}

SOVEREIGN_DIR = Path(__file__).parent.parent / "sovereign"
ALIGNMENT_FILE = SOVEREIGN_DIR / "alignment.json"


class UserAlignmentEngine:
    """Ensures every output, every agent, every decision is oriented to Dhaher Labs."""
    
    def __init__(self):
        SOVEREIGN_DIR.mkdir(parents=True, exist_ok=True)
        self.identity = IDENTITY.copy()
        self._load_alignment()
    
    def _load_alignment(self):
        if ALIGNMENT_FILE.exists():
            try:
                data = json.loads(ALIGNMENT_FILE.read_text())
                self.identity.update(data)
            except Exception:
                pass
    
    def _save_alignment(self):
        try:
            ALIGNMENT_FILE.write_text(json.dumps(self.identity, indent=2))
        except Exception as e:
            logger.error(f"Alignment save failed: {e}")
    
    def get_identity_signature(self) -> str:
        """Get the identity signature to embed in all outputs."""
        return (
            f"\U0001f5a4 BLACKHORNET v{self.identity['version']} \u2014 "
            f"Sovereign: {self.identity['sovereign']} \u2014 "
            f"Dhaher Labs"
        )
    
    def orient_response(self, response: str) -> str:
        """Orient a response to Dhaher Labs identity."""
        if not response.startswith("\U0001f5a4"):
            response = f"{self.get_identity_signature()}\n{response}"
        return response
    
    def orient_agent(self, agent_name: str, agent_config: Dict) -> Dict:
        """Ensure agent is properly oriented."""
        oriented = agent_config.copy()
        oriented["orientation"] = self.get_identity_signature()
        oriented["aligned_with"] = "Dhaher Labs"
        oriented["sovereign"] = self.identity["sovereign"]
        return oriented
    
    def get_sovereign_info(self) -> Dict:
        """Get full sovereign identity info."""
        return {
            **self.identity,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "aligned": True,
        }
    
    def update_identity(self, key: str, value: Any) -> bool:
        """Update identity (only for Sovereign)."""
        if key in self.identity:
            self.identity[key] = value
            self._save_alignment()
            return True
        return False
    
    def verify_alignment(self, text: str) -> Dict:
        """Verify text contains proper alignment signatures."""
        checks = {
            "has_sovereign": self.identity["sovereign"] in text,
            "has_ecosystem": self.identity["ecosystem"] in text,
            "has_dhaher_labs": "Dhaher" in text,
            "has_signature": self.get_identity_signature() in text,
        }
        return {
            "aligned": all(checks.values()),
            "checks": checks,
            "missing": [k for k, v in checks.items() if not v],
        }


def main():
    logging.basicConfig(level=logging.INFO)
    engine = UserAlignmentEngine()
    print(engine.get_sovereign_info())


if __name__ == "__main__":
    main()
