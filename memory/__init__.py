"""
Memory systems for the Brain Swarm.

This module provides hierarchical memory capabilities with a 4-layer Knowledge Cortex:
- Cache Layer: Redis for fast access
- Vector Layer: ChromaDB for semantic search
- Graph Layer: NetworkX+DuckDB for relational knowledge
- Archive Layer: S3+DuckDB for long-term storage

Also includes legacy WorkingMemory and LongTermMemory for backward compatibility.
"""

from .memory import WorkingMemory, LongTermMemory, working_memory, long_term_memory
from .backends import MemoryBackend, MemoryBackendFactory
from .knowledge_cortex import KnowledgeCortex, knowledge_cortex

__all__ = [
    # New Knowledge Cortex system
    'KnowledgeCortex',
    'knowledge_cortex',

    # Legacy systems (backward compatibility)
    'WorkingMemory',
    'LongTermMemory',
    'working_memory',
    'long_term_memory',

    # Backend infrastructure
    'MemoryBackend',
    'MemoryBackendFactory'
]