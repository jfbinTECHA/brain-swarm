"""
Memory systems for the Brain Swarm.

This module provides working memory and long-term memory capabilities,
including episodic memory, semantic memory, and memory consolidation.
Supports pluggable backends (Redis, PostgreSQL, in-memory).
"""

from .memory import WorkingMemory, LongTermMemory, working_memory, long_term_memory
from .backends import MemoryBackend, MemoryBackendFactory

__all__ = [
    'WorkingMemory',
    'LongTermMemory',
    'working_memory',
    'long_term_memory',
    'MemoryBackend',
    'MemoryBackendFactory'
]