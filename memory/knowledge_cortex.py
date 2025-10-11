"""
Knowledge Cortex Memory System - 4-Layer Architecture

Implements a hierarchical memory system with:
- Cache Layer: Redis for fast access
- Vector Layer: ChromaDB for semantic search
- Graph Layer: NetworkX+DuckDB for relational knowledge
- Archive Layer: S3+DuckDB for long-term storage
"""

from typing import Any, Dict, List, Optional, Union
from ..core.base import MemorySystem, logger, metrics
from ..observability.metrics import prometheus_metrics
from .backends import (
    RedisCacheBackend,
    ChromaVectorBackend,
    NetworkXGraphBackend,
    S3ArchiveBackend,
    MemoryBackend
)
import time
import json


class KnowledgeCortex(MemorySystem):
    """
    4-layer hierarchical memory system implementing Cache → Vector → Graph → Archive architecture.

    Layer hierarchy:
    1. Cache: Fast temporary storage with TTL
    2. Vector: Semantic search and similarity matching
    3. Graph: Relational knowledge with temporal/semantic/relational edges
    4. Archive: Long-term persistent storage
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or self._default_config()
        self.layers = {}

        # Initialize layers
        self._init_layers()

        # Layer access patterns tracking
        self.access_stats = {
            "cache_hits": 0,
            "cache_misses": 0,
            "vector_searches": 0,
            "graph_queries": 0,
            "archive_accesses": 0
        }

    def _default_config(self) -> Dict[str, Any]:
        """Default configuration for all layers"""
        return {
            "cache": {
                "backend": "redis_cache",
                "host": "localhost",
                "port": 6379,
                "db": 0,
                "key_prefix": "brain_cache:",
                "default_ttl": 3600
            },
            "vector": {
                "backend": "chroma_vector",
                "host": "localhost",
                "port": 8000,
                "collection_name": "brain_vectors"
            },
            "graph": {
                "backend": "networkx_graph",
                "db_path": "brain_graph.db"
            },
            "archive": {
                "backend": "s3_archive",
                "bucket_name": "brain-archive",
                "region": "us-east-1",
                "db_path": "brain_archive.db"
            }
        }

    def _init_layers(self):
        """Initialize all four memory layers"""
        try:
            # Cache layer
            cache_config = self.config.get("cache", {})
            self.layers["cache"] = RedisCacheBackend(**cache_config)
            logger.log("INFO", "KnowledgeCortex", "Cache layer initialized")
        except Exception as e:
            logger.log("WARNING", "KnowledgeCortex", f"Cache layer failed to initialize: {e}")
            self.layers["cache"] = None

        try:
            # Vector layer
            vector_config = self.config.get("vector", {})
            self.layers["vector"] = ChromaVectorBackend(**vector_config)
            logger.log("INFO", "KnowledgeCortex", "Vector layer initialized")
        except Exception as e:
            logger.log("WARNING", "KnowledgeCortex", f"Vector layer failed to initialize: {e}")
            self.layers["vector"] = None

        try:
            # Graph layer
            graph_config = self.config.get("graph", {})
            self.layers["graph"] = NetworkXGraphBackend(**graph_config)
            logger.log("INFO", "KnowledgeCortex", "Graph layer initialized")
        except Exception as e:
            logger.log("WARNING", "KnowledgeCortex", f"Graph layer failed to initialize: {e}")
            self.layers["graph"] = None

        try:
            # Archive layer
            archive_config = self.config.get("archive", {})
            self.layers["archive"] = S3ArchiveBackend(**archive_config)
            logger.log("INFO", "KnowledgeCortex", "Archive layer initialized")
        except Exception as e:
            logger.log("WARNING", "KnowledgeCortex", f"Archive layer failed to initialize: {e}")
            self.layers["archive"] = None

    def store(self, key: str, data: Any, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Store data across appropriate layers based on metadata hints.

        Storage strategy:
        - All data goes to cache (if available) for fast access
        - Vectorizable content goes to vector layer
        - Relational data goes to graph layer
        - All data gets archived for long-term storage
        """
        start_time = time.time()
        success = True
        meta = metadata or {}

        # Record memory operation start
        prometheus_metrics.record_memory_operation("store_start", "knowledge_cortex")

        # Determine storage layers based on content type and metadata
        store_cache = self.layers["cache"] is not None
        store_vector = self._should_store_vector(data, meta)
        store_graph = self._should_store_graph(data, meta)
        store_archive = self.layers["archive"] is not None

        # Store in cache (fast access layer)
        if store_cache:
            cache_meta = meta.copy()
            cache_meta["layer"] = "cache"
            if self.layers["cache"].store(key, data, cache_meta):
                logger.log("DEBUG", "KnowledgeCortex", f"Stored in cache: {key}")
            else:
                logger.log("WARNING", "KnowledgeCortex", f"Failed to store in cache: {key}")
                success = False

        # Store in vector layer (semantic search)
        if store_vector and self.layers["vector"]:
            vector_meta = meta.copy()
            vector_meta["layer"] = "vector"
            if self.layers["vector"].store(key, data, vector_meta):
                logger.log("DEBUG", "KnowledgeCortex", f"Stored in vector: {key}")
            else:
                logger.log("WARNING", "KnowledgeCortex", f"Failed to store in vector: {key}")

        # Store in graph layer (relational knowledge)
        if store_graph and self.layers["graph"]:
            graph_meta = meta.copy()
            graph_meta["layer"] = "graph"
            if self.layers["graph"].store(key, data, graph_meta):
                logger.log("DEBUG", "KnowledgeCortex", f"Stored in graph: {key}")
            else:
                logger.log("WARNING", "KnowledgeCortex", f"Failed to store in graph: {key}")

        # Store in archive (long-term persistence)
        if store_archive:
            archive_meta = meta.copy()
            archive_meta["layer"] = "archive"
            archive_meta["stored_at"] = time.time()
            if self.layers["archive"].store(key, data, archive_meta):
                logger.log("DEBUG", "KnowledgeCortex", f"Stored in archive: {key}")
            else:
                logger.log("WARNING", "KnowledgeCortex", f"Failed to store in archive: {key}")
                success = False

        # Track metrics
        metrics.track_memory_operation("store", len(str(data).encode('utf-8')), success)

        # Record completion metrics
        processing_time = time.time() - start_time
        prometheus_metrics.record_memory_operation("store_complete", "knowledge_cortex", processing_time)

        return success

    def _should_store_vector(self, data: Any, metadata: Dict[str, Any]) -> bool:
        """Determine if data should be stored in vector layer"""
        if not self.layers["vector"]:
            return False

        # Store text content for semantic search
        if metadata.get("vectorize", False):
            return True

        # Auto-detect text content
        data_str = str(data)
        if len(data_str) > 10 and not data_str.isdigit():
            return True

        return False

    def _should_store_graph(self, data: Any, metadata: Dict[str, Any]) -> bool:
        """Determine if data should be stored in graph layer"""
        if not self.layers["graph"]:
            return False

        # Explicit graph storage request
        if metadata.get("store_graph", False):
            return True

        # Check for relational data patterns
        if isinstance(data, dict):
            if any(key in data for key in ["source", "target", "edges", "nodes"]):
                return True
            if metadata.get("type") in ["node", "edge", "relation"]:
                return True

        return False

    def retrieve(self, key: str, search_fallback: bool = True) -> Optional[Any]:
        """
        Retrieve data using hierarchical lookup: Cache → Vector → Graph → Archive

        Args:
            key: The key to retrieve
            search_fallback: If True, fall back to semantic search if direct lookup fails
        """
        start_time = time.time()

        # Record retrieval start
        prometheus_metrics.record_memory_operation("retrieve_start", "knowledge_cortex")

        # Try cache first (fastest)
        if self.layers["cache"]:
            result = self.layers["cache"].retrieve(key)
            if result is not None:
                self.access_stats["cache_hits"] += 1
                processing_time = time.time() - start_time
                prometheus_metrics.record_memory_operation("retrieve_complete", "knowledge_cortex", processing_time)
                logger.log("DEBUG", "KnowledgeCortex", f"Cache hit for: {key}")
                return result
            else:
                self.access_stats["cache_misses"] += 1

        # Try vector layer
        if self.layers["vector"]:
            result = self.layers["vector"].retrieve(key)
            if result is not None:
                self.access_stats["vector_searches"] += 1
                logger.log("DEBUG", "KnowledgeCortex", f"Vector retrieval for: {key}")
                # Cache the result for future fast access
                if self.layers["cache"]:
                    self.layers["cache"].store(key, result, {"source": "vector"})
                return result

        # Try graph layer
        if self.layers["graph"]:
            result = self.layers["graph"].retrieve(key)
            if result is not None:
                self.access_stats["graph_queries"] += 1
                logger.log("DEBUG", "KnowledgeCortex", f"Graph retrieval for: {key}")
                # Cache the result
                if self.layers["cache"]:
                    self.layers["cache"].store(key, result, {"source": "graph"})
                return result

        # Try archive (slowest)
        if self.layers["archive"]:
            result = self.layers["archive"].retrieve(key)
            if result is not None:
                self.access_stats["archive_accesses"] += 1
                logger.log("DEBUG", "KnowledgeCortex", f"Archive retrieval for: {key}")
                # Cache the result for future fast access
                if self.layers["cache"]:
                    self.layers["cache"].store(key, result, {"source": "archive"})
                return result

        # If direct lookup failed and search_fallback is enabled, try semantic search
        if search_fallback:
            result = self._semantic_search_retrieve(key)
            if result is not None:
                processing_time = time.time() - start_time
                prometheus_metrics.record_memory_operation("retrieve_complete", "knowledge_cortex", processing_time)
                return result

        processing_time = time.time() - start_time
        prometheus_metrics.record_memory_operation("retrieve_complete", "knowledge_cortex", processing_time)
        return None

    def _semantic_search_retrieve(self, key: str) -> Optional[Any]:
        """Attempt retrieval using semantic search as fallback"""
        if not self.layers["vector"]:
            return None

        # Use the key as a search query
        search_results = self.layers["vector"].search(key, top_k=1)
        if search_results:
            result = search_results[0]
            logger.log("DEBUG", "KnowledgeCortex", f"Semantic search fallback for: {key}")
            # Cache the result
            if self.layers["cache"]:
                self.layers["cache"].store(key, result, {"source": "semantic_search"})
            return result

        return None

    def search(self, query: str, **kwargs) -> List[Any]:
        """
        Multi-layer search combining results from all available layers.

        Search strategy:
        1. Vector layer for semantic similarity
        2. Graph layer for relational matches
        3. Archive layer for historical data
        4. Cache layer for recent results
        """
        all_results = []
        search_type = kwargs.get("search_type", "combined")

        # Vector search (semantic similarity)
        if self.layers["vector"] and search_type in ["combined", "semantic"]:
            vector_results = self.layers["vector"].search(query, **kwargs)
            all_results.extend([{"source": "vector", "data": r} for r in vector_results])
            self.access_stats["vector_searches"] += 1

        # Graph search (relational)
        if self.layers["graph"] and search_type in ["combined", "relational"]:
            graph_results = self.layers["graph"].search(query, **kwargs)
            all_results.extend([{"source": "graph", "data": r} for r in graph_results])
            self.access_stats["graph_queries"] += 1

        # Archive search (historical)
        if self.layers["archive"] and search_type in ["combined", "historical"]:
            archive_results = self.layers["archive"].search(query, **kwargs)
            all_results.extend([{"source": "archive", "data": r} for r in archive_results])
            self.access_stats["archive_accesses"] += 1

        # Cache search (recent)
        if self.layers["cache"] and search_type in ["combined", "recent"]:
            cache_results = self.layers["cache"].search(query, **kwargs)
            all_results.extend([{"source": "cache", "data": r} for r in cache_results])

        # Remove duplicates and sort by relevance
        unique_results = self._deduplicate_results(all_results)

        logger.log("INFO", "KnowledgeCortex", f"Multi-layer search for '{query}' returned {len(unique_results)} results")
        return unique_results

    def _deduplicate_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate results and sort by relevance"""
        seen = set()
        unique = []

        for result in results:
            # Create a hash of the data for deduplication
            data_hash = hash(str(result["data"]))
            if data_hash not in seen:
                seen.add(data_hash)
                unique.append(result)

        # Sort by source priority (cache > vector > graph > archive)
        priority_order = {"cache": 0, "vector": 1, "graph": 2, "archive": 3}
        unique.sort(key=lambda x: priority_order.get(x["source"], 99))

        return unique

    def add_relationship(self, source: str, target: str, relation_type: str,
                        metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Add a relationship between entities in the graph layer.

        Supports temporal, semantic, and relational edge types.
        """
        if not self.layers["graph"]:
            logger.log("WARNING", "KnowledgeCortex", "Graph layer not available for relationships")
            return False

        edge_data = {
            "relation_type": relation_type,
            "timestamp": time.time()
        }

        if metadata:
            edge_data.update(metadata)

        edge_key = f"{source}_{relation_type}_{target}_{int(time.time())}"

        graph_meta = {
            "type": "edge",
            "source": source,
            "target": target,
            "edge_type": relation_type,
            "layer": "graph"
        }

        success = self.layers["graph"].store(edge_key, edge_data, graph_meta)

        if success:
            logger.log("INFO", "KnowledgeCortex", f"Added {relation_type} relationship: {source} -> {target}")

            # Also store in cache for fast access
            if self.layers["cache"]:
                self.layers["cache"].store(edge_key, edge_data, graph_meta)

        return success

    def get_relationships(self, entity: str, relation_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get relationships for an entity from the graph layer"""
        if not self.layers["graph"]:
            return []

        # This is a simplified implementation - in practice, you'd need more sophisticated
        # graph traversal methods in the NetworkXGraphBackend
        relationships = []

        # Search for edges involving this entity
        all_edges = self.layers["graph"].search(entity)
        for edge in all_edges:
            if edge.get("type") == "edge":
                if relation_type is None or edge.get("edge_type") == relation_type:
                    relationships.append(edge)

        return relationships

    def archive_old_data(self, age_threshold_days: int = 30):
        """Move old data from cache/vector to archive for long-term storage"""
        if not self.layers["archive"]:
            return

        current_time = time.time()
        threshold_seconds = age_threshold_days * 24 * 3600

        archived_count = 0

        # Archive old cache entries
        if self.layers["cache"]:
            cache_keys = self.layers["cache"].keys()
            for key in cache_keys:
                entry = self.layers["cache"].retrieve(key)
                if entry and isinstance(entry, dict):
                    age = current_time - entry.get("timestamp", 0)
                    if age > threshold_seconds:
                        # Move to archive
                        archive_meta = entry.get("metadata", {}).copy()
                        archive_meta["archived_from"] = "cache"
                        archive_meta["archive_timestamp"] = current_time

                        self.layers["archive"].store(key, entry["data"], archive_meta)
                        self.layers["cache"].delete(key)
                        archived_count += 1

        logger.log("INFO", "KnowledgeCortex", f"Archived {archived_count} old entries")

    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of all layers"""
        status = {
            "overall_status": "healthy",
            "layers": {},
            "access_stats": self.access_stats.copy()
        }

        unhealthy_layers = []

        for layer_name, layer in self.layers.items():
            if layer:
                try:
                    layer_status = layer.health_check()
                    status["layers"][layer_name] = layer_status
                    if layer_status.get("status") != "healthy":
                        unhealthy_layers.append(layer_name)
                except Exception as e:
                    status["layers"][layer_name] = {"status": "error", "error": str(e)}
                    unhealthy_layers.append(layer_name)
            else:
                status["layers"][layer_name] = {"status": "not_initialized"}
                unhealthy_layers.append(layer_name)

        if unhealthy_layers:
            status["overall_status"] = "degraded"
            status["unhealthy_layers"] = unhealthy_layers

        return status

    def optimize(self):
        """Optimize all layers (cleanup, compaction, etc.)"""
        logger.log("INFO", "KnowledgeCortex", "Starting memory optimization")

        # Archive old data
        self.archive_old_data()

        # Each layer can implement its own optimization
        for layer_name, layer in self.layers.items():
            if layer and hasattr(layer, 'optimize'):
                try:
                    layer.optimize()
                    logger.log("DEBUG", "KnowledgeCortex", f"Optimized layer: {layer_name}")
                except Exception as e:
                    logger.log("WARNING", "KnowledgeCortex", f"Failed to optimize layer {layer_name}: {e}")

        logger.log("INFO", "KnowledgeCortex", "Memory optimization completed")


# Global instance for easy access
_knowledge_cortex_config = {
    "cache": {
        "backend": "redis_cache",
        "host": "localhost",
        "port": 6379,
        "db": 0,
        "key_prefix": "brain_cache:",
        "default_ttl": 3600
    },
    "vector": {
        "backend": "chroma_vector",
        "host": "localhost",
        "port": 8000,
        "collection_name": "brain_vectors"
    },
    "graph": {
        "backend": "networkx_graph",
        "db_path": "brain_graph.db"
    },
    "archive": {
        "backend": "s3_archive",
        "bucket_name": "brain-archive",
        "region": "us-east-1",
        "db_path": "brain_archive.db"
    }
}

# Create global instance
try:
    knowledge_cortex = KnowledgeCortex(_knowledge_cortex_config)
    logger.log("INFO", "KnowledgeCortex", "Knowledge Cortex initialized successfully")
except Exception as e:
    logger.log("ERROR", "KnowledgeCortex", f"Failed to initialize Knowledge Cortex: {e}")
    knowledge_cortex = None