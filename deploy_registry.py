#!/usr/bin/env python3
"""
Registry Deployment Script

Automated deployment and management script for the Brain Swarm Federation Registry.
Supports development, staging, and production deployments with security best practices.
"""

import argparse
import subprocess
import sys
import os
import json
import secrets
from pathlib import Path
from typing import Dict, Any, Optional

class RegistryDeployer:
    """Registry deployment and management tool."""

    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file or "registry_config.json"
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load deployment configuration."""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                return json.load(f)

        # Default configuration
        return {
            "registry": {
                "host": "0.0.0.0",
                "port": 8001,
                "workers": 1,
                "ssl": {
                    "enabled": False,
                    "cert_file": "cert.pem",
                    "key_file": "key.pem"
                }
            },
            "security": {
                "admin_key_file": "admin_key.txt",
                "generate_admin_key": True,
                "rate_limit_default": 100
            },
            "deployment": {
                "environment": "development",
                "log_level": "info",
                "auto_cleanup": True,
                "cleanup_interval": 300
            }
        }

    def _save_config(self):
        """Save current configuration."""
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)

    def generate_admin_key(self) -> str:
        """Generate and save admin API key."""
        admin_key = secrets.token_urlsafe(32)
        key_file = self.config["security"]["admin_key_file"]

        with open(key_file, 'w') as f:
            f.write(admin_key)

        # Set restrictive permissions
        os.chmod(key_file, 0o600)

        print(f"🔑 Admin API key generated and saved to {key_file}")
        print(f"⚠️  Key: {admin_key}")
        print("   Store this key securely and delete from logs!")

        return admin_key

    def generate_ssl_certificates(self):
        """Generate self-signed SSL certificates."""
        cert_file = self.config["registry"]["ssl"]["cert_file"]
        key_file = self.config["registry"]["ssl"]["key_file"]

        if os.path.exists(cert_file) or os.path.exists(key_file):
            print("SSL certificates already exist. Skipping generation.")
            return

        print("🔐 Generating self-signed SSL certificates...")

        # Generate private key and certificate
        cmd = [
            "openssl", "req", "-x509", "-newkey", "rsa:4096",
            "-keyout", key_file, "-out", cert_file, "-days", "365",
            "-nodes", "-subj", "/C=US/ST=State/L=City/O=BrainSwarm/CN=registry.localhost"
        ]

        try:
            subprocess.run(cmd, check=True, capture_output=True)
            os.chmod(key_file, 0o600)
            print(f"✅ SSL certificates generated: {cert_file}, {key_file}")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to generate SSL certificates: {e}")
            sys.exit(1)

    def check_dependencies(self):
        """Check if required dependencies are installed."""
        required_packages = ["fastapi", "uvicorn", "aiohttp"]

        print("🔍 Checking dependencies...")
        missing = []

        for package in required_packages:
            try:
                __import__(package.replace("-", "_"))
            except ImportError:
                missing.append(package)

        if missing:
            print(f"❌ Missing dependencies: {', '.join(missing)}")
            print("Install with: pip install fastapi uvicorn aiohttp")
            sys.exit(1)

        print("✅ All dependencies available")

    def deploy_development(self):
        """Deploy registry in development mode."""
        print("🚀 Deploying registry in development mode...")

        self.check_dependencies()

        if self.config["security"]["generate_admin_key"]:
            self.generate_admin_key()

        # Build uvicorn command
        cmd = [
            sys.executable, "-m", "uvicorn",
            "brain_swarm.federation_registry:app",
            "--host", self.config["registry"]["host"],
            "--port", str(self.config["registry"]["port"]),
            "--reload",
            "--log-level", self.config["deployment"]["log_level"]
        ]

        if self.config["registry"]["ssl"]["enabled"]:
            self.generate_ssl_certificates()
            cmd.extend([
                "--ssl-certfile", self.config["registry"]["ssl"]["cert_file"],
                "--ssl-keyfile", self.config["registry"]["ssl"]["key_file"]
            ])

        print(f"📡 Starting registry on {self.config['registry']['host']}:{self.config['registry']['port']}")
        print(f"Command: {' '.join(cmd)}")

        try:
            subprocess.run(cmd)
        except KeyboardInterrupt:
            print("\n🛑 Registry stopped")

    def deploy_production(self):
        """Deploy registry in production mode."""
        print("🚀 Deploying registry in production mode...")

        self.check_dependencies()

        if self.config["security"]["generate_admin_key"]:
            self.generate_admin_key()

        # Build uvicorn command for production
        cmd = [
            sys.executable, "-m", "uvicorn",
            "brain_swarm.federation_registry:app",
            "--host", self.config["registry"]["host"],
            "--port", str(self.config["registry"]["port"]),
            "--workers", str(self.config["registry"]["workers"]),
            "--log-level", self.config["deployment"]["log_level"]
        ]

        if self.config["registry"]["ssl"]["enabled"]:
            self.generate_ssl_certificates()
            cmd.extend([
                "--ssl-certfile", self.config["registry"]["ssl"]["cert_file"],
                "--ssl-keyfile", self.config["registry"]["ssl"]["key_file"]
            ])

        print(f"🏭 Starting production registry on {self.config['registry']['host']}:{self.config['registry']['port']}")
        print(f"Workers: {self.config['registry']['workers']}")

        try:
            subprocess.run(cmd)
        except KeyboardInterrupt:
            print("\n🛑 Registry stopped")

    def create_systemd_service(self):
        """Create systemd service file for production deployment."""
        service_content = f"""[Unit]
