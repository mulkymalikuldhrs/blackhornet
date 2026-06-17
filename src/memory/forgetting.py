"""ForgettingMechanism – decay-based forgetting with configurable thresholds.

Sub-agent 2.6: Implements decay-based forgetting and archival using the
formula ``access_count / max(hours_since_access, 1) * exp(-0.01 * hours_since_access)``.

Thresholds
----------
- Archive threshold: ``decay_score < 0.01``
- Delete threshold: ``decay_score < 0.001`` AND ``age > 90 days``
"""

from __future__ import annotations

import json
import logging
import math
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class ForgettingReport:
    """Result of a full forgetting cycle.

    Attributes
    ----------
    timestamp : str
        ISO-8601 timestamp of when the cycle started.
    archived : int
        Number of entries moved to cold storage.
    deleted : int
        Number of entries permanently deleted.
    decayed_entries : int
        Number of entries whose decay score fell below the archive
        threshold (subset of ``archived + deleted``).
    errors : list[str]
        Error messages collected during the cycle.
    duration_ms : float
        Wall-clock duration in milliseconds.
    """
    timestamp: str = ""
    archived: int = 0
    deleted: int = 0
    decayed_entries: int = 0
    errors: list[str] = field(default_factory=list)
    duration_ms: float = 0.0


