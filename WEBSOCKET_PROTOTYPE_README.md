# WebSocket Connection Prototype for Brain Swarm Federation

This prototype demonstrates WebSocket-based communication between swarm nodes for the Brain Swarm federation system.

## Overview

The prototype consists of two main components:
- **SwarmWebSocketServer**: WebSocket server that accepts client connections and handles federation messages
- **SwarmWebSocketClient**: WebSocket client that connects to servers and exchanges messages

## Features

- **Authentication**: Simple authentication handshake upon connection
- **Message Types**: Support for ping, task requests, status updates, and broadcasts
- **Federation Broadcasting**: Messages can be broadcast to all connected clients
- **Interactive Client**: Command-line interface for testing different message types
- **Connection Management**: Automatic ping/pong for connection health monitoring

## Quick Start

### Prerequisites
- Python 3.8+
- websockets library (included in requirements)

### Basic Usage

1. **Start a server** (in terminal 1):
   ```bash
   python websocket_prototype.py server
   ```

2. **Start a client** (in terminal 2):
   ```bash
   python websocket_prototype.py client
   ```

3. **Start another client** (in terminal 3):
   ```bash
   python websocket_prototype.py client --swarm-id swarm-2
   ```

The clients will automatically authenticate and can exchange messages.

## Command Line Options

### Server Mode
```bash
python websocket_prototype.py server [options]
```

Options:
- `--host HOST`: Server host (default: localhost)
- `--port PORT`: Server port (default: 8765)
- `--swarm-id SWARM_ID`: Server swarm ID (default: test-swarm)
- `--verbose, -v`: Enable verbose logging

### Client Mode
```bash
python websocket_prototype.py client [options]
```

Options:
- `--server URI`: Server URI (default: auto-construct from host:port)
- `--host HOST`: Server host for auto-URI (default: localhost)
- `--port PORT`: Server port for auto-URI (default: 8765)
- `--swarm-id SWARM_ID`: Client swarm ID (default: test-swarm)
- `--node-name NODE_NAME`: Client node name (default: test-node)
- `--interactive`: Enable interactive command mode
- `--verbose, -v`: Enable verbose logging

## Interactive Client Commands

When started with `--interactive`, the client provides a command-line interface:

```
WebSocket Client Commands:
  ping          - Send ping message
  tasks         - Request available tasks
  status        - Send status update
  broadcast     - Send broadcast message
  quit          - Disconnect and quit
```

## Message Types

### Authentication Messages
```json
// Client -> Server
{
  "type": "authenticate",
  "swarm_id": "my-swarm",
  "node_name": "node-1",
  "capabilities": ["communication", "task_sharing"],
  "timestamp": 1638360000.123
}

// Server -> Client
{
  "type": "auth_success",
  "server_swarm_id": "server-swarm",
  "message": "Authentication successful",
  "timestamp": 1638360000.456
}
```

### Ping/Pong Messages
```json
// Client -> Server
{
  "type": "ping",
  "timestamp": 1638360000.123
}

// Server -> Client
{
  "type": "pong",
  "timestamp": 1638360000.456,
  "server_swarm_id": "server-swarm"
}
```

### Task Messages
```json
// Client -> Server
{
  "type": "task_request",
  "requirements": {"priority": "any"},
  "timestamp": 1638360000.123
}

// Server -> Client
{
  "type": "task_response",
  "available_tasks": [
    {
      "task_id": "task_abc123",
      "type": "computation",
      "priority": 1,
      "description": "Sample computational task"
    }
  ],
  "timestamp": 1638360000.456
}
```

### Status Messages
```json
// Client -> Server
{
  "type": "status_update",
  "status": "active",
  "load_factor": 0.5,
  "active_tasks": 2,
  "timestamp": 1638360000.123
}

// Server -> Client
{
  "type": "status_ack",
  "received": true,
  "timestamp": 1638360000.456
}
```

### Broadcast Messages
```json
// Client -> Server
{
  "type": "broadcast",
  "message": "Hello federation!",
  "from_swarm": "my-swarm",
  "timestamp": 1638360000.123
}

// Server -> Client (broadcast to all other clients)
{
  "type": "federation_broadcast",
  "from_swarm": "sender-swarm",
  "original_data": {...},
  "timestamp": 1638360000.456
}

// Server -> Sender
{
  "type": "broadcast_ack",
  "recipients": 2,
  "timestamp": 1638360000.456
}
```

## Example Scenarios

### Multi-Client Federation Test
```bash
# Terminal 1: Server
python websocket_prototype.py server --swarm-id federation-hub

# Terminal 2: Client 1 (interactive)
python websocket_prototype.py client --swarm-id swarm-alpha --interactive

# Terminal 3: Client 2 (interactive)
python websocket_prototype.py client --swarm-id swarm-beta --interactive

# Terminal 4: Client 3 (demo mode)
python websocket_prototype.py client --swarm-id swarm-gamma
```

### Load Testing
```bash
# Start server
python websocket_prototype.py server --port 8765

# Start multiple clients
for i in {1..5}; do
  python websocket_prototype.py client --swarm-id "swarm-$i" &
done
```

### Custom Server Configuration
```bash
# Server on different host/port
python websocket_prototype.py server --host 0.0.0.0 --port 9000 --swarm-id production-hub

# Clients connecting to custom server
python websocket_prototype.py client --server ws://192.168.1.100:9000 --swarm-id client-1
```

## Technical Details

- **Protocol**: WebSocket over TCP
- **Authentication**: Simple JSON-based handshake
- **Message Format**: UTF-8 encoded JSON
- **Connection Health**: Automatic ping/pong every 30 seconds
- **Threading**: Asyncio-based concurrent connections
- **Error Handling**: Graceful handling of connection errors and invalid messages

## Integration with Full System

This prototype demonstrates the core WebSocket communication mechanism used by the full Brain Swarm federation system in `federation_connection.py`. The full system includes:

- Connection pooling and management
- Message encryption and security
- Advanced routing and load balancing
- Integration with discovery layer
- Persistent connection recovery

## Troubleshooting

### Connection Refused
- Ensure the server is running and accessible
- Check firewall settings for the specified port
- Verify the server URI format (ws://host:port)

### Authentication Failures
- Check that the server is accepting connections
- Verify swarm IDs are properly configured
- Look for authentication timeout messages

### Message Not Received
- Ensure clients are properly authenticated
- Check for JSON parsing errors in logs
- Verify message type handlers are registered

### Port Already in Use
- Choose a different port with `--port` option
- Check for other processes using the port
- Use `netstat` or `ss` to identify port usage

## Stopping

Press `Ctrl+C` in any terminal to gracefully stop servers and clients.