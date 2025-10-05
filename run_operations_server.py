#!/usr/bin/env python3
"""
Run script for the Brain Swarm Federation Operations Server

This script starts the operations server that provides real-time monitoring
and control capabilities for the Brain Swarm Federation Operations Platform.

Usage:
    python run_operations_server.py

The server will start on http://localhost:8001 with WebSocket support.
"""

import sys
import os

# Add the brain_swarm directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from federation_operations_server import app, socket_app

if __name__ == "__main__":
    print("🚀 Starting Brain Swarm Federation Operations Server...")
    print("📊 WebSocket endpoint: ws://localhost:8001/socket.io/")
    print("🌐 HTTP API endpoint: http://localhost:8001/")
    print("📱 Operations Platform: Open federation_operations_platform.html in your browser")
    print("🔐 Default admin credentials: admin / admin123")
    print()

    # Run the server
    import uvicorn
    uvicorn.run(
        socket_app,
        host="0.0.0.0",
        port=8001,
        log_level="info"
    )