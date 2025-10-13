# 🧠 Cortex AI Prototype

[![Lint](https://github.com/jfbinTECHA/brain-swarm/actions/workflows/lint.yml/badge.svg)](https://github.com/jfbinTECHA/brain-swarm/actions/workflows/lint.yml)
[![Test](https://github.com/jfbinTECHA/brain-swarm/actions/workflows/test.yml/badge.svg)](https://github.com/jfbinTECHA/brain-swarm/actions/workflows/test.yml)
[![Build](https://github.com/jfbinTECHA/brain-swarm/actions/workflows/build.yml/badge.svg)](https://github.com/jfbinTECHA/brain-swarm/actions/workflows/build.yml)
[![Version](https://img.shields.io/github/v/tag/jfbinTECHA/brain-swarm)](https://github.com/jfbinTECHA/brain-swarm/releases)
[![v3 in Development](https://img.shields.io/badge/v3-in%20development-orange)](https://github.com/jfbinTECHA/brain-swarm/pull/123)

A lean, self-healing Docker-based AI prototype stack featuring FastAPI, Redis, DuckDB, Prometheus, and Grafana for monitoring and visualization.

**🚀 Quick Start**: `make up` | **📊 Dashboard**: http://localhost:3000 | **📖 Docs**: [/docs/](/docs/)

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Git

### Run Locally
```bash
git clone https://github.com/jfbinTECHA/brain-swarm.git
cd brain-swarm

# Configure environment (optional)
cp .env.example .env

# Start stack
make up

# Check status
make status
```

### Access Services
- **Grafana**: http://localhost:3000 (admin/admin)
- **API**: http://localhost:8001/docs
- **Prometheus**: http://localhost:9090
- **Stop**: `make down`

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
├── backend/                 # FastAPI application and core swarm logic
│   └── main.py
├── cortex/                  # Memory and vector modules (future)
├── helm/                    # Helm charts for Kubernetes deployment
├── infra/                   # Infrastructure: Docker, K8s, Prometheus, Grafana
│   ├── .cortex-control.kilo # Automation scripts
│   └── dashboards/          # Grafana configuration and dashboards
├── docs/                    # Design docs, ROADMAP, diagrams
├── tests/                   # Unit and integration tests
├── docker-compose.yml       # Local development stack
├── Makefile                 # Build and management scripts
├── README.md
└── .github/workflows/       # CI/CD pipelines
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

## Documentation

- **[Architecture](/docs/ARCHITECTURE.md)** - System design and data flow
- **[Roadmap](/docs/ROADMAP.md)** - Development milestones and features
- **[Demo Script](/docs/demo.sh)** - Interactive demo of the system
- **[Changelog](/CHANGELOG.md)** - Version history and changes
- **[API Docs](http://localhost:8001/docs)** - Interactive API documentation

## Development

### Available Commands
```bash
make help          # Show all commands
make up            # Start services
make down          # Stop services
make status        # Check health
make logs          # Follow logs
make test          # Run tests
make clean         # Rebuild everything
```

### Testing
```bash
# Run all tests
make test

# Run specific test
pytest tests/test_api.py
```

## Use Cases & Applications

- **[Maine Operations Brief](/docs/MAINE_OPS_BRIEF.md)** - Public health and forestry integration
- **[Deployment Scenario](/docs/DEPLOYMENT_SCENARIO.md)** - Sensor network and emergency response integration
- **[EBT LiveHeap System Design](/docs/EBT_LIVEHEAP_SYSTEM_DESIGN.md)** - Maine DHS EBT automation with Brain-Swarm agents
- **[EBT LiveHeap Agent Behavior Tree](/docs/EBT_LIVEHEAP_AGENT_BEHAVIOR_TREE.md)** - Agent hierarchy and roles for EBT processing

## 🧩 Use Case: Maine DHS EBT LiveHeap Pilot

**Summary:**
The EBT LiveHeap concept integrates Brain-Swarm’s multi-agent intelligence into the Maine DHS EBT program to automate eligibility checks, detect fraud, and streamline benefit renewals.

**Key Features:**
- Swarm-based AI decisioning for faster case handling
- Real-time LiveHeap memory synchronization
- Transparent dashboards for supervisors
- Secure integration with state systems

**Related Documentation:**
- [EBT LiveHeap System Design](docs/EBT_LIVEHEAP_SYSTEM_DESIGN.md)
- [EBT LiveHeap Agent Behavior Tree](docs/EBT_LIVEHEAP_AGENT_BEHAVIOR_TREE.md)

**Deployment Status:**
`In planning / sandbox prototype stage`

**Overview:**
The **EBT LiveHeap Pilot** demonstrates how the Brain-Swarm framework can modernize the Maine Department of Human Services (DHS) **Electronic Benefit Transfer (EBT)** system.
It introduces intelligent agent coordination, live memory streaming, and process automation — improving efficiency, transparency, and citizen experience.

**💡 Objectives**
- Automate eligibility checks with Analyst Agents
- Detect fraud and duplicate claims in real-time
- Optimize task routing for case workers through Planner Agents
- Maintain synchronized program state via LiveHeap memory
- Deliver transparent metrics to DHS dashboards

**🧩 Integration Summary**
- **Brain-Swarm Layer:** Supervisor, Planner, Analyst agents orchestrate decisions
- **LiveHeap Engine:** Provides real-time, in-memory state persistence and analytics
- **DHS API Gateway:** Serves as the secure interface between state systems and AI agents
- **GovNet Infrastructure:** Hosts all components under state-level compliance

**📄 Related Documentation**
- [EBT LiveHeap System Design](docs/EBT_LIVEHEAP_SYSTEM_DESIGN.md)
- [EBT LiveHeap Agent Behavior Tree](docs/EBT_LIVEHEAP_AGENT_BEHAVIOR_TREE.md)

**🚀 Deployment Phase**
> *Status:* Sandbox / Pilot Proposal
> *Goal:* Integrate prototype Brain-Swarm deployment with DHS test datasets to validate eligibility automation, fraud detection, and dashboard performance.

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make changes and add tests
4. Run `make test` to ensure everything works
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## License

MIT License - see LICENSE file for details.