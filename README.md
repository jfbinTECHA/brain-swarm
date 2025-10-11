# Cortex AI Prototype

A lean, self-healing Docker-based AI prototype stack featuring FastAPI, Redis, DuckDB, Prometheus, and Grafana for monitoring and visualization.

## Architecture

- **FastAPI Backend**: REST API with Prometheus metrics instrumentation
- **Redis**: In-memory data store for caching and session management
- **DuckDB**: Embedded analytical database for data processing
- **Prometheus**: Metrics collection and monitoring
- **Grafana**: Dashboard visualization with pre-configured datasources

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Git

### Run the Stack

```bash
# Clone the repository
git clone https://github.com/jfbinTECHA/ai-prototype-laptop-.git
cd ai-prototype-laptop-

# Start all services
docker compose up -d

# Check status
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

### Access Services
- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090
- **API**: http://localhost:8001/ping
- **Redis**: localhost:6379

### Stop the Stack
```bash
docker compose down
```

## Development

### Local API Development
```bash
cd backend
pip install fastapi uvicorn prometheus-fastapi-instrumentator
uvicorn main:app --reload
```

### Monitoring
- Metrics available at `/metrics` on the API
- Grafana dashboards auto-provisioned
- Prometheus scrapes API metrics

## Project Structure

```
.
├── backend/                 # FastAPI application
│   └── main.py
├── dashboards/              # Grafana configuration and dashboards
│   ├── provisioning/
│   │   ├── datasources/     # Datasource configurations
│   │   └── dashboards/      # Dashboard configurations
│   └── *.json               # Dashboard JSON files
├── data/                    # Persistent data (gitignored)
│   ├── redis/
│   └── duckdb/
├── docker-compose.yml       # Service definitions
├── .cortex-control.kilo     # Automation scripts
└── README.md
```

## Current Status

### ✅ Implemented
- Docker Compose stack with all services
- Basic FastAPI ping endpoint
- Grafana provisioning with Prometheus and Redis datasources
- Prometheus metrics collection
- Kilo automation scripts for stack management

### 🚧 Work in Progress
- Agent dispatch system
- Memory summarization
- Advanced dashboard visualizations
- Cortex AI core logic

### 📋 Next Steps / Roadmap
1. Implement agent dispatch and orchestration
2. Add memory management and summarization
3. Build comprehensive dashboards
4. Add case studies and examples
5. Implement CI/CD pipelines
6. Add Helm charts for Kubernetes deployment

## Automation

Use the included Kilo scripts for stack management:

```bash
# Available tasks in VSCode Command Palette (Kilo: Refresh Tasks)
- Start Cortex Stack
- Check Cortex Status
- Fix Grafana Permissions
- Restart API
- Rebuild Everything (Clean)
- Follow Logs
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes
4. Test with `docker compose up`
5. Submit a pull request

## License

MIT License - see LICENSE file for details.