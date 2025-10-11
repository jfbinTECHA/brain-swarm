"""
Command Line Interface for Brain Swarm

Provides CLI commands for running, managing, and monitoring Brain Swarm instances.
"""

import typer
from typing import Optional
import uvicorn
from pathlib import Path
import sys
import os

# Add the parent directory to the path so we can import brain_swarm
sys.path.insert(0, str(Path(__file__).parent.parent))

from brain_swarm.coordination.coordinator import SwarmCoordinator
from brain_swarm.dashboard.dashboard import BrainSwarmDashboard
from brain_swarm.core.base import logger

app = typer.Typer(
    name="brain-swarm",
    help="Brain Swarm - Multi-Agent Swarm Intelligence System",
    add_completion=True,
)

@app.command()
def run(
    host: str = typer.Option("0.0.0.0", help="Host to bind the server to"),
    port: int = typer.Option(8000, help="Port to bind the server to"),
    swarm_id: str = typer.Option("default", help="Swarm identifier"),
    reload: bool = typer.Option(False, help="Enable auto-reload for development"),
    workers: int = typer.Option(1, help="Number of worker processes"),
):
    """Start the Brain Swarm API server"""
    typer.echo(f"🚀 Starting Brain Swarm server on {host}:{port}")

    # Set environment variables for the swarm
    os.environ["BRAIN_SWARM_NODE_NAME"] = swarm_id
    os.environ["BRAIN_SWARM_DASHBOARD_PORT"] = str(port)

    # Import here to avoid circular imports
    from brain_swarm.api.main import app as fastapi_app

    uvicorn.run(
        "brain_swarm.api.main:app",
        host=host,
        port=port,
        reload=reload,
        workers=workers,
        log_level="info"
    )

@app.command()
def dashboard(
    port: int = typer.Option(3000, help="Port for the dashboard"),
    host: str = typer.Option("localhost", help="Host for the dashboard"),
    swarm_url: str = typer.Option("http://localhost:8000", help="Brain Swarm API URL"),
):
    """Start the Brain Swarm dashboard"""
    typer.echo(f"📊 Starting Brain Swarm dashboard on http://{host}:{port}")
    typer.echo(f"🔗 Connected to Brain Swarm API: {swarm_url}")

    # For now, just show a message - dashboard would be implemented separately
    typer.echo("Dashboard functionality would be implemented here")
    typer.echo("Use the API server for programmatic access")

@app.command()
def test(
    verbose: bool = typer.Option(False, "-v", help="Verbose output"),
    coverage: bool = typer.Option(False, help="Run with coverage"),
    pattern: str = typer.Option("brain_swarm/tests", help="Test path pattern"),
    frontend: bool = typer.Option(False, help="Run frontend tests instead of backend"),
    unit_only: bool = typer.Option(False, help="Run only unit tests"),
    integration_only: bool = typer.Option(False, help="Run only integration tests"),
    markers: str = typer.Option("", help="Pytest markers to filter tests"),
):
    """Run the test suite"""
    import subprocess
    import sys

    if frontend:
        # Run frontend tests
        cmd = ["npm", "test"]
        if not verbose:
            cmd.append("--watchAll=false")
        if coverage:
            cmd.append("--coverage")

        typer.echo(f"🧪 Running frontend tests: {' '.join(cmd)}")
        os.chdir("src")  # Frontend code is in src/
        result = subprocess.run(cmd, cwd="src")
    else:
        # Run backend tests
        cmd = [sys.executable, "-m", "pytest", pattern]

        if verbose:
            cmd.append("-v")
        if coverage:
            cmd.extend(["--cov=brain_swarm", "--cov-report=html", "--cov-report=term-missing"])
        if unit_only:
            cmd.extend(["-m", "unit"])
        elif integration_only:
            cmd.extend(["-m", "integration"])
        elif markers:
            cmd.extend(["-m", markers])

        typer.echo(f"🧪 Running backend tests: {' '.join(cmd)}")
        result = subprocess.run(cmd)

    sys.exit(result.returncode)

@app.command()
def test_frontend(
    coverage: bool = typer.Option(False, help="Run with coverage"),
    watch: bool = typer.Option(False, help="Run in watch mode"),
    pattern: str = typer.Option("", help="Test file pattern"),
):
    """Run frontend tests specifically"""
    import subprocess
    import sys

    cmd = ["npm", "test"]

    if not watch:
        cmd.append("--watchAll=false")
    if coverage:
        cmd.append("--coverage")
    if pattern:
        cmd.extend(["--testPathPattern", pattern])

    typer.echo(f"🧪 Running frontend tests: {' '.join(cmd)}")
    os.chdir("src")
    result = subprocess.run(cmd, cwd="src")
    sys.exit(result.returncode)

