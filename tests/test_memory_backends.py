import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from brain_swarm.memory.backends import (
    MemoryBackend, InMemoryBackend, RedisBackend, PostgresBackend, MemoryBackendFactory
)


class TestInMemoryBackend:
    """Test suite for InMemoryBackend edge cases"""

    def setup_method(self):
        """Set up test fixtures"""
        self.backend = InMemoryBackend()

    def test_initialization(self):
        """Test backend initializes correctly"""
        assert isinstance(self.backend.store_data, dict)
        assert len(self.backend.store_data) == 0

    def test_store_and_retrieve(self):
        """Test basic store and retrieve operations"""
        key = "test_key"
        data = {"test": "data", "number": 42}

        # Store
        success = self.backend.store(key, data)
        assert success is True

        # Retrieve
        retrieved = self.backend.retrieve(key)
        assert retrieved == data

    def test_retrieve_nonexistent_key(self):
        """Test retrieving non-existent key returns None"""
        retrieved = self.backend.retrieve("nonexistent")
        assert retrieved is None

    def test_delete_existing_key(self):
        """Test deleting existing key"""
        key = "test_key"
        self.backend.store(key, "test_data")

        success = self.backend.delete(key)
        assert success is True

        # Verify deletion
        retrieved = self.backend.retrieve(key)
        assert retrieved is None

    def test_delete_nonexistent_key(self):
        """Test deleting non-existent key"""
        success = self.backend.delete("nonexistent")
        assert success is False

    def test_search_functionality(self):
        """Test search across stored data"""
        # Store test data
        self.backend.store("key1", "hello world")
        self.backend.store("key2", {"message": "hello universe"})
        self.backend.store("key3", "goodbye world")

        # Search for "world"
        results = self.backend.search("world")
        assert len(results) == 2  # Should find key1 and key3

        # Search for "hello"
        results = self.backend.search("hello")
        assert len(results) == 2  # Should find key1 and key2

        # Search for non-existent term
        results = self.backend.search("nonexistent")
        assert len(results) == 0

    def test_keys_functionality(self):
        """Test keys listing functionality"""
        # Store test data
        self.backend.store("key1", "data1")
        self.backend.store("key2", "data2")
        self.backend.store("prefix_key3", "data3")

        # Get all keys
        all_keys = self.backend.keys()
        assert len(all_keys) == 3
        assert "key1" in all_keys
        assert "key2" in all_keys
        assert "prefix_key3" in all_keys

        # Get keys with pattern
        prefix_keys = self.backend.keys("prefix_*")
        assert len(prefix_keys) == 1
        assert "prefix_key3" in prefix_keys

    def test_clear_functionality(self):
        """Test clear all data"""
        # Store test data
        self.backend.store("key1", "data1")
        self.backend.store("key2", "data2")

        # Clear
        success = self.backend.clear()
        assert success is True

        # Verify cleared
        assert len(self.backend.store_data) == 0
        retrieved = self.backend.retrieve("key1")
        assert retrieved is None

    def test_health_check(self):
        """Test health check functionality"""
        health = self.backend.health_check()

        assert health["backend"] == "in_memory"
        assert health["status"] == "healthy"
        assert "entries" in health
        assert health["memory_usage"] == "N/A"

    def test_large_data_handling(self):
        """Test handling of large data objects"""
        large_data = {"data": "x" * 1000000}  # 1MB string

        success = self.backend.store("large_key", large_data)
        assert success is True

        retrieved = self.backend.retrieve("large_key")
        assert retrieved == large_data

    def test_special_characters_in_keys(self):
        """Test keys with special characters"""
        special_keys = [
            "key with spaces",
            "key-with-dashes",
            "key_with_underscores",
            "key.with.dots",
            "key/with/slashes"
        ]

        for key in special_keys:
            success = self.backend.store(key, f"data for {key}")
            assert success is True

            retrieved = self.backend.retrieve(key)
            assert retrieved == f"data for {key}"

    def test_none_values(self):
        """Test storing and retrieving None values"""
        success = self.backend.store("none_key", None)
        assert success is True

        retrieved = self.backend.retrieve("none_key")
        assert retrieved is None

    def test_complex_nested_data(self):
        """Test storing complex nested data structures"""
        complex_data = {
            "nested": {
                "deeply": {
                    "nested": {
                        "value": [1, 2, {"more": "complexity"}]
                    }
                }
            },
            "list": [1, "string", {"key": "value"}],
            "timestamp": time.time()
        }

        success = self.backend.store("complex_key", complex_data)
        assert success is True

        retrieved = self.backend.retrieve("complex_key")
        assert retrieved == complex_data


