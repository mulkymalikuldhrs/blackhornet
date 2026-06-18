"""ColonyConsciousness — bridges lifecycle events into memory and the knowledge graph.

Gives the colony an evolving sense of its own history and state by:
  - Reading lifecycle events from LifecycleRecorder
  - Storing them in MemorySystem (STM + LTM + Episodic)
  - Syncing to knowledge graph via GraphifySyncBridge
  - Providing a query interface for self-summary, timeline, and state
  - Auto-consolidating events on a periodic loop

Usage:
    cc = ColonyConsciousness(lifecycle_recorder, memory_system, graph_sync)
    await cc.start()
    summary = await cc.self_summary()
    timeline = await cc.timeline(hours=24)
    await cc.stop()
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from typing import Any, Optional

from src.config.logging_config import get_logger

logger = get_logger(__name__)

CONSOLIDATE_INTERVAL = 300


class ColonyConsciousness:
    """Bridges colony lifecycle events into persistent memory and graph awareness.

    Every significant lifecycle event (boot, task, error, agent spawn, milestone)
    is automatically recorded into:
      1. STM — recent events (fast recall)
      2. LTM — persistent searchable memory
      3. Episodic — timeline with agent/task context
      4. Graphify — knowledge graph nodes and edges

    The colony can then answer: "What happened?" / "What is my state?"
    """

    def __init__(
        self,
        lifecycle_recorder: Any = None,
        memory_system: Any = None,
        graph_sync: Any = None,
        colony_id: str = "colony-1",
        consolidate_interval: int = CONSOLIDATE_INTERVAL,
    ) -> None:
        self._lifecycle = lifecycle_recorder
        self._memory = memory_system
        self._graph_sync = graph_sync
        self._colony_id = colony_id
        self._consolidate_interval = consolidate_interval

        self._running = False
        self._tasks: list[asyncio.Task] = []
        self._consolidation_count = 0
        self._last_consolidated: Optional[float] = None
        self._last_event_id_processed: Optional[str] = None
        self._processed_ids: set[str] = set()
        self._processed_count = 0

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._tasks.append(asyncio.create_task(self._consolidate_loop()))
        logger.info("consciousness_started colony=%s", self._colony_id)

    async def stop(self) -> None:
        self._running = False
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        logger.info("consciousness_stopped colony=%s", self._colony_id)

    async def process_events(self, events: Optional[list[dict[str, Any]]] = None) -> int:
        """Process lifecycle events into memory and graph.

        Args:
            events: List of lifecycle event dicts. If None, fetches from LifecycleRecorder.

        Returns:
            Number of events processed.
        """
        if events is None:
            if not self._lifecycle:
                return 0
            events = await self._lifecycle.get_history(limit=200)

        if not events:
            return 0

        count = 0
        for event in events:
            event_id = event.get("id", "")
            event_type = event.get("event_type", "unknown")
            data = event.get("data", {}) or {}
            source = event.get("source", "system")
            timestamp = event.get("timestamp", time.time())

            if event_id and event_id in self._processed_ids:
                continue

            try:
                await self._store_to_stm(event)
                await self._store_to_ltm(event)
                await self._store_to_episodic(event)
                await self._sync_to_graph(event)

                if event_id:
                    self._processed_ids.add(event_id)
                count += 1
            except Exception as e:
                logger.debug("consciousness_event_error type=%s err=%s", event_type, e)

        self._processed_count += count
        return count

    async def self_summary(self) -> dict[str, Any]:
        """Return a human-readable summary of colony state and history.

        Answers: "What happened?" / "What is your state?"
        """
        summary: dict[str, Any] = {
            "colony_id": self._colony_id,
            "timestamp": time.time(),
            "datetime": datetime.now(timezone.utc).isoformat(),
            "processed_events": self._processed_count,
            "consolidations": self._consolidation_count,
            "recent_memories": [],
            "episodic_timeline": [],
            "state": {},
        }

        if self._memory:
            try:
                stm_recent = self._memory.recent_stm(limit=10) if hasattr(self._memory, "recent_stm") else []
                summary["recent_memories"] = stm_recent
            except Exception as e:
                summary["recent_memories_error"] = str(e)

            try:
                epi = self._memory.get_episodes("consciousness", limit=10) if hasattr(self._memory, "get_episodes") else []
                summary["episodic_timeline"] = epi
            except Exception as e:
                summary["episodic_timeline_error"] = str(e)

        if self._lifecycle:
            try:
                lc_summary = await self._lifecycle.get_summary() if hasattr(self._lifecycle, "get_summary") else {}
                summary["lifecycle"] = lc_summary
            except Exception as e:
                summary["lifecycle_error"] = str(e)

            try:
                milestones = await self._lifecycle.get_milestones() if hasattr(self._lifecycle, "get_milestones") else []
                summary["milestones"] = milestones[-5:] if milestones else []
            except Exception as e:
                summary["milestones_error"] = str(e)

        return summary

    async def timeline(
        self,
        hours: int = 24,
        event_type: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Return events from the given time window.

        Args:
            hours: How far back to look.
            event_type: Filter by event type (optional).
            limit: Max events to return.

        Returns:
            List of event dicts.
        """
        results: list[dict[str, Any]] = []

        if self._lifecycle:
            since = time.time() - (hours * 3600)
            events = await self._lifecycle.get_history(
                event_type=event_type if event_type else None,
                since=since,
                limit=limit,
            )
            results.extend(events)

        if self._memory and hasattr(self._memory, "get_timeline"):
            try:
                since = time.time() - (hours * 3600)
                mem_events = self._memory.get_timeline(since, time.time(), limit=limit)
                results.extend(mem_events)
            except Exception as e:
                logger.debug("consciousness_timeline_memory_error err=%s", e)

        results.sort(key=lambda e: e.get("timestamp", 0), reverse=True)
        return results[:limit]

    async def search_memories(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        """Search across all memory stores for a query.

        Args:
            query: Search string.
            limit: Max results.

        Returns:
            Combined search results from LTM + Semantic + Episodic.
        """
        results: list[dict[str, Any]] = []
        if not self._memory:
            return results

        try:
            if hasattr(self._memory, "search"):
                ltm_results = self._memory.search(query, limit=limit)
                if ltm_results:
                    results.extend(ltm_results)
        except Exception as e:
            logger.debug("consciousness_search_ltm_error err=%s", e)

        try:
            if hasattr(self._memory, "search_semantic"):
                sem_results = self._memory.search_semantic(query, limit=limit)
                if sem_results:
                    results.extend(sem_results)
        except Exception as e:
            logger.debug("consciousness_search_sem_error err=%s", e)

        return results[:limit]

    def get_stats(self) -> dict[str, Any]:
        return {
            "running": self._running,
            "processed_events": self._processed_count,
            "consolidations": self._consolidation_count,
            "last_consolidated": self._last_consolidated,
            "lifecycle_wired": self._lifecycle is not None,
            "memory_wired": self._memory is not None,
            "graph_sync_wired": self._graph_sync is not None,
        }

    async def _store_to_stm(self, event: dict[str, Any]) -> None:
        if not self._memory or not hasattr(self._memory, "remember"):
            return
        try:
            event_type = event.get("event_type", "event")
            event_id = event.get("id", str(time.time()))
            content = f"[{event_type}] {event.get('data', {}).get('task_id', event_id)}"
            self._memory.remember(f"lifecycle:{event_id}", content)
        except Exception as e:
            logger.debug("consciousness_stm_error err=%s", e)

    async def _store_to_ltm(self, event: dict[str, Any]) -> None:
        if not self._memory or not hasattr(self._memory, "store"):
            return
        try:
            event_type = event.get("event_type", "event")
            event_id = event.get("id", str(time.time()))
            data = event.get("data", {}) or {}
            content = str(data.get("task_id", data.get("message", data.get("description", ""))))
            tags = [event_type, event.get("source", "system"), "lifecycle"]
            if data.get("agent_id"):
                tags.append(f"agent:{data['agent_id']}")
            self._memory.store(
                key=f"lifecycle:{event_id}",
                content=content or f"Lifecycle event: {event_type}",
                tags=tags,
                importance=0.8 if event_type in ("boot", "error", "milestone") else 0.5,
            )
        except Exception as e:
            logger.debug("consciousness_ltm_error err=%s", e)

    async def _store_to_episodic(self, event: dict[str, Any]) -> None:
        if not self._memory or not hasattr(self._memory, "record_episode"):
            return
        try:
            event_type = event.get("event_type", "event")
            data = event.get("data", {}) or {}
            agent_id = data.get("agent_id", "consciousness")
            summary = f"{event_type}: {str(data.get('task_id', data.get('message', data.get('description', ''))))[:200]}" or f"Lifecycle event: {event_type}"
            outcome = "failure" if event_type == "error" else ("success" if event_type in ("boot", "task_completed") else "")
            self._memory.record_episode(
                agent_id=agent_id,
                event_type=event_type,
                summary=summary[:200],
                outcome=outcome,
            )
        except Exception as e:
            logger.debug("consciousness_episodic_error err=%s", e)

    async def _sync_to_graph(self, event: dict[str, Any]) -> None:
        if not self._graph_sync or not hasattr(self._graph_sync, "sync_lifecycle_event"):
            return
        try:
            self._graph_sync.sync_lifecycle_event(event)
        except Exception as e:
            logger.debug("consciousness_graph_error err=%s", e)

    async def _consolidate_loop(self) -> None:
        while self._running:
            try:
                count = await self.process_events()
                if count > 0:
                    self._consolidation_count += 1
                    self._last_consolidated = time.time()
                    logger.debug("consciousness_consolidated count=%d", count)

                if self._memory and hasattr(self._memory, "consolidate"):
                    try:
                        result = self._memory.consolidate()
                        if result:
                            logger.debug("consciousness_memory_consolidation=%s", result)
                    except Exception as e:
                        logger.debug("consciousness_memory_consolidation_error err=%s", e)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.debug("consciousness_loop_error err=%s", e)

            await asyncio.sleep(self._consolidate_interval)
