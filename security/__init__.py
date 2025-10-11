"""
Security module for Brain Swarm
Provides authentication, authorization, and audit logging capabilities.
"""

from enum import Enum
from typing import Dict, List, Any, Optional
import json
import os
import hashlib
import secrets
import time
from datetime import datetime

class PermissionLevel(Enum):
    """Permission levels for API access"""
    VIEW_ONLY = "view_only"
    OPERATOR = "operator"
    ADMIN = "admin"

class ClientCredentials:
    """Represents authenticated client credentials"""

    def __init__(self, client_id: str, client_name: str, permission_level: PermissionLevel,
                 swarm_id: Optional[str] = None, api_key_hash: str = None):
        self.client_id = client_id
        self.client_name = client_name
        self.permission_level = permission_level
        self.swarm_id = swarm_id
        self.api_key_hash = api_key_hash
        self.created_at = time.time()
        self.last_used = time.time()

class SecurityManager:
    """Manages authentication, authorization, and audit logging"""

    def __init__(self, credentials_file: str = "credentials.json",
                 audit_log_file: str = "audit.log",
                 cert_file: Optional[str] = None,
                 key_file: Optional[str] = None):
        self.credentials_file = credentials_file
        self.audit_log_file = audit_log_file
        self.cert_file = cert_file
        self.key_file = key_file
        self.credentials_store: Dict[str, ClientCredentials] = {}
        self.audit_log_file_handle = None

        # Load existing credentials
        self._load_credentials()

        # Open audit log
        self._open_audit_log()

    def _load_credentials(self):
        """Load credentials from file"""
        if os.path.exists(self.credentials_file):
            try:
                with open(self.credentials_file, 'r') as f:
                    data = json.load(f)
                    for client_id, creds_data in data.items():
                        permission_level = PermissionLevel(creds_data['permission_level'])
                        creds = ClientCredentials(
                            client_id=client_id,
                            client_name=creds_data['client_name'],
                            permission_level=permission_level,
                            swarm_id=creds_data.get('swarm_id'),
                            api_key_hash=creds_data.get('api_key_hash')
                        )
                        self.credentials_store[client_id] = creds
            except Exception as e:
                print(f"Error loading credentials: {e}")

    def _save_credentials(self):
        """Save credentials to file"""
        data = {}
        for client_id, creds in self.credentials_store.items():
            data[client_id] = {
                'client_name': creds.client_name,
                'permission_level': creds.permission_level.value,
                'swarm_id': creds.swarm_id,
                'api_key_hash': creds.api_key_hash,
                'created_at': creds.created_at,
                'last_used': creds.last_used
            }

        with open(self.credentials_file, 'w') as f:
            json.dump(data, f, indent=2)

    def _open_audit_log(self):
        """Open audit log file"""
        try:
            self.audit_log_file_handle = open(self.audit_log_file, 'a')
        except Exception as e:
            print(f"Error opening audit log: {e}")

    def create_client_credentials(self, client_name: str, permission_level: PermissionLevel,
                                swarm_id: Optional[str] = None) -> tuple[str, str]:
        """Create new client credentials and return (client_id, api_key)"""
        client_id = f"{client_name}_{int(time.time())}"
        api_key = secrets.token_urlsafe(32)

        # Hash the API key for storage
        api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        creds = ClientCredentials(
            client_id=client_id,
            client_name=client_name,
            permission_level=permission_level,
            swarm_id=swarm_id,
            api_key_hash=api_key_hash
        )

        self.credentials_store[client_id] = creds
        self._save_credentials()

        return client_id, api_key

    def authenticate_client(self, api_key: str, client_type: str = "dashboard",
                          remote_addr: Optional[str] = None) -> Optional[ClientCredentials]:
        """Authenticate client with API key"""
        if not api_key:
            return None

        api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        # Find client by API key hash
        for creds in self.credentials_store.values():
            if creds.api_key_hash == api_key_hash:
                creds.last_used = time.time()
                self._save_credentials()
                return creds

        return None

    def authorize_action(self, client_credentials: ClientCredentials, action: str,
                        resource_type: str, resource_id: Optional[str]) -> bool:
        """Check if client is authorized for an action"""
        if not client_credentials:
            return False

        # Admin can do anything
        if client_credentials.permission_level == PermissionLevel.ADMIN:
            return True

        # Operator permissions
        if client_credentials.permission_level == PermissionLevel.OPERATOR:
            # Can control nodes and tasks, view security, but not manage credentials
            allowed_actions = [
                'start_node', 'stop_node', 'reset_node',
                'start_task', 'stop_task', 'update_task_priority', 'update_node_config',
                'inject_scenario', 'view_security_status'
            ]
            return action in allowed_actions

        # View-only permissions
        if client_credentials.permission_level == PermissionLevel.VIEW_ONLY:
            # Can only view data, no control actions
            return False

        return False

    def revoke_client_credentials(self, client_id: str) -> bool:
        """Revoke client credentials"""
        if client_id in self.credentials_store:
            del self.credentials_store[client_id]
            self._save_credentials()
            return True
        return False

    def list_clients(self) -> List[Dict[str, Any]]:
        """List all client credentials (without API keys)"""
        clients = []
        for client_id, creds in self.credentials_store.items():
            clients.append({
                'client_id': client_id,
                'client_name': creds.client_name,
                'permission_level': creds.permission_level.value,
                'swarm_id': creds.swarm_id,
                'created_at': creds.created_at,
                'last_used': creds.last_used
            })
        return clients

    def log_audit_event(self, client_id: str, client_name: str, action: str,
                       resource_type: str, resource_id: Optional[str],
                       permission_level: str, success: bool,
                       details: Dict[str, Any], ip_address: Optional[str]):
        """Log audit event"""
        if not self.audit_log_file_handle:
            return

        event = {
            'timestamp': datetime.now().isoformat(),
            'client_id': client_id,
            'client_name': client_name,
            'action': action,
            'resource_type': resource_type,
            'resource_id': resource_id,
            'permission_level': permission_level,
            'success': success,
            'details': details,
            'ip_address': ip_address
        }

        try:
            json.dump(event, self.audit_log_file_handle)
            self.audit_log_file_handle.write('\n')
            self.audit_log_file_handle.flush()
        except Exception as e:
            print(f"Error writing audit log: {e}")

    def get_security_status(self) -> Dict[str, Any]:
        """Get current security status"""
        total_clients = len(self.credentials_store)
        active_clients = sum(1 for c in self.credentials_store.values()
                           if time.time() - c.last_used < 3600)  # Active in last hour

        return {
            'total_clients': total_clients,
            'active_clients': active_clients,
            'tls_enabled': bool(self.cert_file and self.key_file),
            'audit_logging': bool(self.audit_log_file_handle),
            'last_audit_entry': datetime.now().isoformat()
        }

    def create_ssl_context(self):
        """Create SSL context for TLS/HTTPS"""
        if not self.cert_file or not self.key_file:
            return None

        try:
            import ssl
            ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            ssl_context.load_cert_chain(self.cert_file, self.key_file)
            return ssl_context
        except Exception as e:
            print(f"Error creating SSL context: {e}")
            return None

    def __del__(self):
        """Cleanup resources"""
        if self.audit_log_file_handle:
            self.audit_log_file_handle.close()