"""Short-term memory – in-memory ring buffer with TTL-based expiry.

STM holds the most recent, currently relevant information in a
configurable-capacity ordered store. Entries auto-expire after a
time-to-live (default 1 hour). Provides substring/prefix search and
usage statistics.
"""

from __future__ import annotations

import logging
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class STMEntry:
    """A single short-term memory entry with TTL metadata."""

    key: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: float = 0.0
    ttl_seconds: float = 3600.0

    @property
    def is_expired(self) -> bool:
        """Check whether this entry has outlived its TTL."""
        return time.time() > self.created_at + self.ttl_seconds


class ShortTermMemory:
    """In-memory ring buffer with TTL-based expiry.

    Capacity is configurable via ``max_entries`` (default 100). When the
    buffer is full, the oldest entry is evicted automatically. Entries
    are checked for expiry on every access.

    Uses ``collections.OrderedDict`` internally for O(1) add / get /
    remove and insertion-ordered iteration.
    """

    def __init__(self, max_entries: int = 100, default_ttl: float = 3600.0) -> None:
        self.max_entries = max_entries
        self.default_ttl = default_ttl
        self._store: OrderedDict[str, STMEntry] = OrderedDict()
        self._access_count: int = 0
        self._eviction_count: int = 0
        self._expiry_count: int = 0

    # ── Public API ─────────────────────────────────────────────────

    def add(
        self,
        key: str,
        content: str,
        metadata: Optional[dict[str, Any]] = None,
        ttl: Optional[float] = None,
    ) -> STMEntry:
        """Store a new entry, evicting oldest if at capacity.

        Args:
            key: Unique identifier for the entry.
            content: The memory content.
            metadata: Optional structured metadata.
            ttl: Override the default TTL in seconds.

        Returns:
            The newly created entry.
        """
        now = time.time()

        # Evict oldest entry if at capacity (before adding)
        if len(self._store) >= self.max_entries:
            _evicted_key, _evicted_entry = self._store.popitem(last=False)
            self._eviction_count += 1
            logger.debug("Evicted oldest entry: %s", _evicted_key)

        entry = STMEntry(
            key=key,
            content=content,
            metadata=metadata or {},
            created_at=now,
            ttl_seconds=ttl if ttl is not None else self.default_ttl,
        )

        # Remove existing entry with same key to maintain freshness
        if key in self._store:
            del self._store[key]

        self._store[key] = entry
        return entry

    def get(self, key: str) -> Optional[STMEntry]:
        """Retrieve an entry by key.

        Returns ``None`` and removes the entry if it has expired.
        """
        entry = self._store.get(key)
        if entry is None:
            return None

        self._access_count += 1

        if entry.is_expired:
            del self._store[key]
            self._expiry_count += 1
            logger.debug("Removed expired entry: %s", key)
            return None

        # Move to end to mark as recently used
        self._store.move_to_end(key)
        return entry

    def remove(self, key: str) -> bool:
        """Remove an entry by key.

        Returns ``True`` if the entry existed and was removed.
        """
        if key in self._store:
            del self._store[key]
            return True
        return False

    def clear(self) -> None:
        """Remove all entries and reset statistics."""
        self._store.clear()
        self._access_count = 0
        self._eviction_count = 0
        self._expiry_count = 0

    def recent(self, n: int = 10) -> list[STMEntry]:
        """Return the *n* most recent non-expired entries."""
        self._purge_expired()
        entries = list(self._store.values())
        return entries[-n:]

    def search(self, query: str) -> list[STMEntry]:
        """Simple substring/prefix search across all non-expired entries.

        Returns entries whose *key* or *content* contains *query*
        (case-insensitive).
        """
        self._purge_expired()
        q = query.lower()
        results: list[STMEntry] = []
        for entry in self._store.values():
            if q in entry.key.lower() or q in entry.content.lower():
                results.append(entry)
        return results

    def all_entries(self) -> list[STMEntry]:
        """Return all non-expired entries."""
        self._purge_expired()
        return list(self._store.values())

    def count(self) -> int:
        """Return the number of non-expired entries."""
        self._purge_expired()
        return len(self._store)

    def stats(self) -> dict[str, Any]:
        """Return usage statistics for this short-term memory store."""
        self._purge_expired()
        return {
            "max_entries": self.max_entries,
            "current_entries": len(self._store),
            "usage_ratio": round(len(self._store) / max(1, self.max_entries), 3),
            "default_ttl_seconds": self.default_ttl,
            "access_count": self._access_count,
            "eviction_count": self._eviction_count,
            "expiry_count": self._expiry_count,
        }

    # ── Internal helpers ───────────────────────────────────────────

    def _purge_expired(self) -> int:
        """Remove all expired entries and return how many were purged."""
        now = time.time()
        expired_keys = [
            k for k, e in self._store.items()
            if now > e.created_at + e.ttl_seconds
        ]
        for k in expired_keys:
            del self._store[k]
        if expired_keys:
            self._expiry_count += len(expired_keys)
            logger.debug("Purged %d expired entries", len(expired_keys))
        return len(expired_keys)
