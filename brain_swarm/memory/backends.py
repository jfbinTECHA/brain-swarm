from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import time
import json
import os

class MemoryBackend(ABC):
    """Abstract base class for memory storage backends"""

    @abstractmethod
    def store(self, key: str, data: Any, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Store data with optional metadata"""
        pass

    @abstractmethod
    def retrieve(self, key: str) -> Optional[Any]:
        """Retrieve data by key"""
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete data by key"""
        pass

    @abstractmethod
    def search(self, query: str, **kwargs) -> List[Any]:
        """Search for data matching query"""
        pass

    @abstractmethod
    def keys(self, pattern: str = "*") -> List[str]:
        """Get all keys matching pattern"""
        pass

    @abstractmethod
    def clear(self) -> bool:
        """Clear all data"""
        pass

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """Check backend health and status"""
        pass

class InMemoryBackend(MemoryBackend):
    """In-memory storage backend (default, fast but not persistent)"""

    def __init__(self):
        self.store_data: Dict[str, Dict[str, Any]] = {}

    def store(self, key: str, data: Any, metadata: Optional[Dict[str, Any]] = None) -> bool:
        try:
            self.store_data[key] = {
                "data": data,
                "metadata": metadata or {},
                "timestamp": time.time()
            }
            return True
        except Exception:
            return False

    def retrieve(self, key: str) -> Optional[Any]:
        entry = self.store_data.get(key)
        return entry["data"] if entry else None

    def delete(self, key: str) -> bool:
        return self.store_data.pop(key, None) is not None

    def search(self, query: str, **kwargs) -> List[Any]:
        results = []
        for key, entry in self.store_data.items():
            if query.lower() in key.lower():
                results.append(entry["data"])
            elif isinstance(entry["data"], str) and query.lower() in entry["data"].lower():
                results.append(entry["data"])
        return results

    def keys(self, pattern: str = "*") -> List[str]:
        if pattern == "*":
            return list(self.store_data.keys())
        return [k for k in self.store_data.keys() if pattern in k]

    def clear(self) -> bool:
        self.store_data.clear()
        return True

    def health_check(self) -> Dict[str, Any]:
        return {
            "backend": "in_memory",
            "status": "healthy",
            "entries": len(self.store_data),
            "memory_usage": "N/A"
        }

class RedisBackend(MemoryBackend):
    """Redis-based storage backend (persistent, distributed)"""

    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0,
                 password: Optional[str] = None, key_prefix: str = "brain_swarm:"):
        self.key_prefix = key_prefix
        self.redis_client = None

        try:
            import redis
            self.redis_client = redis.Redis(
                host=host,
                port=port,
                db=db,
                password=password,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # Test connection
            self.redis_client.ping()
        except ImportError:
            raise ImportError("redis package not installed. Install with: pip install redis")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Redis: {e}")

    def _make_key(self, key: str) -> str:
        return f"{self.key_prefix}{key}"

    def store(self, key: str, data: Any, metadata: Optional[Dict[str, Any]] = None) -> bool:
        try:
            full_key = self._make_key(key)
            entry = {
                "data": data,
                "metadata": metadata or {},
                "timestamp": time.time()
            }
            self.redis_client.set(full_key, json.dumps(entry))
            return True
        except Exception:
            return False

    def retrieve(self, key: str) -> Optional[Any]:
        try:
            full_key = self._make_key(key)
            data = self.redis_client.get(full_key)
            if data:
                entry = json.loads(data)
                return entry["data"]
            return None
        except Exception:
            return None

    def delete(self, key: str) -> bool:
        try:
            full_key = self._make_key(key)
            return self.redis_client.delete(full_key) > 0
        except Exception:
            return False

    def search(self, query: str, **kwargs) -> List[Any]:
        # Redis doesn't have built-in text search, so we scan keys
        results = []
        try:
            for key in self.redis_client.scan_iter(f"{self.key_prefix}*"):
                data = self.redis_client.get(key)
                if data:
                    entry = json.loads(data)
                    if query.lower() in key.lower():
                        results.append(entry["data"])
                    elif isinstance(entry["data"], str) and query.lower() in entry["data"].lower():
                        results.append(entry["data"])
        except Exception:
            pass
        return results

    def keys(self, pattern: str = "*") -> List[str]:
        try:
            full_pattern = f"{self.key_prefix}{pattern}"
            keys = list(self.redis_client.scan_iter(full_pattern))
            # Remove prefix
            return [k[len(self.key_prefix):] for k in keys]
        except Exception:
            return []

    def clear(self) -> bool:
        try:
            keys = list(self.redis_client.scan_iter(f"{self.key_prefix}*"))
            if keys:
                self.redis_client.delete(*keys)
            return True
        except Exception:
            return False

    def health_check(self) -> Dict[str, Any]:
        try:
            info = self.redis_client.info()
            key_count = len(list(self.redis_client.scan_iter(f"{self.key_prefix}*")))
            return {
                "backend": "redis",
                "status": "healthy",
                "entries": key_count,
                "memory_usage": info.get("used_memory_human", "unknown"),
                "connections": info.get("connected_clients", 0)
            }
        except Exception as e:
            return {
                "backend": "redis",
                "status": "unhealthy",
                "error": str(e)
            }

class PostgresBackend(MemoryBackend):
    """PostgreSQL-based storage backend (persistent, relational)"""

    def __init__(self, host: str = "localhost", port: int = 5432, database: str = "brain_swarm",
                 user: str = "postgres", password: str = "", table_name: str = "memory_store"):
        self.table_name = table_name
        self.connection = None

        try:
            import psycopg2
            self.connection = psycopg2.connect(
                host=host,
                port=port,
                database=database,
                user=user,
                password=password,
                connect_timeout=5
            )
            self.connection.autocommit = True

            # Create table if it doesn't exist
            self._create_table()

        except ImportError:
            raise ImportError("psycopg2 package not installed. Install with: pip install psycopg2-binary")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to PostgreSQL: {e}")

    def _create_table(self):
        """Create memory storage table if it doesn't exist"""
        create_query = f"""
        CREATE TABLE IF NOT EXISTS {self.table_name} (
            key TEXT PRIMARY KEY,
            data JSONB,
            metadata JSONB,
            timestamp DOUBLE PRECISION,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_{self.table_name}_timestamp ON {self.table_name}(timestamp);
        """
        with self.connection.cursor() as cursor:
            cursor.execute(create_query)

    def store(self, key: str, data: Any, metadata: Optional[Dict[str, Any]] = None) -> bool:
        try:
            with self.connection.cursor() as cursor:
                query = f"""
                INSERT INTO {self.table_name} (key, data, metadata, timestamp)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (key) DO UPDATE SET
                    data = EXCLUDED.data,
                    metadata = EXCLUDED.metadata,
                    timestamp = EXCLUDED.timestamp;
                """
                cursor.execute(query, (key, json.dumps(data), json.dumps(metadata or {}), time.time()))
            return True
        except Exception:
            return False

    def retrieve(self, key: str) -> Optional[Any]:
        try:
            with self.connection.cursor() as cursor:
                query = f"SELECT data FROM {self.table_name} WHERE key = %s;"
                cursor.execute(query, (key,))
                result = cursor.fetchone()
                if result:
                    return json.loads(result[0])
                return None
        except Exception:
            return None

    def delete(self, key: str) -> bool:
        try:
            with self.connection.cursor() as cursor:
                query = f"DELETE FROM {self.table_name} WHERE key = %s;"
                cursor.execute(query, (key,))
            return True
        except Exception:
            return False

    def search(self, query: str, **kwargs) -> List[Any]:
        results = []
        try:
            with self.connection.cursor() as cursor:
                # Search in keys and text data
                search_query = f"""
                SELECT data FROM {self.table_name}
                WHERE key ILIKE %s OR data::text ILIKE %s
                ORDER BY timestamp DESC;
                """
                cursor.execute(search_query, (f"%{query}%", f"%{query}%"))
                for row in cursor.fetchall():
                    results.append(json.loads(row[0]))
        except Exception:
            pass
        return results

    def keys(self, pattern: str = "*") -> List[str]:
        try:
            with self.connection.cursor() as cursor:
                if pattern == "*":
                    query = f"SELECT key FROM {self.table_name};"
                    cursor.execute(query)
                else:
                    query = f"SELECT key FROM {self.table_name} WHERE key LIKE %s;"
                    cursor.execute(query, (pattern.replace("*", "%"),))

                return [row[0] for row in cursor.fetchall()]
        except Exception:
            return []

    def clear(self) -> bool:
        try:
            with self.connection.cursor() as cursor:
                query = f"DELETE FROM {self.table_name};"
                cursor.execute(query)
            return True
        except Exception:
            return False

    def health_check(self) -> Dict[str, Any]:
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(f"SELECT COUNT(*) FROM {self.table_name};")
                count = cursor.fetchone()[0]

                cursor.execute("SELECT pg_database_size(current_database());")
                size_bytes = cursor.fetchone()[0]

            return {
                "backend": "postgres",
                "status": "healthy",
                "entries": count,
                "database_size": f"{size_bytes / (1024*1024):.2f} MB"
            }
        except Exception as e:
            return {
                "backend": "postgres",
                "status": "unhealthy",
                "error": str(e)
            }

class MemoryBackendFactory:
    """Factory for creating memory backends"""

    @staticmethod
    def create_backend(backend_type: str, **config) -> MemoryBackend:
        """Create a memory backend instance"""
        if backend_type.lower() == "memory" or backend_type.lower() == "in_memory":
            return InMemoryBackend()
        elif backend_type.lower() == "redis":
            return RedisBackend(**config)
        elif backend_type.lower() == "postgres" or backend_type.lower() == "postgresql":
            return PostgresBackend(**config)
        else:
            raise ValueError(f"Unknown backend type: {backend_type}")

    @staticmethod
    def get_available_backends() -> List[str]:
        """Get list of available backend types"""
        backends = ["memory"]

        # Check for optional dependencies
        try:
            import redis
            backends.append("redis")
        except ImportError:
            pass

        try:
            import psycopg2
            backends.append("postgres")
        except ImportError:
            pass

        return backends