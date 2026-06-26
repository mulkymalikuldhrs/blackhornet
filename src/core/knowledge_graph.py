"""OpenFang-inspired Knowledge Graph for entity-relation storage with persistence."""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import json
import os
import logging

logger = logging.getLogger(__name__)


@dataclass
class Entity:
    id: str
    type: str
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Relation:
    source: str
    target: str
    relation: str
    weight: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class KnowledgeGraph:
    """Entity-relation knowledge graph with JSON persistence."""

    def __init__(self, persist_path: str = "data/knowledge_graph.json"):
        self.persist_path = persist_path
        self.entities: Dict[str, Entity] = {}
        self.relations: List[Relation] = []
        os.makedirs(os.path.dirname(persist_path) or ".", exist_ok=True)
        self._load()

    def add_entity(self, entity: Entity):
        self.entities[entity.id] = entity
        self._save()

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        return self.entities.get(entity_id)

    def add_relation(self, relation: Relation):
        self.relations.append(relation)
        self._save()

    def query(self, entity_id: str, max_depth: int = 2) -> Dict[str, Any]:
        result = {
            "entity": None,
            "relations": [],
            "related_entities": [],
            "paths": [],
        }
        if entity_id in self.entities:
            result["entity"] = {
                "id": self.entities[entity_id].id,
                "type": self.entities[entity_id].type,
                "properties": self.entities[entity_id].properties,
            }

        for r in self.relations:
            if r.source == entity_id:
                result["relations"].append({
                    "source": r.source,
                    "target": r.target,
                    "relation": r.relation,
                    "weight": r.weight,
                })
                if r.target in self.entities:
                    result["related_entities"].append({
                        "id": self.entities[r.target].id,
                        "type": self.entities[r.target].type,
                    })

        if entity_id in self.entities:
            visited = {entity_id}
            queue = [(entity_id, 0, [entity_id])]
            while queue:
                current, depth, path = queue.pop(0)
                if depth >= max_depth:
                    continue
                for r in self.relations:
                    if r.source == current and r.target not in visited:
                        visited.add(r.target)
                        new_path = path + [r.target]
                        result["paths"].append({
                            "path": new_path,
                            "relation": r.relation,
                            "weight": r.weight,
                        })
                        queue.append((r.target, depth + 1, new_path))

        return result

    def get_stats(self) -> Dict[str, Any]:
        return {
            "entities": len(self.entities),
            "relations": len(self.relations),
            "entity_types": list(set(e.type for e in self.entities.values())),
        }

    def _load(self):
        if os.path.exists(self.persist_path):
            try:
                with open(self.persist_path) as f:
                    data = json.load(f)
                    self.entities = {}
                    for eid, edata in data.get("entities", {}).items():
                        self.entities[eid] = Entity(**edata)
                    self.relations = [Relation(**r) for r in data.get("relations", [])]
                logger.info(f"Loaded {len(self.entities)} entities, {len(self.relations)} relations from {self.persist_path}")
            except Exception as e:
                logger.warning(f"Failed to load knowledge graph: {e}")

    def _save(self):
        try:
            data = {
                "entities": {
                    eid: {"id": e.id, "type": e.type, "properties": e.properties}
                    for eid, e in self.entities.items()
                },
                "relations": [
                    {"source": r.source, "target": r.target, "relation": r.relation, "weight": r.weight, "metadata": r.metadata}
                    for r in self.relations
                ],
            }
            with open(self.persist_path, "w") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.warning(f"Failed to save knowledge graph: {e}")