Description=Brain Swarm Federation Registry
After=network.target

[Service]
Type=simple
User={os.getenv('USER', 'www-data')}
WorkingDirectory={os.getcwd()}
ExecStart={sys.executable} -m uvicorn brain_swarm.federation_registry:app --host {self.config['registry']['host']} --port {self.config['registry']['port']} --workers {self.config['registry']['workers']}
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
"""

        service_file = "/etc/systemd/system/brain-swarm-registry.service"

        try:
            with open(service_file, 'w') as f:
                f.write(service_content)

            print(f"✅ Systemd service created: {service_file}")
            print("Enable with: sudo systemctl enable brain-swarm-registry")
            print("Start with: sudo systemctl start brain-swarm-registry")

        except PermissionError:
            print("❌ Permission denied. Run with sudo or create service file manually.")
            print("Service content:")
            print(service_content)

    def test_registry(self):
        """Test registry deployment."""
        import requests
        import time

        registry_url = f"http{'s' if self.config['registry']['ssl']['enabled'] else ''}://{self.config['registry']['host']}:{self.config['registry']['port']}"

        print(f"🧪 Testing registry at {registry_url}...")

        try:
            # Test health endpoint
            response = requests.get(f"{registry_url}/health", timeout=5)
            if response.status_code == 200:
                print("✅ Health check passed")
            else:
                print(f"❌ Health check failed: {response.status_code}")
                return False

            # Load admin key if available
            admin_key = None
            key_file = self.config["security"]["admin_key_file"]
            if os.path.exists(key_file):
                with open(key_file, 'r') as f:
                    admin_key = f.read().strip()

            if admin_key:
                # Test stats endpoint
                headers = {"X-API-Key": admin_key}
                response = requests.get(f"{registry_url}/stats", headers=headers, timeout=5)
                if response.status_code == 200:
                    stats = response.json()
                    print(f"✅ Stats endpoint working - {stats['active_swarms']} active swarms")
                else:
                    print(f"❌ Stats endpoint failed: {response.status_code}")

            print("✅ Registry test completed")
            return True

        except requests.RequestException as e:
            print(f"❌ Registry test failed: {e}")
            return False

    def show_config(self):
        """Display current configuration."""
        print("📋 Current Registry Configuration:")
        print(json.dumps(self.config, indent=2))

    def update_config(self, key: str, value: Any):
        """Update configuration value."""
        keys = key.split('.')
        config = self.config

        for k in keys[:-1]:
            config = config.setdefault(k, {})

        config[keys[-1]] = value
        self._save_config()
        print(f"✅ Updated {key} = {value}")


def main():
    """Main CLI interface."""
    parser = argparse.ArgumentParser(description="Brain Swarm Registry Deployment Tool")
    parser.add_argument("command", choices=[
        "deploy-dev", "deploy-prod", "test", "config", "update-config",
        "generate-key", "generate-ssl", "systemd", "check-deps"
    ], help="Deployment command")

    parser.add_argument("--config", help="Configuration file path")
    parser.add_argument("--key", help="Configuration key to update")
    parser.add_argument("--value", help="New value for configuration key")

    args = parser.parse_args()

    deployer = RegistryDeployer(args.config)

    if args.command == "deploy-dev":
        deployer.deploy_development()
    elif args.command == "deploy-prod":
        deployer.deploy_production()
    elif args.command == "test":
        success = deployer.test_registry()
        sys.exit(0 if success else 1)
    elif args.command == "config":
        deployer.show_config()
    elif args.command == "update-config":
        if not args.key or args.value is None:
            print("❌ --key and --value required for update-config")
            sys.exit(1)
        deployer.update_config(args.key, args.value)
    elif args.command == "generate-key":
        deployer.generate_admin_key()
    elif args.command == "generate-ssl":
        deployer.generate_ssl_certificates()
    elif args.command == "systemd":
        deployer.create_systemd_service()
    elif args.command == "check-deps":
        deployer.check_dependencies()


if __name__ == "__main__":
    main()