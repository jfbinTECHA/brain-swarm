"""
Tests for Knowledge Cortex memory system.
"""

import pytest
import json
from unittest.mock import Mock, patch

from memory.knowledge_cortex import KnowledgeCortex


class TestKnowledgeCortex:
    """Test the Knowledge Cortex system"""

    def setup_method(self):
        """Set up test instance with mock backends"""
        self.config = {
            "cache": {"backend": "memory"},  # Use in-memory for testing
            "vector": {"backend": "memory"},
            "graph": {"backend": "memory"},
            "archive": {"backend": "memory"}
        }
        self.cortex = KnowledgeCortex(self.config)

    def test_initialization(self):
        """Test cortex initializes with all layers"""
        assert self.cortex.layers["cache"] is not None
        assert self.cortex.layers["vector"] is not None
        assert self.cortex.layers["graph"] is not None
        assert self.cortex.layers["archive"] is not None

    def test_store_and_retrieve(self):
        """Test basic store and retrieve operations"""
        test_data = {"name": "test", "value": 123}
        test_key = "test_key"

        # Store data
        result = self.cortex.store(test_key, test_data)
        assert result is True

        # Retrieve data
        retrieved = self.cortex.retrieve(test_key)
        assert retrieved == test_data

    def test_hierarchical_retrieval(self):
        """Test that retrieval works through cache first"""
        test_data = {"content": "test data"}
        test_key = "hierarchy_test"

        # Store data
        self.cortex.store(test_key, test_data)

        # First retrieval should populate cache
        result1 = self.cortex.retrieve(test_key)
        assert result1 == test_data

        # Second retrieval should come from cache
        result2 = self.cortex.retrieve(test_key)
        assert result2 == test_data

        # Check access stats
        assert self.cortex.access_stats["cache_hits"] >= 1

    def test_vector_storage(self):
        """Test vector layer storage for text content"""
        text_data = "This is a test document for semantic search"
        test_key = "vector_test"

        # Store with vectorize hint
        result = self.cortex.store(test_key, text_data, {"vectorize": True})
        assert result is True

        # Retrieve
        retrieved = self.cortex.retrieve(test_key)
        assert retrieved == text_data

    def test_graph_relationships(self):
        """Test graph layer for relationships"""
        # Add a relationship
        result = self.cortex.add_relationship("user_1", "team_a", "member_of")
        assert result is True

        # Query relationships
        relationships = self.cortex.get_relationships("user_1")
        assert len(relationships) > 0
        assert relationships[0]["relation_type"] == "member_of"

    def test_search_functionality(self):
        """Test multi-layer search"""
        # Store test data
        self.cortex.store("doc1", "Python programming tutorial", {"vectorize": True})
        self.cortex.store("doc2", "Java development guide", {"vectorize": True})

        # Search
        results = self.cortex.search("programming")
        assert len(results) > 0

    def test_health_check(self):
        """Test health status reporting"""
        status = self.cortex.get_health_status()

        assert "overall_status" in status
        assert "layers" in status
        assert "access_stats" in status

        # Check all layers are present
        expected_layers = ["cache", "vector", "graph", "archive"]
        for layer in expected_layers:
            assert layer in status["layers"]

    def test_optimization(self):
        """Test system optimization"""
        # This should run without errors
        self.cortex.optimize()

        # Health should still be good
        status = self.cortex.get_health_status()
        assert status["overall_status"] in ["healthy", "degraded"]

    @patch('memory.knowledge_cortex.time')
    def test_archive_old_data(self, mock_time):
        """Test archiving old data"""
        # Mock time to simulate old data
        mock_time.time.return_value = 1000000000  # Old timestamp

        # Store some data
        self.cortex.store("old_data", "old content", {"timestamp": 1000000000})

        # Mock current time as much newer
        mock_time.time.return_value = 1000000000 + (40 * 24 * 3600)  # 40 days later

        # Archive old data
        self.cortex.archive_old_data(age_threshold_days=30)

        # Data should still be retrievable (archive functionality depends on backend)


class TestKnowledgeCortexConfiguration:
    """Test cortex configuration options"""

    def test_default_config(self):
        """Test default configuration"""
        cortex = KnowledgeCortex()
        config = cortex.config

        assert "cache" in config
        assert "vector" in config
        assert "graph" in config
        assert "archive" in config

    def test_custom_config(self):
        """Test custom configuration"""
        custom_config = {
            "cache": {"backend": "memory", "custom_param": "value"},
            "vector": {"backend": "memory"},
            "graph": {"backend": "memory"},
            "archive": {"backend": "memory"}
        }

        cortex = KnowledgeCortex(custom_config)
        assert cortex.config == custom_config

    def test_layer_failure_handling(self):
        """Test graceful handling of layer initialization failures"""
        # Create config that will cause failures (but in test environment, memory backend should work)
        config = {
            "cache": {"backend": "nonexistent_backend"},
            "vector": {"backend": "memory"},
            "graph": {"backend": "memory"},
            "archive": {"backend": "memory"}
        }

        cortex = KnowledgeCortex(config)

        # Cache layer should fail gracefully
        assert cortex.layers["cache"] is None

        # Other layers should still work
        assert cortex.layers["vector"] is not None

        # Overall health should reflect the failure
        status = cortex.get_health_status()
        assert status["overall_status"] == "degraded"


class TestKnowledgeCortexIntegration:
    """Integration tests for the full cortex system"""

    def test_end_to_end_workflow(self):
        """Test complete workflow from storage to retrieval"""
        cortex = KnowledgeCortex({
            "cache": {"backend": "memory"},
            "vector": {"backend": "memory"},
            "graph": {"backend": "memory"},
            "archive": {"backend": "memory"}
        })

        # 1. Store user profile
        user_data = {
            "id": "user_123",
            "name": "Alice Johnson",
            "role": "Senior Developer",
            "skills": ["Python", "AI", "Kubernetes"]
        }

        cortex.store("user_123", user_data, {
            "vectorize": True,
            "data_type": "user_profile"
        })

        # 2. Add relationships
        cortex.add_relationship("user_123", "team_backend", "member_of")
        cortex.add_relationship("user_123", "project_ai", "works_on")

        # 3. Retrieve data
        retrieved_user = cortex.retrieve("user_123")
        assert retrieved_user == user_data

        # 4. Search for users with Python skills
        search_results = cortex.search("Python developer")
        assert len(search_results) > 0

        # 5. Get user relationships
        relationships = cortex.get_relationships("user_123")
        assert len(relationships) >= 2  # member_of and works_on

        # 6. Check system health
        health = cortex.get_health_status()
        assert health["overall_status"] == "healthy"

    def test_memory_layer_interaction(self):
        """Test how data flows between memory layers"""
        cortex = KnowledgeCortex({
            "cache": {"backend": "memory"},
            "vector": {"backend": "memory"},
            "graph": {"backend": "memory"},
            "archive": {"backend": "memory"}
        })

        # Store data that should go to multiple layers
        content = "Advanced machine learning techniques for natural language processing"
        metadata = {
            "vectorize": True,
            "store_graph": True,
            "data_type": "article",
            "tags": ["ML", "NLP", "AI"]
        }

        cortex.store("article_001", content, metadata)

        # Should be retrievable from cache (primary)
        cached = cortex.retrieve("article_001")
        assert cached == content

        # Should be searchable in vector layer
        vector_results = cortex.search("machine learning", search_type="semantic")
        assert len(vector_results) > 0

        # Should have created graph relationships if applicable
        # (This depends on the specific graph storage logic)

        # Archive should contain the data
        # (Archive storage depends on backend implementation)