# Full-Stack System Flow — Brain-Swarm & Maine DHS EBT LiveHeap

## Overview
This diagram shows the end-to-end integration of citizens, DHS EBT systems, Brain-Swarm agents, and LiveHeap memory coordination.

```mermaid
graph LR
    A[Citizen Portal (Web/Mobile Access)] --> B[DHS API Gateway]
    B --> C[Brain-Swarm Supervisor Agent]
    C --> D1[Planner Agent (Workflow)]
    C --> D2[Analyst Cluster (Eligibility/Fraud)]
    D1 --> E1[LiveHeap Engine (In-Memory State)]
    D2 --> E1
    E1 --> F[DHS Data Lake (Records)]
    F --> G[Monitoring Dashboard (KPIs)]
    G --> H[DHS Supervisors (Oversight)]
    H --> I[Feedback Loop (Policy Updates)]
    I --> C
    E1 -->|Case Status| A
