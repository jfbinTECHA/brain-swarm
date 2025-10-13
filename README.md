# Brain-Swarm: AI Coordination Framework for EBT LiveHeap

<p align="center">
  <img src="https://img.shields.io/badge/Build-Stable-brightgreen?style=flat-square" alt="Build Status">
  <img src="https://img.shields.io/badge/Docs-Complete-blue?style=flat-square" alt="Documentation Status">
  <img src="https://img.shields.io/badge/License-MIT-lightgrey?style=flat-square" alt="License: MIT">
  <img src="https://img.shields.io/badge/AI_Framework-BrainSwarm-orange?style=flat-square" alt="AI Framework">
  <img src="https://img.shields.io/badge/Use_Case-Maine_DHS_EBT_LiveHeap-blueviolet?style=flat-square" alt="Use Case">
</p>

> **Brain-Swarm** orchestrates multi-agent intelligence using memory synchronization, adaptive planning, and human-in-the-loop governance — bringing self-organizing AI to secure, data-driven public systems.

<p align="center">
  <a href="docs/EBT_LIVEHEAP_SYSTEM_DESIGN.md">
    <img src="https://img.shields.io/badge/View%20Docs-System%20Design-blue?style=for-the-badge" alt="View Docs">
  </a>
  <a href="docs/EBT_LIVEHEAP_AGENT_BEHAVIOR_TREE.md">
    <img src="https://img.shields.io/badge/Agent%20Flow-Behavior%20Tree-blueviolet?style=for-the-badge" alt="Agent Behavior Tree">
  </a>
  <a href="#use-case-maine-dhs--ebt-liveheap-pilot">
    <img src="https://img.shields.io/badge/Use%20Case-EBT%20LiveHeap-orange?style=for-the-badge" alt="Use Case Section">
  </a>
  <a href="LICENSE">
    <img src="https://img.shields.io/badge/License-MIT-lightgrey?style=for-the-badge" alt="License">
  </a>
</p>

---

## Repository Overview

```mermaid
graph TD
    A[brain-swarm Repository] --> B[Core AI Engine]
    A --> C[Documentation / Docs Folder]
    A --> D[Use Cases]
    A --> E[Deployment Layer]

    subgraph CORE["Brain-Swarm Core"]
        B1[Supervisor Agent\n(Task Control, Routing)]
        B2[Planner Agent\n(Workflow Optimization)]
        B3[Analyst Agents\n(Eligibility, Risk, Compliance)]
        B4[LiveHeap Engine\n(State Memory, Caching)]
    end

    subgraph DOCS["Docs"]
        C1[EBT_LIVEHEAP_SYSTEM_DESIGN.md]
        C2[EBT_LIVEHEAP_AGENT_BEHAVIOR_TREE.md]
        C3[README.md Overview + Use Cases]
    end

    subgraph USECASES["Use Cases"]
        D1[EBT LiveHeap Pilot\n(Maine DHS Integration)]
        D2[Future Federated AI Use Cases\n(Modular Expansion)]
    end

    subgraph DEPLOY["Deployment"]
        E1[Local Sandbox / Docker Compose]
        E2[API Gateway Integration]
        E3[Dashboard + Monitor Layer]
    end

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

---

## Deployment Workflow

```mermaid
flowchart TD
    A[Developer / IT Admin] --> B[Clone brain-swarm Repository]
    B --> C[Configure Environment\n(Docker Compose / .env)]
    C --> D[Launch Local Sandbox\n(Brain-Swarm Core + LiveHeap Engine)]
    D --> E[Deploy Agents\n(Supervisor / Planner / Analyst)]
    E --> F[Connect to DHS API Gateway\n(GovNet Sandbox)]
    F --> G[Activate Monitoring Dashboard\n(LiveHeap Metrics & Logs)]
    G --> H{Tests Pass?}
    H -->|Yes| I[Deploy to Pilot Environment\n(Maine DHS EBT Sandbox)]
    H -->|No| J[Review Logs & Re-train Models]
    I --> K[Real-Time Agent Coordination Live]
    K --> L[DHS Supervisors Access Dashboard]
    L --> M[Automated Reports & Citizen Notifications]
```

---

<p align="center">
  <img src="https://img.shields.io/badge/Architecture-Core%20Design-blue?style=for-the-badge" alt="Architecture">
  <img src="https://img.shields.io/badge/Agents-BrainSwarm%20Intelligence-orange?style=for-the-badge" alt="Agents">
  <img src="https://img.shields.io/badge/Deployment-Automated%20Pipeline-brightgreen?style=for-the-badge" alt="Deployment">
  <img src="https://img.shields.io/badge/System%20Flow-End%20to%20End%20Integration-blueviolet?style=for-the-badge" alt="System Flow">
  <img src="https://img.shields.io/badge/Docs-LiveHeap%20and%20EBT%20Design-lightgrey?style=for-the-badge" alt="Docs">
</p>

---

## Full-Stack System Flow

```mermaid
graph LR
    A[Citizen Portal\n(Web/Mobile Access)] --> B[DHS API Gateway]
    B --> C[Brain-Swarm Supervisor Agent]
    C --> D1[Planner Agent\n(Workflow Orchestration)]
    C --> D2[Analyst Cluster\n(Eligibility, Fraud, Compliance)]
    D1 --> E1[LiveHeap Engine\n(In-Memory State)]
    D2 --> E1
    E1 --> F[DHS Data Lake\n(Historical + Financial)]
    F --> G[Monitoring Dashboard\n(Program KPIs, Agent Logs)]
    G --> H[DHS Supervisors\n(Oversight & Auditing)]
    H --> I[Feedback Loop\n(Policy Adjustments, Training)]
    I --> C
    E1 -->|Case Status Updates| A