class TestRedisBackend:
    """Test suite for RedisBackend edge cases"""

    def setup_method(self):
        """Set up test fixtures with mocked Redis"""
        self.mock_redis = MagicMock()
        self.backend = RedisBackend.__new__(RedisBackend)
        self.backend.redis_client = self.mock_redis
        self.backend.key_prefix = "test:"

    def test_initialization_success(self):
        """Test successful Redis backend initialization"""
        with patch('redis.Redis') as mock_redis_class:
            mock_client = MagicMock()
            mock_redis_class.return_value = mock_client
            mock_client.ping.return_value = True

            backend = RedisBackend(host="localhost", port=6379)

            assert backend.redis_client == mock_client
            mock_redis_class.assert_called_once()

    def test_initialization_connection_failure(self):
        """Test Redis backend initialization with connection failure"""
        with patch('redis.Redis') as mock_redis_class:
            mock_client = MagicMock()
            mock_redis_class.return_value = mock_client
            mock_client.ping.side_effect = Exception("Connection failed")

            with pytest.raises(ConnectionError):
                RedisBackend(host="localhost", port=6379)

    def test_store_operation(self):
        """Test Redis store operation"""
        self.mock_redis.set.return_value = True

        success = self.backend.store("test_key", "test_data")

        assert success is True
        self.mock_redis.set.assert_called_once_with("test:test_key", '{"data": "test_data", "metadata": {}, "timestamp": 0.0}')

    def test_retrieve_operation(self):
        """Test Redis retrieve operation"""
        import json
        test_data = {"data": "test_value", "metadata": {}, "timestamp": 1234567890.0}
        self.mock_redis.get.return_value = json.dumps(test_data)

        result = self.backend.retrieve("test_key")

        assert result == "test_value"
        self.mock_redis.get.assert_called_once_with("test:test_key")

    def test_retrieve_nonexistent_key(self):
        """Test retrieving non-existent key from Redis"""
        self.mock_redis.get.return_value = None

        result = self.backend.retrieve("nonexistent")

        assert result is None

    def test_delete_operation(self):
        """Test Redis delete operation"""
        self.mock_redis.delete.return_value = 1

        success = self.backend.delete("test_key")

        assert success is True
        self.mock_redis.delete.assert_called_once_with("test:test_key")

    def test_delete_nonexistent_key(self):
        """Test deleting non-existent key from Redis"""
        self.mock_redis.delete.return_value = 0

        success = self.backend.delete("nonexistent")

        assert success is False

    def test_search_operation(self):
        """Test Redis search operation (scan-based)"""
        # Mock scan to return keys
        self.mock_redis.scan_iter.return_value = ["test:key1", "test:key2"]
        self.mock_redis.get.side_effect = [
            '{"data": "hello world", "metadata": {}, "timestamp": 0.0}',
            '{"data": "goodbye world", "metadata": {}, "timestamp": 0.0}'
        ]

        results = self.backend.search("world")

        assert len(results) == 2
        self.mock_redis.scan_iter.assert_called_once_with("test:*")

    def test_keys_operation(self):
        """Test Redis keys operation"""
        self.mock_redis.scan_iter.return_value = ["test:key1", "test:key2", "test:key3"]

        keys = self.backend.keys()

        assert len(keys) == 3
        assert "key1" in keys
        assert "key2" in keys
        assert "key3" in keys

    def test_keys_with_pattern(self):
        """Test Redis keys operation with pattern"""
        self.mock_redis.scan_iter.return_value = ["test:prefix_key1", "test:prefix_key2"]

        keys = self.backend.keys("prefix_*")

        assert len(keys) == 2
        assert "prefix_key1" in keys
        assert "prefix_key2" in keys

    def test_clear_operation(self):
        """Test Redis clear operation"""
        self.mock_redis.scan_iter.return_value = ["test:key1", "test:key2"]
        self.mock_redis.delete.return_value = 2

        success = self.backend.clear()

        assert success is True
        self.mock_redis.delete.assert_called_once_with("test:key1", "test:key2")

    def test_health_check_success(self):
        """Test Redis health check when healthy"""
        mock_info = {
            "used_memory_human": "10M",
            "connected_clients": "5"
        }
        self.mock_redis.info.return_value = mock_info
        self.mock_redis.scan_iter.return_value = ["test:key1"]

        health = self.backend.health_check()

        assert health["backend"] == "redis"
        assert health["status"] == "healthy"
        assert health["entries"] == 1
        assert health["memory_usage"] == "10M"
        assert health["connections"] == "5"

    def test_health_check_failure(self):
        """Test Redis health check when unhealthy"""
        self.mock_redis.info.side_effect = Exception("Connection error")

        health = self.backend.health_check()

        assert health["backend"] == "redis"
        assert health["status"] == "unhealthy"
        assert "error" in health


