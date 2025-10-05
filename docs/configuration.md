# Configuration

Brain Swarm uses a hierarchical configuration system with support for multiple sources.

## Configuration Sources

Configuration is loaded from the following sources (in order of precedence):

1. **Environment Variables** (highest priority)
2. **Secrets Manager** (Vault or AWS Secrets Manager)
3. **Configuration Files** (.env, YAML, etc.)
4. **Default Values** (lowest priority)

## Secrets Management

Brain Swarm supports multiple secrets management backends:

### HashiCorp Vault

```python
# Configuration for Vault
secrets:
  provider: "vault"
  vault_url: "https://vault.example.com:8200"
  vault_token: "hvs.your-vault-token"
  vault_mount_point: "secret"
  vault_path: "brain-swarm"
```

### AWS Secrets Manager

```python
# Configuration for AWS
secrets:
  provider: "aws"
  aws_region: "us-east-1"
  aws_secret_name: "brain-swarm"
```

## Environment Variables

### API Keys

```bash
# OpenAI API Key
OPENAI_API_KEY=sk-your-openai-key

# OpenRouter API Key
OPENROUTER_API_KEY=sk-or-v1-your-openrouter-key

# Anthropic API Key
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key

# Grok API Key
GROK_API_KEY=xai-your-grok-key
```

### Node Configuration

```bash
# Node settings
BRAIN_SWARM_NODE_NAME=my_swarm_node
SWARM_ID=production_swarm
HOST=0.0.0.0
PORT=8000
MAX_AGENTS=10
MAX_AGENT_LOAD=3
```

### Database

```bash
# Database connection
DATABASE_URL=postgresql://user:password@localhost:5432/brain_swarm
DATABASE_POOL_SIZE=5
DATABASE_MAX_OVERFLOW=10
```

### Security

```bash
# JWT settings
JWT_SECRET=your-super-secret-jwt-key-change-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# API Keys for agent registration
API_KEY_AGENT_1=secret-key-1
API_KEY_AGENT_2=secret-key-2
```

### Logging

```bash
# Logging configuration
LOG_LEVEL=INFO
LOG_FORMAT="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_FILE_PATH=/var/log/brain_swarm.log
```

## Configuration File

You can also use a `.env` file for configuration:

```bash
# .env file
OPENAI_API_KEY=sk-your-openai-key
BRAIN_SWARM_NODE_NAME=production_node
DATABASE_URL=sqlite:///brain_swarm.db
```

## Programmatic Configuration

```python
from config import settings

# Access configuration
api_key = settings.api_keys.openai_api_key
node_name = settings.node.node_name
db_url = settings.database.url

# Modify settings
settings.node.max_agents = 20
```

## Federation Configuration

```python
# Federation settings
federation:
  enabled: true
  discovery_url: "https://federation.example.com"
  shared_memory_url: "redis://shared-memory:6379"
```

## Scalability Configuration

Brain Swarm supports horizontal scaling with Redis-backed message queues and multi-cluster federation.

### Environment Variables

```bash
# Enable scalability features
SCALABILITY__ENABLED=true

# Message queue mode: single_node, cluster, or partitioned
SCALABILITY__MESSAGE_QUEUE_MODE=cluster

# Redis URLs for message queue
SCALABILITY__REDIS_URLS=["redis://redis-1:6379", "redis://redis-2:6379", "redis://redis-3:6379"]

# Number of message queue partitions
SCALABILITY__PARTITIONS=8

# Enable async agents with load balancing
SCALABILITY__ASYNC_AGENTS_ENABLED=true

# Agent pool size configuration
SCALABILITY__AGENT_POOL_MIN=2
SCALABILITY__AGENT_POOL_MAX=20

# Load balancing strategy: least_loaded, weighted, round_robin, geographic
SCALABILITY__LOAD_BALANCING_STRATEGY=least_loaded

# Multi-cluster federation
SCALABILITY__MULTI_CLUSTER_ENABLED=true
SCALABILITY__CLUSTER_ID=my_cluster
SCALABILITY__CLUSTER_ROLE=primary

# Auto-scaling coordination
SCALABILITY__AUTO_SCALING_ENABLED=true
```

### Programmatic Configuration

```python
from config import settings

# Enable scalability
settings.scalability.enabled = True
settings.scalability.message_queue_mode = "cluster"
settings.scalability.redis_urls = ["redis://redis-1:6379", "redis://redis-2:6379"]
settings.scalability.async_agents_enabled = True
settings.scalability.multi_cluster_enabled = True

# Access scalability settings
print(f"Scalability enabled: {settings.scalability.enabled}")
print(f"Agent pool range: {settings.scalability.agent_pool_min}-{settings.scalability.agent_pool_max}")
```

## Validation

Configuration values are validated using Pydantic models, ensuring type safety and providing helpful error messages for invalid configurations.

## Environment-Specific Configuration

Use different configuration files for different environments:

```bash
# development.env
ENVIRONMENT=development
LOG_LEVEL=DEBUG
DATABASE_URL=sqlite:///dev.db

# production.env
ENVIRONMENT=production
LOG_LEVEL=INFO
DATABASE_URL=postgresql://prod-user:prod-pass@prod-db:5432/brain_swarm
```

## Security Best Practices

1. **Never commit secrets** to version control
2. **Use secrets managers** in production
3. **Rotate keys regularly**
4. **Use strong, unique keys** for each environment
5. **Limit key permissions** to minimum required
6. **Monitor key usage** through audit logs