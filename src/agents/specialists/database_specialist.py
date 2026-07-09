"""Database specialist — Database design, optimization, and management."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.colony_types import AgentSpec, AgentType, Task

logger = logging.getLogger(__name__)


class DatabaseSpecialist(BaseAgent):
    """Specialist agent for database design, optimization, and management.

    Handles schema design, query optimization, indexing strategies,
    connection pooling, and database migration planning.
    """

    def __init__(self, spec: Optional[AgentSpec] = None, **kwargs):
        spec = spec or AgentSpec(agent_type=AgentType.CODER, autonomy_level=3)
        super().__init__(spec=spec, **kwargs)
        self._schemas: Dict[str, Dict[str, Any]] = {}
        self._query_stats: Dict[str, Dict[str, Any]] = {}
        self._indexes: Dict[str, List[Dict[str, Any]]] = {}

    async def on_task(self, task: Task) -> Any:
        action = task.payload.get("action", "execute")
        if action == "design_schema":
            return await self._design_schema(task)
        elif action == "optimize_query":
            return await self._optimize_query(task)
        elif action == "analyze_indexes":
            return await self._analyze_indexes(task)
        elif action == "create_index":
            return await self._create_index(task)
        elif action == "migration_plan":
            return await self._migration_plan(task)
        elif action == "connection_pool_config":
            return await self._connection_pool_config(task)
        elif action == "monitor":
            return self._monitor()
        elif action == "report":
            return self._report()
        return {"success": False, "error": f"Unknown action: {action}"}

    async def on_message(self, message: Dict[str, Any]) -> Any:
        msg_type = message.get("message_type", "")
        if msg_type == "schema_query":
            name = message.get("payload", {}).get("schema", "")
            return self._schemas.get(name, {"found": False})
        elif msg_type == "db_health_check":
            return {"status": "healthy", "schemas": len(self._schemas)}
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        return [
            "schema_design", "query_optimization", "index_management",
            "migration_planning", "connection_pooling", "database_profiling",
            "replication_management", "backup_strategies",
        ]

    async def _design_schema(self, task: Task) -> Dict[str, Any]:
        name = task.payload.get("name", "default_schema")
        tables = task.payload.get("tables", [])
        relations = task.payload.get("relations", [])

        schema = {
            "name": name,
            "tables": {},
            "relations": relations,
            "created_at": time.time(),
            "normalized": True,
        }

        for table in tables:
            table_name = table.get("name", "unnamed")
            columns = table.get("columns", [])
            schema["tables"][table_name] = {
                "columns": columns,
                "primary_key": table.get("primary_key", "id"),
                "indexes": [],
                "constraints": [],
            }

        self._schemas[name] = schema
        logger.info(f"Designed schema: {name} with {len(tables)} tables")
        return {"success": True, "schema": name, "table_count": len(tables)}

    async def _optimize_query(self, task: Task) -> Dict[str, Any]:
        query = task.payload.get("query", "")
        schema_name = task.payload.get("schema", "default")

        optimizations: List[str] = []
        if "SELECT *" in query.upper():
            optimizations.append("avoid_select_star")
        if "WHERE" not in query.upper():
            optimizations.append("add_where_clause")
        if "JOIN" in query.upper() and "ON" not in query.upper():
            optimizations.append("add_join_condition")

        estimated_improvement = len(optimizations) * 15
        return {
            "success": True,
            "query": query[:100],
            "optimizations": optimizations,
            "estimated_improvement_percent": min(estimated_improvement, 80),
        }

    async def _analyze_indexes(self, task: Task) -> Dict[str, Any]:
        schema_name = task.payload.get("schema", "default")
        schema = self._schemas.get(schema_name, {})
        tables = schema.get("tables", {})

        recommendations: List[Dict[str, Any]] = []
        for table_name, table_info in tables.items():
            if not table_info.get("indexes"):
                recommendations.append({
                    "table": table_name,
                    "recommendation": "add_primary_index",
                    "priority": "high",
                })

        return {"success": True, "schema": schema_name, "recommendations": recommendations}

    async def _create_index(self, task: Task) -> Dict[str, Any]:
        table = task.payload.get("table", "")
        columns = task.payload.get("columns", [])
        index_type = task.payload.get("type", "btree")
        unique = task.payload.get("unique", False)

        index_name = f"idx_{table}_{'_'.join(columns)}"
        index = {
            "name": index_name,
            "table": table,
            "columns": columns,
            "type": index_type,
            "unique": unique,
            "created_at": time.time(),
        }

        if table not in self._indexes:
            self._indexes[table] = []
        self._indexes[table].append(index)

        return {"success": True, "index": index_name, "config": index}

    async def _migration_plan(self, task: Task) -> Dict[str, Any]:
        from_schema = task.payload.get("from_schema", {})
        to_schema = task.payload.get("to_schema", {})
        steps = [
            {"step": 1, "action": "backup_current", "description": "Create full database backup"},
            {"step": 2, "action": "create_new_schema", "description": "Deploy new schema version"},
            {"step": 3, "action": "migrate_data", "description": "Migrate data to new schema"},
            {"step": 4, "action": "validate", "description": "Run validation queries"},
            {"step": 5, "action": "swap", "description": "Swap schema versions"},
        ]
        return {"success": True, "migration_steps": steps, "estimated_duration_minutes": len(steps) * 5}

    async def _connection_pool_config(self, task: Task) -> Dict[str, Any]:
        min_connections = task.payload.get("min_connections", 5)
        max_connections = task.payload.get("max_connections", 20)
        timeout_seconds = task.payload.get("timeout_seconds", 30)

        config = {
            "min_connections": min_connections,
            "max_connections": max_connections,
            "timeout_seconds": timeout_seconds,
            "idle_timeout_seconds": task.payload.get("idle_timeout_seconds", 300),
            "validation_query": "SELECT 1",
        }
        return {"success": True, "pool_config": config}

    def _monitor(self) -> Dict[str, Any]:
        return {
            "success": True,
            "metrics": {
                "schemas_count": len(self._schemas),
                "indexes_count": sum(len(idx) for idx in self._indexes.values()),
                "total_tables": sum(len(s.get("tables", {})) for s in self._schemas.values()),
            },
        }

    def _report(self) -> Dict[str, Any]:
        return {
            "success": True,
            "domain": "database",
            "metrics": self._monitor()["metrics"],
        }
