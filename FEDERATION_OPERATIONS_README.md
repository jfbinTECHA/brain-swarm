# Brain Swarm Federation Operations Platform

A comprehensive live monitoring and control platform for Brain Swarm Federation operations. This platform extends the simulation into a real-time monitoring system that can connect to actual Brain Swarm nodes via APIs, WebSockets, and federated communication channels.

## Features

### 🔍 Real-Time Monitoring
- **Live Swarm Discovery**: Automatically discovers Brain Swarm nodes via federation registry and direct network scanning
- **Real-Time Metrics**: Connects to swarm APIs to fetch live health, performance, and task metrics
- **Dynamic Topology Visualization**: Interactive network graph showing swarm connections and federation links
- **Alert System**: Real-time alerts for swarm health issues, overload conditions, and network problems

### 🎛️ Control Operations
- **Swarm Management**: Start, stop, and restart individual swarms via API calls
- **Federation Control**: Create and dissolve federations between swarms
- **Load Balancing**: Distribute tasks across available swarms
- **Emergency Controls**: System-wide emergency stop and reset capabilities

### 📊 Analytics & History
- **Historical Metrics**: 24-hour retention of performance data
- **Analytics Dashboard**: Statistical analysis of system performance
- **Trend Analysis**: Identify patterns and predict issues
- **Export Capabilities**: Export metrics data for external analysis

### 🔐 Security & Authentication
- **API Key Authentication**: Secure access control for operations
- **Role-Based Permissions**: Different access levels for monitoring vs control
- **Audit Logging**: Complete audit trail of all operations
- **TLS Support**: Encrypted communications

## Architecture

```
┌─────────────────┐    WebSocket    ┌──────────────────────┐
│ Operations      │◄──────────────►│ Federation Registry  │
│ Platform HTML   │                 │ (Port 8002)         │
└─────────────────┘                 └──────────────────────┘
         │                                   │
         │ HTTP API calls                    │
         ▼                                   ▼
┌─────────────────┐    REST APIs     ┌──────────────────────┐
│ Operations      │◄────────────────►│ Brain Swarm Nodes   │
│ Server          │                   │ (Ports 8000+)       │
│ (Port 8001)     │                   └──────────────────────┘
└─────────────────┘
```

## Quick Start

### 1. Start the Operations Server

```bash
cd brain_swarm
python run_operations_server.py
```

The server will start on `http://localhost:8001` with WebSocket support.

### 2. Open the Operations Platform

Open `federation_operations_platform.html` in your web browser. The platform will automatically:

- Connect to the operations server via WebSocket
- Discover available Brain Swarm nodes
- Display real-time monitoring data
- Provide control interfaces

### 3. Authentication

Use the default credentials to access control features:
- **Username**: `admin`
- **Password**: `admin123`

## Swarm Discovery

The platform automatically discovers swarms through multiple methods:

### Federation Registry
- Queries the federation registry at `http://localhost:8002/swarms`
- Discovers registered swarms with their connection details
- Updates swarm metadata and capabilities

### Direct Network Discovery
- Scans common ports (8000, 8001, 8002, 8765) on localhost
- Tests `/health` endpoints to identify active swarms
- Fetches metrics from `/metrics` endpoints

### Simulated Fallback
- When no real swarms are found, creates simulated swarms for demonstration
- Provides realistic metrics and behavior for testing

## API Endpoints

### Operations Server Endpoints

- `GET /` - Server information
- `GET /health` - Server health check
- `GET /stats` - Global system statistics
- `GET /analytics/summary` - Analytics summary
- `GET /analytics/metrics/{name}` - Historical metric data
- `GET /analytics/metrics` - Available metrics list

### Swarm Node Endpoints (Expected)

Operations platform expects swarm nodes to provide these endpoints:

- `GET /health` - Health status and basic info
- `GET /metrics` - Detailed performance metrics
- `POST /control/start` - Start the swarm
- `POST /control/stop` - Stop the swarm
- `POST /control/restart` - Restart the swarm

## Control Operations

