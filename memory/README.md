# Knowledge Cortex Memory System

The Brain Swarm Knowledge Cortex implements a sophisticated 4-layer hierarchical memory architecture designed for enterprise-grade AI applications.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Knowledge Cortex                          │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  Cache Layer (Redis) - Fast Access & TTL Management     │ │
│  └─────────────────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  Vector Layer (ChromaDB + FAISS) - Semantic Search      │ │
│  └─────────────────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  Graph Layer (NetworkX + DuckDB) - Relational Knowledge │ │
│  └─────────────────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  Archive Layer (S3 + DuckDB) - Long-term Storage        │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Layer Descriptions

### 1. Cache Layer (Redis)
**Purpose**: Ultra-fast temporary storage with TTL management
- **Backend**: `RedisCacheBackend`
- **Features**: Automatic TTL refresh on access, LRU eviction, access counting
- **Use Cases**: Session data, frequently accessed results, API responses

### 2. Vector Layer (ChromaDB + FAISS)
**Purpose**: Semantic search and similarity matching
- **Backend**: `ChromaVectorBackend` + `VectorStore`
- **Features**: Embedding generation, vector similarity search, FAISS local caching
- **Use Cases**: Document similarity, recommendation systems, semantic search

### 3. Graph Layer (NetworkX + DuckDB)
**Purpose**: Relational knowledge representation and traversal
- **Backend**: `NetworkXGraphBackend` + `GraphStore`
- **Features**: Node/edge relationships, graph algorithms, persistent storage
- **Use Cases**: Knowledge graphs, dependency mapping, relationship analysis

### 4. Archive Layer (S3 + DuckDB)
**Purpose**: Long-term persistent storage with metadata indexing
- **Backend**: `S3ArchiveBackend` + `ArchiveStore`
- **Features**: Cloud storage, metadata indexing, data lifecycle management
- **Use Cases**: Historical data, compliance archives, backup storage

## Quick Start

### Basic Usage

```python
from memory.knowledge_cortex import knowledge_cortex

# Store data with automatic layer selection
knowledge_cortex.store("user_123", {
    "name": "John Doe",
    "preferences": ["ai_assistance", "real_time_updates"]
}, {
    "vectorize": True,  # Store in vector layer for semantic search
    "type": "user_profile"
})

# Retrieve with hierarchical lookup
user_data = knowledge_cortex.retrieve("user_123")

# Multi-layer search
results = knowledge_cortex.search("user preferences", search_type="semantic")
```

### Advanced Configuration

```python
from memory.knowledge_cortex import KnowledgeCortex

# Custom configuration
config = {
    "cache": {
        "host": "redis-cluster",
        "port": 6379,
        "default_ttl": 7200  # 2 hours
    },
    "vector": {
        "host": "chroma-service",
        "port": 8000,
        "collection_name": "enterprise_knowledge"
    },
    "graph": {
        "db_path": "/data/graph.db"
    },
    "archive": {
        "bucket_name": "enterprise-archive",
        "region": "us-east-1"
    }
}

cortex = KnowledgeCortex(config)
```

## API Reference

### KnowledgeCortex Class

#### Methods

- `store(key, data, metadata=None)` - Store data across appropriate layers
- `retrieve(key, search_fallback=True)` - Retrieve with hierarchical lookup
- `search(query, **kwargs)` - Multi-layer search
- `add_relationship(source, target, relation_type, metadata=None)` - Add graph relationships
- `get_relationships(entity, relation_type=None)` - Query graph relationships
- `archive_old_data(age_threshold_days=30)` - Move old data to archive
- `get_health_status()` - Check all layer health
- `optimize()` - Optimize all layers

#### Storage Strategy

Data is automatically distributed based on content and metadata:

```python
# All data goes to cache
metadata = {
    "vectorize": True,      # → Vector layer for semantic search
    "store_graph": True,    # → Graph layer for relationships
    "data_type": "user"     # → Helps with layer selection
}

knowledge_cortex.store("key", data, metadata)
```

## Backend Implementations

### Available Backends

| Backend | Purpose | Dependencies |
|---------|---------|--------------|
| `RedisCacheBackend` | Fast caching | redis |
| `ChromaVectorBackend` | Vector search | chromadb |
| `NetworkXGraphBackend` | Graph storage | networkx, duckdb |
| `S3ArchiveBackend` | Cloud archive | boto3, duckdb |
| `InMemoryBackend` | Development | None |
| `PostgresBackend` | Relational DB | psycopg2 |

### Custom Backends

