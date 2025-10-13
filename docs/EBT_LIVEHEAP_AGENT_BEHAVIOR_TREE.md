# 🤖 EBT LiveHeap Agent Behavior Tree

## Agent Hierarchy & Roles
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