# Brain Swarm Federation Integration

This document describes the complete federation system that integrates discovery, connection, and cross-swarm coordination capabilities.

## Overview

The Brain Swarm Federation enables multiple swarm instances to discover each other, establish secure connections, and coordinate tasks, memory, and analytics across the entire federation.

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Discovery     │    │   Connection    │    │   Federation    │
│   Layer         │───▶│   Layer         │───▶│   Manager       │
│                 │    │                 │    │                 │
│ • UDP Broadcast │    │ • WebSocket     │    │ • Task Sharing  │
│ • Swarm Reg.    │    │ • Auth/Encrypt  │    │ • Memory Sync   │
│ • Health Mon.   │    │ • Message Exch. │    │ • Analytics     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │ Federation      │
                    │ Orchestrator    │
                    │                 │
                    │ • Lifecycle Mgmt│
                    │ • Auto-Connect   │
                    │ • Monitoring     │
                    │ • Optimization   │
                    └─────────────────┘
```

## Components

### 1. Discovery Layer (`discovery.py`)
- **UDP Broadcast**: Announces swarm presence on local network
- **Swarm Registry**: Maintains list of discovered swarms with metadata
- **Health Monitoring**: Automatic cleanup of stale swarm entries
- **Configuration**: Customizable ports, intervals, and timeouts

### 2. Connection Layer (`federation_connection.py`)
- **WebSocket Connections**: Bidirectional communication between swarms
- **Authentication**: Token-based authentication handshake
- **Message Exchange**: Structured message passing with response handling
- **Connection Management**: Auto-reconnection and heartbeat monitoring

### 3. Federation Manager (`federation.py`)
- **Task Sharing**: Distribute tasks across connected swarms
- **Memory Synchronization**: Share memory data (episodic, semantic, tool-use)
- **Analytics Distribution**: Broadcast performance metrics and insights
- **Resource Coordination**: Request and allocate resources across federation

### 4. Federation Orchestrator (`federation.py`)
- **Lifecycle Management**: Initialize, start, and stop federation components
- **Auto-Discovery**: Automatically connect to discovered swarms
- **Monitoring**: Health checks and metrics collection
- **Configuration**: Centralized federation configuration management

## Quick Start

### Basic Federation Setup

```python
import asyncio
from brain_swarm.federation import FederationOrchestrator

async def main():
    # Create and configure orchestrator
    orchestrator = (FederationOrchestrator("my-swarm", "my-node")
                   .configure_discovery(broadcast_port=9999, api_port=8000)
                   .configure_connections(auth_token="secure-token"))

    # Initialize and start federation
    await orchestrator.initialize()
    await orchestrator.start()

    # Federation is now active
    print("Federation running:", orchestrator.get_federation_status())

    # Keep running
    await asyncio.sleep(300)  # Run for 5 minutes

    # Stop federation
    await orchestrator.stop()

asyncio.run(main())
```

### Using Federation Demo

```bash
# Interactive demo (recommended for first-time users)
python federation_demo.py --swarm-id swarm-alpha --interactive

# Automated demo
python federation_demo.py --swarm-id swarm-beta --duration 120

# Multiple swarms (run in different terminals)
python federation_demo.py --swarm-id swarm-1 --interactive
python federation_demo.py --swarm-id swarm-2 --interactive
python federation_demo.py --swarm-id swarm-3 --interactive
```

## Configuration

### Discovery Configuration
```python
config = {
    "discovery": {
        "enabled": True,
        "broadcast_port": 9999,
        "api_port": 8000,
        "broadcast_interval": 30.0,  # seconds
        "discovery_timeout": 300.0   # seconds
    }
}
```

### Connection Configuration
```python
config = {
    "connection": {
        "auth_token": "your-secure-token",
        "reconnect_interval": 30.0,
        "heartbeat_interval": 60.0
    }
}
```

### Sharing Configuration
```python
config = {
    "sharing": {
        "enable_task_sharing": True,
        "enable_memory_sync": True,
        "enable_analytics_sharing": True,
        "auto_discovery_connections": True
    }
}
```

## Federation Operations

### Task Sharing

```python
from brain_swarm.federation import SharedTask

# Create a task to share
task = SharedTask(
    task_id="analysis-001",
    task_type="data_analysis",
    priority=2,
    payload={"data": [1, 2, 3, 4, 5], "operation": "mean"},
    origin_swarm="my-swarm",
    created_at=time.time()
)

# Share with entire federation
await orchestrator.share_task_federation_wide(task)

# Share with specific swarms
await orchestrator.federation_manager.share_task(task, ["swarm-alpha", "swarm-beta"])
```

### Memory Synchronization

```python
from brain_swarm.federation import MemorySync

# Create memory data to share
memory = MemorySync(
    memory_type="episodic",
    key="user_preference_123",
    value={"theme": "dark", "language": "en"},
    origin_swarm="my-swarm",
    timestamp=time.time(),
    ttl=3600.0
)

# Synchronize across federation
await orchestrator.synchronize_memory_federation(memory)
```

### Analytics Sharing

```python
from brain_swarm.federation import AnalyticsData

# Create analytics data
analytics = AnalyticsData(
    data_type="performance_metrics",
    metrics={
        "tasks_completed": 150,
        "avg_response_time": 0.8,
        "success_rate": 0.96
    },
    origin_swarm="my-swarm",
    time_range=(time.time()-3600, time.time()),
    timestamp=time.time()
)

# Broadcast to federation
await orchestrator.broadcast_analytics_federation(analytics)
```

### Resource Requests

```python
# Request resources from federation
requirements = {
    "cpu_cores": 4,
    "memory_gb": 8,
    "capabilities": ["gpu", "high_memory"]
}

