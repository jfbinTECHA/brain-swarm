#!/usr/bin/env python3
"""
UDP Broadcast Prototype for LAN Discovery

A simple standalone prototype for testing UDP-based swarm discovery on local networks.
This prototype demonstrates the core discovery mechanism used by the Brain Swarm federation.

Usage:
    # Terminal 1: Start a listener
    python lan_discovery_prototype.py listen

    # Terminal 2: Start broadcasting
    python lan_discovery_prototype.py broadcast

    # Terminal 3: Start another broadcaster with different swarm
    python lan_discovery_prototype.py broadcast --swarm-id swarm-2 --node-name node-2
"""

import socket
import threading
import time
import json
import argparse
import logging
from typing import Dict, Any, Optional
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SwarmBroadcaster:
    """Simple UDP broadcaster for swarm discovery."""

    def __init__(self, swarm_id: str = "test-swarm", node_name: str = "test-node",
                 broadcast_port: int = 9999, broadcast_interval: float = 5.0):
        self.swarm_id = swarm_id
        self.node_name = node_name
        self.broadcast_port = broadcast_port
        self.broadcast_interval = broadcast_interval

        # Network setup
        self.broadcast_address = '<broadcast>'
        self.local_ip = self._get_local_ip()

        # Socket
        self.broadcast_socket: Optional[socket.socket] = None
        self.running = False

        logger.info(f"Broadcaster initialized: {swarm_id} ({node_name}) on {self.local_ip}:{broadcast_port}")

    def _get_local_ip(self) -> str:
        """Get the local IP address."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except Exception as e:
            logger.warning(f"Could not determine local IP: {e}")
            return "127.0.0.1"

    def _setup_socket(self):
        """Setup the broadcast socket."""
        try:
            self.broadcast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self.broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            logger.debug("Broadcast socket configured")
        except Exception as e:
            logger.error(f"Failed to setup broadcast socket: {e}")
            raise

    def _create_announcement(self) -> Dict[str, Any]:
        """Create a swarm announcement message."""
        return {
            "type": "swarm_announcement",
            "timestamp": time.time(),
            "swarm_id": self.swarm_id,
            "node_name": self.node_name,
            "host": self.local_ip,
            "port": self.broadcast_port,
            "capabilities": ["discovery", "communication"],
            "status": "active",
            "version": "1.0.0-prototype"
        }

    def start(self):
        """Start broadcasting."""
        if self.running:
            logger.warning("Broadcaster already running")
            return

        logger.info(f"Starting broadcaster for {self.swarm_id}")
        self.running = True
        self._setup_socket()

        # Start broadcast thread
        broadcast_thread = threading.Thread(target=self._broadcast_loop, daemon=True)
        broadcast_thread.start()

        try:
            # Keep running until interrupted
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Stopping broadcaster...")
            self.stop()

    def stop(self):
        """Stop broadcasting."""
        self.running = False
        if self.broadcast_socket:
            self.broadcast_socket.close()
        logger.info("Broadcaster stopped")

    def _broadcast_loop(self):
        """Main broadcast loop."""
        logger.info(f"Broadcasting every {self.broadcast_interval} seconds...")

        while self.running:
            try:
                self._send_broadcast()
                time.sleep(self.broadcast_interval)
            except Exception as e:
                logger.error(f"Error in broadcast loop: {e}")
                time.sleep(1)

    def _send_broadcast(self):
        """Send a single broadcast message."""
        if not self.broadcast_socket:
            return

        try:
            announcement = self._create_announcement()
            data = json.dumps(announcement).encode('utf-8')

            self.broadcast_socket.sendto(data, (self.broadcast_address, self.broadcast_port))

            logger.info(f"Broadcast sent: {self.swarm_id} at {self.local_ip}")

        except Exception as e:
            logger.error(f"Failed to send broadcast: {e}")


class SwarmListener:
    """Simple UDP listener for swarm discovery."""

    def __init__(self, listen_port: int = 9999):
        self.listen_port = listen_port
        self.local_ip = self._get_local_ip()

        # Discovered swarms
        self.discovered_swarms: Dict[str, Dict[str, Any]] = {}

        # Socket
        self.listen_socket: Optional[socket.socket] = None
        self.running = False

        logger.info(f"Listener initialized on {self.local_ip}:{listen_port}")

    def _get_local_ip(self) -> str:
        """Get the local IP address."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except Exception as e:
            logger.warning(f"Could not determine local IP: {e}")
            return "127.0.0.1"

    def _setup_socket(self):
        """Setup the listen socket."""
        try:
            self.listen_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.listen_socket.bind(('', self.listen_port))
            self.listen_socket.settimeout(1.0)  # 1 second timeout for clean shutdown
            logger.debug("Listen socket configured")
        except Exception as e:
            logger.error(f"Failed to setup listen socket: {e}")
            raise

    def start(self):
        """Start listening."""
        if self.running:
            logger.warning("Listener already running")
            return

        logger.info("Starting listener...")
        self.running = True
        self._setup_socket()

        # Start listen thread
        listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
        listen_thread.start()

        # Start status display thread
        status_thread = threading.Thread(target=self._status_display_loop, daemon=True)
        status_thread.start()

        try:
            # Keep running until interrupted
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Stopping listener...")
            self.stop()

    def stop(self):
        """Stop listening."""
        self.running = False
        if self.listen_socket:
            self.listen_socket.close()
        logger.info("Listener stopped")

    def _listen_loop(self):
        """Main listen loop."""
        logger.info("Listening for broadcasts...")

        while self.running:
            try:
                self._listen_for_broadcasts()
            except Exception as e:
                logger.error(f"Error in listen loop: {e}")
                time.sleep(1)

    def _listen_for_broadcasts(self):
        """Listen for incoming broadcasts."""
        if not self.listen_socket:
            return

        try:
            while self.running:
                try:
                    data, addr = self.listen_socket.recvfrom(4096)
                    self._process_broadcast(data, addr)
                except socket.timeout:
                    continue  # Expected timeout
                except OSError:
                    break  # Socket closed

        except Exception as e:
            logger.error(f"Error listening for broadcasts: {e}")

    def _process_broadcast(self, data: bytes, addr: tuple):
        """Process an incoming broadcast message."""
        try:
            message = json.loads(data.decode('utf-8'))

            if message.get("type") != "swarm_announcement":
                return

            swarm_id = message.get("swarm_id")
            if not swarm_id:
                return

            # Update discovered swarms
            message["discovered_at"] = time.time()
            message["source_addr"] = addr

            was_new = swarm_id not in self.discovered_swarms
            self.discovered_swarms[swarm_id] = message

            if was_new:
                logger.info(f"Discovered new swarm: {swarm_id} at {addr[0]}:{message.get('port', 'unknown')}")
            else:
                logger.debug(f"Updated swarm: {swarm_id}")

        except json.JSONDecodeError:
            logger.debug("Received invalid JSON broadcast")
        except Exception as e:
            logger.error(f"Error processing broadcast: {e}")

    def _status_display_loop(self):
        """Display current status periodically."""
        while self.running:
            time.sleep(10)  # Display every 10 seconds

            if self.discovered_swarms:
                logger.info(f"Currently tracking {len(self.discovered_swarms)} swarm(s):")
                for swarm_id, info in self.discovered_swarms.items():
                    age = time.time() - info.get("discovered_at", 0)
                    logger.info(f"  - {swarm_id} ({info.get('node_name', 'unknown')}) - {age:.1f}s ago")
            else:
                logger.info("No swarms discovered yet")

    def get_discovered_swarms(self) -> Dict[str, Dict[str, Any]]:
        """Get currently discovered swarms."""
        return self.discovered_swarms.copy()


def main():
    """Main CLI interface."""
    parser = argparse.ArgumentParser(description="UDP Broadcast Prototype for LAN Discovery")
    parser.add_argument("mode", choices=["broadcast", "listen"],
                       help="Mode: broadcast or listen")
    parser.add_argument("--swarm-id", default="test-swarm",
                       help="Swarm ID for broadcasting (default: test-swarm)")
    parser.add_argument("--node-name", default="test-node",
                       help="Node name for broadcasting (default: test-node)")
    parser.add_argument("--port", type=int, default=9999,
                       help="UDP port for discovery (default: 9999)")
    parser.add_argument("--interval", type=float, default=5.0,
                       help="Broadcast interval in seconds (default: 5.0)")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        if args.mode == "broadcast":
            logger.info(f"Starting broadcaster: swarm={args.swarm_id}, node={args.node_name}, port={args.port}")
            broadcaster = SwarmBroadcaster(
                swarm_id=args.swarm_id,
                node_name=args.node_name,
                broadcast_port=args.port,
                broadcast_interval=args.interval
            )
            broadcaster.start()

        elif args.mode == "listen":
            logger.info(f"Starting listener on port {args.port}")
            listener = SwarmListener(listen_port=args.port)
            listener.start()

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()