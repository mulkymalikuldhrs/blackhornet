#!/usr/bin/env python3
"""
BH Vector Memory System
=======================
Pure Python vector store using word frequency + cosine similarity.
No external dependencies. Persists to data/memory/ as JSONL files.

Provides episodic memory (past goals, results, learnings) with
TF-like bag-of-words vectors and consolidation into higher-level concepts.
"""

import json
import math
import os
import re
import time
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from threading import Lock


BASE_DIR = Path(__file__).resolve().parent.parent
MEMORY_DIR = BASE_DIR / "data" / "memory"
os.makedirs(MEMORY_DIR, exist_ok=True)

EPISODIC_FILE = MEMORY_DIR / "episodic.jsonl"
CONSOLIDATED_FILE = MEMORY_DIR / "consolidated.jsonl"
VOCAB_FILE = MEMORY_DIR / "vocab.json"


def _tokenize(text: str) -> list[str]:
    tokens = re.findall(r"[a-zA-Z]+", text.lower())
    return [t for t in tokens if len(t) > 1]


def _compute_tf_vector(text: str, vocab: dict[str, int]) -> list[float]:
    tokens = _tokenize(text)
    if not tokens:
        return [0.0] * len(vocab)
    tf = Counter(tokens)
    max_freq = max(tf.values())
    vec = [0.0] * len(vocab)
    for word, idx in vocab.items():
        vec[idx] = tf.get(word, 0) / max_freq
    return vec


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(ai * bi for ai, bi in zip(a, b))
    na = math.sqrt(sum(ai * ai for ai in a))
    nb = math.sqrt(sum(bi * bi for bi in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _build_vocab(texts: list[str], min_freq: int = 2) -> dict[str, int]:
    counter: Counter = Counter()
    for t in texts:
        counter.update(_tokenize(t))
    vocab = {}
    for word, freq in counter.most_common():
        if freq >= min_freq:
            vocab[word] = len(vocab)
    return vocab


class VectorMemory:
    """
    Persistent vector memory using bag-of-words TF vectors.

    Stores items as JSONL with precomputed vectors.
    Supports recall via cosine similarity and consolidation
    into higher-level concepts.
    """

    def __init__(self):
        self._lock = Lock()
        self.vocab: dict[str, int] = self._load_vocab()
        self.episodic: list[dict] = []
        self.consolidated: list[dict] = []
        self._dirty = False
        self._load_episodic()
        self._load_consolidated()

    def _load_vocab(self) -> dict[str, int]:
        if VOCAB_FILE.exists():
            return json.loads(VOCAB_FILE.read_text())
        return {}

    def _save_vocab(self):
        VOCAB_FILE.write_text(json.dumps(self.vocab))

    def _load_episodic(self):
        if EPISODIC_FILE.exists():
            for line in EPISODIC_FILE.read_text().strip().splitlines():
                if line:
                    self.episodic.append(json.loads(line))

    def _load_consolidated(self):
        if CONSOLIDATED_FILE.exists():
            for line in CONSOLIDATED_FILE.read_text().strip().splitlines():
                if line:
                    self.consolidated.append(json.loads(line))

    def _append_jsonl(self, path: Path, record: dict):
        with open(path, "a") as f:
            f.write(json.dumps(record) + "\n")

    def store(self, text: str, metadata: dict | None = None) -> str:
        """Store text with metadata. Returns memory ID."""
        with self._lock:
            if not self.vocab:
                self._rebuild_vocab()
            mid = f"mem-{int(time.time() * 1000)}-{len(self.episodic)}"
            vector = _compute_tf_vector(text, self.vocab)
            record = {
                "id": mid,
                "text": text,
                "vector": vector,
                "metadata": metadata or {},
                "timestamp": datetime.utcnow().isoformat(),
            }
            self.episodic.append(record)
            self._append_jsonl(EPISODIC_FILE, record)
            self._rebuild_vocab_if_needed()
            return mid

    def recall(self, query: str, n: int = 5) -> list[dict]:
        """Find n most similar stored items using cosine similarity."""
        if not self.vocab or not self.episodic:
            return []
        qvec = _compute_tf_vector(query, self.vocab)
        scored = []
        for item in self.episodic:
            vec = item.get("vector", [])
            if not vec:
                vec = _compute_tf_vector(item["text"], self.vocab)
                item["vector"] = vec
            sim = _cosine_similarity(qvec, vec)
            scored.append((sim, item))
        scored.sort(key=lambda x: x[0], reverse=True)
        results = []
        for sim, item in scored[:n]:
            r = dict(item)
            r["similarity"] = round(sim, 4)
            results.append(r)
        return results

    def consolidate(self) -> list[dict]:
        """Merge related episodic items into higher-level concepts."""
        with self._lock:
            if len(self.episodic) < 3:
                return []
            clusters = self._cluster_similar()
            new_concepts = []
            for cluster in clusters:
                texts = [c["text"] for c in cluster]
                combined = " ".join(texts)
                concept = {
                    "id": f"concept-{int(time.time())}-{len(self.consolidated)}",
                    "summary": combined[:300],
                    "source_ids": [c["id"] for c in cluster],
                    "size": len(cluster),
                    "created": datetime.utcnow().isoformat(),
                }
                self.consolidated.append(concept)
                self._append_jsonl(CONSOLIDATED_FILE, concept)
                new_concepts.append(concept)
            if new_concepts:
                self._rebuild_vocab()
            return new_concepts

    def _cluster_similar(self, threshold: float = 0.3) -> list[list[dict]]:
        if not self.vocab:
            return []
        used = set()
        clusters = []
        items = list(self.episodic)
        for i, item_a in enumerate(items):
            if i in used:
                continue
            cluster = [items[i]]
            used.add(i)
            avec = item_a.get("vector") or _compute_tf_vector(item_a["text"], self.vocab)
            for j in range(i + 1, len(items)):
                if j in used:
                    continue
                bvec = items[j].get("vector") or _compute_tf_vector(items[j]["text"], self.vocab)
                if _cosine_similarity(avec, bvec) > threshold:
                    cluster.append(items[j])
                    used.add(j)
            if len(cluster) > 1:
                clusters.append(cluster)
        return clusters

    def repair_vectors(self) -> int:
        """Recompute all vectors from scratch.
        
        Fixes items stored when vocab was empty. Returns count repaired.
        """
        with self._lock:
            # Count items with empty vectors before rebuild
            was_empty = sum(
                1 for item in self.episodic
                if not item.get("vector") or len(item["vector"]) == 0
            )
            self._rebuild_vocab()
            # Rewrite the file with corrected vectors
            EPISODIC_FILE.write_text(
                "\n".join(json.dumps(item) for item in self.episodic) + "\n"
            )
            return was_empty

    def stats(self) -> dict:
        """Return memory size and top topics."""
        with self._lock:
            all_tokens = []
            for item in self.episodic:
                all_tokens.extend(_tokenize(item["text"]))
            top_words = Counter(all_tokens).most_common(10)
            return {
                "episodic_count": len(self.episodic),
                "consolidated_count": len(self.consolidated),
                "vocab_size": len(self.vocab),
                "top_topics": [w for w, _ in top_words],
            }

    def _rebuild_vocab_if_needed(self):
        if len(self.episodic) % 10 == 0 and len(self.episodic) > 0:
            self._rebuild_vocab()

    def _rebuild_vocab(self):
        texts = [item["text"] for item in self.episodic]
        new_vocab = _build_vocab(texts, min_freq=1)
        self.vocab = new_vocab
        self._save_vocab()
        for item in self.episodic:
            item["vector"] = _compute_tf_vector(item["text"], self.vocab)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="BH Vector Memory")
    parser.add_argument("action", choices=["store", "recall", "consolidate", "stats"])
    parser.add_argument("--text", help="Text to store or query")
    parser.add_argument("--n", type=int, default=5, help="Number of results for recall")
    args = parser.parse_args()

    mem = VectorMemory()

    if args.action == "store":
        if not args.text:
            print("--text is required")
            sys.exit(1)
        mid = mem.store(args.text)
        print(f"Stored: {mid}")

    elif args.action == "recall":
        if not args.text:
            print("--text is required")
            sys.exit(1)
        results = mem.recall(args.text, args.n)
        for r in results:
            print(f"[{r['similarity']:.3f}] {r['text'][:100]}")

    elif args.action == "consolidate":
        concepts = mem.consolidate()
        print(f"Created {len(concepts)} new concepts")

    elif args.action == "stats":
        s = mem.stats()
        for k, v in s.items():
            print(f"{k}: {v}")
