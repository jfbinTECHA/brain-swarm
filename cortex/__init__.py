"""
Knowledge Cortex - 4-Layer Memory System for Brain Swarm.

This module provides a hierarchical memory architecture with:
- Cache Layer: Redis-based high-performance caching
- Vector Layer: ChromaDB + FAISS semantic search
- Graph Layer: NetworkX + DuckDB relationship storage
- Archive Layer: S3 + DuckDB long-term storage
"""

from .cache_layer import RedisCache
from .vector_layer import VectorStore
from .graph_layer import GraphStore
from .archive_layer import ArchiveStore
from .cortex_api import router as cortex_router
from .metrics import prometheus_metrics as cortex_metrics

__all__ = [
    'RedisCache',
    'VectorStore',
    'GraphStore',
    'ArchiveStore',
    'cortex_router',
    'cortex_metrics'
]