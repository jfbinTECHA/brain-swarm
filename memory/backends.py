from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple
import time
import json
import os
import hashlib
from datetime import datetime, timedelta

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
        elif backend_type.lower() == "redis_cache":
            return RedisCacheBackend(**config)
        elif backend_type.lower() == "chroma_vector":
            return ChromaVectorBackend(**config)
        elif backend_type.lower() == "networkx_graph":
            return NetworkXGraphBackend(**config)
        elif backend_type.lower() == "s3_archive":
            return S3ArchiveBackend(**config)
        else:
            raise ValueError(f"Unknown backend type: {backend_type}")

    @staticmethod
    def get_available_backends() -> List[str]:
        """Get list of available backend types"""
        backends = ["memory"]

        # Check for optional dependencies
        try:
            import redis
            backends.extend(["redis", "redis_cache"])
        except ImportError:
            pass

        try:
            import psycopg2
            backends.append("postgres")
        except ImportError:
            pass

        try:
            import chromadb
            backends.append("chroma_vector")
        except ImportError:
            pass

        try:
            import networkx
            import duckdb
            backends.append("networkx_graph")
        except ImportError:
            pass

        try:
            import boto3
            import duckdb
            backends.append("s3_archive")
        except ImportError:
            pass

        return backends

class RedisCacheBackend(MemoryBackend):
    """Redis-based cache layer with TTL and eviction policies"""

    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0,
                 password: Optional[str] = None, key_prefix: str = "brain_cache:",
                 default_ttl: int = 3600, max_memory_policy: str = "allkeys-lru"):
        self.key_prefix = key_prefix
        self.default_ttl = default_ttl
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

            # Configure maxmemory policy for cache behavior
            self.redis_client.config_set('maxmemory-policy', max_memory_policy)

        except ImportError:
            raise ImportError("redis package not installed. Install with: pip install redis")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Redis cache: {e}")

    def _make_key(self, key: str) -> str:
        return f"{self.key_prefix}{key}"

    def store(self, key: str, data: Any, metadata: Optional[Dict[str, Any]] = None) -> bool:
        try:
            full_key = self._make_key(key)
            ttl = metadata.get('ttl', self.default_ttl) if metadata else self.default_ttl

            entry = {
                "data": data,
                "metadata": metadata or {},
                "timestamp": time.time(),
                "access_count": 0
            }

            self.redis_client.setex(full_key, ttl, json.dumps(entry))
            return True
        except Exception:
            return False

    def retrieve(self, key: str) -> Optional[Any]:
        try:
            full_key = self._make_key(key)
            data = self.redis_client.get(full_key)
            if data:
                entry = json.loads(data)
                # Update access count
                entry["access_count"] = entry.get("access_count", 0) + 1
                # Refresh TTL on access
                self.redis_client.expire(full_key, self.default_ttl)
                # Save updated entry
                self.redis_client.setex(full_key, self.default_ttl, json.dumps(entry))
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
        # Cache layer doesn't support complex search, just key-based lookup
        results = []
        try:
            for key in self.redis_client.scan_iter(f"{self.key_prefix}*"):
                data = self.redis_client.get(key)
                if data:
                    entry = json.loads(data)
                    if query.lower() in key.lower():
                        results.append(entry["data"])
        except Exception:
            pass
        return results

    def keys(self, pattern: str = "*") -> List[str]:
        try:
            full_pattern = f"{self.key_prefix}{pattern}"
            keys = list(self.redis_client.scan_iter(full_pattern))
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
                "backend": "redis_cache",
                "status": "healthy",
                "entries": key_count,
                "memory_usage": info.get("used_memory_human", "unknown"),
                "hit_rate": "N/A",  # Would need additional tracking
                "evictions": info.get("evicted_keys", 0)
            }
        except Exception as e:
            return {
                "backend": "redis_cache",
                "status": "unhealthy",
                "error": str(e)
            }

