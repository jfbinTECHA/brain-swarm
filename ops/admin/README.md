# Local Admin Panel

A FastAPI-based web interface for system administration with authentication, user management, SSH key monitoring, and login attempt logging.

## Features

- **Authentication**: JWT-based login with role-based access (admin/viewer)
- **User Management**: Create users, manage registrations (admin only)
- **SSH Key Monitoring**: Display fingerprints of authorized SSH keys
- **Login Attempts**: Log and display SSH authentication attempts from journalctl
- **System Dashboard**: Real-time CPU, memory, and disk usage charts
- **IP Blocking**: Block suspicious IPs using ufw or iptables

## Setup

Run the setup script:

```bash
./setup_local_admin.sh
```

This will:
- Install system dependencies
- Create Python virtual environment
- Install Python packages
- Set up systemd service for auto-startup
- Start the service

## Configuration

The admin panel can be configured via environment variables:

- `ADMIN_PANEL_PORT`: Port to run the admin panel on (default: 8060)
- `ADMIN_PANEL_SECRET`: JWT secret key for authentication (change this!)
- `ALLOW_REGISTRATION`: Allow user self-registration (default: false)
- `BRAIN_SWARM_BASE_URL`: Base URL for Brain-Swarm API integration (default: http://localhost:8000)
- `BRAIN_SWARM_API_KEY`: Optional API key for Brain-Swarm authentication

## Usage

- Access at http://localhost:8060
- Default admin: `admin` / `admin` (change immediately!)
- Create additional users via the admin panel

## Security Considerations

- **Registration**: Keep `ALLOW_REGISTRATION=false` unless self-service is needed. Rely on admin-created accounts.
- **CSRF Protection**: Consider adding CSRF tokens for POST forms if exposing beyond localhost.
- **Rate Limiting**: Add rate limiting on `/login` endpoint (e.g., via in-memory counter).
- **HTTPS**: For production, add SSL/TLS termination.
- **Firewall**: Restrict access to localhost or trusted networks.

## Remote Access

Use SSH tunneling:

```bash
ssh -L 8060:127.0.0.1:8060 yourserver
```

Then open http://localhost:8060 locally.

## Manual Testing

```bash
cd /opt/local-admin
source .venv/bin/activate
export ALLOW_REGISTRATION=true  # for testing
python app.py
```

## Service Management

```bash
sudo systemctl status local-admin
sudo systemctl restart local-admin
sudo systemctl stop local-admin
```

## Future Enhancements

- **Rich UI**: Replace simple HTML with HTMX + Tailwind for live-updating dashboards
- **Metrics**: Add `/metrics` endpoint for Prometheus with sparklines of failed attempts per hour
- **Enhanced Logging**: Parse additional auth events (PAM, key-based logins, sudo events)
- **IP Reputation**: Add IP reputation lookup using MaxMind DB or ipinfo API
- **External WebSocket Integration**: Connect to brain-swarm WebSocket streams (e.g., `ws://localhost:9000/stream?topic=logins`) for real-time event streaming across the ecosystem