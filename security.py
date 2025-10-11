#!/usr/bin/env python3
"""
Security Module for Real-Time Swarm Monitor
Provides TLS/HTTPS, API key authentication, permission levels, and audit logging
"""

import ssl
import secrets
import hashlib
import json
import time
import logging
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, asdict
from enum import Enum
import os
from pathlib import Path


class PermissionLevel(Enum):
    """Permission levels for swarm monitor access"""
    VIEW_ONLY = "view_only"      # Read-only access to monitoring data
    OPERATOR = "operator"        # Can execute commands and modify parameters
    ADMIN = "admin"             # Full access including system administration


@dataclass
class ClientCredentials:
    """Client authentication credentials"""
    client_id: str
    client_name: str
    api_key_hash: str
    permission_level: PermissionLevel
    swarm_id: Optional[str] = None  # For swarm-specific clients
    created_at: float = None
    last_used: float = None
    is_active: bool = True

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()
        if self.last_used is None:
            self.last_used = time.time()


@dataclass
class AuditLogEntry:
    """Audit log entry for security events and control actions"""
    timestamp: float
    client_id: str
    client_name: str
    action: str
    resource_type: str  # node, task, system, swarm, etc.
    resource_id: str
    permission_level: str
    success: bool
    details: Dict[str, Any]
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class SecurityManager:
    """Central security manager for the swarm monitor"""

    def __init__(self, credentials_file: str = "credentials.json",
                 audit_log_file: str = "audit.log",
                 cert_file: str = None,
                 key_file: str = None):
        self.credentials_file = Path(credentials_file)
        self.audit_log_file = Path(audit_log_file)
        self.cert_file = cert_file
        self.key_file = key_file

        # In-memory credential storage
        self.credentials: Dict[str, ClientCredentials] = {}
        self.api_key_to_client: Dict[str, str] = {}  # api_key -> client_id

        # Audit logging
        self.audit_logger = logging.getLogger('swarm_monitor_audit')
        self.audit_logger.setLevel(logging.INFO)

        # File handler for audit log
        audit_handler = logging.FileHandler(self.audit_log_file)
        audit_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        self.audit_logger.addHandler(audit_handler)

        # Load existing credentials
        self.load_credentials()

        # Create default admin credentials if none exist
        if not self.credentials:
            self.create_default_admin()

    def create_default_admin(self):
        """Create default admin credentials for initial setup"""
        admin_key = secrets.token_url_safe(32)
        admin_creds = ClientCredentials(
            client_id="admin",
            client_name="System Administrator",
            api_key_hash=self.hash_api_key(admin_key),
            permission_level=PermissionLevel.ADMIN
        )
        self.credentials["admin"] = admin_creds
        self.api_key_to_client[admin_key] = "admin"
        self.save_credentials()

        print("🔐 Default admin credentials created!")
        print(f"   Client ID: admin")
        print(f"   API Key: {admin_key}")
        print("   ⚠️  Please save this API key securely and change it immediately!")

    def hash_api_key(self, api_key: str) -> str:
        """Hash API key for secure storage"""
        return hashlib.sha256(api_key.encode()).hexdigest()

    def verify_api_key(self, api_key: str) -> Optional[ClientCredentials]:
        """Verify API key and return client credentials"""
        client_id = self.api_key_to_client.get(api_key)
        if not client_id:
            return None

        creds = self.credentials.get(client_id)
        if not creds or not creds.is_active:
            return None

        # Update last used timestamp
        creds.last_used = time.time()
        return creds

    def authenticate_client(self, api_key: str, client_type: str = "unknown",
                          ip_address: str = None) -> Optional[ClientCredentials]:
        """Authenticate a client and log the attempt"""
        creds = self.verify_api_key(api_key)

        # Log authentication attempt
        success = creds is not None
        self.audit_logger.info(
            f"Authentication {'successful' if success else 'failed'} "
            f"for {client_type} client from {ip_address or 'unknown'}"
        )

        if creds:
            # Log successful authentication
            self.log_audit_event(
                client_id=creds.client_id,
                client_name=creds.client_name,
                action="authenticate",
                resource_type="system",
                resource_id="authentication",
                permission_level=creds.permission_level.value,
                success=True,
                details={"client_type": client_type},
                ip_address=ip_address
            )

        return creds

    def authorize_action(self, creds: ClientCredentials, action: str,
                        resource_type: str, resource_id: str) -> bool:
        """Check if client is authorized to perform an action"""
        if not creds or not creds.is_active:
            return False

        # Define permission mappings
        action_permissions = {
            "view": {PermissionLevel.VIEW_ONLY, PermissionLevel.OPERATOR, PermissionLevel.ADMIN},
            "start_node": {PermissionLevel.OPERATOR, PermissionLevel.ADMIN},
            "stop_node": {PermissionLevel.OPERATOR, PermissionLevel.ADMIN},
            "reset_node": {PermissionLevel.OPERATOR, PermissionLevel.ADMIN},
            "start_task": {PermissionLevel.OPERATOR, PermissionLevel.ADMIN},
            "stop_task": {PermissionLevel.OPERATOR, PermissionLevel.ADMIN},
            "update_task_priority": {PermissionLevel.OPERATOR, PermissionLevel.ADMIN},
            "update_parameter": {PermissionLevel.OPERATOR, PermissionLevel.ADMIN},
            "inject_scenario": {PermissionLevel.ADMIN},
            "create_swarm": {PermissionLevel.ADMIN},
            "delete_swarm": {PermissionLevel.ADMIN},
            "system_reset": {PermissionLevel.ADMIN},
            "emergency_stop": {PermissionLevel.ADMIN}
        }

        required_permissions = action_permissions.get(action, {PermissionLevel.ADMIN})
        return creds.permission_level in required_permissions

    def log_audit_event(self, client_id: str, client_name: str, action: str,
                       resource_type: str, resource_id: str, permission_level: str,
                       success: bool, details: Dict[str, Any],
                       ip_address: str = None, user_agent: str = None):
        """Log an audit event"""
        entry = AuditLogEntry(
            timestamp=time.time(),
            client_id=client_id,
            client_name=client_name,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            permission_level=permission_level,
            success=success,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )

        # Log to file
        log_message = (
            f"AUDIT: {client_name} ({client_id}) - {action} on {resource_type}:{resource_id} - "
            f"{'SUCCESS' if success else 'FAILED'} - {json.dumps(details)}"
        )
        self.audit_logger.info(log_message)

    def create_client_credentials(self, client_name: str, permission_level: PermissionLevel,
                                swarm_id: Optional[str] = None) -> tuple[str, str]:
        """Create new client credentials and return (client_id, api_key)"""
        client_id = f"{client_name.lower().replace(' ', '_')}_{secrets.token_hex(4)}"
        api_key = secrets.token_url_safe(32)

        creds = ClientCredentials(
            client_id=client_id,
            client_name=client_name,
            api_key_hash=self.hash_api_key(api_key),
            permission_level=permission_level,
            swarm_id=swarm_id
        )

        self.credentials[client_id] = creds
        self.api_key_to_client[api_key] = client_id
        self.save_credentials()

        return client_id, api_key

    def revoke_client_credentials(self, client_id: str) -> bool:
        """Revoke client credentials"""
        if client_id not in self.credentials:
            return False

        creds = self.credentials[client_id]
        creds.is_active = False

        # Remove from api_key mapping
        api_keys_to_remove = [key for key, cid in self.api_key_to_client.items() if cid == client_id]
        for key in api_keys_to_remove:
            del self.api_key_to_client[key]

        self.save_credentials()
        return True

    def list_clients(self) -> List[Dict[str, Any]]:
        """List all client credentials (without sensitive data)"""
        return [
            {
                "client_id": creds.client_id,
                "client_name": creds.client_name,
                "permission_level": creds.permission_level.value,
                "swarm_id": creds.swarm_id,
                "created_at": creds.created_at,
                "last_used": creds.last_used,
                "is_active": creds.is_active
            }
            for creds in self.credentials.values()
        ]

    def save_credentials(self):
        """Save credentials to file"""
        data = {
            "credentials": {cid: asdict(creds) for cid, creds in self.credentials.items()},
            "api_key_mapping": self.api_key_to_client.copy()
        }

        # Remove sensitive data before saving
        for creds_data in data["credentials"].values():
            if "api_key_hash" in creds_data:
                del creds_data["api_key_hash"]  # Never save actual API keys

        with open(self.credentials_file, 'w') as f:
            json.dump(data, f, indent=2)

    def load_credentials(self):
        """Load credentials from file"""
        if not self.credentials_file.exists():
            return

        try:
            with open(self.credentials_file, 'r') as f:
                data = json.load(f)

            # Reconstruct credentials (API keys are not stored, only mappings)
            for client_id, creds_data in data.get("credentials", {}).items():
                permission_level = PermissionLevel(creds_data["permission_level"])
                creds = ClientCredentials(
                    client_id=creds_data["client_id"],
                    client_name=creds_data["client_name"],
                    api_key_hash="",  # Will be set when API key is used
                    permission_level=permission_level,
                    swarm_id=creds_data.get("swarm_id"),
                    created_at=creds_data.get("created_at", time.time()),
                    last_used=creds_data.get("last_used", time.time()),
                    is_active=creds_data.get("is_active", True)
                )
                self.credentials[client_id] = creds

            # Load API key mappings (these contain the actual keys)
            self.api_key_to_client = data.get("api_key_mapping", {})

            # Update API key hashes for loaded credentials
            for api_key, client_id in self.api_key_to_client.items():
                if client_id in self.credentials:
                    self.credentials[client_id].api_key_hash = self.hash_api_key(api_key)

        except Exception as e:
            print(f"Error loading credentials: {e}")

    def create_ssl_context(self) -> Optional[ssl.SSLContext]:
        """Create SSL context for TLS/HTTPS"""
        if not self.cert_file or not self.key_file:
            return None

        try:
            ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            ssl_context.load_cert_chain(self.cert_file, self.key_file)
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE  # For development - use proper certs in production
            return ssl_context
        except Exception as e:
            print(f"Error creating SSL context: {e}")
            return None

    def get_security_status(self) -> Dict[str, Any]:
        """Get current security status"""
        return {
            "tls_enabled": bool(self.cert_file and self.key_file and
                              Path(self.cert_file).exists() and Path(self.key_file).exists()),
            "total_clients": len(self.credentials),
            "active_clients": len([c for c in self.credentials.values() if c.is_active]),
            "admin_clients": len([c for c in self.credentials.values()
                                if c.permission_level == PermissionLevel.ADMIN and c.is_active]),
            "operator_clients": len([c for c in self.credentials.values()
                                   if c.permission_level == PermissionLevel.OPERATOR and c.is_active]),
            "view_only_clients": len([c for c in self.credentials.values()
                                    if c.permission_level == PermissionLevel.VIEW_ONLY and c.is_active]),
            "audit_log_size": self.audit_log_file.stat().st_size if self.audit_log_file.exists() else 0
        }


# Global security manager instance
security_manager = SecurityManager()