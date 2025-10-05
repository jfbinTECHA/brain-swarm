# 🧠 Brain Swarm

**Brain Swarm** is a modular, swarm-intelligence AI framework designed to coordinate multiple agents across distributed environments.  
It’s the foundation for Joseph Buzzell’s *Zeta AI / Kilo Code / Nomi Bridge* ecosystem — built for research, DevOps automation, and real-time adaptive reasoning.

---
<p align="center">
  <img src="https://github.com/jfbinTECHA/brain-swarm/assets/brain.png" width="100%" alt="Brain Swarm Banner"/>
</p>

## 🚀 Features

- **Agent Swarm Control Hub** – orchestrates multi-agent collaboration and messaging  
- **Transformer-ready Core** – supports integration with LLMs via OpenAI / OpenRouter APIs  
- **Realtime WebSocket Prototype** – bidirectional communication layer for dashboards  
- **Kubernetes-Native Design** – scalable across cloud nodes  
- **Plug-and-Play Modules** – attach agents, data streams, or external APIs easily
- **Enterprise Observability** – comprehensive monitoring, tracing, and alerting system
- **Developer Portal** – interactive API documentation with MkDocs Material

---

## 🧩 Architecture


---

## 🧰 Tech Stack

| Component | Technology |
|------------|-------------|
| Core Agents | Python 3.12+ |
| Communication | WebSockets / FastAPI |
| Dashboard | Next.js / Vercel |
| Deployment | Docker & Kubernetes |
| Version Control | Git + GitHub |

---

## 🚀 Scalability & Multi-Cluster Federation

Brain Swarm supports **horizontal scaling** with Redis-backed message buses and multi-cluster federation for enterprise-grade deployments.

### Quick Scalable Deployment

```bash
# Deploy scalable multi-cluster setup
docker-compose -f docker-compose.scalable.yml up -d

# Access points:
# - Primary API: http://localhost:8000 (Load balanced across clusters)
# - Monitoring: http://localhost:9090 (Prometheus)
# - Dashboards: http://localhost:3000 (Grafana)
# - Traefik Dashboard: http://localhost:8080
```

### Architecture Features

- **Redis Cluster**: 3-node Redis cluster for persistent, scalable messaging
- **Multi-Cluster Federation**: Intelligent task distribution across specialized clusters
- **Async Agent Pools**: Auto-scaling agent pools with load balancing
- **Horizontal Scaling**: Add clusters dynamically based on workload
- **Load Balancing**: Multiple strategies (least-loaded, weighted, geographic)
- **Monitoring**: Comprehensive observability across all clusters

### Cluster Types

- **Primary Cluster**: API gateway, coordination, and general task processing
- **Compute Clusters**: Specialized math/computation workloads
- **AI Clusters**: ML inference and GPU-accelerated processing
- **Edge Clusters**: Low-latency, real-time processing

### Scaling Commands

```bash
# Scale up compute cluster
docker-compose -f docker-compose.scalable.yml up -d --scale brain-swarm-compute-1=3

# Add new AI cluster
docker-compose -f docker-compose.scalable.yml up -d brain-swarm-ai-2

# Check cluster health
curl http://localhost:8000/health
```

---

## � Documentation

Brain Swarm features a comprehensive developer portal with interactive API documentation:

### Local Development

```bash
# Install documentation dependencies
pip install mkdocs mkdocs-material mkdocstrings mkdocs-openapi-plugin

# Generate API documentation
python generate_docs.py

# Serve documentation locally
mkdocs serve

# Access at http://localhost:8000
```

### Features

- **Interactive API Explorer**: Try API endpoints directly from the browser
- **Auto-generated OpenAPI Spec**: Always up-to-date API documentation
- **Monitoring & Observability Guide**: Complete observability documentation
- **Code Examples**: Python, JavaScript, and curl examples
- **Architecture Diagrams**: Visual system architecture documentation

### CI/CD Integration

Documentation is automatically generated and deployed via GitHub Actions on every push to main branch.

---

## 🧑‍💻 Usage

```bash
git clone git@github.com:jfbinTECHA/brain-swarm.git
cd brain-swarm
python3 websocket_prototype.py

Save with **Ctrl + O**, then **Enter**, and exit with **Ctrl + X**.

---

## ⚙️ Step 2: Add a `.gitignore`

```bash
nano .gitignore
# Brain Swarm Core Prototype

