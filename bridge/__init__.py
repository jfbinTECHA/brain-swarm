"""
Webhook Bridge Service - External System Integration.

This module provides webhook endpoints and ticket synchronization for:
- GitHub: Issues, PRs, Actions, Releases
- Jira: Issue tracking and project management
- ServiceNow: Incident management and IT service desk

Features:
- HMAC signature validation
- Redis event publication
- Bi-directional ticket synchronization
- Comprehensive metrics and monitoring
"""

from .webhook_service import WebhookService
from .ticket_sync import TicketSyncManager
from .validation import validate_webhook_signature
from .metrics import prometheus_metrics as bridge_metrics
from .config import bridge_config

__all__ = [
    'WebhookService',
    'TicketSyncManager',
    'validate_webhook_signature',
    'bridge_metrics',
    'bridge_config'
]