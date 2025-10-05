"""
Tests for the Discovery Layer component.
"""

import pytest
import time
import threading
import socket
from unittest.mock import Mock, patch, MagicMock
from brain_swarm.discovery import DiscoveryLayer, SwarmMetadata, create_discovery_layer


class TestSwarmMetadata:
    """Test SwarmMetadata dataclass functionality."""

    def test_metadata_creation(self):
        """Test creating SwarmMetadata with required fields."""
        metadata = SwarmMetadata(
            swarm_id="test_swarm",
            node_name="test_node",
            host="192.168.1.100",
            port=9999,
            api_port=8000,
            capabilities=["coordination", "task_execution"],
            agent_count=5,
            last_seen=time.time()
        )

        assert metadata.swarm_id == "test_swarm"
        assert metadata.node_name == "test_node"
        assert metadata.host == "192.168.1.100"
        assert metadata.port == 9999
        assert metadata.api_port == 8000
        assert metadata.capabilities == ["coordination", "task_execution"]
        assert metadata.agent_count == 5
        assert metadata.status == "active"
        assert metadata.federation_enabled is True
        assert len(metadata.unique_id) == 8  # MD5 hash truncated

    def test_metadata_to_dict(self):
        """Test converting SwarmMetadata to dictionary."""
        metadata = SwarmMetadata(
            swarm_id="test_swarm",
            node_name="test_node",
            host="192.168.1.100",
            port=9999,
            api_port=8000,
            capabilities=["coordination"],
            agent_count=3,
            last_seen=1234567890.0
        )

        data = metadata.to_dict()
        assert isinstance(data, dict)
        assert data["swarm_id"] == "test_swarm"
        assert data["node_name"] == "test_node"
        assert data["host"] == "192.168.1.100"
        assert data["port"] == 9999
        assert data["api_port"] == 8000
        assert data["capabilities"] == ["coordination"]
        assert data["agent_count"] == 3

    def test_metadata_from_dict(self):
        """Test creating SwarmMetadata from dictionary."""
        data = {
            "swarm_id": "test_swarm",
            "node_name": "test_node",
            "host": "192.168.1.100",
            "port": 9999,
            "api_port": 8000,
            "capabilities": ["coordination"],
            "agent_count": 3,
            "last_seen": 1234567890.0,
            "status": "active",
            "version": "1.0.0",
            "federation_enabled": True,
            "load_factor": 0.5
        }

        metadata = SwarmMetadata.from_dict(data)
        assert metadata.swarm_id == "test_swarm"
        assert metadata.node_name == "test_node"
        assert metadata.host == "192.168.1.100"
        assert metadata.port == 9999
        assert metadata.api_port == 8000
        assert metadata.capabilities == ["coordination"]
        assert metadata.agent_count == 3
        assert metadata.load_factor == 0.5

    def test_metadata_expiration(self):
        """Test metadata expiration checking."""
        # Fresh metadata
        recent_time = time.time()
        metadata = SwarmMetadata(
            swarm_id="test_swarm",
            node_name="test_node",
            host="192.168.1.100",
            port=9999,
            api_port=8000,
            capabilities=[],
            agent_count=0,
            last_seen=recent_time
        )

        assert not metadata.is_expired(300.0)  # Not expired

        # Old metadata
        old_time = time.time() - 400  # 400 seconds ago
        metadata.last_seen = old_time
        assert metadata.is_expired(300.0)  # Expired

    def test_metadata_update_activity(self):
        """Test updating metadata activity timestamp."""
        metadata = SwarmMetadata(
            swarm_id="test_swarm",
            node_name="test_node",
            host="192.168.1.100",
            port=9999,
            api_port=8000,
            capabilities=[],
            agent_count=0,
            last_seen=1234567890.0
        )

        old_time = metadata.last_seen
        time.sleep(0.01)  # Small delay
        metadata.update_activity()

        assert metadata.last_seen > old_time


