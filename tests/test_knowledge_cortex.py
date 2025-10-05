"""
Tests for the Knowledge Cortex Memory System - 4-layer architecture
"""
import pytest
import time
from unittest.mock import Mock, patch
from memory.knowledge_cortex import KnowledgeCortex
from memory.backends import (
    RedisCacheBackend,
    ChromaVectorBackend,
    NetworkXGraphBackend,
    S3ArchiveBackend
)


class TestKnowledgeCortex:
    """Test suite for Knowledge Cortex memory system"""

    def test_initialization(self):
        """Test Knowledge Cortex initialization"""
        config = {
            "cache": {"backend": "redis_cache", "host": "localhost", "port": 6379},
            "vector": {"backend": "chroma_vector", "host": "localhost", "port": 8000},
            "graph": {"backend": "networkx_graph", "db_path": ":memory:"},
            "archive": {"backend": "s3_archive", "bucket_name": "test-bucket"}
        }

        cortex = KnowledgeCortex(config)

        # Should have all layers initialized (even if some fail due to missing services)
        assert hasattr(cortex, 'layers')
        assert 'cache' in cortex.layers
        assert 'vector' in cortex.layers
        assert 'graph' in cortex.layers
        assert 'archive' in cortex.layers

    def test_hierarchical_storage(self):
        """Test that data is stored across appropriate layers"""
        # Mock all backends to avoid external dependencies
        with patch('memory.backends.RedisCacheBackend') as mock_cache, \
             patch('memory.backends.ChromaVectorBackend') as mock_vector, \
             patch('memory.backends.NetworkXGraphBackend') as mock_graph, \
             patch('memory.backends.S3ArchiveBackend') as mock_archive:

            # Setup mocks
            mock_cache.return_value.store.return_value = True
            mock_vector.return_value.store.return_value = True
            mock_graph.return_value.store.return_value = True
            mock_archive.return_value.store.return_value = True

            cortex = KnowledgeCortex()
            cortex.layers['cache'] = mock_cache.return_value
            cortex.layers['vector'] = mock_vector.return_value
            cortex.layers['graph'] = mock_graph.return_value
            cortex.layers['archive'] = mock_archive.return_value

            # Test storing regular data
            test_data = "test knowledge"
            metadata = {"type": "semantic"}

            result = cortex.store("test_key", test_data, metadata)

            # Should attempt to store in all layers
            mock_cache.return_value.store.assert_called()
            mock_vector.return_value.store.assert_called()
            mock_graph.return_value.store.assert_called()  # Graph gets all data for potential relationships
            mock_archive.return_value.store.assert_called()

            assert result is True

    def test_hierarchical_retrieval(self):
        """Test hierarchical retrieval: Cache → Vector → Graph → Archive"""
        with patch('memory.backends.RedisCacheBackend') as mock_cache, \
             patch('memory.backends.ChromaVectorBackend') as mock_vector, \
             patch('memory.backends.NetworkXGraphBackend') as mock_graph, \
             patch('memory.backends.S3ArchiveBackend') as mock_archive:

            cortex = KnowledgeCortex()
            cortex.layers['cache'] = mock_cache.return_value
            cortex.layers['vector'] = mock_vector.return_value
            cortex.layers['graph'] = mock_graph.return_value
            cortex.layers['archive'] = mock_archive.return_value

            # Test cache hit
            mock_cache.return_value.retrieve.return_value = "cached_data"
            result = cortex.retrieve("test_key")
            assert result == "cached_data"
            mock_cache.return_value.retrieve.assert_called_with("test_key")

            # Reset and test cache miss, vector hit
            mock_cache.return_value.retrieve.return_value = None
            mock_vector.return_value.retrieve.return_value = "vector_data"

            result = cortex.retrieve("test_key")
            assert result == "vector_data"
            mock_vector.return_value.retrieve.assert_called_with("test_key")
            # Should cache the result
            mock_cache.return_value.store.assert_called()

    def test_semantic_search_fallback(self):
        """Test semantic search fallback when direct retrieval fails"""
        with patch('memory.backends.RedisCacheBackend') as mock_cache, \
             patch('memory.backends.ChromaVectorBackend') as mock_vector:

            cortex = KnowledgeCortex()
            cortex.layers['cache'] = mock_cache.return_value
            cortex.layers['vector'] = mock_vector.return_value
            cortex.layers['graph'] = None
            cortex.layers['archive'] = None

            # All direct retrievals fail
            mock_cache.return_value.retrieve.return_value = None
            mock_vector.return_value.retrieve.return_value = None

            # But semantic search succeeds
            mock_vector.return_value.search.return_value = ["semantic_result"]

            result = cortex.retrieve("test_key", search_fallback=True)

            assert result == "semantic_result"
            mock_vector.return_value.search.assert_called_with("test_key", top_k=1)

    def test_relationship_management(self):
        """Test adding and querying relationships"""
        with patch('memory.backends.NetworkXGraphBackend') as mock_graph, \
             patch('memory.backends.RedisCacheBackend') as mock_cache:

            cortex = KnowledgeCortex()
            cortex.layers['graph'] = mock_graph.return_value
            cortex.layers['cache'] = mock_cache.return_value

            mock_graph.return_value.store.return_value = True

            # Add a relationship
            result = cortex.add_relationship("entity1", "entity2", "related_to",
                                           {"confidence": 0.8})

            assert result is True
            mock_graph.return_value.store.assert_called()

            # Should also cache the relationship
            mock_cache.return_value.store.assert_called()

    def test_multi_layer_search(self):
        """Test searching across multiple layers"""
        with patch('memory.backends.ChromaVectorBackend') as mock_vector, \
             patch('memory.backends.NetworkXGraphBackend') as mock_graph, \
             patch('memory.backends.S3ArchiveBackend') as mock_archive:

            cortex = KnowledgeCortex()
            cortex.layers['vector'] = mock_vector.return_value
            cortex.layers['graph'] = mock_graph.return_value
            cortex.layers['archive'] = mock_archive.return_value
            cortex.layers['cache'] = None

            # Setup mock returns
            mock_vector.return_value.search.return_value = [{"vector": "result1"}]
            mock_graph.return_value.search.return_value = [{"graph": "result2"}]
            mock_archive.return_value.search.return_value = [{"archive": "result3"}]

            results = cortex.search("test query")

            # Should get results from all layers
            assert len(results) == 3
            assert any("vector" in str(r) for r in results)
            assert any("graph" in str(r) for r in results)
            assert any("archive" in str(r) for r in results)

    def test_health_status(self):
        """Test health status reporting"""
        with patch('memory.backends.RedisCacheBackend') as mock_cache:

            cortex = KnowledgeCortex()
            cortex.layers['cache'] = mock_cache.return_value
            cortex.layers['vector'] = None
            cortex.layers['graph'] = None
            cortex.layers['archive'] = None

            mock_cache.return_value.health_check.return_value = {
                "status": "healthy",
                "entries": 42
            }

            status = cortex.get_health_status()

            assert status["overall_status"] == "degraded"  # Some layers not initialized
            assert "cache" in status["layers"]
            assert status["layers"]["cache"]["status"] == "healthy"
            assert "unhealthy_layers" in status

    def test_data_archiving(self):
        """Test archiving old data"""
        with patch('memory.backends.RedisCacheBackend') as mock_cache, \
             patch('memory.backends.S3ArchiveBackend') as mock_archive:

            cortex = KnowledgeCortex()
            cortex.layers['cache'] = mock_cache.return_value
            cortex.layers['archive'] = mock_archive.return_value

            # Mock old cache entry
            old_timestamp = time.time() - (31 * 24 * 3600)  # 31 days ago
            mock_cache.return_value.keys.return_value = ["old_key"]
            mock_cache.return_value.retrieve.return_value = {
                "data": "old_data",
                "timestamp": old_timestamp,
                "metadata": {}
            }
            mock_archive.return_value.store.return_value = True

            cortex.archive_old_data(age_threshold_days=30)

            # Should archive the old data
            mock_archive.return_value.store.assert_called_with(
                "old_key", "old_data", pytest.any(dict)
            )
            # Should delete from cache
            mock_cache.return_value.delete.assert_called_with("old_key")

    def test_layer_initialization_failure(self):
        """Test graceful handling of layer initialization failures"""
        # Test with invalid config that will cause failures
        config = {
            "cache": {"backend": "redis_cache", "host": "invalid_host", "port": 99999},
            "vector": {"backend": "chroma_vector", "host": "invalid_host", "port": 99999},
            "graph": {"backend": "networkx_graph", "db_path": "/invalid/path"},
            "archive": {"backend": "s3_archive", "bucket_name": "invalid_bucket"}
        }

        cortex = KnowledgeCortex(config)

        # Should still initialize but layers should be None or handle errors gracefully
        assert cortex.layers is not None

        # Health check should report issues
        status = cortex.get_health_status()
        assert status["overall_status"] in ["degraded", "unhealthy"]