```

### Flow Summary
1. Citizens interact through the portal to manage benefits.
2. The API Gateway validates input and routes to Brain-Swarm.
3. Agents analyze eligibility, detect fraud, and plan actions.
4. LiveHeap maintains synchronized state across all workflows.
5. The DHS Data Lake stores transaction and history data.
6. Dashboards display live KPIs for administrators.
7. Supervisors feed data back to improve policies and AI models.

---

## Use Case: Maine DHS — EBT LiveHeap Pilot

<p align="center">
  <img src="https://img.shields.io/badge/Status-Prototype-blueviolet?style=for-the-badge" alt="Status: Prototype">
  <img src="https://img.shields.io/badge/Docs-Available-brightgreen?style=for-the-badge" alt="Docs Available">
  <img src="https://img.shields.io/badge/License-MIT-lightgrey?style=for-the-badge" alt="License">
  <img src="https://img.shields.io/badge/AI%20Framework-BrainSwarm-orange?style=for-the-badge" alt="AI Framework: BrainSwarm">
  <img src="https://img.shields.io/badge/Use%20Case-Maine%20DHS%20EBT%20LiveHeap-blue?style=for-the-badge" alt="Use Case: DHS EBT LiveHeap">
</p>

**Overview:**
The **EBT LiveHeap Pilot** demonstrates how the Brain-Swarm framework can modernize the Maine DHS Electronic Benefit Transfer (EBT) system.
It introduces intelligent agent coordination, live memory streaming, and process automation — improving efficiency, transparency, and citizen experience.

**💡 Objectives**
- Automate eligibility checks with Analyst Agents
- Detect fraud and duplicate claims in real-time
- Optimize task routing for case workers through Planner Agents
- Maintain synchronized program state via LiveHeap memory
- Deliver transparent metrics to DHS dashboards

**📄 Related Documentation**
- [EBT LiveHeap System Design](docs/EBT_LIVEHEAP_SYSTEM_DESIGN.md)
- [EBT LiveHeap Agent Behavior Tree](docs/EBT_LIVEHEAP_AGENT_BEHAVIOR_TREE.md)
- [Full-Stack System Flow](docs/EBT_LIVEHEAP_FULLSTACK_FLOW.md)

**🚀 Deployment Phase**
> *Status:* Sandbox / Pilot Proposal
> *Goal:* Integrate prototype Brain-Swarm deployment with DHS test datasets to validate eligibility automation, fraud detection, and dashboard performance.

---

## Integration with Maine DHS EBT Systems

### 🔗 API Gateway Connection
- **Endpoint:** `https://api.dhs.maine.gov/ebt/liveheap`
- **Authentication:** OAuth2 with GovNet certificates
- **Data Format:** JSON payloads with encrypted PII
- **Rate Limits:** 1000 requests/minute (configurable)

### 📊 LiveHeap Memory Synchronization
- **State Persistence:** Redis-backed in-memory cache
- **Data Streams:** Real-time event processing from DHS Data Lake
- **Audit Trail:** Immutable logs for compliance
- **Failover:** Automatic recovery with state reconstruction

### 🤖 Agent Deployment Configuration
```yaml
# Example agent-config.yaml
supervisor:
  routing_rules: eligibility_first
  escalation_threshold: 0.85
analyst_cluster:
  fraud_detection: enabled
  compliance_check: strict
  confidence_threshold: 0.92
liveheap:
  sync_interval: 30s
  retention_policy: 90_days
```

### 📈 Monitoring & Dashboards
- **Metrics Endpoint:** `/metrics` (Prometheus format)
- **Dashboard URL:** `https://dashboard.dhs.maine.gov/liveheap`
- **Alert Rules:** Configurable thresholds for agent performance
- **Log Aggregation:** ELK stack integration

### 🔒 Security & Compliance
- **Encryption:** AES-256 for data at rest/transit
- **Access Control:** Role-based permissions (RBAC)
- **Audit Logs:** SOC2 compliant event tracking
- **Data Residency:** All data remains within GovNet boundaries

---

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- Git
- Python 3.12+ (for local development)

### Local Development Setup
```bash
git clone https://github.com/jfbinTECHA/brain-swarm.git
cd brain-swarm

# Configure environment
cp .env.example .env

# Start local stack
make up

# Access services
open http://localhost:3000  # Grafana Dashboard
open http://localhost:8001/docs  # API Documentation
```

### DHS Integration Testing
```bash
# Run integration tests
make test-integration

# Deploy to sandbox
make deploy-sandbox

# Monitor logs
make logs
```

---

## 📚 Documentation

- **[System Architecture](docs/EBT_LIVEHEAP_SYSTEM_DESIGN.md)** - Complete technical design
- **[Agent Behavior Tree](docs/EBT_LIVEHEAP_AGENT_BEHAVIOR_TREE.md)** - AI agent coordination
- **[Full-Stack Flow](docs/EBT_LIVEHEAP_FULLSTACK_FLOW.md)** - End-to-end integration
- **[API Reference](docs/api/overview.md)** - REST API documentation
- **[Deployment Guide](docs/installation.md)** - Setup and configuration

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make changes and add tests
4. Run `make test` to ensure everything works
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

*Last updated: October 2025 — Authored by jfbinTECHA with ChatGPT AI collaboration.*