@app.command()
def test_coverage(
    report: bool = typer.Option(True, help="Generate coverage report"),
    html: bool = typer.Option(False, help="Generate HTML coverage report"),
    fail_under: int = typer.Option(80, help="Fail if coverage below threshold"),
):
    """Run tests with coverage analysis"""
    import subprocess
    import sys

    # Run backend tests with coverage
    cmd = [
        sys.executable, "-m", "pytest",
        "brain_swarm/tests",
        f"--cov=brain_swarm",
        f"--cov-fail-under={fail_under}",
        "--cov-report=term-missing"
    ]

    if html:
        cmd.append("--cov-report=html")

    typer.echo(f"📊 Running coverage analysis: {' '.join(cmd)}")
    result = subprocess.run(cmd)

    if result.returncode == 0:
        typer.echo("✅ Coverage requirements met!")
    else:
        typer.echo("❌ Coverage requirements not met!")

    # Run frontend tests with coverage
    typer.echo("🧪 Running frontend coverage...")
    os.chdir("src")
    frontend_cmd = ["npm", "test", "--watchAll=false", "--coverage"]
    frontend_result = subprocess.run(frontend_cmd, cwd="src")

    if frontend_result.returncode != 0:
        typer.echo("❌ Frontend tests failed!")
        sys.exit(frontend_result.returncode)

    sys.exit(result.returncode)

@app.command()
def test_integration(
    api_url: str = typer.Option("http://localhost:8000", help="API URL for integration tests"),
    full: bool = typer.Option(False, help="Run full integration test suite"),
):
    """Run integration tests"""
    import subprocess
    import sys

    if full:
        # Check if API is running
        import requests
        try:
            response = requests.get(f"{api_url}/health", timeout=5)
            if response.status_code != 200:
                typer.echo(f"❌ API server not responding at {api_url}")
                sys.exit(1)
        except requests.exceptions.RequestException:
            typer.echo(f"❌ Cannot connect to API server at {api_url}")
            typer.echo("Make sure to start the server with 'brain-swarm run' first")
            sys.exit(1)

        typer.echo("✅ API server is running")

    # Run integration tests
    cmd = [
        sys.executable, "-m", "pytest",
        "brain_swarm/tests",
        "-m", "integration",
        "-v"
    ]

    if full:
        # Also run API integration tests
        cmd.extend(["--api-url", api_url])

    typer.echo(f"🔗 Running integration tests: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    sys.exit(result.returncode)

@app.command()
def init(
    path: Path = typer.Option(".", help="Path to initialize the project"),
    force: bool = typer.Option(False, help="Overwrite existing files"),
):
    """Initialize a new Brain Swarm project"""
    typer.echo(f"📁 Initializing Brain Swarm project at {path}")

    # Create basic directory structure
    dirs = [
        path / "config",
        path / "logs",
        path / "data",
        path / "scripts",
    ]

    for dir_path in dirs:
        dir_path.mkdir(parents=True, exist_ok=True)
        typer.echo(f"  📁 Created {dir_path}")

    # Create basic config files
    config_files = {
        path / "config" / "swarm.yaml": """# Brain Swarm Configuration
swarm:
  id: "my_swarm"
  max_agents: 10

agents:
  - type: "LanguageAgent"
    count: 2
  - type: "VisionAgent"
    count: 1

memory:
  working_memory_size: 100
  long_term_memory_size: 1000
""",
        path / ".env": """# Brain Swarm Environment Configuration
BRAIN_SWARM_MODE=development
BRAIN_SWARM_NODE_NAME=my_swarm
BRAIN_SWARM_DASHBOARD_PORT=8000
LOG_LEVEL=INFO
""",
    }

    for file_path, content in config_files.items():
        if not file_path.exists() or force:
            file_path.write_text(content)
            typer.echo(f"  📄 Created {file_path}")
        else:
            typer.echo(f"  ⚠️  Skipped {file_path} (already exists)")

    typer.echo("✅ Brain Swarm project initialized!")
    typer.echo("Run 'brain-swarm run' to start the server")

@app.command()
def version():
    """Show version information"""
    from brain_swarm import __version__, __author__, __description__
    typer.echo(f"Brain Swarm v{__version__}")
    typer.echo(f"Author: {__author__}")
    typer.echo(f"Description: {__description__}")

@app.command()
def status(
    api_url: str = typer.Option("http://localhost:8000", help="Brain Swarm API URL"),
):
    """Check the status of a Brain Swarm instance"""
    import requests

    try:
        response = requests.get(f"{api_url}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            typer.echo("✅ Brain Swarm is running")
            typer.echo(f"   Swarm ID: {data.get('swarm_id', 'unknown')}")
            typer.echo(f"   Agents: {data.get('agent_count', 0)}")
            typer.echo(f"   Active Tasks: {data.get('active_tasks', 0)}")
        else:
            typer.echo(f"❌ Brain Swarm returned status {response.status_code}")
    except requests.exceptions.RequestException as e:
        typer.echo(f"❌ Could not connect to Brain Swarm: {e}")
        typer.echo("Make sure the server is running with 'brain-swarm run'")

if __name__ == "__main__":
    app()