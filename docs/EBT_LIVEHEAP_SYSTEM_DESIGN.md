# Maine DHS EBT LiveHeap System — Architecture & Integration with Brain-Swarm

## Overview
The **EBT LiveHeap** concept brings intelligent automation and swarm coordination to the Maine Department of Human Services’ Electronic Benefit Transfer (EBT) operations.
It integrates **AI-driven agents**, **real-time memory streams**, and **state-secured data infrastructure** to reduce manual work, accelerate eligibility decisions, and improve transparency.

## System Architecture (High-Level)
```mermaid
graph TD
    subgraph DHS["Maine DHS Environment"]
        D1[Citizen Portal\n(Web/Mobile Access)]
        D2[Case Worker Dashboard\n(Eligibility & Benefits)]
        D3[EBT Core System\n(Balances, Transactions)]
        D4[Document Intake / OCR]
        D5[Reporting & Audit Tools]
    end

    subgraph BrainSwarm["Brain-Swarm AI Layer"]
        B1[Supervisor Agent\n(Task Routing & Policy)]
        B2[Analyst Agents\n(Eligibility, Fraud, Insights)]
        B3[Planner Agent\n(Process Optimization)]
        B4[Knowledge Core\n(Rules, ML Models, Data)]
        B5[LiveHeap Engine\n(Real-time State & Cache)]
    end

    subgraph CloudInfra["GovNet / State Cloud"]
        C1[DHS API Gateway]
        C2[Data Lake\n(Citizen, Program, Financial)]
        C3[Monitoring & Dashboards]
        C4[Authentication & Identity]
    end

    %% Data Flow
    D1 --> C1
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

## Process Flow (Detailed)
```mermaid
flowchart LR
    A[Citizen Submits Application] --> B[API Gateway Validates Input]
    B --> C[Brain-Swarm Supervisor Classifies Request]
    C --> D1[Analyst Agent 1: Eligibility]
    C --> D2[Analyst Agent 2: Fraud Checks]
    C --> D3[Analyst Agent 3: Financial]
    D1 --> E[Planner Agent Compiles Results]
    D2 --> E
    D3 --> E
    E --> F[Supervisor Reviews Plan]
    F --> G[Decision: Approve/Deny/Review]
    G -->|Approved| H[Case Worker Notified]
    G -->|Denied| I[Citizen Portal Sends Notice]
    G -->|Needs Review| J[Human Escalation Queue]
    H --> K[EBT Core System Activated]
    I --> L[End Process]
    J --> L
```

## Agent Hierarchy & Roles
```mermaid
graph TD
    S[Supervisor Agent] --> A1[Planner Agent]
    S --> A2[Analyst Agent Cluster]
    S --> A3[Monitor Agent]
    A1 --> P1[Task Sequencer]
    A1 --> P2[Workflow Optimizer]
    A1 --> P3[Time Allocation]
    A2 --> B1[Eligibility Analyzer]
    A2 --> B2[Fraud Detector]
    A2 --> B3[Compliance Checker]
    A3 --> M1[Performance Tracker]
    A3 --> M2[Log Auditor]
    A3 --> M3[Error Recovery]
```

## Sequence Diagram (EBT Renewal Process)
```mermaid
sequenceDiagram
    participant Portal as Citizen Portal
    participant Gateway as API Gateway
    participant Supervisor as Supervisor Agent
    participant Planner as Planner Agent
    participant Analyst as Analyst Cluster
    participant Heap as LiveHeap Memory
    participant Dashboard as DHS Dashboard
    Portal->>Gateway: Submit EBT Renewal
    Gateway->>Supervisor: Forward Request
    Supervisor->>Planner: Request Schedule
    Planner-->>Supervisor: Execution Plan
    Supervisor->>Analyst: Dispatch Case Packet
    Analyst->>Heap: Read Case History
    Analyst-->>Supervisor: Results and Scores
    Supervisor->>Heap: Commit Updates
    Heap->>Dashboard: Update KPIs
    Dashboard-->>Portal: Citizen Status Update
```

## Decision Flowchart (Application Processing)
```mermaid
flowchart TD
    START((Start))
    A[Receive Application Data]
    B{All Required Fields Present?}
    C[Request Missing Data]
    D[Analyze Income & Household]
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

## Simplified Data Flow
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

## � Implementation Roadmap
- Build a prototype of the Analyst Cluster.
- Implement the LiveHeap memory API.
- Connect a visualization dashboard.
- Conduct a 30-day sandbox evaluation.