class ForgettingMechanism:
    """Decay-based forgetting with configurable thresholds.

    The decay formula favours frequently-accessed, recent entries and
    penalises entries that have not been touched in a long time:

    ``decay_score = access_count / max(hours_since_access, 1) * exp(-0.01 * hours_since_access)``

    Thresholds
    ----------
    - **Archive** (move to cold storage): ``decay_score < 0.01``
    - **Delete** (permanent removal): ``decay_score < 0.001`` AND
      ``age > 90 days``

    Parameters
    ----------
    ltm : LongTermMemory
        Long-term memory store.
    semantic : SemanticMemory
        Semantic memory store.
    episodic : EpisodicMemory or None
        Optional episodic memory store.
    archive_dir : str
        Directory for cold storage archive files (default
        ``~/.bh/memory/archive/``).
    """

    def __init__(
        self,
        ltm: Any,
        semantic: Any,
        episodic: Optional[Any] = None,
        archive_dir: str = "~/.bh/memory/archive/",
    ) -> None:
        self._ltm = ltm
        self._semantic = semantic
        self._episodic = episodic
        self._archive_dir = os.path.expanduser(archive_dir)
        os.makedirs(self._archive_dir, exist_ok=True)

    # ── Full cycle ─────────────────────────────────────────────────

    def run_forgetting(self) -> ForgettingReport:
        """Run the full forgetting cycle.

        Stages
        ------
        1. Find all entries with ``decay_score < 0.01``.
        2. Separate into archive candidates and delete candidates.
        3. Archive eligible entries to cold storage JSON.
        4. Permanently delete entries that qualify.

        Returns
        -------
        ForgettingReport
            Detailed results of the forgetting cycle.
        """
        start = time.time()
        report = ForgettingReport(
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        try:
            decayed = self.find_decayed_entries(threshold=0.01)
            report.decayed_entries = len(decayed)
        except Exception as exc:
            msg = f"find_decayed_entries failed: {exc}"
            logger.exception(msg)
            report.errors.append(msg)
            decayed = []

        # Separate into archive vs delete candidates
        archive_candidates: list[Any] = []
        delete_candidates: list[Any] = []
        now = time.time()

        for entry in decayed:
            age_hours = (now - entry.created_at) / 3600.0 if hasattr(entry, "created_at") else 0.0
            score = self.calculate_decay(entry)

            if score < 0.001 and age_hours > 90 * 24:
                delete_candidates.append(entry)
            else:
                archive_candidates.append(entry)

        # Archive
        if archive_candidates:
            try:
                report.archived = self.archive_entries(archive_candidates)
            except Exception as exc:
                msg = f"archive_entries failed: {exc}"
                logger.exception(msg)
                report.errors.append(msg)

        # Delete
        if delete_candidates:
            try:
                report.deleted = self.delete_entries(delete_candidates)
            except Exception as exc:
                msg = f"delete_entries failed: {exc}"
                logger.exception(msg)
                report.errors.append(msg)

        report.duration_ms = (time.time() - start) * 1000
        logger.info(
            "Forgetting complete: archived=%d deleted=%d decayed=%d errors=%d",
            report.archived,
            report.deleted,
            report.decayed_entries,
            len(report.errors),
        )
        return report

    # ── Decay formula ──────────────────────────────────────────────

    def calculate_decay(self, entry: Any) -> float:
        """Compute the decay score for a memory entry.

        Formula
        -------
        ``decay_score = access_count / max(hours_since_access, 1) * exp(-0.01 * hours_since_access)``

        Parameters
        ----------
        entry
            An object with ``access_count``, ``accessed_at``, and
            ``created_at`` numeric attributes (e.g. ``LTMEntry``).

        Returns
        -------
        float
            Decay score — higher means more valuable / less decayed.
        """
        now = time.time()
        access_count = getattr(entry, "access_count", 0) or 0
        accessed_at = getattr(entry, "accessed_at", 0) or now
        created_at = getattr(entry, "created_at", 0) or now

        hours_since_access = max((now - accessed_at) / 3600.0, 1.0)
        age_multiplier = math.exp(-0.01 * hours_since_access)
        return access_count / hours_since_access * age_multiplier

    # ── Find decayed entries ───────────────────────────────────────

    def find_decayed_entries(self, threshold: float = 0.01) -> list[Any]:
        """Return entries whose decay score is below *threshold*.

        Iterates over all LTM entries, computes the decay score for
        each, and collects those that fall below the threshold.

        Parameters
        ----------
        threshold : float
            Decay score threshold (default 0.01).

        Returns
        -------
        list[LTMEntry]
            Entries eligible for archiving or deletion.
        """
        entries = self._ltm.all_entries()
        decayed: list[Any] = []
        for entry in entries:
            try:
                score = self.calculate_decay(entry)
                if score < threshold:
                    decayed.append(entry)
            except Exception as exc:
                logger.debug("Error calculating decay for entry %d: %s", getattr(entry, "id", 0), exc)
                continue
        return decayed

    # ── Archive entries ────────────────────────────────────────────

    def archive_entries(self, entries: list[Any]) -> int:
        """Move entries to cold storage.

        Saves entries as a JSON array in
        ``{archive_dir}/archive-{date}.json`` and removes them from
        the main LTM database.

        Parameters
        ----------
        entries : list[LTMEntry]
            Entries to archive.

        Returns
        -------
        int
            Number of entries successfully archived.
        """
        if not entries:
            return 0

        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        archive_path = os.path.join(self._archive_dir, f"archive-{date_str}.json")

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
                "id": getattr(entry, "id", 0),
                "key": getattr(entry, "key", ""),
                "content": getattr(entry, "content", ""),
                "tags": getattr(entry, "tags", []),
                "metadata": getattr(entry, "metadata", {}),
                "created_at": getattr(entry, "created_at", 0.0),
                "accessed_at": getattr(entry, "accessed_at", 0.0),
                "access_count": getattr(entry, "access_count", 0),
                "importance": getattr(entry, "importance", 0.0),
                "archived_at": time.time(),
            })

        existing.extend(archive_data)
        with open(archive_path, "w") as f:
            json.dump(existing, f, indent=2)

        removed = 0
        for entry in entries:
            eid = getattr(entry, "id", None)
            if eid is None:
                key = getattr(entry, "key", None)
                if key:
                    try:
                        self._ltm.remove(key)
                        removed += 1
                    except Exception as exc:
                        logger.warning("Failed to remove archived entry (key=%s): %s", key, exc)
                continue
            try:
                self._ltm.remove_by_id(eid)
                removed += 1
            except Exception as exc:
                logger.warning("Failed to remove archived LTM entry %d: %s", eid, exc)

        logger.info("Archived %d entries to %s", removed, archive_path)
        return removed

    # ── Delete entries ─────────────────────────────────────────────

    def delete_entries(self, entries: list[Any]) -> int:
        """Permanently delete entries from the LTM database.

        Only call this for entries that meet the delete threshold
        (``decay_score < 0.001`` AND ``age > 90 days``).  This
        operation **cannot** be undone.

        Parameters
        ----------
        entries : list[LTMEntry]
            Entries to permanently delete.

        Returns
        -------
        int
            Number of entries successfully deleted.
        """
        deleted = 0
        now = time.time()

        for entry in entries:
            age_hours = (now - getattr(entry, "created_at", now)) / 3600.0
            score = self.calculate_decay(entry)

            if score >= 0.001 or age_hours <= 90 * 24:
                continue

            eid = getattr(entry, "id", None)
            if eid is not None:
                try:
                    self._ltm.remove_by_id(eid)
                    deleted += 1
                except Exception as exc:
                    logger.warning("Failed to delete LTM entry %d: %s", eid, exc)
            else:
                key = getattr(entry, "key", None)
                if key:
                    try:
                        self._ltm.remove(key)
                        deleted += 1
                    except Exception as exc:
                        logger.warning("Failed to delete entry (key=%s): %s", key, exc)

        if deleted:
            logger.info("Permanently deleted %d entries", deleted)
        return deleted

    # ── Restore from archive ───────────────────────────────────────

    def restore_archive(self, date: str) -> int:
        """Restore entries from an archive file back into LTM.

        Parameters
        ----------
        date : str
            Date string in ``YYYY-MM-DD`` format matching an archive
            filename (``archive-{date}.json``).

        Returns
        -------
        int
            Number of entries restored.
        """
        archive_path = os.path.join(self._archive_dir, f"archive-{date}.json")

        if not os.path.exists(archive_path):
            logger.warning("Archive file not found: %s", archive_path)
            return 0

        try:
            with open(archive_path) as f:
                archived_entries = json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            logger.error("Failed to read archive %s: %s", archive_path, exc)
            return 0

        restored = 0
        for ae in archived_entries:
            try:
                self._ltm.add(
                    key=ae.get("key", f"restored-{ae.get('id', 0)}"),
                    content=ae.get("content", ""),
                    tags=ae.get("tags", []),
                    metadata={
                        **(ae.get("metadata", {})),
                        "restored_from_archive": date,
                        "original_id": ae.get("id", 0),
                        "restored_at": time.time(),
                    },
                    importance=ae.get("importance", 0.5),
                )
                restored += 1
            except Exception as exc:
                logger.warning("Failed to restore entry %s: %s", ae.get("key", "?"), exc)
                continue

        # Remove archive file after successful restore
        if restored > 0:
            try:
                os.remove(archive_path)
                logger.info("Removed archive file after restoring %d entries: %s", restored, archive_path)
            except OSError as exc:
                logger.warning("Failed to remove archive file %s: %s", archive_path, exc)

        logger.info("Restored %d entries from archive %s", restored, date)
        return restored

    # ── List archives ──────────────────────────────────────────────

    def list_archives(self) -> list[str]:
        """List available archive files.

        Returns
        -------
        list[str]
            Date strings (``YYYY-MM-DD``) for each archive file found
            in the archive directory, sorted ascending.
        """
        if not os.path.isdir(self._archive_dir):
            return []

        dates: list[str] = []
        for filename in sorted(os.listdir(self._archive_dir)):
            if filename.startswith("archive-") and filename.endswith(".json"):
                date_part = filename[len("archive-"):-len(".json")]
                dates.append(date_part)
        return dates

    # ── Statistics ─────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        """Return forgetting mechanism statistics.

        Returns
        -------
        dict
            Keys: ``archive_dir``, ``archive_count``, ``total_ltm_entries``,
            ``total_ltm_access_count``.
        """
        ltm_stats = self._ltm.stats()
        archive_files = self.list_archives()

        total_archived = 0
        for date_str in archive_files:
            path = os.path.join(self._archive_dir, f"archive-{date_str}.json")
            try:
                with open(path) as f:
                    data = json.load(f)
                    total_archived += len(data)
            except (json.JSONDecodeError, OSError):
                pass

        return {
            "archive_dir": self._archive_dir,
            "archive_files": len(archive_files),
            "archive_dates": archive_files,
            "total_archived_entries": total_archived,
            "total_ltm_entries": ltm_stats.get("total_entries", 0),
            "total_ltm_access_count": ltm_stats.get("total_access_count", 0),
            "avg_ltm_importance": ltm_stats.get("avg_importance", 0.0),
        }