class ChromaVectorBackend(MemoryBackend):
    """ChromaDB-based vector store for semantic search"""

    def __init__(self, host: str = "localhost", port: int = 8000,
                 collection_name: str = "brain_vectors"):
        self.collection_name = collection_name
        self.chroma_client = None
        self.collection = None

        try:
            import chromadb
            from chromadb.config import Settings

            self.chroma_client = chromadb.HttpClient(
                host=host,
                port=port,
                settings=Settings(anonymized_telemetry=False)
            )

            # Get or create collection
            try:
                self.collection = self.chroma_client.get_collection(name=collection_name)
            except:
                self.collection = self.chroma_client.create_collection(name=collection_name)

        except ImportError:
            raise ImportError("chromadb package not installed. Install with: pip install chromadb")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to ChromaDB: {e}")

    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embeddings for text using the embedding adapter"""
        try:
            from ..cortex.adapters.embedding_adapter import embedding_adapter
            if embedding_adapter:
                embeddings = embedding_adapter.embed_texts([text])
                return embeddings[0] if embeddings else []
            else:
                # Fallback to simple hash-based embedding
                return self._fallback_embedding(text)
        except Exception as e:
            logger.log("WARNING", "ChromaVectorBackend", f"Embedding failed, using fallback: {e}")
            return self._fallback_embedding(text)

    def _fallback_embedding(self, text: str) -> List[float]:
        """Fallback hash-based embedding"""
        import hashlib
        hash_obj = hashlib.md5(text.encode())
        # Convert to 384-dimensional vector (common embedding size)
        hash_bytes = hash_obj.digest()
        embedding = []
        for i in range(0, len(hash_bytes), 4):
            chunk = hash_bytes[i:i+4].ljust(4, b'\x00')
            embedding.append(int.from_bytes(chunk, 'big') / 2**32)
        return embedding[:384]  # Truncate to 384 dimensions

    def store(self, key: str, data: Any, metadata: Optional[Dict[str, Any]] = None) -> bool:
        try:
            text_content = str(data)
            embedding = self._generate_embedding(text_content)

            # Prepare metadata
            doc_metadata = metadata.copy() if metadata else {}
            doc_metadata.update({
                "timestamp": time.time(),
                "original_key": key
            })

            self.collection.add(
                embeddings=[embedding],
                documents=[text_content],
                metadatas=[doc_metadata],
                ids=[key]
            )
            return True
        except Exception:
            return False

    def retrieve(self, key: str) -> Optional[Any]:
        try:
            results = self.collection.get(ids=[key])
            if results['documents']:
                return results['documents'][0]
            return None
        except Exception:
            return None

    def delete(self, key: str) -> bool:
        try:
            self.collection.delete(ids=[key])
            return True
        except Exception:
            return False

    def search(self, query: str, **kwargs) -> List[Any]:
        try:
            top_k = kwargs.get('top_k', 5)
            query_embedding = self._generate_embedding(query)

            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k
            )

            return results['documents'][0] if results['documents'] else []
        except Exception:
            return []

    def keys(self, pattern: str = "*") -> List[str]:
        try:
            results = self.collection.get()
            ids = results.get('ids', [])
            if pattern == "*":
                return ids
            return [id for id in ids if pattern in id]
        except Exception:
            return []

    def clear(self) -> bool:
        try:
            self.chroma_client.delete_collection(self.collection_name)
            self.collection = self.chroma_client.create_collection(name=self.collection_name)
            return True
        except Exception:
            return False

    def health_check(self) -> Dict[str, Any]:
        try:
            count = self.collection.count()
            return {
                "backend": "chroma_vector",
                "status": "healthy",
                "entries": count,
                "collection": self.collection_name
            }
        except Exception as e:
            return {
                "backend": "chroma_vector",
                "status": "unhealthy",
                "error": str(e)
            }

class NetworkXGraphBackend(MemoryBackend):
    """NetworkX graph backend with DuckDB persistence for relational knowledge"""

    def __init__(self, db_path: str = "brain_graph.db"):
        self.db_path = db_path
        self.graph = None
        self.conn = None

        try:
            import networkx as nx
            import duckdb

            self.graph = nx.MultiDiGraph()
            self.conn = duckdb.connect(db_path)

            # Create tables for persistence
            self._create_tables()

            # Load existing graph from database
            self._load_graph()

        except ImportError as e:
            raise ImportError(f"Required packages not installed: {e}. Install with: pip install networkx duckdb")
        except Exception as e:
            raise ConnectionError(f"Failed to initialize graph backend: {e}")

    def _create_tables(self):
        """Create DuckDB tables for graph persistence"""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS nodes (
                id TEXT PRIMARY KEY,
                data JSON,
                metadata JSON,
                timestamp DOUBLE
            )
        """)

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS edges (
                source TEXT,
                target TEXT,
                key TEXT,
                edge_type TEXT,
                data JSON,
                metadata JSON,
                timestamp DOUBLE,
                PRIMARY KEY (source, target, key)
            )
        """)

    def _load_graph(self):
        """Load graph from DuckDB"""
        # Load nodes
        nodes_df = self.conn.execute("SELECT * FROM nodes").fetchdf()
        for _, row in nodes_df.iterrows():
            self.graph.add_node(row['id'], **json.loads(row['data']))

        # Load edges
        edges_df = self.conn.execute("SELECT * FROM edges").fetchdf()
        for _, row in edges_df.iterrows():
            self.graph.add_edge(
                row['source'],
                row['target'],
                row['key'],
                edge_type=row['edge_type'],
                **json.loads(row['data'])
            )

    def _save_node(self, node_id: str, data: Dict[str, Any], metadata: Dict[str, Any]):
        """Save node to DuckDB"""
        self.conn.execute("""
            INSERT OR REPLACE INTO nodes (id, data, metadata, timestamp)
            VALUES (?, ?, ?, ?)
        """, (node_id, json.dumps(data), json.dumps(metadata), time.time()))

    def _save_edge(self, source: str, target: str, key: str, edge_type: str,
                   data: Dict[str, Any], metadata: Dict[str, Any]):
        """Save edge to DuckDB"""
        self.conn.execute("""
            INSERT OR REPLACE INTO edges (source, target, key, edge_type, data, metadata, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (source, target, key, edge_type, json.dumps(data), json.dumps(metadata), time.time()))

    def store(self, key: str, data: Any, metadata: Optional[Dict[str, Any]] = None) -> bool:
        try:
            # For graph backend, we expect data to be node or edge information
            data_dict = data if isinstance(data, dict) else {"content": str(data)}
            meta = metadata or {}

            if meta.get("type") == "node":
                self.graph.add_node(key, **data_dict)
                self._save_node(key, data_dict, meta)
            elif meta.get("type") == "edge":
                source = meta.get("source")
                target = meta.get("target")
                edge_type = meta.get("edge_type", "related")
                if source and target:
                    self.graph.add_edge(source, target, key, edge_type=edge_type, **data_dict)
                    self._save_edge(source, target, key, edge_type, data_dict, meta)

            return True
        except Exception:
            return False

    def retrieve(self, key: str) -> Optional[Any]:
        try:
            if key in self.graph.nodes:
                return dict(self.graph.nodes[key])
            # Check if it's an edge
            for source, target, edge_key, data in self.graph.edges(keys=True, data=True):
                if edge_key == key:
                    return {
                        "source": source,
                        "target": target,
                        "edge_type": data.get("edge_type", "related"),
                        **data
                    }
            return None
        except Exception:
            return None

    def delete(self, key: str) -> bool:
        try:
            if key in self.graph.nodes:
                self.graph.remove_node(key)
                self.conn.execute("DELETE FROM nodes WHERE id = ?", (key,))
                return True

            # Check edges
            edges_to_remove = []
            for source, target, edge_key in self.graph.edges(keys=True):
                if edge_key == key:
                    edges_to_remove.append((source, target, edge_key))

            for source, target, edge_key in edges_to_remove:
                self.graph.remove_edge(source, target, edge_key)
                self.conn.execute("DELETE FROM edges WHERE source = ? AND target = ? AND key = ?",
                                (source, target, edge_key))

            return len(edges_to_remove) > 0
        except Exception:
            return False

    def search(self, query: str, **kwargs) -> List[Any]:
        results = []
        try:
            # Search nodes
            for node_id, node_data in self.graph.nodes(data=True):
                content = str(node_data)
                if query.lower() in content.lower():
                    results.append({"type": "node", "id": node_id, **node_data})

            # Search edges
            for source, target, key, data in self.graph.edges(keys=True, data=True):
                content = str(data)
                if query.lower() in content.lower():
                    results.append({
                        "type": "edge",
                        "source": source,
                        "target": target,
                        "key": key,
                        **data
                    })

            return results
        except Exception:
            return []

    def keys(self, pattern: str = "*") -> List[str]:
        try:
            node_keys = list(self.graph.nodes())
            edge_keys = [key for _, _, key in self.graph.edges(keys=True)]

            all_keys = node_keys + edge_keys
            if pattern == "*":
                return all_keys
            return [k for k in all_keys if pattern in k]
        except Exception:
            return []

    def clear(self) -> bool:
        try:
            self.graph.clear()
            self.conn.execute("DELETE FROM nodes")
            self.conn.execute("DELETE FROM edges")
            return True
        except Exception:
            return False

    def health_check(self) -> Dict[str, Any]:
        try:
            node_count = self.graph.number_of_nodes()
            edge_count = self.graph.number_of_edges()
            return {
                "backend": "networkx_graph",
                "status": "healthy",
                "nodes": node_count,
                "edges": edge_count,
                "db_path": self.db_path
            }
        except Exception as e:
            return {
                "backend": "networkx_graph",
                "status": "unhealthy",
                "error": str(e)
            }

