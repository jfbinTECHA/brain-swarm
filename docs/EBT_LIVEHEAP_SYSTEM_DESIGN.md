# 🧩 Maine DHS EBT LiveHeap System — Architecture & Integration with Brain-Swarm

## 📘 Overview
The **EBT LiveHeap** concept brings intelligent automation and swarm coordination to the Maine Department of Human Services’ Electronic Benefit Transfer (EBT) operations.
It integrates **AI-driven agents**, **real-time memory streams**, and **state-secured data infrastructure** to reduce manual work, accelerate eligibility decisions, and improve transparency.

## 🧠 System Architecture (High-Level)
```mermaid
graph TD
    subgraph DHS["Maine DHS Environment"]
        D1[Citizen Portal<br>(Mobile/Web Access)]
        D2[Case Worker Dashboard<br>(Eligibility & Benefits Management)]
        D3[EBT Core System<br>(Balances, Transactions, Card Mgmt)]
        D4[Document Intake / OCR System]
        D5[Reporting & Audit Tools]
    end

    subgraph BrainSwarm["Brain-Swarm AI Layer"]
        B1[Supervisor Agent<br>(Task Routing & Policy Logic)]
        B2[Analyst Agents<br>(Eligibility Analysis, Fraud Detection, Case Insights)]
        B3[Planner Agent<br>(Process Optimization, Load Balancing)]
        B4[Knowledge Core<br>(Rules, ML Models, Historical Data)]
        B5[LiveHeap Engine<br>(Real-time State & Memory Cache)]
    end

    subgraph CloudInfra["GovNet / State Cloud Infrastructure"]
        C1[Secure API Gateway]
        C2[Data Lake<br>(Citizen, Program, Financial Data)]
        C3[Monitoring & Dashboards]
        C4[Authentication & Identity Service]
    end

    %% Data Flow
    D1 -->|Applications, Updates| C1
    D2 -->|Case Notes, Approvals| C1
    D4 -->|Scanned Docs| C2
    D3 -->|Transactions| C2
    C1 --> B1
    B1 -->|Route Tasks| B2
    B2 -->|Insights, Scoring| B1
    B1 -->|Optimized Plan| B3
    B3 -->|Workflow Commands| D2
    B4 <--> B2
    B5 <--> B4
    B5 --> C3
    C2 -->|Data Streams| B5
    C3 -->|Program Metrics| DHS
    D1 -->|Citizen Notifications| D2
```

## 🔄 Process Flow (Detailed)
```mermaid
flowchart LR
    A[Citizen Submits Application] --> B[API Gateway Validates Input]
    B --> C[Brain-Swarm Supervisor Classifies Request]
    C --> D1[Analyst Agent 1: Eligibility Rules]
    C --> D2[Analyst Agent 2: Fraud & Duplicate Checks]
    C --> D3[Analyst Agent 3: Financial Consistency]
    D1 --> E[Planner Agent Compiles Results]
    D2 --> E
    D3 --> E
    E --> F[Supervisor Reviews Plan]
    F --> G[Decision: Approve / Deny / Needs Review]
    G -->|Approved| H[Case Worker Notified via Dashboard]
    G -->|Denied| I[Citizen Portal Sends Notice]
    G -->|Needs Review| J[Human Escalation Queue]
    H --> K[EBT Core System Activated]
    I --> L[End Process]
    J --> L
```

## 🤖 Agent Hierarchy & Roles
```mermaid
graph TD
    S[Supervisor Agent] --> A1[Planner Agent]
    S --> A2[Analyst Agent Cluster]
    S --> A3[Monitor Agent]
    A1 --> P1[Task Sequencer]
    A1 --> P2[Workflow Optimizer]
    A1 --> P3[Time Allocation Model]
    A2 --> B1[Eligibility Analyzer]
    A2 --> B2[Fraud & Risk Detector]
    A2 --> B3[Compliance Checker]
    A3 --> M1[Performance Tracker]
    A3 --> M2[Log Auditor]
    A3 --> M3[Error Recovery Handler]
```

## ⏳ Sequence Diagram (EBT Renewal Process)
```mermaid
sequenceDiagram
    participant Portal as Citizen Portal
    participant Gateway as API Gateway
    participant Supervisor as Supervisor Agent
    participant Planner as Planner Agent
    participant Analyst as Analyst Cluster
    participant Heap as LiveHeap Memory
    participant Dashboard as DHS Dashboard
    Portal->>Gateway: Submit EBT Renewal Request
    Gateway->>Supervisor: Forward Structured Payload
    Supervisor->>Planner: Request Task Schedule
    Planner-->>Supervisor: Optimal Execution Order
    Supervisor->>Analyst: Dispatch Case Packet
    Analyst->>Heap: Read Case History + Prior State
    Analyst-->>Supervisor: Results + Confidence Scores
    Supervisor->>Heap: Commit Updates
    Heap->>Dashboard: Update Visuals + KPIs
    Dashboard-->>Portal: Citizen Status Update
```

## 🔀 Decision Flowchart (Application Processing)
```mermaid
flowchart TD
    START((Start))
    A[Receive Application Data]
    B{All Required Fields Present?}
    C[Request Missing Data]
    D[Analyze Income & Household Size]
    E{Meets Eligibility Thresholds?}
    F[Send to Case Worker for Review]
    G[Approve Automatically]
    H[Flag Potential Fraud]
    I[Supervisor Logs Decision]
    J[Update LiveHeap + Dashboard]
    K((End))
    START --> A --> B
    B -->|No| C --> F
    B -->|Yes| D --> E
    E -->|No| F
    E -->|Yes| G --> J
    D --> H --> F
    F --> I --> J --> K
    G --> I --> J --> K
```

## 🚀 Implementation Roadmap
- Build a prototype of the Analyst Cluster.
- Implement the LiveHeap memory API.
- Connect a visualization dashboard.
- Conduct a 30-day sandbox evaluation.