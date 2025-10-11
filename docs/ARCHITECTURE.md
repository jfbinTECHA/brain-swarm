# Brain-Swarm Architecture

Brain-Swarm is a distributed agent orchestration platform that combines knowledge processing, real-time messaging, and observability into a cohesive system for building intelligent multi-agent applications.

## System Overview

```mermaid
graph TB
    A[FastAPI Backend] --> B[Agent Registry]
    A --> C[Task Dispatcher]
    A --> D[Supervisor Orchestrator]

    B --> E[Redis Cache]
    C --> E
    D --> E

    F[Cortex Knowledge Engine] --> G[Vector Store]
    F --> H[Graph Store]
    F --> I[Archive Store]
    F --> J[Embedding Adapter]

    K[Message Queue] --> L[Redis Streams]
    K --> M[Consumer Groups]

    N[Event Summarizer] --> K
    N --> F

    O[Prometheus Metrics] --> P[Grafana Dashboards]
    O --> Q[Alerting Rules]

    R[VSCode Tasks] --> S[CI/CD Pipeline]
    S --> T[GitHub Actions]
```

## Core Components

### 1. FastAPI Backend (`backend/main.py`)

The central API server that exposes endpoints for:
- **Agent Management**: Registration, status monitoring, capability discovery
- **Task Dispatch**: Queue-based task distribution to available agents
- **Supervisor Orchestration**: Multi-agent workflow coordination
- **Metrics Exposure**: Prometheus-compatible `/metrics` endpoint

### 2. Agent Registry

In-memory registry of active agents with:
- Agent capabilities and metadata
- Health status and last heartbeat
- Task assignment tracking

### 3. Task Dispatcher (`/agent/dispatch`)

Implements a simple round-robin task distribution:
- Accepts task requests with agent type requirements
- Matches tasks to available agents
- Tracks task lifecycle (queued → dispatched → completed/failed)

### 4. Supervisor Orchestrator (`/supervisor/orchestrate`)

Coordinates complex multi-agent workflows:
- Accepts workflow definitions with task dependencies
- Dispatches tasks in sequence or parallel
- Aggregates results and handles failures

### 5. Cortex Knowledge Engine (`cortex/`)

Multi-layered knowledge processing system:

#### Vector Layer (`cortex/adapters/vector_chroma_faiss.py`)
- ChromaDB for vector storage
- FAISS for efficient similarity search
- Configurable embedding dimensions

#### Graph Layer (`cortex/adapters/graph_nx_duckdb.py`)
- NetworkX for in-memory graph operations
- DuckDB for persistent graph storage
- Temporal relationship modeling

#### Archive Layer (`cortex/adapters/archive_s3_duckdb.py`)
- S3-compatible object storage
- DuckDB for metadata indexing
- Long-term knowledge retention

#### Embedding Adapter (`cortex/adapters/embedding_adapter.py`)
- Pluggable embedding providers
- Fallback to SHA256 for development
- Batch processing capabilities

### 6. Message Queue (`message_queue.py`)

Redis Streams-based messaging system:
- Persistent message storage
- Consumer groups for load balancing
- Broadcast and point-to-point messaging
- Message replay capabilities

### 7. Event Summarizer (`cortex/summarizer_job.py`)

Automated event compaction and summarization:
- Collects events from Redis streams
- Groups by topic and time windows
- Generates embeddings for summaries
- Stores in Cortex for retrieval

### 8. Observability Stack

#### Prometheus Metrics (`prometheus_fastapi_instrumentator`)
- HTTP request metrics
- Custom business metrics
- Agent performance tracking
- System health indicators

#### Grafana Dashboards (`infra/dashboards/`)
- Agent activity monitoring
- System performance metrics
- Task completion rates
- Error tracking and alerting

### 9. CI/CD Pipeline (`.github/workflows/`)

Automated quality assurance:
- **CI** (`ci.yml`): Linting, testing, security scanning
- **Docs** (`docs.yml`): Automated documentation deployment
- **Release** (`release.yml`): Changelog generation and tagging

### 10. VSCode Tasks (`.vscode/tasks.json`)

Developer control panel with:
- Repository maintenance tasks
- Build and test automation
- Deployment workflows
- Monitoring and verification

## Data Flow

```mermaid
sequenceDiagram
    participant U as User
    participant A as API
    participant R as Agent Registry
    participant T as Task Dispatcher
    participant M as Message Queue
    participant Ag as Agent
    participant C as Cortex
    participant S as Summarizer

    U->>A: Register Agent
    A->>R: Store agent info

    U->>A: Dispatch Task
    A->>T: Find available agent
    T->>M: Queue task message
    M->>Ag: Deliver task
    Ag->>M: Send completion
    M->>S: Event for summarization
    S->>C: Store summary with embedding
```

## Deployment Architecture

```mermaid
graph TB
    subgraph "Docker Compose Stack"
        API[FastAPI Backend]
        RQ[Redis Queue]
        RC[Redis Cache]
        CH[ChromaDB]
        DD[DuckDB]
        GR[Grafana]
        PR[Prometheus]
    end

    subgraph "External Services"
        S3[(S3 Storage)]
        GH[GitHub Actions]
    end

    API --> RQ
    API --> RC
    API --> CH
    API --> DD
    API --> GR
    API --> PR

    DD --> S3
    GH --> API
```

## Security Considerations

- **API Authentication**: JWT-based agent authentication
- **Message Encryption**: TLS for Redis connections
- **Access Control**: Capability-based agent permissions
- **Audit Logging**: Comprehensive event logging in Cortex
- **SBOM Generation**: Automated dependency vulnerability scanning

## Scalability Features

- **Horizontal Agent Scaling**: Add agents without system changes
- **Partitioned Message Queues**: Redis cluster support
- **Federated Deployments**: Multi-region swarm coordination
- **Async Processing**: Non-blocking task execution
- **Resource Pooling**: Shared knowledge stores across agents

## Development Workflow

See [Developer Guide](DEVELOPER_GUIDE.md) for detailed setup and usage instructions.

## Roadmap

See [Roadmap](ROADMAP.md) for upcoming features and milestones.

---

*This architecture supports both simple agent coordination and complex multi-agent workflows with full observability and automated maintenance.*
