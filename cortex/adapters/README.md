# Cortex Adapters

This directory contains adapter implementations for the Knowledge Cortex memory system.

## Available Adapters

### 🔍 Vector Adapters

#### ChromaDB + FAISS (`vector_chroma_faiss.py`)
- **Purpose**: Vector storage with semantic search capabilities
- **Features**:
  - ChromaDB for persistent vector storage
  - FAISS for local similarity search acceleration
  - Automatic embedding generation
  - Metadata filtering and search
- **Use Cases**: Document similarity, recommendation systems, semantic search

#### Embedding Adapter (`embedding_adapter.py`)
- **Purpose**: Multi-provider embedding generation
- **Supported Providers**:
  - **OpenAI**: `text-embedding-3-small/large` (1536/3072 dimensions)
  - **OpenRouter**: Access to various embedding models via OpenRouter API
  - **Local**: Sentence transformers (384 dimensions, offline)
  - **Fallback**: Hash-based embeddings (256 dimensions, always available)
- **Features**:
  - Automatic provider fallback
  - Configurable dimensions
  - Environment variable configuration
  - Health monitoring

### 🕸️ Graph Adapters

#### NetworkX + DuckDB (`graph_nx_duckdb.py`)
- **Purpose**: Graph-based relational knowledge storage
- **Features**:
  - NetworkX for in-memory graph operations
  - DuckDB for persistent graph storage
  - Node and edge relationships
  - Graph traversal algorithms
- **Use Cases**: Knowledge graphs, dependency mapping, relationship analysis

### 📦 Archive Adapters

#### S3 + DuckDB (`archive_s3_duckdb.py`)
- **Purpose**: Long-term cloud storage with metadata indexing
- **Features**:
  - S3 for scalable object storage
  - DuckDB for metadata indexing and search
  - Automatic data lifecycle management
  - Checksum validation
- **Use Cases**: Historical data, compliance archives, backup storage

### 🔄 Cache Adapters

#### Redis Cache (`cache_redis.py`)
- **Purpose**: High-performance caching layer
- **Features**:
  - TTL-based expiration
  - Access count tracking
  - LRU eviction policies
  - Connection pooling
- **Use Cases**: Session storage, frequently accessed data, API response caching

## Configuration

### Embedding Adapter Configuration

```python
from cortex.adapters.embedding_adapter import EmbeddingAdapter

config = {
    "providers": {
        "openai": {
            "enabled": True,
            "api_key": "your-openai-key",
            "model": "text-embedding-3-small",
            "dimension": 1536
        },
        "openrouter": {
            "enabled": True,
            "api_key": "your-openrouter-key",
            "model": "text-embedding-3-small",
            "dimension": 1536
        },
        "local": {
            "enabled": True,
            "model_name": "all-MiniLM-L6-v2",
            "dimension": 384
        },
        "fallback": {
            "enabled": True,
            "dimension": 256
        }
    },
    "default_provider": "local"
}

adapter = EmbeddingAdapter(config)
```

### Environment Variables

```bash
# OpenAI
OPENAI_API_KEY=sk-your-openai-key

# OpenRouter
OPENROUTER_API_KEY=sk-or-your-openrouter-key

# Embedding provider selection
EMBEDDING_PROVIDER=openai  # openai, openrouter, local, or fallback
```

## Usage Examples

### Basic Embedding Generation

```python
from cortex.adapters.embedding_adapter import embedding_adapter

# Embed single text
texts = ["This is a sample document for embedding"]
embeddings = embedding_adapter.embed_texts(texts)
print(f"Embedding dimension: {len(embeddings[0])}")

# Embed multiple texts
texts = ["Document 1", "Document 2", "Document 3"]
embeddings = embedding_adapter.embed_texts(texts)
print(f"Generated {len(embeddings)} embeddings")
```

### Vector Storage with ChromaDB

```python
from cortex.adapters.vector_chroma_faiss import VectorStore

# Initialize vector store
vector_store = VectorStore(
    host="localhost",
    port=8000,
    collection="my_documents",
    faiss_enable=True,
    faiss_index_path="/tmp/faiss_index.idx"
)

# Store documents with embeddings
documents = ["Document 1 content", "Document 2 content"]
embeddings = embedding_adapter.embed_texts(documents)
metadata = [{"source": "doc1"}, {"source": "doc2"}]

vector_store.add(
    ids=["doc1", "doc2"],
    embeddings=embeddings,
    metadatas=metadata,
    documents=documents
)

# Search similar documents
query_embedding = embedding_adapter.embed_texts(["Find similar content"])[0]
results = vector_store.query(
    query_embeddings=[query_embedding],
    n_results=5
)
```

