# 🧠 Brain-Swarm

<p align="center">
  <img src="https://img.shields.io/badge/Build-Stable%20✅-brightgreen?style=flat-square" alt="Build Status">
  <img src="https://img.shields.io/badge/Docs-Complete%20📘-blue?style=flat-square" alt="Documentation Status">
  <img src="https://img.shields.io/badge/License-MIT%20⚖️-lightgrey?style=flat-square" alt="License: MIT">
  <img src="https://img.shields.io/badge/AI_Framework-BrainSwarm%20🤖-orange?style=flat-square" alt="AI Framework">
  <img src="https://img.shields.io/badge/Use_Case-Maine_DHS_EBT_LiveHeap%20🧩-blueviolet?style=flat-square" alt="Use Case">
</p>

> **Brain-Swarm** orchestrates multi-agent intelligence using memory synchronization, adaptive planning, and human-in-the-loop governance — bringing self-organizing AI to secure, data-driven public systems.

---

[![Lint](https://github.com/jfbinTECHA/brain-swarm/actions/workflows/lint.yml/badge.svg)](https://github.com/jfbinTECHA/brain-swarm/actions/workflows/lint.yml)
[![Test](https://github.com/jfbinTECHA/brain-swarm/actions/workflows/test.yml/badge.svg)](https://github.com/jfbinTECHA/brain-swarm/actions/workflows/test.yml)
[![Build](https://github.com/jfbinTECHA/brain-swarm/actions/workflows/build.yml/badge.svg)](https://github.com/jfbinTECHA/brain-swarm/actions/workflows/build.yml)
[![Version](https://img.shields.io/github/v/tag/jfbinTECHA/brain-swarm)](https://github.com/jfbinTECHA/brain-swarm/releases)
[![v3 in Development](https://img.shields.io/badge/v3-in%20development-orange)](https://github.com/jfbinTECHA/brain-swarm/pull/123)

A lean, self-healing Docker-based AI prototype stack featuring FastAPI, Redis, DuckDB, Prometheus, and Grafana for monitoring and visualization.

## 🧩 Repository Overview

```mermaid
graph TD
    A[📁 brain-swarm Repository] --> B[🤖 Core AI Engine]
    A --> C[📘 Documentation / Docs Folder]
    A --> D[🧪 Use Cases]
    A --> E[⚙️ Deployment Layer]

    subgraph CORE["🤖 Brain-Swarm Core"]
        B1[Supervisor Agent<br>(Task Control, Routing)]
        B2[Planner Agent<br>(Workflow Optimization)]
        B3[Analyst Agents<br>(Eligibility, Risk, Compliance)]
        B4[LiveHeap Engine<br>(State Memory, Caching)]
    end

    subgraph DOCS["📘 Docs"]
        C1[EBT_LIVEHEAP_SYSTEM_DESIGN.md]
        C2[EBT_LIVEHEAP_AGENT_BEHAVIOR_TREE.md]
        C3[README.md Overview + Use Cases]
    end

    subgraph USECASES["🧪 Use Cases"]
        D1[EBT LiveHeap Pilot<br>(Maine DHS Integration)]
        D2[Future Federated AI Use Cases<br>(Modular Expansion)]
    end

    subgraph DEPLOY["⚙️ Deployment"]
        E1[Local Sandbox / Docker Compose]
        E2[API Gateway Integration]
        E3[Dashboard + Monitor Layer]
    end

    %% Connections
    B1 --> B4
    B2 --> B4
    B3 --> B4
    B4 --> C1
    B4 --> C2
    C1 --> D1
    C2 --> D1
    D1 --> E1
    D1 --> E2
    D1 --> E3
```

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

<p align="center">
  <a href="docs/EBT_LIVEHEAP_SYSTEM_DESIGN.md">
    <img src="https://img.shields.io/badge/View%20Docs-📘%20System%20Design-blue?style=for-the-badge" alt="View Docs">
  </a>
  <a href="docs/EBT_LIVEHEAP_AGENT_BEHAVIOR_TREE.md">
    <img src="https://img.shields.io/badge/Agent%20Flow-🧠%20Behavior%20Tree-blueviolet?style=for-the-badge" alt="Agent Behavior Tree">
  </a>
  <a href="#-use-case-maine-dhs--ebt-liveheap-pilot">
    <img src="https://img.shields.io/badge/Use%20Case-EBT%20LiveHeap%20🧩-orange?style=for-the-badge" alt="Use Case Section">
  </a>
  <a href="LICENSE">
    <img src="https://img.shields.io/badge/License-MIT%20⚖️-lightgrey?style=for-the-badge" alt="License">
  </a>
</p>

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