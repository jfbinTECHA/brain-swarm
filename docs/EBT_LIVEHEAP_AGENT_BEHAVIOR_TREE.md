# Brain-Swarm Agent Behavior Tree — EBT LiveHeap Program

## Core Agent Hierarchy
```mermaid
graph TD
    S[Supervisor Agent] --> A1[Planner Agent]
    S --> A2[Analyst Cluster]
    S --> A3[Monitor Agent]
    A1 --> P1[Task Sequencer]
    A1 --> P2[Workflow Optimizer]
    A2 --> B1[Eligibility Analyzer]
    A2 --> B2[Fraud Detector]
    A3 --> M1[Performance Tracker]
    A3 --> M2[Error Handler]
