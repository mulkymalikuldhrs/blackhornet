"""Memory system for AI-MultiColony.

Provides the unified memory gateway (MemoryManager), Letta-style paging
(LettaStylePaging), vector store (VectorStore), eight condenser types,
knowledge base (KnowledgeBase), temporal knowledge graph
(TemporalKnowledgeGraph), session memory (SessionMemory),
consolidation pipeline (MemoryConsolidator), forgetting mechanism
(ForgettingMechanism), short/long-term/semantic/episodic stores.
"""

from .short_term import ShortTermMemory, STMEntry
from .long_term import LongTermMemory, LTMEntry
from .semantic import SemanticMemory, SemanticEntry, compute_ngrams, ngram_similarity
from .episodic import EpisodicMemory, Episode
from .consolidation import MemoryConsolidator, ConsolidationReport
from .forgetting import ForgettingMechanism, ForgettingReport
from .manager import MemoryManager, MemoryTier
from .paging import LettaStylePaging, PagingManager, MemoryPage, WorkingSetEntry
from .vector import VectorStore, VectorDocument, QueryResult, CollectionInfo
from .condensers import (
    BaseCondenser,
    SummaryCondenser,
    KeyFactCondenser,
    TemporalCondenser,
    RelevanceCondenser,
    RedundancyCondenser,
    ProceduralCondenser,
    RelationalCondenser,
    HybridCondenser,
    # Backward-compat aliases
    ExtractionCondenser,
    RollupCondenser,
    PriorityCondenser,
    DeduplicationCondenser,
    SlidingWindowCondenser,
    HierarchicalCondenser,
    CONDENSERS,
)
from .knowledge import KnowledgeBase, Fact, Document, Chunk
from .knowledge_graph import TemporalKnowledgeGraph, Triple, Entity, EvolutionEntry
from .neural_bridge import NeuralMemoryBridge
from .neural_graph import NeuralGraphMemory, NeuronData, SynapseData
from .session import SessionMemory, Session, Message, CompactionResult

# Self-consolidation (arXiv:2602.01966)
from src.memory.self_consolidation import SelfConsolidation, ConsolidatedMemory, ReflectedInsight, Experience

__all__ = [
    # Short-term
    "ShortTermMemory",
    "STMEntry",
    # Long-term
    "LongTermMemory",
    "LTMEntry",
    # Semantic
    "SemanticMemory",
    "SemanticEntry",
    "compute_ngrams",
    "ngram_similarity",
    # Episodic
    "EpisodicMemory",
    "Episode",
    # Consolidation
    "MemoryConsolidator",
    "ConsolidationReport",
    # Forgetting
    "ForgettingMechanism",
    "ForgettingReport",
    # Manager
    "MemoryManager",
    "MemoryTier",
    # Paging
    "LettaStylePaging",
    "PagingManager",
    "MemoryPage",
    "WorkingSetEntry",
    # Vector
    "VectorStore",
    "VectorDocument",
    "QueryResult",
    "CollectionInfo",
    # Condensers
    "BaseCondenser",
    "SummaryCondenser",
    "KeyFactCondenser",
    "TemporalCondenser",
    "RelevanceCondenser",
    "RedundancyCondenser",
    "ProceduralCondenser",
    "RelationalCondenser",
    "HybridCondenser",
    "ExtractionCondenser",
    "RollupCondenser",
    "PriorityCondenser",
    "DeduplicationCondenser",
    "SlidingWindowCondenser",
    "HierarchicalCondenser",
    "CONDENSERS",
    # Knowledge
    "KnowledgeBase",
    "Fact",
    "Document",
    "Chunk",
    # Knowledge Graph
    "TemporalKnowledgeGraph",
    "Triple",
    "Entity",
    "EvolutionEntry",
    # Session
    "SessionMemory",
    "Session",
    "Message",
    "CompactionResult",
    # Self-consolidation (v2.0)
    "SelfConsolidation",
    "ConsolidatedMemory",
    "ReflectedInsight",
    "Experience",
    # Neural Bridge
    "NeuralMemoryBridge",
    "NeuralGraphMemory",
    "NeuronData",
    "SynapseData",
]
