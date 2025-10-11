# UDP Broadcast Prototype for LAN Discovery

This prototype demonstrates UDP-based swarm discovery for Brain Swarm federation on local area networks (LAN).

## Overview

The prototype consists of two main components:
- **SwarmBroadcaster**: Sends periodic UDP broadcast messages announcing swarm presence
- **SwarmListener**: Listens for broadcast messages and tracks discovered swarms

## Quick Start

### Prerequisites
- Python 3.8+
- Access to UDP port 9999 (configurable)

### Basic Usage

1. **Start a listener** (in terminal 1):
   ```bash
   python lan_discovery_prototype.py listen
   ```

2. **Start a broadcaster** (in terminal 2):
   ```bash
   python lan_discovery_prototype.py broadcast
   ```

3. **Start another broadcaster** (in terminal 3):
   ```bash
   python lan_discovery_prototype.py broadcast --swarm-id swarm-2 --node-name node-2
   ```

The listener will show discovered swarms, and broadcasters will announce themselves every 5 seconds.

## Command Line Options

### Broadcast Mode
```bash
python lan_discovery_prototype.py broadcast [options]
```

Options:
- `--swarm-id SWARM_ID`: Swarm identifier (default: test-swarm)
- `--node-name NODE_NAME`: Node name (default: test-node)
- `--port PORT`: UDP port (default: 9999)
- `--interval INTERVAL`: Broadcast interval in seconds (default: 5.0)
- `--verbose, -v`: Enable verbose logging

### Listen Mode
```bash
python lan_discovery_prototype.py listen [options]
```

Options:
- `--port PORT`: UDP port to listen on (default: 9999)
- `--verbose, -v`: Enable verbose logging

## Example Scenarios

### Single Network Test
```bash
# Terminal 1: Listener
python lan_discovery_prototype.py listen

# Terminal 2: Broadcaster 1
python lan_discovery_prototype.py broadcast --swarm-id alpha --node-name alpha-01

# Terminal 3: Broadcaster 2
python lan_discovery_prototype.py broadcast --swarm-id beta --node-name beta-01
```

### Multi-Network Simulation
```bash
# Simulate different networks by using different ports
python lan_discovery_prototype.py listen --port 9999    # Network A
python lan_discovery_prototype.py listen --port 10000   # Network B

python lan_discovery_prototype.py broadcast --port 9999 --swarm-id net-a-swarm
python lan_discovery_prototype.py broadcast --port 10000 --swarm-id net-b-swarm
```

## Message Format

Broadcast messages are JSON-formatted:

```json
{
  "type": "swarm_announcement",
  "timestamp": 1638360000.123,
  "swarm_id": "test-swarm",
  "node_name": "test-node",
  "host": "192.168.1.100",
  "port": 9999,
  "capabilities": ["discovery", "communication"],
  "status": "active",
  "version": "1.0.0-prototype"
}
```

## Technical Details

- **Protocol**: UDP broadcast on configurable port
- **Address**: `<broadcast>` (255.255.255.255)
- **Socket Options**: SO_BROADCAST and SO_REUSEADDR enabled
- **Timeout**: 1-second socket timeout for clean shutdown
- **Threading**: Separate threads for broadcast/listen loops
- **Encoding**: UTF-8 JSON messages

## Troubleshooting

### Firewall Issues
UDP broadcasts may be blocked by firewalls. Ensure port 9999 is open for UDP traffic.

### Multiple Network Interfaces
On systems with multiple network interfaces, broadcasts may go out on all interfaces. The prototype uses the interface determined by connecting to 8.8.8.8.

### Port Conflicts
If port 9999 is in use, specify a different port with `--port` option.

### No Discoveries
- Ensure broadcaster and listener are on the same network segment
- Check that UDP broadcasts are not filtered by network equipment
- Verify firewall settings allow UDP traffic on the specified port

## Integration with Full System

This prototype demonstrates the core discovery mechanism used by the full Brain Swarm federation system in `discovery.py`. The full system includes:

- Persistent swarm registry with metadata
- Automatic cleanup of stale entries
- Integration with WebSocket connections
- Health monitoring and failure recovery

## Stopping

Press `Ctrl+C` in any terminal to stop the broadcaster or listener gracefully.