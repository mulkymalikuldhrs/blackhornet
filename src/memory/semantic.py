"""SemanticMemory – n-gram based semantic similarity search with
FTS5 keyword fallback. Zero external dependencies, stdlib only.

Stores text entries and supports similarity retrieval using character
n-gram overlap (default n=3). Uses sqlite3 FTS5 for exact keyword
matching as a fast first pass before falling back to n-gram comparison.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# ── N-gram utilities ──────────────────────────────────────────────

def compute_ngrams(text: str, n: int = 3) -> Set[str]:
    """Generate character n-grams from *text*.

    Pads the text with ``_`` on both sides so that short strings still
    produce meaningful n-grams.  Returns the empty set when *text* is
    empty.

    Parameters
    ----------
    text : str
        Input string.
    n : int
        N-gram length (default 3).

    Returns
    -------
    set[str]
        All character n-grams present in the padded text.
    """
    if not text:
        return set()
    padded = f"{'_' * (n - 1)}{text.lower()}{'_' * (n - 1)}"
    return {padded[i:i + n] for i in range(len(padded) - n + 1)}


def ngram_similarity(a: str, b: str, n: int = 3) -> float:
    """Jaccard similarity between character n-gram sets of two strings.

    Returns a float in ``[0.0, 1.0]`` where 1.0 means identical
    n-gram composition.

    Parameters
    ----------
    a : str
        First string.
    b : str
        Second string.
    n : int
        N-gram length (default 3).

    Returns
    -------
    float
        Jaccard similarity coefficient.
    """
    grams_a = compute_ngrams(a, n)
    grams_b = compute_ngrams(b, n)
    if not grams_a or not grams_b:
        return 0.0
    intersection = grams_a & grams_b
    union = grams_a | grams_b
    return len(intersection) / len(union)


def ngrams_to_hash(ngrams: Set[str]) -> str:
    """Serialize an n-gram set to a sorted, comma-separated string.

    Parameters
    ----------
    ngrams : set[str]
        Set of character n-grams.

    Returns
    -------
    str
        Sorted, comma-separated string (empty string if set is empty).
    """
    return ",".join(sorted(ngrams))


def hash_to_ngrams(hash_str: str) -> Set[str]:
    """Deserialize a comma-separated n-gram hash back into a set.

    Parameters
    ----------
    hash_str : str
        Comma-separated n-gram string as produced by :func:`ngrams_to_hash`.

    Returns
    -------
    set[str]
        Deserialized n-gram set (empty set if *hash_str* is empty).
    """
    if not hash_str:
        return set()
    return set(hash_str.split(","))


# ── Data model ────────────────────────────────────────────────────

@dataclass
class SemanticEntry:
    """A single entry in semantic memory.

    Attributes
    ----------
    id : int
        Database rowid (auto-increment, 0 before insertion).
    text : str
        The stored text content.
    source : str
        Origin of the entry (e.g. ``"conversation"``, ``"document"``,
        ``"skill"``).
    embeddings_ngram : str
        Pre-computed comma-separated character n-grams for fast
        similarity comparison.
    metadata : dict[str, Any]
        Arbitrary key-value metadata attached to the entry.
    created_at : float
        Unix timestamp of creation.
    accessed_at : float
        Unix timestamp of last access.
    relevance_score : float
        Decay-adjusted relevance score for ranking.
    """
    id: int = 0
    text: str = ""
    source: str = ""
    embeddings_ngram: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = 0.0
    accessed_at: float = 0.0
    relevance_score: float = 0.0


# ── Semantic Memory ───────────────────────────────────────────────

class SemanticMemory:
    """N-gram based semantic memory with FTS5 keyword fallback.

    Stores text entries in a local sqlite3 database.  Queries are
    answered with a hybrid strategy:
        1. Fast FTS5 keyword search (exact / prefix match).
        2. N-gram similarity scan against recently accessed entries.
        3. Results are merged, deduplicated, and sorted by combined
           relevance score.

    No external dependencies — runs entirely on Python stdlib.

    Parameters
    ----------
    db_path : str
        Filesystem path for the sqlite database.  ``~`` is expanded.
    ngram_n : int
        Character n-gram length for similarity (default 3).
    """

    def __init__(self, db_path: str = "~/.bh/memory/semantic.db", ngram_n: int = 3) -> None:
        self.db_path = os.path.expanduser(db_path)
        self.ngram_n = ngram_n
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()

    # ── Database init ────────────────────────────────────────────

    def _init_db(self) -> None:
        """Create tables and indexes if they do not exist."""
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS entries (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                text            TEXT    NOT NULL,
                source          TEXT    NOT NULL DEFAULT 'conversation',
                ngram_hash      TEXT    NOT NULL DEFAULT '',
                metadata        TEXT    NOT NULL DEFAULT '{}',
                created_at      REAL    NOT NULL,
                accessed_at     REAL    NOT NULL,
                relevance_score REAL    NOT NULL DEFAULT 0.0
            );

            CREATE INDEX IF NOT EXISTS idx_entries_source
                ON entries(source);

            CREATE INDEX IF NOT EXISTS idx_entries_accessed
                ON entries(accessed_at DESC);

            CREATE INDEX IF NOT EXISTS idx_entries_relevance
                ON entries(relevance_score DESC);

            -- FTS5 virtual table for keyword search
            CREATE VIRTUAL TABLE IF NOT EXISTS entries_fts
                USING fts5(content, source, content=entries, content_rowid=id);

            -- Triggers to keep FTS index in sync
            CREATE TRIGGER IF NOT EXISTS entries_ai AFTER INSERT ON entries BEGIN
                INSERT INTO entries_fts(rowid, content, source)
                VALUES (new.id, new.text, new.source);
            END;

            CREATE TRIGGER IF NOT EXISTS entries_ad AFTER DELETE ON entries BEGIN
                INSERT INTO entries_fts(entries_fts, rowid, content, source)
                VALUES ('delete', old.id, old.text, old.source);
            END;

            CREATE TRIGGER IF NOT EXISTS entries_au AFTER UPDATE ON entries BEGIN
                INSERT INTO entries_fts(entries_fts, rowid, content, source)
                VALUES ('delete', old.id, old.text, old.source);
                INSERT INTO entries_fts(rowid, content, source)
                VALUES (new.id, new.text, new.source);
            END;
        """)
        conn.commit()
        logger.debug("SemanticMemory db ready at %s", self.db_path)

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def close(self) -> None:
        """Close the database connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> SemanticMemory:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    # ── CRUD ─────────────────────────────────────────────────────

    def add(
        self,
        text: str,
        source: str = "conversation",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Add a new entry to semantic memory.

        The entry's n-gram hash is pre-computed so that similarity
        queries do not need to regenerate it.

        Parameters
        ----------
        text : str
            The text content to store.
        source : str
            Origin label (default ``"conversation"``).
        metadata : dict or None
            Optional key-value metadata.

        Returns
        -------
        int
            The new entry's rowid.
        """
        ngrams = compute_ngrams(text, self.ngram_n)
        ngram_hash = ngrams_to_hash(ngrams)
        now = time.time()
        meta_json = json.dumps(metadata or {})

        conn = self._get_conn()
        cursor = conn.execute(
            """INSERT INTO entries (text, source, ngram_hash, metadata,
                                    created_at, accessed_at, relevance_score)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (text, source, ngram_hash, meta_json, now, now, 0.0),
        )
        conn.commit()
        entry_id = cursor.lastrowid
        logger.debug("Added semantic entry %d: source=%s", entry_id, source)
        return entry_id

    def get(self, id: int) -> Optional[SemanticEntry]:
        """Retrieve a single entry by its rowid.

        Parameters
        ----------
        id : int
            Entry rowid.

        Returns
        -------
        SemanticEntry or None
            The entry, or ``None`` if not found.
        """
        row = self._get_conn().execute(
            "SELECT * FROM entries WHERE id = ?", (id,)
        ).fetchone()
        if row is None:
            return None
        # Touch accessed_at
        self._get_conn().execute(
            "UPDATE entries SET accessed_at = ? WHERE id = ?",
            (time.time(), id),
        )
        self._get_conn().commit()
        return self._row_to_entry(row)

    def remove(self, id: int) -> bool:
        """Delete an entry by rowid.

        Parameters
        ----------
        id : int
            Entry rowid.

        Returns
        -------
        bool
            ``True`` if the entry existed and was deleted.
        """
        conn = self._get_conn()
        cursor = conn.execute("DELETE FROM entries WHERE id = ?", (id,))
        conn.commit()
        deleted = cursor.rowcount > 0
        if deleted:
            logger.debug("Removed semantic entry %d", id)
        return deleted

    # ── Count / Stats ────────────────────────────────────────────

    def count(self) -> int:
        """Return total number of entries in semantic memory."""
        row = self._get_conn().execute("SELECT COUNT(*) AS cnt FROM entries").fetchone()
        return row["cnt"] if row else 0

    def stats(self) -> Dict[str, Any]:
        """Return aggregate statistics about the semantic store.

        Returns
        -------
        dict
            Keys: ``total_entries``, ``sources``, ``avg_relevance``,
            ``entries_with_ngrams``, ``db_size_bytes``.
        """
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) AS cnt FROM entries").fetchone()["cnt"]

        sources_row = conn.execute(
            "SELECT source, COUNT(*) AS cnt FROM entries GROUP BY source"
        ).fetchall()
        sources = {r["source"]: r["cnt"] for r in sources_row}

        avg_rel = conn.execute(
            "SELECT COALESCE(AVG(relevance_score), 0.0) AS avg FROM entries"
        ).fetchone()["avg"]

        with_ngrams = conn.execute(
            "SELECT COUNT(*) AS cnt FROM entries WHERE ngram_hash != ''"
        ).fetchone()["cnt"]

        db_size = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0

        return {
            "total_entries": total,
            "sources": sources,
            "avg_relevance": round(avg_rel, 4),
            "entries_with_ngrams": with_ngrams,
            "ngram_n": self.ngram_n,
            "db_size_bytes": db_size,
        }

    # ── Search ───────────────────────────────────────────────────

    def search(self, query: str, limit: int = 10) -> List[SemanticEntry]:
        """Hybrid search: FTS5 keyword first, n-gram similarity fallback.

        Results are merged, deduplicated by entry ID, and sorted by
        combined score descending.  The combined score is the maximum
        of the FTS5 rank and the n-gram similarity.

        Parameters
        ----------
        query : str
            Search query.
        limit : int
            Maximum results to return (default 10).

        Returns
        -------
        list[SemanticEntry]
            Ranked results with ``relevance_score`` populated.
        """
        # Phase 1: FTS5 keyword search
        fts_results: List[SemanticEntry] = self.search_keyword(query, limit * 2)

        # Phase 2: n-gram similarity against recent entries
        ngram_results: List[SemanticEntry] = self.search_similar(
            query, threshold=0.15, limit=limit * 2
        )

        # Merge by ID, keep max relevance
        merged: Dict[int, SemanticEntry] = {}
        for entry in fts_results + ngram_results:
            if entry.id in merged:
                existing = merged[entry.id]
                entry.relevance_score = max(existing.relevance_score, entry.relevance_score)
            merged[entry.id] = entry

        # Sort by relevance_score descending, then accessed_at descending
        sorted_entries = sorted(
            merged.values(),
            key=lambda e: (e.relevance_score, e.accessed_at),
            reverse=True,
        )

        return sorted_entries[:limit]

    def search_similar(
        self,
        text: str,
        threshold: float = 0.3,
        limit: int = 10,
    ) -> List[SemanticEntry]:
        """Search by n-gram similarity only.

        Compares the query text's character n-grams against all stored
        entries.  This is O(n) on the number of entries — fine for up
        to tens of thousands of entries.

        Parameters
        ----------
        text : str
            Reference text to find similar entries for.
        threshold : float
            Minimum similarity score (Jaccard) to include (default 0.3).
        limit : int
            Maximum results to return (default 10).

        Returns
        -------
        list[SemanticEntry]
            Entries sorted by similarity (highest first) with
            ``relevance_score`` set to the similarity value.
        """
        query_ngrams = compute_ngrams(text, self.ngram_n)
        if not query_ngrams:
            return []

        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM entries WHERE ngram_hash != ''"
        ).fetchall()

        scored: List[Tuple[float, SemanticEntry]] = []
        for row in rows:
            stored_ngrams = hash_to_ngrams(row["ngram_hash"])
            if not stored_ngrams:
                continue
            intersection = query_ngrams & stored_ngrams
            union = query_ngrams | stored_ngrams
            sim = len(intersection) / len(union)
            if sim >= threshold:
                entry = self._row_to_entry(row)
                entry.relevance_score = sim
                scored.append((sim, entry))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [entry for _, entry in scored[:limit]]

    def search_keyword(self, query: str, limit: int = 20) -> List[SemanticEntry]:
        """FTS5 keyword search only.

        Uses sqlite FTS5's built-in ranking.  The query supports FTS5
        syntax (prefix matching with ``*``, phrase with ``"..."``, etc).

        Parameters
        ----------
        query : str
            FTS5 query string.
        limit : int
            Maximum results to return (default 20).

        Returns
        -------
        list[SemanticEntry]
            Matching entries sorted by FTS5 rank with ``relevance_score``
            set to the normalised rank.
        """
        conn = self._get_conn()
        try:
            rows = conn.execute(
                """SELECT e.*, rank AS relevance_score
                   FROM entries_fts
                   JOIN entries e ON e.id = entries_fts.rowid
                   WHERE entries_fts MATCH ?
                   ORDER BY rank
                   LIMIT ?""",
                (query, limit),
            ).fetchall()
        except sqlite3.OperationalError:
            # Malformed FTS query — return empty
            return []

        results: List[SemanticEntry] = []
        for row in rows:
            entry = self._row_to_entry(row)
            # Normalise rank to a 0-1 score (FTS5 rank is negative for good matches)
            entry.relevance_score = max(0.0, min(1.0, -row["relevance_score"] / 100.0))
            results.append(entry)

        # Track access
        if results:
            ids = tuple(e.id for e in results)
            now = time.time()
            conn.execute(
                f"UPDATE entries SET accessed_at = ? WHERE id IN ({','.join('?' * len(ids))})",
                (now, *ids),
            )
            conn.commit()

        return results

    # ── Internal ─────────────────────────────────────────────────

    @staticmethod
    def _row_to_entry(row: sqlite3.Row) -> SemanticEntry:
        """Convert a sqlite3.Row to a SemanticEntry."""
        return SemanticEntry(
            id=row["id"],
            text=row["text"],
            source=row["source"],
            embeddings_ngram=row["ngram_hash"],
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
            created_at=row["created_at"],
            accessed_at=row["accessed_at"],
            relevance_score=row["relevance_score"] if "relevance_score" in row.keys() else 0.0,
        )