class TestTemporalSemanticRelationalEdges:
    """Test the different edge types supported by the graph layer"""

    def test_temporal_edges(self):
        """Test temporal relationship edges"""
        with patch('memory.backends.NetworkXGraphBackend') as mock_graph:

            cortex = KnowledgeCortex()
            cortex.layers['graph'] = mock_graph.return_value
            mock_graph.return_value.store.return_value = True

            # Add temporal relationship (before/after)
            result = cortex.add_relationship(
                "event1", "event2", "happened_before",
                {"edge_type": "temporal", "time_diff": 3600}
            )

            assert result is True

            # Verify the call
            call_args = mock_graph.return_value.store.call_args
            assert call_args[1]["metadata"]["edge_type"] == "happened_before"

    def test_semantic_edges(self):
        """Test semantic relationship edges"""
        with patch('memory.backends.NetworkXGraphBackend') as mock_graph:

            cortex = KnowledgeCortex()
            cortex.layers['graph'] = mock_graph.return_value
            mock_graph.return_value.store.return_value = True

            # Add semantic relationship (is_a, part_of, etc.)
            result = cortex.add_relationship(
                "cat", "animal", "is_a",
                {"edge_type": "semantic", "confidence": 0.95}
            )

            assert result is True

    def test_relational_edges(self):
        """Test relational edges between entities"""
        with patch('memory.backends.NetworkXGraphBackend') as mock_graph:

            cortex = KnowledgeCortex()
            cortex.layers['graph'] = mock_graph.return_value
            mock_graph.return_value.store.return_value = True

            # Add relational edge (works_with, located_in, etc.)
            result = cortex.add_relationship(
                "alice", "bob", "collaborates_with",
                {"edge_type": "relational", "project": "brain_swarm"}
            )

            assert result is True


