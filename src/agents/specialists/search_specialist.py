"""Search specialist — Search infrastructure and information retrieval."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)


class SearchSpecialist(BaseAgent):
    """Specialist agent for search infrastructure and information retrieval.

    Handles search index management, query optimization, relevance tuning,
    autocomplete, and full-text search capabilities.
    """

    def __init__(self, spec: Optional[AgentSpec] = None, **kwargs):
        spec = spec or AgentSpec(agent_type=AgentType.EXECUTOR, autonomy_level=2)
        super().__init__(spec=spec, **kwargs)
        self._indexes: Dict[str, Dict[str, Any]] = {}
        self._documents: Dict[str, List[Dict[str, Any]]] = {}
        self._search_stats: Dict[str, Dict[str, Any]] = {}

    async def on_task(self, task: Task) -> Any:
        action = task.payload.get("action", "execute")
        if action == "create_index":
            return await self._create_index(task)
        elif action == "index_document":
            return await self._index_document(task)
        elif action == "search":
            return await self._search(task)
        elif action == "configure_synonyms":
            return await self._configure_synonyms(task)
        elif action == "optimize_query":
            return await self._optimize_query(task)
        elif action == "monitor":
            return self._monitor()
        elif action == "report":
            return self._report()
        return {"success": False, "error": f"Unknown action: {action}"}

    async def on_message(self, message: Dict[str, Any]) -> Any:
        msg_type = message.get("message_type", "")
        if msg_type == "search_request":
            query = message.get("payload", {}).get("query", "")
            return await self._search_impl(query)
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "index_management", "document_indexing", "full_text_search",
            "synonym_management", "query_optimization", "relevance_tuning",
            "autocomplete", "faceted_search",
        ]

    async def _create_index(self, task: Task) -> Dict[str, Any]:
        name = task.payload.get("name", "default_index")
        fields = task.payload.get("fields", ["title", "content"])
        settings = task.payload.get("settings", {})

        index = {
            "name": name,
            "fields": fields,
            "settings": {
                "shards": settings.get("shards", 1),
                "replicas": settings.get("replicas", 1),
                "similarity": settings.get("similarity", "bm25"),
                "analyzer": settings.get("analyzer", "standard"),
            },
            "document_count": 0,
            "created_at": time.time(),
        }
        self._indexes[name] = index
        self._documents[name] = []
        self._search_stats[name] = {"queries": 0, "total_results": 0}
        return {"success": True, "index": name, "config": index}

    async def _index_document(self, task: Task) -> Dict[str, Any]:
        index_name = task.payload.get("index", "default_index")
        doc_id = task.payload.get("doc_id", f"doc-{int(time.time())}")
        document = task.payload.get("document", {})

        if index_name not in self._documents:
            self._documents[index_name] = []

        doc = {
            "doc_id": doc_id,
            "index": index_name,
            "data": document,
            "indexed_at": time.time(),
        }
        self._documents[index_name].append(doc)
        if index_name in self._indexes:
            self._indexes[index_name]["document_count"] += 1

        return {"success": True, "doc_id": doc_id, "index": index_name}

    async def _search(self, task: Task) -> Dict[str, Any]:
        query = task.payload.get("query", "")
        index_name = task.payload.get("index", "default_index")
        limit = task.payload.get("limit", 10)

        return await self._search_impl(query, index_name, limit)

    async def _search_impl(self, query: str, index_name: str = "default_index", limit: int = 10) -> Dict[str, Any]:
        documents = self._documents.get(index_name, [])
        query_lower = query.lower()

        results: List[Dict[str, Any]] = []
        for doc in documents:
            data = doc.get("data", {})
            score = 0.0
            for field, value in data.items():
                if isinstance(value, str) and query_lower in value.lower():
                    score += 1.0

            if score > 0:
                results.append({**doc, "score": score})

        results.sort(key=lambda x: x.get("score", 0), reverse=True)
        results = results[:limit]

        if index_name in self._search_stats:
            self._search_stats[index_name]["queries"] += 1
            self._search_stats[index_name]["total_results"] += len(results)

        return {"success": True, "query": query, "results": results, "total": len(results)}

    async def _configure_synonyms(self, task: Task) -> Dict[str, Any]:
        index_name = task.payload.get("index", "default_index")
        synonyms = task.payload.get("synonyms", [])

        if index_name in self._indexes:
            self._indexes[index_name]["synonyms"] = synonyms

        return {"success": True, "index": index_name, "synonyms_count": len(synonyms)}

    async def _optimize_query(self, task: Task) -> Dict[str, Any]:
        query = task.payload.get("query", "")
        optimizations: List[str] = []

        if len(query.split()) > 5:
            optimizations.append("use_phrase_matching")
        if "-" in query or "+" in query:
            optimizations.append("use_boolean_operators")
        optimizations.extend(["use_field_boosting", "enable_fuzzy_matching"])

        return {"success": True, "query": query, "optimizations": optimizations}

    def _monitor(self) -> Dict[str, Any]:
        total_docs = sum(len(d) for d in self._documents.values())
        total_queries = sum(s["queries"] for s in self._search_stats.values())
        return {
            "success": True,
            "metrics": {
                "indexes_count": len(self._indexes),
                "total_documents": total_docs,
                "total_queries": total_queries,
            },
        }

    def _report(self) -> Dict[str, Any]:
        return {
            "success": True,
            "domain": "search",
            "metrics": self._monitor()["metrics"],
        }
