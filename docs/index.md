# Brain Swarm API Documentation

Welcome to the Brain Swarm API documentation. Brain Swarm is a modular, swarm-intelligence AI framework designed to coordinate multiple agents across distributed environments.

## Overview

Brain Swarm provides a comprehensive API for:

- **Agent Management**: Register, monitor, and coordinate AI agents
- **Task Execution**: Submit tasks and track their progress
- **Swarm Coordination**: Manage multi-agent collaboration
- **Real-time Monitoring**: Access performance metrics and dashboards
- **Federation Support**: Connect multiple swarm instances

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Start the API server
python api/main.py

# Access the API documentation at http://localhost:8000/docs
```

## Key Features

- **RESTful API**: Full REST API with OpenAPI/Swagger documentation
- **WebSocket Support**: Real-time communication for live dashboards
- **Kubernetes Native**: Designed for cloud-native deployments
- **Plugin Architecture**: Extensible agent system
- **Security**: JWT authentication and policy enforcement
- **Comprehensive Observability**: Prometheus metrics, distributed tracing, health checks, and alerting
- **Governance & Compliance**: Automated policy monitoring and compliance reporting
- **Enterprise Monitoring**: Real-time dashboards, alerting, and performance analytics

## Architecture

Brain Swarm follows a hierarchical architecture:

- **Coordinator**: Central orchestration component
- **Agents**: Specialized AI workers (Language, Vision, Math, etc.)
- **Memory System**: Persistent storage and retrieval
- **Federation Layer**: Cross-swarm communication

## API Reference

See the [API Reference](api/overview.md) for detailed endpoint documentation.

## Configuration

Learn how to configure Brain Swarm in the [Configuration](configuration.md) section.

## Deployment

See [Deployment](deployment.md) for production deployment guides.