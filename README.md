# 🧠 Brain Swarm

**Brain Swarm** is a modular, swarm-intelligence AI framework designed to coordinate multiple agents across distributed environments.  
It’s the foundation for Joseph Buzzell’s *Zeta AI / Kilo Code / Nomi Bridge* ecosystem — built for research, DevOps automation, and real-time adaptive reasoning.

---

## 🚀 Features

- **Agent Swarm Control Hub** – orchestrates multi-agent collaboration and messaging  
- **Transformer-ready Core** – supports integration with LLMs via OpenAI / OpenRouter APIs  
- **Realtime WebSocket Prototype** – bidirectional communication layer for dashboards  
- **Kubernetes-Native Design** – scalable across cloud nodes  
- **Plug-and-Play Modules** – attach agents, data streams, or external APIs easily  

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
# Python
__pycache__/
*.py[cod]
*.pyo
*.pyd
*.env
*.venv
.env/
venv/
ENV/
build/
dist/
*.egg-info/

# OS files
.DS_Store
Thumbs.db

# VS Code
.vscode/

# Logs / temp
*.log
logs/
tmp/
.cache/

# Bytebot / Nomi / Brain Swarm
*.db
*.sqlite
*.sock
*.pid
