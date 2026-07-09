"""GraphVisualizer — generate graph visualizations in multiple formats.

Produces JSON, ASCII-art, and DOT (Graphviz) representations of the
entity-relationship graph for both Web UI and TUI consumption.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class VisualGraph:
    nodes: List[Dict[str, Any]] = field(default_factory=list)
    edges: List[Dict[str, Any]] = field(default_factory=list)


class GraphVisualizer:
    """Generate graph visualizations in JSON, ASCII, and DOT formats."""

    def __init__(self, graph_store: Any = None, entity_tracker: Any = None,
                 relationship_mapper: Any = None):
        self._graph = graph_store
        self._tracker = entity_tracker
        self._mapper = relationship_mapper

    def set_stores(self, graph_store: Any = None, entity_tracker: Any = None,
                   relationship_mapper: Any = None) -> None:
        if graph_store:
            self._graph = graph_store
        if entity_tracker:
            self._tracker = entity_tracker
        if relationship_mapper:
            self._mapper = relationship_mapper

    def build_graph(self, center: str = "", max_depth: int = 1) -> VisualGraph:
        vg = VisualGraph()
        if self._graph:
            data = self._graph.export_json()
            vg.nodes = data.get("nodes", [])
            vg.edges = data.get("edges", [])
        if self._mapper and center:
            sub = self._mapper.get_graph(center, max_depth)
            node_set = set(sub.get("nodes", []))
            vg.nodes = [n for n in vg.nodes if n.get("label") in node_set]
            vg.edges = sub.get("edges", [])
        return vg

    def to_json(self, center: str = "", max_depth: int = 1, pretty: bool = False) -> str:
        vg = self.build_graph(center, max_depth)
        indent = 2 if pretty else None
        return json.dumps({"nodes": vg.nodes, "edges": vg.edges}, indent=indent)

    def to_dot(self, center: str = "", max_depth: int = 1) -> str:
        vg = self.build_graph(center, max_depth)
        lines = ["digraph KnowledgeGraph {"]
        lines.append('  rankdir=LR;')
        lines.append('  node [shape=box, style=rounded];')

        type_colors = {"concept": "#4A90D9", "person": "#50C878", "task": "#FF6B6B",
                       "goal": "#FFD700", "skill": "#9B59B6", "default": "#95A5A6"}

        for node in vg.nodes:
            ntype = node.get("type", "")
            color = type_colors.get(ntype, type_colors["default"])
            label = node.get("label", "").replace('"', '\\"')
            lines.append(f'  n{node.get("id")} [label="{label}", fillcolor="{color}", style="filled,rounded"];')

        for edge in vg.edges:
            src = f'n{edge.get("source")}'
            tgt = f'n{edge.get("target")}'
            rel = edge.get("relation", "")
            weight = edge.get("weight", 1.0)
            penwidth = max(1, min(5, int(weight * 2)))
            lines.append(f'  {src} -> {tgt} [label="{rel}", penwidth={penwidth}];')

        lines.append("}")
        return "\n".join(lines)

    def to_ascii(self, center: str = "", max_depth: int = 1, max_nodes: int = 20) -> str:
        vg = self.build_graph(center, max_depth)
        nodes = vg.nodes[:max_nodes]
        edges = vg.edges[:max_nodes * 2]

        if not nodes:
            return "(empty graph)"

        lines: List[str] = []
        box_width = 50
        lines.append("╔" + "═" * (box_width - 2) + "╗")
        lines.append(f"║  Knowledge Graph{' ' * (box_width - 20)}║")
        lines.append("╠" + "═" * (box_width - 2) + "╣")

        for node in nodes:
            label = node.get("label", "?")[:40]
            ntype = node.get("type", "")
            nid = node.get("id", "")
            lines.append(f"║  [{nid:>4}] {label:<30} ({ntype})")

        lines.append("╠" + "═" * (box_width - 2) + "╣")
        lines.append(f"║  Edges: {len(edges)}")

        for edge in edges[:10]:
            src = edge.get("source", "")
            tgt = edge.get("target", "")
            rel = edge.get("relation", "")
            lines.append(f"║    {src} --[{rel}]--> {tgt}")

        if len(edges) > 10:
            lines.append(f"║    ... and {len(edges) - 10} more")

        lines.append("╚" + "═" * (box_width - 2) + "╝")
        return "\n".join(lines)

    def to_cytoscape_elements(self, center: str = "", max_depth: int = 1) -> List[Dict[str, Any]]:
        vg = self.build_graph(center, max_depth)
        elements: List[Dict[str, Any]] = []
        for node in vg.nodes:
            elements.append({
                "data": {
                    "id": str(node.get("id", "")),
                    "label": node.get("label", ""),
                    "type": node.get("type", ""),
                }
            })
        for edge in vg.edges:
            elements.append({
                "data": {
                    "source": str(edge.get("source", "")),
                    "target": str(edge.get("target", "")),
                    "label": edge.get("relation", ""),
                    "weight": edge.get("weight", 1.0),
                }
            })
        return elements