class TestPostgresBackend:
    """Test suite for PostgresBackend edge cases"""

    def setup_method(self):
        """Set up test fixtures with mocked PostgreSQL"""
        self.mock_connection = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_connection.cursor.return_value = self.mock_cursor
        self.mock_connection.autocommit = True

        self.backend = PostgresBackend.__new__(PostgresBackend)
        self.backend.connection = self.mock_connection
        self.backend.table_name = "test_memory"

    def test_initialization_success(self):
        """Test successful PostgreSQL backend initialization"""
        with patch('psycopg2.connect') as mock_connect, \
             patch.object(PostgresBackend, '_create_table') as mock_create:

            mock_connect.return_value = self.mock_connection

            backend = PostgresBackend(host="localhost", database="test")

            assert backend.connection == self.mock_connection
            mock_create.assert_called_once()

    def test_initialization_connection_failure(self):
        """Test PostgreSQL backend initialization with connection failure"""
        with patch('psycopg2.connect') as mock_connect:
            mock_connect.side_effect = Exception("Connection failed")

            with pytest.raises(ConnectionError):
                PostgresBackend(host="localhost", database="test")

    def test_store_operation(self):
        """Test PostgreSQL store operation"""
        self.mock_cursor.execute.return_value = None

        success = self.backend.store("test_key", "test_data")

        assert success is True
        assert self.mock_cursor.execute.call_count == 1

    def test_retrieve_operation(self):
        """Test PostgreSQL retrieve operation"""
        self.mock_cursor.fetchone.return_value = ['{"data": "test_value", "metadata": {}, "timestamp": 1234567890.0}']

        result = self.backend.retrieve("test_key")

        assert result == "test_value"
        self.mock_cursor.execute.assert_called_once()

    def test_retrieve_nonexistent_key(self):
        """Test retrieving non-existent key from PostgreSQL"""
        self.mock_cursor.fetchone.return_value = None

        result = self.backend.retrieve("nonexistent")

        assert result is None

    def test_delete_operation(self):
        """Test PostgreSQL delete operation"""
        self.mock_cursor.execute.return_value = None

        success = self.backend.delete("test_key")

        assert success is True
        self.mock_cursor.execute.assert_called_once()

    def test_search_operation(self):
        """Test PostgreSQL search operation"""
        self.mock_cursor.fetchall.return_value = [
            ['{"data": "hello world", "metadata": {}, "timestamp": 0.0}'],
            ['{"data": "goodbye world", "metadata": {}, "timestamp": 0.0}']
        ]

        results = self.backend.search("world")

        assert len(results) == 2
        self.mock_cursor.execute.assert_called_once()

    def test_keys_operation(self):
        """Test PostgreSQL keys operation"""
        self.mock_cursor.fetchall.return_value = [("key1",), ("key2",), ("key3",)]

        keys = self.backend.keys()

        assert len(keys) == 3
        assert "key1" in keys

    def test_clear_operation(self):
        """Test PostgreSQL clear operation"""
        self.mock_cursor.execute.return_value = None

        success = self.backend.clear()

        assert success is True
        self.mock_cursor.execute.assert_called_once()

    def test_health_check_success(self):
        """Test PostgreSQL health check when healthy"""
        self.mock_cursor.fetchone.side_effect = [
            (100,),  # COUNT result
            (10485760,)  # pg_database_size result
        ]

        health = self.backend.health_check()

        assert health["backend"] == "postgres"
        assert health["status"] == "healthy"
        assert health["entries"] == 100
        assert "database_size" in health

    def test_health_check_failure(self):
        """Test PostgreSQL health check when unhealthy"""
        self.mock_cursor.execute.side_effect = Exception("Query failed")

        health = self.backend.health_check()

        assert health["backend"] == "postgres"
        assert health["status"] == "unhealthy"
        assert "error" in health