class TestLayerSpecificFunctionality:
    """Test layer-specific functionality"""

    def test_cache_ttl_functionality(self):
        """Test cache TTL behavior"""
        with patch('memory.backends.RedisCacheBackend') as mock_cache:

            cortex = KnowledgeCortex()
            cortex.layers['cache'] = mock_cache.return_value
            mock_cache.return_value.store.return_value = True

            # Store with custom TTL
            cortex.store("ttl_key", "data", {"ttl": 7200})

            # Verify TTL was passed
            call_args = mock_cache.return_value.store.call_args
            assert call_args[1]["metadata"]["ttl"] == 7200

    def test_vector_similarity_search(self):
        """Test vector layer similarity search"""
        with patch('memory.backends.ChromaVectorBackend') as mock_vector:

            cortex = KnowledgeCortex()
            cortex.layers['vector'] = mock_vector.return_value

            mock_vector.return_value.search.return_value = [
                {"document": "similar content", "similarity": 0.85}
            ]

            results = cortex.search("test query", search_type="semantic")

            assert len(results) > 0
            mock_vector.return_value.search.assert_called_with("test query", **{})

    def test_graph_traversal(self):
        """Test graph relationship traversal"""
        with patch('memory.backends.NetworkXGraphBackend') as mock_graph:

            cortex = KnowledgeCortex()
            cortex.layers['graph'] = mock_graph.return_value

            mock_graph.return_value.search.return_value = [
                {"type": "edge", "source": "A", "target": "B", "edge_type": "related"}
            ]

            relationships = cortex.get_relationships("entity_A")

            # This would need more sophisticated implementation in the real graph backend
            # For now, just test that the method exists and calls the backend
            assert isinstance(relationships, list)


if __name__ == "__main__":
    pytest.main([__file__])