class TestDiscoveryLayer:
    """Test DiscoveryLayer functionality."""

    @pytest.fixture
    def discovery_layer(self):
        """Create a discovery layer for testing."""
        return DiscoveryLayer(
            swarm_id="test_swarm",
            node_name="test_node",
            broadcast_port=9998,  # Use different port for tests
            api_port=8000,
            broadcast_interval=0.1,  # Fast for testing
            discovery_timeout=1.0   # Short timeout for testing
        )

    def test_discovery_layer_initialization(self, discovery_layer):
        """Test discovery layer initialization."""
        assert discovery_layer.swarm_id == "test_swarm"
        assert discovery_layer.node_name == "test_node"
        assert discovery_layer.broadcast_port == 9998
        assert discovery_layer.api_port == 8000
        assert discovery_layer.broadcast_interval == 0.1
        assert discovery_layer.discovery_timeout == 1.0
        assert not discovery_layer.running
        assert len(discovery_layer.discovered_swarms) == 0

    def test_own_metadata_creation(self, discovery_layer):
        """Test that own metadata is created correctly."""
        metadata = discovery_layer.own_metadata
        assert metadata.swarm_id == "test_swarm"
        assert metadata.node_name == "test_node"
        assert metadata.port == 9998
        assert metadata.api_port == 8000
        assert metadata.status == "active"
        assert metadata.federation_enabled is True
        assert isinstance(metadata.capabilities, list)

    @patch('brain_swarm.discovery.socket.socket')
    def test_socket_setup(self, mock_socket_class, discovery_layer):
        """Test socket setup for broadcasting and listening."""
        mock_broadcast_socket = MagicMock()
        mock_listen_socket = MagicMock()
        mock_socket_class.side_effect = [mock_broadcast_socket, mock_listen_socket]

        discovery_layer._setup_sockets()

        # Verify broadcast socket setup
        assert mock_broadcast_socket.setsockopt.call_count >= 2
        assert discovery_layer.broadcast_socket == mock_broadcast_socket

        # Verify listen socket setup
        assert mock_listen_socket.setsockopt.called
        mock_listen_socket.bind.assert_called_with(('', 9998))
        assert discovery_layer.listen_socket == mock_listen_socket

    def test_update_own_status(self, discovery_layer):
        """Test updating own status information."""
        # Initial values
        assert discovery_layer.own_metadata.agent_count == 0
        assert discovery_layer.own_metadata.load_factor == 0.0

        # Update values
        discovery_layer.update_own_status(agent_count=5, load_factor=0.75)

        assert discovery_layer.own_metadata.agent_count == 5
        assert discovery_layer.own_metadata.load_factor == 0.75

    def test_get_discovery_stats(self, discovery_layer):
        """Test getting discovery statistics."""
        stats = discovery_layer.get_discovery_stats()

        assert stats["own_swarm_id"] == "test_swarm"
        assert stats["own_node_name"] == "test_node"
        assert stats["discovered_swarms_count"] == 0
        assert stats["broadcast_port"] == 9998
        assert stats["api_port"] == 8000
        assert stats["is_running"] is False
        assert "local_ip" in stats

    def test_get_discovered_swarms_empty(self, discovery_layer):
        """Test getting discovered swarms when none exist."""
        swarms = discovery_layer.get_discovered_swarms()
        assert isinstance(swarms, list)
        assert len(swarms) == 0

    def test_get_swarm_by_id_not_found(self, discovery_layer):
        """Test getting swarm by ID when it doesn't exist."""
        result = discovery_layer.get_swarm_by_id("nonexistent")
        assert result is None

    @patch('brain_swarm.discovery.socket.socket')
    def test_broadcast_message_creation(self, mock_socket_class, discovery_layer):
        """Test broadcast message creation."""
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket

        discovery_layer.broadcast_socket = mock_socket
        discovery_layer._send_broadcast()

        # Verify socket sendto was called
        assert mock_socket.sendto.called

        # Get the data that was sent
        call_args = mock_socket.sendto.call_args
        sent_data = call_args[0][0]
        broadcast_addr = call_args[0][1]

        # Parse the JSON data
        import json
        message = json.loads(sent_data.decode('utf-8'))

        assert message["type"] == "swarm_announcement"
        assert "timestamp" in message
        assert "metadata" in message

        metadata = message["metadata"]
        assert metadata["swarm_id"] == "test_swarm"
        assert metadata["node_name"] == "test_node"
        assert metadata["port"] == 9998
        assert metadata["api_port"] == 8000

        # Verify broadcast address
        assert broadcast_addr == ('<broadcast>', 9998)

    def test_process_broadcast_valid(self, discovery_layer):
        """Test processing a valid broadcast message."""
        # Create a broadcast message
        other_metadata = SwarmMetadata(
            swarm_id="other_swarm",
            node_name="other_node",
            host="192.168.1.101",
            port=9999,
            api_port=8001,
            capabilities=["coordination"],
            agent_count=2,
            last_seen=time.time()
        )

        message = {
            "type": "swarm_announcement",
            "timestamp": time.time(),
            "metadata": other_metadata.to_dict()
        }

        data = json.dumps(message).encode('utf-8')
        addr = ("192.168.1.101", 9999)

        # Process the broadcast
        discovery_layer._process_broadcast(data, addr)

        # Verify the swarm was added to discovered_swarms
        assert len(discovery_layer.discovered_swarms) == 1
        discovered = list(discovery_layer.discovered_swarms.values())[0]
        assert discovered.swarm_id == "other_swarm"
        assert discovered.node_name == "other_node"
        assert discovered.host == "192.168.1.101"
        assert discovered.api_port == 8001

    def test_process_broadcast_own_message(self, discovery_layer):
        """Test that own broadcast messages are ignored."""
        message = {
            "type": "swarm_announcement",
            "timestamp": time.time(),
            "metadata": discovery_layer.own_metadata.to_dict()
        }

        data = json.dumps(message).encode('utf-8')
        addr = (discovery_layer.local_ip, discovery_layer.broadcast_port)

        initial_count = len(discovery_layer.discovered_swarms)
        discovery_layer._process_broadcast(data, addr)

        # Should not have added own swarm
        assert len(discovery_layer.discovered_swarms) == initial_count

    def test_process_broadcast_invalid_json(self, discovery_layer):
        """Test processing invalid JSON broadcast."""
        invalid_data = b"invalid json data"
        addr = ("192.168.1.100", 9999)

        initial_count = len(discovery_layer.discovered_swarms)
        discovery_layer._process_broadcast(invalid_data, addr)

        # Should not have added anything
        assert len(discovery_layer.discovered_swarms) == initial_count

    def test_process_broadcast_wrong_type(self, discovery_layer):
        """Test processing broadcast with wrong message type."""
        message = {
            "type": "wrong_type",
            "timestamp": time.time(),
            "metadata": {}
        }

        data = json.dumps(message).encode('utf-8')
        addr = ("192.168.1.100", 9999)

        initial_count = len(discovery_layer.discovered_swarms)
        discovery_layer._process_broadcast(data, addr)

        # Should not have added anything
        assert len(discovery_layer.discovered_swarms) == initial_count

    def test_cleanup_stale_swarms(self, discovery_layer):
        """Test cleanup of stale swarm entries."""
        # Add a fresh swarm
        fresh_metadata = SwarmMetadata(
            swarm_id="fresh_swarm",
            node_name="fresh_node",
            host="192.168.1.102",
            port=9999,
            api_port=8002,
            capabilities=[],
            agent_count=0,
            last_seen=time.time()
        )
        discovery_layer.discovered_swarms[fresh_metadata.unique_id] = fresh_metadata

        # Add a stale swarm
        stale_metadata = SwarmMetadata(
            swarm_id="stale_swarm",
            node_name="stale_node",
            host="192.168.1.103",
            port=9999,
            api_port=8003,
            capabilities=[],
            agent_count=0,
            last_seen=time.time() - 10  # 10 seconds ago
        )
        discovery_layer.discovered_swarms[stale_metadata.unique_id] = stale_metadata

        assert len(discovery_layer.discovered_swarms) == 2

        # Set short timeout and run cleanup
        discovery_layer.discovery_timeout = 5.0  # 5 seconds
        discovery_layer._cleanup_stale_swarms()

        # Should only have the fresh swarm left
        assert len(discovery_layer.discovered_swarms) == 1
        remaining = list(discovery_layer.discovered_swarms.values())[0]
        assert remaining.swarm_id == "fresh_swarm"

    def test_get_swarm_by_id(self, discovery_layer):
        """Test getting swarm by ID."""
        metadata = SwarmMetadata(
            swarm_id="target_swarm",
            node_name="target_node",
            host="192.168.1.104",
            port=9999,
            api_port=8004,
            capabilities=[],
            agent_count=0,
            last_seen=time.time()
        )
        discovery_layer.discovered_swarms[metadata.unique_id] = metadata

        # Find by swarm_id
        result = discovery_layer.get_swarm_by_id("target_swarm")
        assert result is not None
        assert result.swarm_id == "target_swarm"
        assert result.node_name == "target_node"

        # Try non-existent ID
        result = discovery_layer.get_swarm_by_id("nonexistent")
        assert result is None

    def test_discovery_callbacks(self, discovery_layer):
        """Test discovery callbacks."""
        discovered_callback = Mock()
        lost_callback = Mock()

        discovery_layer.set_discovery_callbacks(
            on_discovered=discovered_callback,
            on_lost=lost_callback
        )

        # Create metadata for a new swarm
        new_metadata = SwarmMetadata(
            swarm_id="callback_test_swarm",
            node_name="callback_node",
            host="192.168.1.105",
            port=9999,
            api_port=8005,
            capabilities=[],
            agent_count=0,
            last_seen=time.time()
        )

        # Simulate discovering new swarm
        discovery_layer._update_discovered_swarm(new_metadata)

        # Verify callback was called
        discovered_callback.assert_called_once()
        args = discovered_callback.call_args[0]
        assert args[0].swarm_id == "callback_test_swarm"

        # Simulate swarm going stale
        new_metadata.last_seen = time.time() - 10
        discovery_layer.discovery_timeout = 5.0
        discovery_layer._cleanup_stale_swarms()

        # Verify lost callback was called
        lost_callback.assert_called_once()
        args = lost_callback.call_args[0]
        assert args[0].swarm_id == "callback_test_swarm"