class TestMemoryBackendFactory:
    """Test suite for MemoryBackendFactory"""

    def test_create_memory_backend(self):
        """Test creating in-memory backend"""
        backend = MemoryBackendFactory.create_backend("memory")

        assert isinstance(backend, InMemoryBackend)

    def test_create_redis_backend(self):
        """Test creating Redis backend"""
        with patch('brain_swarm.memory.backends.RedisBackend.__init__', return_value=None):
            backend = MemoryBackendFactory.create_backend("redis", host="localhost")

            assert isinstance(backend, RedisBackend)

    def test_create_postgres_backend(self):
        """Test creating PostgreSQL backend"""
        with patch('brain_swarm.memory.backends.PostgresBackend.__init__', return_value=None):
            backend = MemoryBackendFactory.create_backend("postgres", host="localhost")

            assert isinstance(backend, PostgresBackend)

    def test_create_unknown_backend(self):
        """Test creating unknown backend type raises error"""
        with pytest.raises(ValueError):
            MemoryBackendFactory.create_backend("unknown")

    def test_get_available_backends(self):
        """Test getting list of available backends"""
        available = MemoryBackendFactory.get_available_backends()

        assert "memory" in available  # Always available

        # Check optional backends based on imports
        try:
            import redis
            assert "redis" in available
        except ImportError:
            assert "redis" not in available

        try:
            import psycopg2
            assert "postgres" in available
        except ImportError:
            assert "postgres" not in available


class TestBackendIntegration:
    """Test suite for backend integration and edge cases"""

    def test_backend_interface_compliance(self):
        """Test that all backends implement the MemoryBackend interface"""
        backends = [
            InMemoryBackend(),
        ]

        # Test optional backends if available
        try:
            with patch('redis.Redis') as mock_redis:
                mock_client = MagicMock()
                mock_redis.return_value = mock_client
                mock_client.ping.return_value = True
                backends.append(RedisBackend())
        except:
            pass

        try:
            with patch('psycopg2.connect') as mock_connect:
                mock_connection = MagicMock()
                mock_connect.return_value = mock_connection
                backends.append(PostgresBackend())
        except:
            pass

        for backend in backends:
            # Test all required methods exist
            assert hasattr(backend, 'store')
            assert hasattr(backend, 'retrieve')
            assert hasattr(backend, 'delete')
            assert hasattr(backend, 'search')
            assert hasattr(backend, 'keys')
            assert hasattr(backend, 'clear')
            assert hasattr(backend, 'health_check')

            # Test health check returns proper structure
            health = backend.health_check()
            assert isinstance(health, dict)
            assert 'backend' in health
            assert 'status' in health

    def test_concurrent_access_simulation(self):
        """Test simulated concurrent access to backends"""
        backend = InMemoryBackend()

        # Simulate concurrent operations
        operations = []
        for i in range(100):
            key = f"concurrent_key_{i}"
            data = f"concurrent_data_{i}"

            # Store
            success = backend.store(key, data)
            assert success is True

            # Retrieve
            retrieved = backend.retrieve(key)
            assert retrieved == data

            operations.append((key, data))

        # Verify all operations succeeded
        for key, expected_data in operations:
            retrieved = backend.retrieve(key)
            assert retrieved == expected_data

    def test_memory_pressure_simulation(self):
        """Test backend behavior under memory pressure"""
        backend = InMemoryBackend()

        # Store many large objects
        for i in range(1000):
            key = f"pressure_key_{i}"
            data = {"large_data": "x" * 1000, "index": i}

            success = backend.store(key, data)
            assert success is True

        # Verify retrieval still works
        for i in range(0, 1000, 100):  # Check every 100th item
            key = f"pressure_key_{i}"
            retrieved = backend.retrieve(key)
            assert retrieved is not None
            assert retrieved["index"] == i

    def test_data_type_preservation(self):
        """Test that various data types are preserved correctly"""
        backend = InMemoryBackend()

        test_data = {
            "string": "hello world",
            "integer": 42,
            "float": 3.14159,
            "boolean": True,
            "none": None,
            "list": [1, 2, 3, "mixed"],
            "dict": {"nested": {"deeply": "nested"}},
            "set": [1, 2, 3],  # Sets become lists in JSON
            "tuple": [1, 2, 3],  # Tuples become lists in JSON
        }

        for key, data in test_data.items():
            success = backend.store(key, data)
            assert success is True

            retrieved = backend.retrieve(key)
            # Note: JSON serialization may change some types (sets->lists, tuples->lists)
            if isinstance(data, (set, tuple)):
                assert retrieved == list(data)
            else:
                assert retrieved == data