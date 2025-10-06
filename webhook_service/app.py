"""
Standalone webhook service application.
"""

import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..config import settings
from ..core.base import logger
from ..observability.metrics import prometheus_metrics
from ..observability.health import health_checker
from ..observability.tracing import tracing_manager
from .api import router

# Create FastAPI app
app = FastAPI(
    title="Brain Swarm Webhook Service",
    description="Webhook service for processing external alerts and incidents",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add Prometheus monitoring
from prometheus_fastapi_instrumentator import Instrumentator
Instrumentator().instrument(app).expose(app, endpoint="/metrics")

# Include webhook router
app.include_router(router)

# Webhook secrets storage
app.state.webhook_secrets = {
    'github': os.getenv('GITHUB_WEBHOOK_SECRET', ''),
    'jira': os.getenv('JIRA_WEBHOOK_SECRET', ''),
    'servicenow': os.getenv('SERVICENOW_WEBHOOK_SECRET', ''),
}


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    try:
        logger.log("INFO", "WebhookService", "Webhook service starting up")

        # Initialize observability
        await health_checker.register_check("webhook_service", lambda: {"status": "healthy"})

        logger.log("INFO", "WebhookService", "Webhook service initialized successfully")

    except Exception as e:
        logger.log("ERROR", "WebhookService", f"Failed to initialize webhook service: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    try:
        logger.log("INFO", "WebhookService", "Webhook service shutting down")
    except Exception as e:
        logger.log("ERROR", "WebhookService", f"Error during webhook service shutdown: {e}")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Brain Swarm Webhook Service",
        "version": "1.0.0",
        "endpoints": {
            "github": "/webhooks/github",
            "gh-webhook": "/webhooks/gh-webhook",
            "jira": "/webhooks/jira",
            "jira-webhook": "/webhooks/jira-webhook",
            "servicenow": "/webhooks/servicenow",
            "servicenow-webhook": "/webhooks/servicenow-webhook",
            "prometheus": "/webhooks/prometheus",
            "generic": "/webhooks/{source}",
            "health": "/health",
            "metrics": "/metrics",
            "docs": "/docs"
        },
        "supported_sources": ["github", "jira", "servicenow", "prometheus"]
    }


if __name__ == "__main__":
    uvicorn.run(
        app,
        host=settings.node.host,
        port=int(os.getenv('WEBHOOK_SERVICE_PORT', '8080')),
        log_level="info"
    )