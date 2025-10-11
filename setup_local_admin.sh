#!/bin/bash

# Setup script for Local Admin environment

echo "Updating package list..."
sudo apt update

echo "Installing system dependencies..."
sudo apt install -y python3 python3-venv python3-pip ripgrep fzf openssh-client jq

echo "Creating /opt/local-admin directory..."
sudo mkdir -p /opt/local-admin

echo "Changing to /opt/local-admin..."
cd /opt/local-admin

echo "Setting up Python virtual environment..."
python3 -m venv .venv

echo "Activating virtual environment..."
source .venv/bin/activate

echo "Upgrading pip..."
pip install --upgrade pip

echo "Installing Python packages..."
pip install fastapi "uvicorn[standard]" sqlmodel passlib[bcrypt] "python-jose[cryptography]" jinja2 pydantic-settings psutil

echo "Installing systemd service..."
sudo cp local_admin.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable local-admin
sudo systemctl start local-admin

echo "Setup complete!"
echo ""
echo "The Local Admin Panel is now running at http://localhost:8060"
echo "First-time admin credentials: admin / admin (change ASAP in /users)"
echo ""
echo "To check status: sudo systemctl status local-admin"
echo "To restart: sudo systemctl restart local-admin"
echo "To stop: sudo systemctl stop local-admin"
echo ""
echo "For remote access via SSH tunnel:"
echo "ssh -L 8060:127.0.0.1:8060 yourserver"
echo "Then open http://localhost:8060 on your local machine"
echo ""
echo "For manual testing (foreground):"
echo "cd /opt/local-admin"
echo "source .venv/bin/activate"
echo "export ALLOW_REGISTRATION=true"
echo "python app.py"