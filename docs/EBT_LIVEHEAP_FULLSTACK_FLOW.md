# 🧩 Full-Stack System Flow — Brain-Swarm & Maine DHS EBT LiveHeap

## 🧠 Overview
This diagram shows the **end-to-end flow** between citizens, the DHS EBT systems, Brain-Swarm agents, and LiveHeap memory coordination. It represents the full intelligent feedback loop that powers automation and transparency across the system.

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
    E1 -->|Case Status| A
```
