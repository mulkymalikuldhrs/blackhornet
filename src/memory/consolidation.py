"""MemoryConsolidator – orchestrates STM→LTM→Semantic transfer pipeline.

Sub-agent 2.5: Runs on schedule (hourly STM→LTM, daily LTM→Semantic,
on-demand dedup + archive). Uses the ShortTermMemory, LongTermMemory,
and SemanticMemory classes.
"""

from __future__ import annotations

import json
import logging
import math
import os
import sqlite3
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class ConsolidationReport:
    """Result of a full consolidation pipeline run.

    Attributes
    ----------
    timestamp : str
        ISO-8601 timestamp of when the run started.
    stm_to_ltm : int
        Number of entries moved from short-term to long-term memory.
    ltm_to_semantic : int
        Number of entries extracted from LTM into semantic memory.
    deduplicated : int
        Number of duplicate groups resolved in LTM.
    archived : int
        Number of entries archived to cold storage.
    errors : list[str]
        Error messages collected during the run.
    duration_ms : float
        Wall-clock duration of the full pipeline in milliseconds.
    """
    timestamp: str = ""
    stm_to_ltm: int = 0
    ltm_to_semantic: int = 0
    deduplicated: int = 0
    archived: int = 0
    errors: list[str] = field(default_factory=list)
    duration_ms: float = 0.0


