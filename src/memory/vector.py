"""VectorStore – ChromaDB-backed vector store with sentence-transformers embeddings.

Real embeddings via sentence-transformers, stored in ChromaDB for
persistent storage and efficient similarity search.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


class VectorStore:
    """ChromaDB-backed vector store with real embeddings.

    Uses sentence-transformers for embedding generation and ChromaDB
    for persistent storage and similarity search.
    """

    def __init__(
        self,
        collection_name: str = "blackhornet",
        persist_dir: str = "data/vectors",
    ):
        self.collection_name = collection_name
        self.persist_dir = persist_dir
        self._collection = None
        self._encoder = None
        self._init_backend()

    def _init_backend(self):
        """Initialize ChromaDB and embedding model."""
        try:
            import chromadb
            from chromadb.config import Settings

            self._client = chromadb.PersistentClient(
                path=self.persist_dir,
                settings=Settings(anonymized_telemetry=False),
            )
            self._collection = self._client.get_or_create_collection(
                name=self.collection_name,
            )
            logger.info(
                "ChromaDB initialized: collection=%s persist=%s",
                self.collection_name, self.persist_dir,
            )
        except ImportError:
            logger.warning(
                "chromadb not installed — VectorStore will operate in "
                "fallback (in-memory) mode"
            )
            self._collection = None

        try:
            from sentence_transformers import SentenceTransformer

            self._encoder = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("sentence-transformers model loaded")
        except ImportError:
            logger.warning(
                "sentence-transformers not installed — using basic "
                "hash-based fallback embeddings"
            )
            self._encoder = None

    def _embed(self, text: str) -> List[float]:
        """Generate embedding vector for text."""
        if self._encoder is not None:
            return self._encoder.encode(text).tolist()
        # Fallback: deterministic hash-based vector
        import hashlib

        h = hashlib.sha256(text.encode()).hexdigest()
        seed = int(h[:8], 16)
        rng = np.random.default_rng(seed)
        return rng.uniform(-0.1, 0.1, 384).tolist()

    def add(
        self,
        doc_id: str,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Add a document to the vector store."""
        embedding = self._embed(text)
        if self._collection is not None:
            self._collection.add(
                ids=[doc_id],
                embeddings=[embedding],
                documents=[text],
                metadatas=[metadata or {}],
            )
        if not hasattr(self, "_fallback_docs"):
            self._fallback_docs = {}
        self._fallback_docs[doc_id] = {
            "text": text,
            "embedding": embedding,
            "metadata": metadata or {},
        }
        logger.debug("Added doc %s to vector store", doc_id)

    def search(
        self,
        query: str,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """Search for documents similar to the query."""
        embedding = self._embed(query)
        if self._collection is not None:
            results = self._collection.query(
                query_embeddings=[embedding],
                n_results=top_k,
            )
            output = []
            for i in range(len(results["ids"][0])):
                output.append({
                    "id": results["ids"][0][i],
                    "text": results["documents"][0][i],
                    "score": (
                        1.0 - results["distances"][0][i]
                        if results.get("distances")
                        else 0.0
                    ),
                    "metadata": results["metadatas"][0][i]
                    if results.get("metadatas")
                    else {},
                })
            return output
        # Fallback: in-memory search via cosine similarity
        query_vec = np.array(embedding)
        scored = []
        for doc_id, doc in getattr(self, "_fallback_docs", {}).items():
            doc_vec = np.array(doc.get("embedding", query_vec))
            sim = float(np.dot(query_vec, doc_vec) / (np.linalg.norm(query_vec) * np.linalg.norm(doc_vec) + 1e-10))
            scored.append((sim, doc_id, doc))
        scored.sort(key=lambda x: -x[0])
        return [
            {
                "id": doc_id,
                "text": doc.get("text", ""),
                "score": sim,
                "metadata": doc.get("metadata", {}),
            }
            for sim, doc_id, doc in scored[:top_k]
        ]

    def delete(self, doc_id: str) -> None:
        """Delete a document from the vector store."""
        if self._collection is not None:
            self._collection.delete(ids=[doc_id])
        if hasattr(self, "_fallback_docs"):
            self._fallback_docs.pop(doc_id, None)

    def count(self) -> int:
        """Return the number of documents in the store."""
        if self._collection is not None:
            return self._collection.count()
        return len(getattr(self, "_fallback_docs", {}))

@dataclass
class VectorDocument:
    id: str
    content: str
    metadata: dict
    embedding: list | None = None

@dataclass
class QueryResult:
    document: VectorDocument
    score: float

@dataclass
class CollectionInfo:
    name: str
    count: int
    dims: int