### Swarm Control
```javascript
// Start a swarm
socket.emit('start_swarm', { swarmId: 'swarm-1' });

// Stop a swarm
socket.emit('stop_swarm', { swarmId: 'swarm-1' });

// Restart a swarm
socket.emit('restart_swarm', { swarmId: 'swarm-1' });
```

### Federation Control
```javascript
// Create federation
socket.emit('create_federation');

// Dissolve federation
socket.emit('dissolve_federation');

// Load balancing
socket.emit('load_balance');
```

### System Control
```javascript
// Emergency stop
socket.emit('emergency_stop');

// System reset
socket.emit('system_reset');

// Create backup
socket.emit('create_backup');
```

## Metrics & Monitoring

### Real-Time Metrics
- **System Load**: Average CPU and memory usage across swarms
- **Active Tasks**: Number of tasks currently executing
- **Network Latency**: Average response times between swarms
- **Federation Throughput**: Data transfer rates between federated swarms

### Health Monitoring
- **Swarm Status**: Online/offline/error states
- **Resource Usage**: CPU, memory, and network utilization
- **Task Performance**: Success rates and completion times
- **Alert Conditions**: Automatic detection of issues

### Historical Analytics
- **24-Hour Retention**: All metrics stored for trend analysis
- **Statistical Summary**: Min, max, average, and standard deviation
- **Performance Trends**: Identify degradation or improvement patterns
- **Predictive Insights**: Forecast potential issues

## Configuration

### Server Configuration

Edit `federation_operations_server.py` to configure:

```python
# Registry URL
self.registry_url = "http://localhost:8002"

# Discovery settings
common_ports = [8000, 8001, 8002, 8765]
discovery_interval = 30  # seconds

# Metrics retention
self.history_retention_hours = 24
self.max_history_size = 10000
```

### Platform Configuration

The HTML platform can be configured via JavaScript variables:

```javascript
// WebSocket server URL
const SERVER_URL = 'ws://localhost:8001';

// Auto-refresh interval
const AUTO_REFRESH_INTERVAL = 5000; // ms

// Alert thresholds
const ALERT_THRESHOLDS = {
    high_load: 0.9,
    critical_memory: 0.95,
    high_latency: 200
};
```

## Troubleshooting

### No Swarms Detected
1. Ensure Brain Swarm nodes are running on expected ports
2. Check that `/health` endpoints are responding
3. Verify network connectivity between operations server and swarms
4. Check server logs for discovery errors

### WebSocket Connection Failed
1. Verify operations server is running on port 8001
2. Check browser console for connection errors
3. Ensure firewall allows WebSocket connections
4. Try refreshing the operations platform page

### Control Commands Not Working
1. Verify authentication is successful
2. Check that target swarm supports control endpoints
3. Review server logs for API call errors
4. Ensure swarm is in a controllable state

### High Latency or Performance Issues
1. Check network connectivity between components
2. Monitor system resources on swarm nodes
3. Review metrics history for performance trends
4. Consider load balancing or scaling operations

## Development

### Adding New Metrics
1. Define metric collection in `_update_real_swarm_states()`
2. Add storage logic in `_store_metric()`
3. Update UI display in the HTML platform
4. Add to analytics calculations if needed

### Extending Control Operations
1. Add new Socket.IO event handlers in the server
2. Implement control logic in `FederationOperationsManager`
3. Add UI controls in the HTML platform
4. Update authentication permissions if needed

### Custom Discovery Methods
1. Extend `_discover_swarm_nodes()` with new discovery logic
2. Add support for different registry types
3. Implement custom health checking logic
4. Update swarm metadata handling

## Security Considerations

### Production Deployment
- Use proper TLS certificates for all communications
- Implement strong authentication and authorization
- Configure firewall rules to restrict access
- Enable audit logging and monitoring
- Regularly update dependencies

### API Key Management
- Rotate API keys regularly
- Use different keys for different access levels
- Monitor key usage patterns
- Implement rate limiting per key

### Network Security
- Use VPNs for inter-swarm communications
- Implement network segmentation
- Monitor for unusual traffic patterns
- Enable intrusion detection systems

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## License

This project is part of the Brain Swarm Federation system. See project root for license information.