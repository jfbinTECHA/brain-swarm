#!/usr/bin/env python3
"""
Startup script for the Brain Swarm Federation Operations Server

This script starts the operations server that provides real-time monitoring
and control capabilities for the federation operations platform.
"""

import subprocess
import sys
import time
import signal
import os

def start_operations_server():
    """Start the federation operations server."""
    print("🧠 Starting Brain Swarm Federation Operations Server...")

    # Check if required packages are installed
    try:
        import fastapi
        import uvicorn
        import socketio
    except ImportError:
        print("❌ Required packages not found. Installing...")
        subprocess.check_call([
            sys.executable, "-m", "pip", "install",
            "fastapi", "uvicorn", "python-socketio", "requests"
        ])

    # Start the operations server
    try:
        from federation_operations_server import socket_app

        print("✅ Starting server on http://localhost:8001")
        print("📊 Operations Platform: Open federation_operations_platform.html in your browser")
        print("🔧 Press Ctrl+C to stop the server")

        uvicorn.run(
            socket_app,
            host="0.0.0.0",
            port=8001,
            log_level="info"
        )

    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        return False

    return True

def start_federation_registry():
    """Start the federation registry (optional background service)."""
    print("📋 Starting Federation Registry...")

    try:
        # Start registry in background
        registry_process = subprocess.Popen([
            sys.executable, "-m", "uvicorn",
            "brain_swarm.federation_registry:app",
            "--host", "0.0.0.0",
            "--port", "8002",
            "--reload"
        ])

        print("✅ Registry started on http://localhost:8002")
        return registry_process

    except Exception as e:
        print(f"⚠️ Could not start registry: {e}")
        return None

if __name__ == "__main__":
    # Handle command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "--registry-only":
            registry_proc = start_federation_registry()
            if registry_proc:
                try:
                    registry_proc.wait()
                except KeyboardInterrupt:
                    registry_proc.terminate()
            sys.exit(0)
        elif sys.argv[1] == "--help":
            print("Usage:")
            print("  python start_operations_server.py              # Start operations server")
            print("  python start_operations_server.py --registry-only  # Start only registry")
            print("  python start_operations_server.py --help      # Show this help")
            sys.exit(0)

    # Start both services
    registry_proc = start_federation_registry()
    time.sleep(2)  # Give registry time to start

    success = start_operations_server()

    # Clean up registry process if it was started
    if registry_proc:
        registry_proc.terminate()

    sys.exit(0 if success else 1)