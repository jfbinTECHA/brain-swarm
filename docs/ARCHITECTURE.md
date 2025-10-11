# Cortex AI Architecture

## System Overview

Cortex AI is a lean, self-healing Docker-based AI prototype stack designed for rapid development and deployment of AI-powered applications.

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI       │    │   Redis         │    │   DuckDB        │
│   Backend       │◄──►│   Cache &       │    │   Analytics     │
│                 │    │   Sessions      │    │   Database      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                        │                        │
         └────────────────────────┼────────────────────────┘
                                  │
                    ┌─────────────────┐
                    │   Prometheus    │
                    │   Metrics       │
                    └─────────────────┘
                           │
                    ┌─────────────────┐
                    │   Grafana       │
                    │   Dashboards    │
                    └─────────────────┘
```

## Components

### FastAPI Backend
- **Purpose**: REST API server with automatic OpenAPI documentation
- **Features**:
  - Health check endpoints (`/ping`)
  - Prometheus metrics integration (`/metrics`)
  - CORS enabled for web clients
  - Async request handling
- **Technology**: FastAPI, Uvicorn, Prometheus FastAPI Instrumentator

### Redis
- **Purpose**: High-performance in-memory data store
- **Use Cases**:
  - Session storage
  - Cache for frequent queries
  - Message queue (future)
  - Rate limiting (future)
- **Configuration**: Standalone mode, persistent storage

### DuckDB
- **Purpose**: Embedded analytical database
- **Features**:
  - SQL interface for complex queries
  - Fast analytical workloads
  - Embedded (no separate server)
  - ACID transactions
- **Data Path**: `/data/cortex.duckdb`

### Prometheus
- **Purpose**: Metrics collection and monitoring
- **Targets**:
  - FastAPI application metrics
  - Docker container metrics
  - Custom business metrics (future)
- **Configuration**: Scrapes API every 15s

### Grafana
- **Purpose**: Visualization and dashboards
- **Features**:
  - Pre-configured datasources (Prometheus, Redis)
  - Auto-provisioned dashboards
  - User management
  - Alerting (future)
- **Access**: http://localhost:3000 (admin/admin)

## Data Flow

1. **Client Request** → FastAPI endpoint
2. **Business Logic** → Query Redis/DuckDB as needed
3. **Metrics Collection** → Prometheus scrapes FastAPI
4. **Visualization** → Grafana queries Prometheus
5. **Monitoring** → Dashboards display real-time metrics

## Future Architecture: Agent System

```
┌─────────────────┐    ┌─────────────────┐
│   User Query    │───►│   Agent         │
│                 │    │   Dispatcher    │
└─────────────────┘    └─────────────────┘
         ▲                       │
         │                       ▼
┌─────────────────┐    ┌─────────────────┐
│   Response      │◄───│   Agent         │
│   Stream        │    │   Executor      │
└─────────────────┘    └─────────────────┘
         ▲                       │
         │                       ▼
┌─────────────────┐    ┌─────────────────┐
│   Memory        │◄──►│   Vector DB     │
│   Manager       │    │   (Embeddings)  │
└─────────────────┘    └─────────────────┘
```

### Agent Flow
1. **Query Reception**: User sends natural language query
2. **Intent Analysis**: Agent dispatcher analyzes query intent
3. **Context Retrieval**: Memory manager fetches relevant context
4. **Tool Selection**: Choose appropriate tools/agents
5. **Execution**: Run agent with tools and context
6. **Response Generation**: Format and stream response
7. **Memory Update**: Store conversation for future reference

## Deployment Options

### Local Development
- Docker Compose for all-in-one development
- Hot reload for backend changes
- Local data persistence

### Production (Future)
- Kubernetes with Helm charts
- Horizontal Pod Autoscaling
- Persistent volumes for data
- Ingress controllers for external access
- Service mesh (Istio/Linkerd)

## Security Considerations

- Environment variables for secrets
- Network isolation between services
- API authentication (future)
- Rate limiting (future)
- Audit logging (future)

## Monitoring & Observability

- **Application Metrics**: Request latency, error rates, throughput
- **System Metrics**: CPU, memory, disk usage
- **Business Metrics**: User interactions, agent performance
- **Logging**: Structured logs with correlation IDs
- **Alerting**: Automated alerts for critical issues