class TestDiscoveryLayerIntegration:
    """Integration tests for DiscoveryLayer."""

    def test_create_discovery_layer(self):
        """Test the convenience function for creating discovery layer."""
        discovery = create_discovery_layer(
            swarm_id="integration_test",
            node_name="integration_node",
            broadcast_port=9997,
            api_port=8001
        )

        assert discovery.swarm_id == "integration_test"
        assert discovery.node_name == "integration_node"
        assert discovery.broadcast_port == 9997
        assert discovery.api_port == 8001

    @patch('brain_swarm.discovery.socket.socket')
    def test_start_stop_lifecycle(self, mock_socket_class, discovery_layer):
        """Test the start/stop lifecycle of discovery layer."""
        mock_broadcast_socket = MagicMock()
        mock_listen_socket = MagicMock()
        mock_socket_class.side_effect = [mock_broadcast_socket, mock_listen_socket]

        # Start discovery
        discovery_layer.start()

        # Verify sockets were created
        assert discovery_layer.broadcast_socket is not None
        assert discovery_layer.listen_socket is not None
        assert discovery_layer.running is True

        # Stop discovery
        discovery_layer.stop()

        # Verify cleanup
        assert discovery_layer.running is False
        mock_broadcast_socket.close.assert_called_once()
        mock_listen_socket.close.assert_called_once()

    def test_unique_id_generation(self):
        """Test that unique IDs are generated consistently."""
        metadata1 = SwarmMetadata(
            swarm_id="test_swarm",
            node_name="node1",
            host="192.168.1.100",
            port=9999,
            api_port=8000,
            capabilities=[],
            agent_count=0,
            last_seen=time.time()
        )

        metadata2 = SwarmMetadata(
            swarm_id="test_swarm",
            node_name="node1",
            host="192.168.1.100",
            port=9999,
            api_port=8000,
            capabilities=[],
            agent_count=0,
            last_seen=time.time()
        )

        # Same parameters should generate same unique ID
        assert metadata1.unique_id == metadata2.unique_id

        metadata3 = SwarmMetadata(
            swarm_id="different_swarm",
            node_name="node1",
            host="192.168.1.100",
            port=9999,
            api_port=8000,
            capabilities=[],
            agent_count=0,
            last_seen=time.time()
        )

        # Different swarm_id should generate different unique ID
        assert metadata1.unique_id != metadata3.unique_id