```python
from memory.backends import MemoryBackend

class CustomBackend(MemoryBackend):
    def store(self, key: str, data: Any, metadata=None) -> bool:
        # Implement custom storage logic
        pass

    def retrieve(self, key: str) -> Optional[Any]:
        # Implement custom retrieval logic
        pass

    # Implement other required methods...
```

## Configuration

### Environment Variables

```bash
# Redis Cache
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# ChromaDB Vector
CHROMA_HOST=localhost
CHROMA_PORT=8000
CHROMA_COLLECTION=brain_vectors

# Graph Database
GRAPH_DB_PATH=/data/brain_graph.db

# S3 Archive
S3_BUCKET=brain-archive
S3_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
```

### Docker Compose

```yaml
version: '3.8'
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  chroma:
    image: chromadb/chroma:0.4.18
    ports:
      - "8000:8000"
    volumes:
      - chroma_data:/chroma/chroma

  brain-swarm:
    image: brain-swarm:latest
    environment:
      - REDIS_HOST=redis
      - CHROMA_HOST=chroma
    depends_on:
      - redis
      - chroma
```

## Performance Characteristics

### Layer Performance

| Layer | Read Latency | Write Latency | Scalability | Persistence |
|-------|-------------|---------------|-------------|-------------|
| Cache | < 1ms | < 1ms | High | TTL-based |
| Vector | 10-100ms | 100-500ms | Medium | Persistent |
| Graph | 1-50ms | 10-200ms | Medium | Persistent |
| Archive | 100-1000ms | 500-2000ms | High | Persistent |

### Optimization Strategies

1. **Caching Strategy**: Frequently accessed data stays in cache
2. **Vector Indexing**: FAISS provides fast similarity search
3. **Graph Partitioning**: Large graphs can be partitioned
4. **Archive Lifecycle**: Automatic data movement based on access patterns

## Monitoring & Observability

### Health Checks

```python
# Check all layers
status = knowledge_cortex.get_health_status()
print(f"Overall status: {status['overall_status']}")

for layer, info in status['layers'].items():
    print(f"{layer}: {info['status']}")
```

### Metrics

The system tracks:
- Cache hit/miss ratios
- Vector search performance
- Graph query statistics
- Archive access patterns
- Layer health status

### Logging

All operations are logged with correlation IDs for tracing:

```
INFO KnowledgeCortex Stored in cache: user_123
INFO KnowledgeCortex Vector retrieval for: user_123
DEBUG KnowledgeCortex Cache hit for: user_123
```

## Use Cases

### Enterprise Knowledge Management

```python
# Store user profiles with semantic search
knowledge_cortex.store("user_123", user_profile, {"vectorize": True})

# Store organizational relationships
knowledge_cortex.add_relationship("user_123", "team_alpha", "member_of")
knowledge_cortex.add_relationship("team_alpha", "dept_engineering", "part_of")

# Semantic search across knowledge base
results = knowledge_cortex.search("experienced Python developers")
```

### Incident Response System

```python
# Store incident data with relationships
knowledge_cortex.store("incident_456", incident_data, {
    "vectorize": True,
    "store_graph": True,
    "type": "incident"
})

# Link related incidents
knowledge_cortex.add_relationship("incident_456", "server_web01", "affects")
knowledge_cortex.add_relationship("incident_456", "user_john", "reported_by")

# Find similar incidents
similar = knowledge_cortex.search("database connection timeout", search_type="semantic")
```

### Learning & Adaptation

```python
# Store AI model performance data
knowledge_cortex.store("model_v2_metrics", performance_data, {
    "vectorize": True,
    "data_type": "metrics"
})

# Archive old data automatically
knowledge_cortex.archive_old_data(age_threshold_days=90)

# Retrieve historical performance for comparison
historical = knowledge_cortex.search("model performance 2023", search_type="historical")
```

## Troubleshooting

### Common Issues

1. **Layer Initialization Failures**
   ```python
   # Check layer status
   status = knowledge_cortex.get_health_status()
   print(status['layers'])
   ```

2. **Slow Queries**
   ```python
   # Check access statistics
   print(knowledge_cortex.access_stats)
   ```

3. **Memory Issues**
   ```python
   # Run optimization
   knowledge_cortex.optimize()
   ```

### Debug Mode

Enable detailed logging:

```python
import logging
logging.getLogger('memory.knowledge_cortex').setLevel(logging.DEBUG)
```

## Contributing

When adding new backends:

1. Extend `MemoryBackend` abstract class
2. Implement all required methods
3. Add to `MemoryBackendFactory`
4. Update documentation
5. Add tests

## License

This memory system is part of the Brain Swarm project.