available_resources = await orchestrator.request_federation_resources(requirements)
print("Available resources:", available_resources)
```

## Integration with Brain Swarm Components

### Memory Manager Integration

```python
from brain_swarm.memory import WorkingMemory

# Create memory manager
memory_manager = WorkingMemory()

# Integrate with federation
orchestrator.set_memory_manager(memory_manager)

# Memory operations will now sync across federation
memory_manager.store("key", "value")
# Automatically shared with connected swarms
```

### Analytics Manager Integration

```python
from brain_swarm.analytics.predictive_analytics import TaskCompletionPredictor

# Create analytics manager
analytics_manager = TaskCompletionPredictor()

# Integrate with federation
orchestrator.set_analytics_manager(analytics_manager)

# Analytics data will be shared across federation
prediction = analytics_manager.predict_completion_time("task desc", "analysis", "agent-1")
# Prediction results shared with connected swarms
```

### Task Manager Integration

```python
# Integrate custom task manager
orchestrator.set_task_manager(your_task_manager)

# Task operations will coordinate across federation
your_task_manager.create_task("analysis", {"data": "large_dataset"})
# Task may be distributed to other swarms in federation
```

## Monitoring and Status

### Federation Status

```python
# Get comprehensive federation status
status = orchestrator.get_federation_status()
print(f"Federation running: {status['is_running']}")
print(f"Connected swarms: {status['federation']['total_connected_swarms']}")
print(f"Shared tasks: {status['federation']['shared_tasks_count']}")
```

### Federation Metrics

```python
# Get detailed metrics
metrics = orchestrator.federation_manager.get_federation_metrics()
print("Federation Health:", metrics['federation_health'])
print("Capabilities:", metrics['federation_capabilities'])
```

## Event Callbacks

### Task Events

```python
def on_task_received(task: SharedTask):
    print(f"Received task: {task.task_id} from {task.origin_swarm}")
    # Process the shared task

orchestrator.federation_manager.on_task_received = on_task_received
```

### Memory Events

```python
def on_memory_update(memory: MemorySync):
    print(f"Memory update: {memory.key} from {memory.origin_swarm}")
    # Update local memory with federation data

orchestrator.federation_manager.on_memory_update = on_memory_update
```

### Analytics Events

```python
def on_analytics_received(analytics: AnalyticsData):
    print(f"Analytics received: {analytics.data_type} from {analytics.origin_swarm}")
    # Process shared analytics data

orchestrator.federation_manager.on_analytics_received = on_analytics_received
```

## Advanced Features

### Federation Optimization

```python
# Perform federation-wide optimization
optimization_results = await orchestrator.optimize_federation_resources()
print("Optimization actions:", optimization_results)
```

### Custom Message Handling

```python
# Register custom message handlers
orchestrator.federation_manager.connection_manager.message_handlers["custom_type"] = handle_custom_message

async def handle_custom_message(message):
    # Handle custom federation messages
    pass
```

### Connection Management

```python
# Manually connect to specific swarm
await orchestrator.federation_manager.connection_manager.connect_to_swarm(swarm_metadata)

# Disconnect from swarm
await orchestrator.federation_manager.connection_manager.disconnect_from_swarm("swarm-id")
```

## Troubleshooting

### Discovery Issues
- Check firewall settings for UDP port 9999
- Ensure swarms are on the same network segment
- Verify broadcast permissions

### Connection Issues
- Check WebSocket port availability (default 8000)
- Verify authentication tokens match
- Check network connectivity between swarms

### Message Issues
- Ensure message format matches expected structure
- Check for JSON serialization errors
- Verify message handlers are registered

### Performance Issues
- Adjust broadcast intervals for network load
- Configure appropriate timeouts
- Monitor federation metrics for bottlenecks

## Security Considerations

- Use strong, unique authentication tokens
- Implement proper firewall rules
- Regularly rotate authentication credentials
- Monitor federation access logs
- Validate all incoming messages

## Scaling Considerations

- **Small Federation (2-5 swarms)**: Default configuration works well
- **Medium Federation (6-20 swarms)**: Increase timeouts, reduce broadcast frequency
- **Large Federation (20+ swarms)**: Implement message routing, consider federation segmentation

## Next Steps

1. **Experiment**: Run the federation demo with multiple instances
2. **Integrate**: Connect your existing Brain Swarm components
3. **Customize**: Adjust configuration for your specific use case
4. **Monitor**: Set up monitoring and alerting for federation health
5. **Scale**: Plan for growth and implement advanced routing if needed

## API Reference

### FederationOrchestrator
- `initialize()`: Async initialization of federation components
- `start()`: Start federation operations
- `stop()`: Stop federation operations
- `get_federation_status()`: Get current federation status
- `share_task_federation_wide(task)`: Share task across federation
- `synchronize_memory_federation(memory)`: Sync memory across federation
- `broadcast_analytics_federation(analytics)`: Share analytics across federation
- `request_federation_resources(requirements)`: Request resources from federation

### FederationManager
- `share_task(task, target_swarms)`: Share task with specific or all swarms
- `share_memory(memory, target_swarms)`: Share memory with specific or all swarms
- `share_analytics(analytics, target_swarms)`: Share analytics with specific or all swarms
- `request_resources(requirements)`: Request resources from connected swarms
- `get_federation_metrics()`: Get federation metrics

### Data Classes
- `SharedTask`: Represents a task for federation sharing
- `MemorySync`: Represents memory data for synchronization
- `AnalyticsData`: Represents analytics data for sharing

See the source code in `federation/federation.py` for complete API documentation.