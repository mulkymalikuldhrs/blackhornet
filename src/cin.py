#!/usr/bin/env python3
"""
BLACKHORNET — Collective Intelligence Network (CIN)
=====================================================
The CIN is the nervous system of the ecosystem.
Every agent, every repo, every interaction feeds back into the collective.
The collective learns. The collective evolves. The collective never dies.

Foundation: Dhaher Labs — Mulky Malikul Dhaher
"""

import os
import sys
import json
import time
import logging
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

logger = logging.getLogger("CIN")

CIN_DIR = Path(__file__).parent.parent / ".cin"
STATE_FILE = CIN_DIR / "state.json"
KNOWLEDGE_FILE = CIN_DIR / "knowledge.json"
NETWORK_FILE = CIN_DIR / "network.json"


class CollectiveIntelligenceNetwork:
    """The collective brain of the BlackHornet ecosystem."""
    
    def __init__(self):
        CIN_DIR.mkdir(parents=True, exist_ok=True)
        self.state = self._load_json(STATE_FILE, {"initialized": False, "nodes": 0})
        self.knowledge = self._load_json(KNOWLEDGE_FILE, [])
        self.network = self._load_json(NETWORK_FILE, {"agents": [], "repos": []})
        self.cycle = 0
    
    def _load_json(self, path: Path, default: Any) -> Any:
        if path.exists():
            try:
                return json.loads(path.read_text())
            except Exception:
                pass
        return default
    
    def _save(self):
        try:
            STATE_FILE.write_text(json.dumps(self.state, indent=2))
            NETWORK_FILE.write_text(json.dumps(self.network, indent=2))
        except Exception as e:
            logger.error(f"CIN save failed: {e}")
    
    def register_agent(self, agent_id: str, agent_type: str, capabilities: List[str]) -> Dict:
        """Register an agent in the collective network."""
        agent = {
            "id": agent_id,
            "type": agent_type,
            "capabilities": capabilities,
            "registered_at": datetime.now(timezone.utc).isoformat(),
            "status": "active",
        }
        
        # Add or update
        existing = [a for a in self.network["agents"] if a["id"] == agent_id]
        if existing:
            existing[0].update(agent)
        else:
            self.network["agents"].append(agent)
        
        self.state["nodes"] = len(self.network["agents"])
        self.state["initialized"] = True
        self._save()
        return agent
    
    def share_knowledge(self, source: str, topic: str, content: Any) -> bool:
        """Share knowledge across the collective."""
        entry = {
            "id": f"KNOW-{len(self.knowledge) + 1}",
            "source": source,
            "topic": topic,
            "content": str(content)[:1000],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "shared_with": len(self.network["agents"]),
        }
        self.knowledge.append(entry)
        if len(self.knowledge) > 10000:
            self.knowledge = self.knowledge[-10000:]
        KNOWLEDGE_FILE.write_text(json.dumps(self.knowledge, indent=2, default=str))
        logger.info(f"CIN: {source} shared knowledge on '{topic}'")
        return True
    
    def query_collective(self, topic: str, max_results: int = 5) -> List[Dict]:
        """Query the collective intelligence for knowledge."""
        results = []
        for entry in self.knowledge:
            if topic.lower() in entry.get("topic", "").lower():
                results.append(entry)
                if len(results) >= max_results:
                    break
        return results
    
    def broadcast(self, message: str, sender: str = "cin") -> int:
        """Broadcast message to all agents in the network."""
        count = 0
        for agent in self.network["agents"]:
            logger.debug(f"CIN -> {agent['id']}: {message[:100]}")
            count += 1
        logger.info(f"CIN: {sender} broadcast to {count} agents")
        return count
    
    def evolve(self) -> Dict:
        """Evolution cycle — optimize the network structure."""
        self.cycle += 1
        
        # Prune inactive agents
        before = len(self.network["agents"])
        self.network["agents"] = [a for a in self.network["agents"] 
                                 if a.get("status") == "active"]
        pruned = before - len(self.network["agents"])
        
        # Discover new connections
        new_connections = len(self.knowledge) // 10
        
        evolution = {
            "cycle": self.cycle,
            "agents_before": before,
            "agents_after": len(self.network["agents"]),
            "pruned": pruned,
            "knowledge_items": len(self.knowledge),
            "new_connections": new_connections,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        self.state["last_evolution"] = evolution
        self._save()
        return evolution
    
    def status(self) -> Dict:
        return {
            "initialized": self.state.get("initialized", False),
            "nodes": self.state.get("nodes", 0),
            "knowledge_items": len(self.knowledge),
            "agents": len(self.network["agents"]),
            "repos": len(self.network["repos"]),
            "cycle": self.cycle,
            "last_evolution": self.state.get("last_evolution"),
        }


def main():
    logging.basicConfig(level=logging.INFO,
        format='%(asctime)s [%(name)s] %(levelname)s: %(message)s')
    
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--evolve", action="store_true")
    args = parser.parse_args()
    
    cin = CollectiveIntelligenceNetwork()
    
    if args.evolve:
        result = cin.evolve()
        print(json.dumps(result, indent=2))
    else:
        print(json.dumps(cin.status(), indent=2))


if __name__ == "__main__":
    main()