class MemoryConsolidator:
    """Orchestrates memory consolidation between tiers.

    Pipeline
    --------
    1. Hourly: STM → LTM (move recent STM entries to LTM)
    2. Daily: LTM → Semantic (extract important LTM entries into semantic)
    3. On-demand: Dedup + Archive

    Uses the ShortTermMemory, LongTermMemory, and SemanticMemory classes.

    Parameters
    ----------
    stm : ShortTermMemory
        Short-term memory store.
    ltm : LongTermMemory
        Long-term memory store (SQLite + FTS5).
    semantic : SemanticMemory
        Semantic memory store (n-gram + FTS5).
    episodic : EpisodicMemory or None
        Optional episodic memory store for recording consolidation events.
    """

    def __init__(
        self,
        stm: Any,
        ltm: Any,
        semantic: Any,
        episodic: Optional[Any] = None,
    ) -> None:
        self._stm = stm
        self._ltm = ltm
        self._semantic = semantic
        self._episodic = episodic

    # ── Full pipeline ─────────────────────────────────────────────

    def run_consolidation(self) -> ConsolidationReport:
        """Run the full consolidation pipeline.

        Executes each stage in order: STM→LTM, LTM→Semantic,
        deduplication, archival. Errors in one stage do not halt
        subsequent stages — they are collected in the report.

        Returns
        -------
        ConsolidationReport
            Detailed results of the pipeline run.
        """
        start = time.time()
        report = ConsolidationReport(
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        try:
            report.stm_to_ltm = self.consolidate_stm_to_ltm()
        except Exception as exc:
            msg = f"stm_to_ltm failed: {exc}"
            logger.exception(msg)
            report.errors.append(msg)

        try:
            report.ltm_to_semantic = self.consolidate_ltm_to_semantic()
        except Exception as exc:
            msg = f"ltm_to_semantic failed: {exc}"
            logger.exception(msg)
            report.errors.append(msg)

        try:
            report.deduplicated = self.deduplicate()
        except Exception as exc:
            msg = f"deduplicate failed: {exc}"
            logger.exception(msg)
            report.errors.append(msg)

        try:
            report.archived = self.archive_old_entries()
        except Exception as exc:
            msg = f"archive_old_entries failed: {exc}"
            logger.exception(msg)
            report.errors.append(msg)

        report.duration_ms = (time.time() - start) * 1000
        logger.info(
            "Consolidation complete: stm->ltm=%d ltm->semantic=%d "
            "dedup=%d archived=%d errors=%d",
            report.stm_to_ltm,
            report.ltm_to_semantic,
            report.deduplicated,
            report.archived,
            len(report.errors),
        )
        return report

    # ── Stage 1: STM → LTM ────────────────────────────────────────

    def consolidate_stm_to_ltm(self) -> int:
        """Move STM entries older than 30 minutes to LTM.

        For each eligible entry:

        1. FTS5 search in LTM for similar content.
        2. If no near-duplicate found → ``add()`` to LTM with
           auto-tags and STM metadata.
        3. If duplicate found → ``update()`` the existing LTM entry:
           merge content (keep longer), combine tags, take max
           importance, increment merge counter.
        4. Remove the entry from STM.

        Returns
        -------
        int
            Number of entries successfully moved.
        """
        moved = 0
        now = time.time()
        cutoff = now - 1800  # 30 minutes

        entries = self._stm.all_entries()
        for entry in entries:
            if entry.created_at > cutoff:
                continue

            try:
                query_terms = entry.content[:150].strip()
                similar: list[Any] = []
                if query_terms:
                    similar = self._ltm.search(query_terms, limit=3)

                auto_tags = list(entry.metadata.get("tags", [])) if entry.metadata else []
                if "stm" not in auto_tags:
                    auto_tags.append("stm")

                if not similar:
                    self._ltm.add(
                        key=entry.key,
                        content=entry.content,
                        tags=auto_tags,
                        metadata={
                            **(entry.metadata or {}),
                            "consolidated_from": "stm",
                            "stm_created_at": entry.created_at,
                            "consolidated_at": now,
                        },
                        importance=entry.metadata.get("importance", 0.5) if entry.metadata else 0.5,
                    )
                else:
                    best = similar[0]
                    merged_tags = list(set(best.tags + auto_tags))
                    merged_content = (
                        best.content
                        if len(best.content) >= len(entry.content)
                        else entry.content
                    )
                    merged_meta = {
                        **(best.metadata or {}),
                        **(entry.metadata or {}),
                        "consolidated_from": "stm",
                        "merged_at": now,
                        "merge_count": (best.metadata or {}).get("merge_count", 0) + 1,
                    }
                    self._ltm.update(
                        best.id,
                        content=merged_content,
                        tags=merged_tags,
                        metadata=merged_meta,
                        importance=max(
                            best.importance if hasattr(best, "importance") else 0.5,
                            entry.metadata.get("importance", 0.5) if entry.metadata else 0.5,
                        ),
                    )

                self._stm.remove(entry.key)
                moved += 1

            except Exception as exc:
                logger.warning("Failed to consolidate STM entry %s: %s", entry.key, exc)
                continue

        if moved:
            logger.info("Consolidated %d entries from STM to LTM", moved)
        return moved

    # ── Stage 2: LTM → Semantic ───────────────────────────────────

    def consolidate_ltm_to_semantic(self) -> int:
        """Extract important LTM entries into semantic memory.

        Candidates:
        - ``importance > 0.7`` (via ``list_by_importance``)
        - Top 10 % by ``access_count``

        Each candidate is added as a ``SemanticEntry`` with
        ``source="ltm_consolidated"``. The LTM entry's metadata is
        updated with ``consolidated_to_semantic=True`` so it is not
        re-extracted on subsequent runs.

        Returns
        -------
        int
            Number of entries added to semantic memory.
        """
        moved = 0

        important = self._ltm.list_by_importance(min_importance=0.7, limit=200)
        all_entries = self._ltm.all_entries()

        if all_entries:
            sorted_by_access = sorted(all_entries, key=lambda e: e.access_count, reverse=True)
            threshold_idx = max(1, len(sorted_by_access) // 10)
            high_access_ids = {e.id for e in sorted_by_access[:threshold_idx]}
        else:
            high_access_ids = set()

        candidates: dict[int, Any] = {e.id: e for e in important}
        for e in all_entries:
            if e.id in high_access_ids:
                candidates[e.id] = e

        for entry in candidates.values():
            try:
                meta = entry.metadata or {}
                if meta.get("consolidated_to_semantic"):
                    continue

                semantic_meta: dict[str, Any] = {
                    "ltm_id": entry.id,
                    "ltm_key": entry.key,
                    "ltm_importance": entry.importance,
                    "ltm_access_count": entry.access_count,
                    "consolidated_at": time.time(),
                    "original_tags": entry.tags,
                }

                self._semantic.add(
                    text=entry.content,
                    source="ltm_consolidated",
                    metadata=semantic_meta,
                )

                meta["consolidated_to_semantic"] = True
                meta["semantic_consolidated_at"] = time.time()
                self._ltm.update(entry.id, metadata=meta)
                moved += 1

            except Exception as exc:
                logger.warning("Failed to consolidate LTM entry %d: %s", entry.id, exc)
                continue

        if moved:
            logger.info("Consolidated %d entries from LTM to semantic memory", moved)
        return moved

    # ── Stage 3: Deduplication ─────────────────────────────────────

    def deduplicate(self) -> int:
        """Find and merge near-duplicate entries in LTM.

        Uses FTS5 search seeded with each entry's first 150 characters,
        then filters candidates with trigram Jaccard similarity
        (threshold 0.75).  Duplicate groups are merged into the entry
        with the highest ID (latest insertion).  The surviving entry
        receives the longest content, combined tags, summed access
        count, and merged metadata.

        Returns
        -------
        int
            Number of duplicate groups resolved.
        """
        merged_count = 0
        entries = self._ltm.all_entries()
        removed_ids: set[int] = set()

        for entry in entries:
            if entry.id in removed_ids:
                continue

            query_terms = entry.content[:150].strip()
            if not query_terms:
                continue

            try:
                similar = self._ltm.search(query_terms, limit=10)
            except Exception:
                continue

            duplicates = [
                s for s in similar
                if s.id != entry.id
                and s.id not in removed_ids
                and _is_near_duplicate(entry.content, s.content)
            ]

            if not duplicates:
                continue

            # Keep the entry with the highest ID (most recent insertion)
            all_dup = duplicates + [entry]
            primary = max(all_dup, key=lambda d: d.id)
            others = [d for d in all_dup if d.id != primary.id]

            merged_content = primary.content
            merged_tags = list(set(primary.tags))
            merged_access = primary.access_count
            merged_meta: dict[str, Any] = dict(primary.metadata or {})

            for dup in others:
                if len(dup.content) > len(merged_content):
                    merged_content = dup.content
                merged_tags = list(set(merged_tags + dup.tags))
                merged_access += dup.access_count
                merged_meta.update(dup.metadata or {})
                merged_meta[f"dedup_merged_id_{dup.id}"] = True
                self._ltm.remove_by_id(dup.id)
                removed_ids.add(dup.id)

            merged_meta["dedup_merged_at"] = time.time()
            merged_meta["dedup_merge_count"] = len(others)

            self._ltm.update(
                primary.id,
                content=merged_content,
                tags=merged_tags,
                metadata=merged_meta,
                importance=max(
                    primary.importance,
                    *(d.importance for d in others if hasattr(d, "importance")),
                ),
            )

            # Update access_count directly — update() does not support it
            try:
                with sqlite3.connect(self._ltm.db_path) as conn:
                    conn.execute(
                        "UPDATE entries SET access_count = ? WHERE id = ?",
                        (merged_access, primary.id),
                    )
            except Exception as exc:
                logger.warning("Failed to update access_count for LTM entry %d: %s", primary.id, exc)

            removed_ids.add(entry.id if entry.id != primary.id else -1)
            merged_count += 1

        if merged_count:
            logger.info("Deduplicated %d groups in LTM", merged_count)
        return merged_count

    # ── Stage 4: Archival ─────────────────────────────────────────

    def archive_old_entries(self, days: int = 90) -> int:
        """Archive LTM entries older than *days* to cold storage.

        The archive is written as a JSON array to
        ``~/.bh/memory/archive/consolidated-{date}.json``.  If the
        archive file already exists (e.g. from a previous run today),
        new entries are appended.  Archived entries are removed from
        the LTM database.

        Parameters
        ----------
        days : int
            Age threshold in days (default 90).

        Returns
        -------
        int
            Number of entries archived.
        """
        cutoff = time.time() - days * 86400
        entries = [
            e for e in self._ltm.all_entries()
            if e.created_at < cutoff
        ]

        if not entries:
            return 0

        archive_dir = os.path.expanduser("~/.bh/memory/archive")
        os.makedirs(archive_dir, exist_ok=True)

        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        archive_path = os.path.join(archive_dir, f"consolidated-{date_str}.json")

        existing: list[dict[str, Any]] = []
        if os.path.exists(archive_path):
            try:
                with open(archive_path) as f:
                    existing = json.load(f)
            except (json.JSONDecodeError, OSError):
                existing = []

        archive_data: list[dict[str, Any]] = []
        for entry in entries:
            archive_data.append({
                "id": entry.id,
                "key": entry.key,
                "content": entry.content,
                "tags": entry.tags,
                "metadata": entry.metadata,
                "created_at": entry.created_at,
                "accessed_at": entry.accessed_at,
                "access_count": entry.access_count,
                "importance": entry.importance,
                "archived_at": time.time(),
            })

        existing.extend(archive_data)
        with open(archive_path, "w") as f:
            json.dump(existing, f, indent=2)

        removed = 0
        for entry in entries:
            try:
                self._ltm.remove_by_id(entry.id)
                removed += 1
            except Exception as exc:
                logger.warning("Failed to remove archived LTM entry %d: %s", entry.id, exc)

        logger.info("Archived %d entries older than %d days to %s", removed, days, archive_path)
        return removed

    # ── Statistics ─────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        """Return pipeline statistics from all three memory tiers.

        Returns
        -------
        dict
            Keys: ``stm``, ``ltm``, ``semantic``, plus aggregate
            counters ``total_stm``, ``total_ltm``, ``total_semantic``.
        """
        stm_stats = self._stm.stats()
        ltm_stats = self._ltm.stats()
        try:
            sem_stats = self._semantic.stats()
        except Exception as exc:
            logger.warning("Failed to get semantic stats: %s", exc)
            sem_stats = {}

        return {
            "stm": stm_stats,
            "ltm": ltm_stats,
            "semantic": sem_stats,
            "total_stm": stm_stats.get("current_entries", 0),
            "total_ltm": ltm_stats.get("total_entries", 0),
            "total_semantic": sem_stats.get("total_entries", 0),
        }


# ── Helper ─────────────────────────────────────────────────────────

def _is_near_duplicate(a: str, b: str, threshold: float = 0.75) -> bool:
    """Check whether two strings are near-duplicates via trigram similarity.

    Parameters
    ----------
    a : str
        First string.
    b : str
        Second string.
    threshold : float
        Jaccard similarity threshold (default 0.75).

    Returns
    -------
    bool
        ``True`` if the trigram Jaccard similarity is ≥ *threshold*.
    """
    if not a or not b:
        return False
    n = 3
    pad = "_" * (n - 1)
    a_padded = f"{pad}{a.lower()}{pad}"
    b_padded = f"{pad}{b.lower()}{pad}"
    grams_a = {a_padded[i:i + n] for i in range(len(a_padded) - n + 1)}
    grams_b = {b_padded[i:i + n] for i in range(len(b_padded) - n + 1)}
    if not grams_a or not grams_b:
        return False
    intersection = grams_a & grams_b
    union = grams_a | grams_b
    return len(intersection) / len(union) >= threshold
