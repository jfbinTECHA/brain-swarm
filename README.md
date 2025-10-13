# 🧠 Brain-Swarm: AI Coordination Framework for EBT LiveHeap

<p align="center">
  <img src="https://img.shields.io/badge/Build-Stable%20✅-brightgreen?style=flat-square" alt="Build Status">
  <img src="https://img.shields.io/badge/Docs-Complete%20📘-blue?style=flat-square" alt="Documentation Status">
  <img src="https://img.shields.io/badge/License-MIT%20⚖️-lightgrey?style=flat-square" alt="License: MIT">
  <img src="https://img.shields.io/badge/AI_Framework-BrainSwarm%20🤖-orange?style=flat-square" alt="AI Framework">
  <img src="https://img.shields.io/badge/Use_Case-Maine_DHS_EBT_LiveHeap%20🧩-blueviolet?style=flat-square" alt="Use Case">
</p>

> **Brain-Swarm** orchestrates multi-agent intelligence using memory synchronization, adaptive planning, and human-in-the-loop governance — bringing self-organizing AI to secure, data-driven public systems.

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

---

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

## ⚙️ Deployment Workflow

```mermaid
flowchart TD
    A[👩‍💻 Developer / IT Admin] --> B[📦 Clone brain-swarm Repository]
    B --> C[⚙️ Configure Environment<br>(Docker Compose / .env)]
    C --> D[🚀 Launch Local Sandbox<br>(Brain-Swarm Core + LiveHeap Engine)]
    D --> E[🧠 Deploy Agents<br>(Supervisor / Planner / Analyst)]
    E --> F[📡 Connect to DHS API Gateway<br>(GovNet Sandbox)]
    F --> G[📊 Activate Monitoring Dashboard<br>(LiveHeap Metrics & Logs)]
    G --> H{✅ Tests Pass?}
    H -->|Yes| I[📈 Deploy to Pilot Environment<br>(Maine DHS EBT Sandbox)]
    H -->|No| J[🔧 Review Logs & Re-train Models]
    I --> K[🕸️ Real-Time Agent Coordination Live]
    K --> L[🏛️ DHS Supervisors Access Dashboard]
    L --> M[📬 Automated Reports & Citizen Notifications]
```

---

<p align="center">
  <img src="https://img.shields.io/badge/🧩%20Architecture-Core%20Design-blue?style=for-the-badge" alt="Architecture">
  <img src="https://img.shields.io/badge/🤖%20Agents-BrainSwarm%20Intelligence-orange?style=for-the-badge" alt="Agents">
  <img src="https://img.shields.io/badge/⚙️%20Deployment-Automated%20Pipeline-brightgreen?style=for-the-badge" alt="Deployment">
  <img src="https://img.shields.io/badge/🌐%20System%20Flow-End%20to%20End%20Integration-blueviolet?style=for-the-badge" alt="System Flow">
  <img src="https://img.shields.io/badge/📘%20Docs-LiveHeap%20and%20EBT%20Design-lightgrey?style=for-the-badge" alt="Docs">
</p>

---

## 🌐 Full-Stack System Flow

```mermaid
graph LR
    A[👩‍👩‍👧 Citizen Portal<br>(Web/Mobile EBT Access)] --> B[📡 DHS API Gateway]
    B --> C[🧠 Brain-Swarm Supervisor Agent]
    C --> D1[📊 Planner Agent<br>(Workflow Orchestration)]
    C --> D2[🔍 Analyst Cluster<br>(Eligibility, Fraud, Compliance)]
    D1 --> E1[⚙️ LiveHeap Engine<br>(In-Memory State)]
    D2 --> E1
    E1 --> F[🗄️ DHS Data Lake<br>(Historical + Financial Records)]
    F --> G[📈 Monitoring Dashboard<br>(Program KPIs, Agent Logs)]
    G --> H[🏛️ DHS Supervisors<br>(Oversight & Auditing)]
    H --> I[🔁 Feedback Loop<br>(Policy Adjustments, Model Training)]
    I --> C
    E1 -->|Case Status Updates| A
```

### 🧠 Flow Summary
1. Citizens interact through the portal to manage benefits.  
2. The API Gateway validates input and routes to Brain-Swarm.  
3. Agents analyze eligibility, detect fraud, and plan actions.  
4. LiveHeap maintains synchronized state across all workflows.  
5. The DHS Data Lake stores transaction and history data.  
6. Dashboards display live KPIs for administrators.  
7. Supervisors feed data back to improve policies and AI models.

---

## 🧠 Use Case: Maine DHS — EBT LiveHeap Pilot

<p align="center">
  <img src="https://img.shields.io/badge/Status-Prototype%20🧪-blueviolet?style=for-the-badge" alt="Status: Prototype">
  <img src="https://img.shields.io/badge/Docs-Available%20📄-brightgreen?style=for-the-badge" alt="Docs Available">
  <img src="https://img.shields.io/badge/License-MIT%20⚖️-lightgrey?style=for-the-badge" alt="License">
  <img src="https://img.shields.io/badge/AI%20Framework-BrainSwarm%20🤖-orange?style=for-the-badge" alt="AI Framework: BrainSwarm">
  <img src="https://img.shields.io/badge/Use%20Case-Maine%20DHS%20EBT%20LiveHeap%20🧩-blue?style=for-the-badge" alt="Use Case: DHS EBT LiveHeap">
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