### Graph Storage with NetworkX

```python
from cortex.adapters.graph_nx_duckdb import GraphStore

# Initialize graph store
graph_store = GraphStore(db_path="/data/knowledge_graph.db")

# Add nodes
graph_store.upsert_node("user_123", "User", metadata={"name": "Alice"})
graph_store.upsert_node("team_alpha", "Team", metadata={"name": "Alpha Team"})

# Add relationships
graph_store.add_edge(
    "user_123",
    "team_alpha",
    "member_of",
    metadata={"role": "developer", "since": "2023-01-01"}
)

# Query relationships
relationships = graph_store.neighbors("user_123")
print(f"User 123 is connected to: {relationships}")
```

### Archive Storage with S3

```python
from cortex.adapters.archive_s3_duckdb import ArchiveStore

# Initialize archive store
archive_store = ArchiveStore(
    duckdb_path="/data/archive.db",
    bucket="brain-swarm-archive",
    region="us-east-1",
    access_key="your-access-key",
    secret_key="your-secret-key"
)

# Archive data
data = {"incident": "server-down", "timestamp": 1234567890}
archive_store.write_jsonl("incident_001", data)

# List archived data
archived_items = archive_store.list()
print(f"Archived {len(archived_items)} items")
```

## Integration with Knowledge Cortex

The adapters are automatically integrated with the Knowledge Cortex:

```python
from memory.knowledge_cortex import knowledge_cortex

# Store data - automatically uses appropriate adapters
knowledge_cortex.store("doc_123", "Document content", {
    "vectorize": True,      # → Vector adapter
    "store_graph": True,    # → Graph adapter
    "data_type": "article"  # → Archive adapter
})

# Search across all layers
results = knowledge_cortex.search("machine learning", search_type="semantic")
```

## Performance Characteristics

| Adapter | Read Latency | Write Latency | Scalability | Persistence |
|---------|-------------|---------------|-------------|-------------|
| Vector (ChromaDB) | 10-100ms | 100-500ms | Medium | Persistent |
| Graph (NetworkX) | 1-50ms | 10-200ms | Medium | Persistent |
| Archive (S3) | 100-1000ms | 500-2000ms | High | Persistent |
| Cache (Redis) | < 1ms | < 1ms | High | TTL-based |

## Monitoring & Health Checks

All adapters include health check methods:

```python
# Check vector store health
health = vector_store.health_check()
print(f"Vector store status: {health['status']}")

# Check embedding adapter
providers = embedding_adapter.get_available_providers()
print(f"Available providers: {providers}")
```

## Development

### Adding New Adapters

1. Create new adapter class inheriting from base interfaces
2. Implement required methods (`store`, `retrieve`, `search`, etc.)
3. Add configuration support
4. Include health checks
5. Add comprehensive tests
6. Update documentation

### Testing

```bash
# Run adapter tests
pytest tests/test_cortex_adapters.py -v

# Test with different providers
pytest tests/test_embedding_adapter.py -k "openai or openrouter"
```

## Dependencies

### Required Packages

```bash
# Vector storage
pip install chromadb faiss-cpu

# Graph storage
pip install networkx duckdb

# Archive storage
pip install boto3 duckdb

# Cache storage
pip install redis

# Embedding providers
pip install openai requests sentence-transformers
```

### Optional Dependencies

- `faiss-cpu`: Local vector similarity acceleration
- `sentence-transformers`: Local embedding models
- `openai`: OpenAI API access
- `boto3`: AWS S3 integration

## Troubleshooting

### Common Issues

1. **ChromaDB Connection Failed**
   ```bash
   # Check ChromaDB service
   curl http://localhost:8000/api/v1/heartbeat
   ```

2. **S3 Access Denied**
   ```bash
   # Verify AWS credentials
   aws sts get-caller-identity
   ```

3. **Embedding Provider Failed**
   ```bash
   # Check API keys and network
   curl -H "Authorization: Bearer $OPENAI_API_KEY" https://api.openai.com/v1/models
   ```

4. **Redis Connection Error**
   ```bash
   # Check Redis service
   redis-cli ping
   ```

### Debug Mode

Enable detailed logging:

```python
import logging
logging.getLogger('cortex.adapters').setLevel(logging.DEBUG)