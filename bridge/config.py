"""
Configuration management for Bridge services.
"""

import os
from typing import Dict, Any, Optional
from ..core.base import logger


class BridgeConfig:
    """Configuration manager for webhook bridge services"""

    def __init__(self):
        self._config = {}
        self._load_config()

    def _load_config(self):
        """Load configuration from environment variables"""
        self._config = {
            # GitHub configuration
            'github': {
                'token': os.getenv('GITHUB_TOKEN', ''),
                'webhook_secret': os.getenv('GITHUB_WEBHOOK_SECRET', ''),
                'owner': os.getenv('GITHUB_OWNER', ''),
                'repo': os.getenv('GITHUB_REPO', '')
            },
            # Jira configuration
            'jira': {
                'url': os.getenv('JIRA_URL', ''),
                'username': os.getenv('JIRA_USERNAME', ''),
                'api_token': os.getenv('JIRA_API_TOKEN', ''),
                'webhook_secret': os.getenv('JIRA_WEBHOOK_SECRET', ''),
                'project_key': os.getenv('JIRA_PROJECT_KEY', 'ALERT')
            },
            # ServiceNow configuration
            'servicenow': {
                'instance_url': os.getenv('SERVICENOW_INSTANCE_URL', ''),
                'username': os.getenv('SERVICENOW_USERNAME', ''),
                'password': os.getenv('SERVICENOW_PASSWORD', ''),
                'access_token': os.getenv('SERVICENOW_ACCESS_TOKEN', ''),
                'assignment_group': os.getenv('SERVICENOW_ASSIGNMENT_GROUP', '')
            },
            # Redis configuration
            'redis': {
                'url': os.getenv('REDIS_URL', 'redis://localhost:6379'),
                'host': os.getenv('REDIS_HOST', 'localhost'),
                'port': int(os.getenv('REDIS_PORT', '6379')),
                'db': int(os.getenv('REDIS_DB', '0'))
            },
            # Bridge service configuration
            'bridge': {
                'host': os.getenv('BRIDGE_HOST', '0.0.0.0'),
                'port': int(os.getenv('BRIDGE_PORT', '8080')),
                'workers': int(os.getenv('BRIDGE_WORKERS', '4')),
                'log_level': os.getenv('BRIDGE_LOG_LEVEL', 'INFO'),
                'enable_polling': os.getenv('BRIDGE_ENABLE_POLLING', 'true').lower() == 'true',
                'poll_interval': int(os.getenv('BRIDGE_POLL_INTERVAL', '300'))
            }
        }

        logger.log("INFO", "BridgeConfig", "Configuration loaded successfully")

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        keys = key.split('.')
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def get_section(self, section: str) -> Dict[str, Any]:
        """Get entire configuration section"""
        return self._config.get(section, {})

    def is_enabled(self, service: str) -> bool:
        """Check if a service is enabled"""
        section = self.get_section(service)
        return bool(section.get('token') or section.get('username') or section.get('access_token'))

    def get_webhook_secret(self, service: str) -> Optional[str]:
        """Get webhook secret for a service"""
        return self.get(f"{service}.webhook_secret")

    def get_redis_url(self) -> str:
        """Get Redis URL"""
        return self.get('redis.url')


# Global configuration instance
bridge_config = BridgeConfig()