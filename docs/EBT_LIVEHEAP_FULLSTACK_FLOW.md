# Full-Stack System Flow — Brain-Swarm & Maine DHS EBT LiveHeap

## Overview
This diagram shows the end-to-end integration of citizens, DHS EBT systems, Brain-Swarm agents, and LiveHeap memory coordination.

```mermaid
graph LR
    A[Citizen Portal] --> B[DHS API Gateway]
    B --> C[Supervisor Agent]
    C --> D1[Planner Agent]
    C --> D2[Analyst Cluster]
    D1 --> E1[LiveHeap Engine]
    D2 --> E1
    E1 --> F[DHS Data Lake]
    F --> G[Monitoring Dashboard]
    G --> H[DHS Supervisors]
    H --> I[Feedback Loop]
    I --> C
    E1 --> A