class S3ArchiveBackend(MemoryBackend):
    """S3-based archive backend with DuckDB for metadata indexing"""

    def __init__(self, bucket_name: str = "brain-archive", region: str = "us-east-1",
                 db_path: str = "brain_archive.db", aws_access_key: Optional[str] = None,
                 aws_secret_key: Optional[str] = None):
        self.bucket_name = bucket_name
        self.region = region
        self.db_path = db_path
        self.s3_client = None
        self.conn = None

        try:
            import boto3
            import duckdb

            # Initialize S3 client
            s3_kwargs = {"region_name": region}
            if aws_access_key and aws_secret_key:
                s3_kwargs.update({
                    "aws_access_key_id": aws_access_key,
                    "aws_secret_access_key": aws_secret_key
                })

            self.s3_client = boto3.client('s3', **s3_kwargs)

            # Test S3 connection
            self.s3_client.head_bucket(Bucket=bucket_name)

            # Initialize DuckDB for metadata
            self.conn = duckdb.connect(db_path)
            self._create_metadata_table()

        except ImportError as e:
            raise ImportError(f"Required packages not installed: {e}. Install with: pip install boto3 duckdb")
        except Exception as e:
            raise ConnectionError(f"Failed to initialize S3 archive backend: {e}")

    def _create_metadata_table(self):
        """Create metadata table in DuckDB"""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS archive_metadata (
                key TEXT PRIMARY KEY,
                s3_key TEXT,
                data_type TEXT,
                metadata JSON,
                timestamp DOUBLE,
                size_bytes INTEGER,
                checksum TEXT
            )
        """)

    def _generate_s3_key(self, key: str) -> str:
        """Generate S3 key with timestamp prefix for organization"""
        timestamp = datetime.now().strftime("%Y/%m/%d/%H/")
        return f"{timestamp}{key}"

    def store(self, key: str, data: Any, metadata: Optional[Dict[str, Any]] = None) -> bool:
        try:
            s3_key = self._generate_s3_key(key)
            data_str = json.dumps(data)
            data_bytes = data_str.encode('utf-8')

            # Calculate checksum
            checksum = hashlib.md5(data_bytes).hexdigest()

            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=data_bytes,
                ContentType='application/json',
                Metadata={'checksum': checksum}
            )

            # Store metadata in DuckDB
            meta = metadata or {}
            self.conn.execute("""
                INSERT OR REPLACE INTO archive_metadata
                (key, s3_key, data_type, metadata, timestamp, size_bytes, checksum)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                key,
                s3_key,
                meta.get('data_type', 'unknown'),
                json.dumps(meta),
                time.time(),
                len(data_bytes),
                checksum
            ))

            return True
        except Exception:
            return False

    def retrieve(self, key: str) -> Optional[Any]:
        try:
            # Get metadata first
            result = self.conn.execute(
                "SELECT s3_key FROM archive_metadata WHERE key = ?",
                (key,)
            ).fetchone()

            if not result:
                return None

            s3_key = result[0]

            # Retrieve from S3
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
            data_bytes = response['Body'].read()
            data_str = data_bytes.decode('utf-8')

            return json.loads(data_str)
        except Exception:
            return None

    def delete(self, key: str) -> bool:
        try:
            # Get S3 key from metadata
            result = self.conn.execute(
                "SELECT s3_key FROM archive_metadata WHERE key = ?",
                (key,)
            ).fetchone()

            if result:
                s3_key = result[0]
                # Delete from S3
                self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)

            # Delete metadata
            self.conn.execute("DELETE FROM archive_metadata WHERE key = ?", (key,))
            return True
        except Exception:
            return False

    def search(self, query: str, **kwargs) -> List[Any]:
        results = []
        try:
            # Search metadata in DuckDB
            search_results = self.conn.execute("""
                SELECT key, s3_key FROM archive_metadata
                WHERE key LIKE ? OR metadata LIKE ?
            """, (f"%{query}%", f"%{query}%")).fetchall()

            for key, s3_key in search_results:
                # Retrieve actual data
                data = self.retrieve(key)
                if data:
                    results.append(data)

            return results
        except Exception:
            return []

    def keys(self, pattern: str = "*") -> List[str]:
        try:
            if pattern == "*":
                results = self.conn.execute("SELECT key FROM archive_metadata").fetchall()
            else:
                results = self.conn.execute(
                    "SELECT key FROM archive_metadata WHERE key LIKE ?",
                    (pattern.replace("*", "%"),)
                ).fetchall()

            return [row[0] for row in results]
        except Exception:
            return []

    def clear(self) -> bool:
        try:
            # Get all S3 keys
            results = self.conn.execute("SELECT s3_key FROM archive_metadata").fetchall()

            # Delete from S3
            for (s3_key,) in results:
                self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)

            # Clear metadata
            self.conn.execute("DELETE FROM archive_metadata")
            return True
        except Exception:
            return False

    def health_check(self) -> Dict[str, Any]:
        try:
            # Check S3 bucket
            self.s3_client.head_bucket(Bucket=self.bucket_name)

            # Get metadata count
            count_result = self.conn.execute("SELECT COUNT(*) FROM archive_metadata").fetchone()
            count = count_result[0] if count_result else 0

            return {
                "backend": "s3_archive",
                "status": "healthy",
                "entries": count,
                "bucket": self.bucket_name,
                "region": self.region
            }
        except Exception as e:
            return {
                "backend": "s3_archive",
                "status": "unhealthy",
                "error": str(e)
            }