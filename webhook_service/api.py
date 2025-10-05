"""
FastAPI endpoints for webhook service.
"""

from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
import time

from ..core.base import logger
from ..observability.metrics import prometheus_metrics
from ..observability.tracing import tracing_manager, get_correlation_id
from ..security.auth import require_api_key
from .webhook_service import webhook_service

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/github")
async def github_webhook(
    request: Request,
    current_user: dict = Depends(require_api_key)
):
    """Handle GitHub webhooks"""
    return await _process_webhook(request, "github")


@router.post("/jira")
async def jira_webhook(
    request: Request,
    current_user: dict = Depends(require_api_key)
):
    """Handle Jira webhooks"""
    return await _process_webhook(request, "jira")


@router.post("/servicenow")
async def servicenow_webhook(
    request: Request,
    current_user: dict = Depends(require_api_key)
):
    """Handle ServiceNow webhooks"""
    return await _process_webhook(request, "servicenow")


@router.post("/prometheus")
async def prometheus_webhook(
    request: Request,
    current_user: dict = Depends(require_api_key)
):
    """Handle Prometheus Alertmanager webhooks"""
    return await _process_webhook(request, "prometheus")


@router.post("/{source}")
async def generic_webhook(
    source: str,
    request: Request,
    current_user: dict = Depends(require_api_key)
):
    """Handle generic webhooks from any source"""
    return await _process_webhook(request, source)


async def _process_webhook(request: Request, source: str) -> JSONResponse:
    """Process webhook from any source"""

    correlation_id = get_correlation_id()
    start_time = time.time()

    with tracing_manager.trace_context("webhook_endpoint", tags={"source": source}):
        try:
            # Get headers
            headers = dict(request.headers)

            # Get raw body
            body = await request.body()

            # Get webhook secret from environment or config
            # In production, this should be configurable per source
            secret = request.app.state.webhook_secrets.get(source) if hasattr(request.app.state, 'webhook_secrets') else None

            # Process webhook
            incident = await webhook_service.process_webhook(source, headers, body, secret)

            # Record metrics
            processing_time = time.time() - start_time
            prometheus_metrics.record_api_request(f"/webhooks/{source}", "POST", 200, processing_time)

            if incident:
                logger.log("INFO", "WebhookAPI", f"Successfully processed {source} webhook: {incident.title}")

                return JSONResponse(
                    content={
                        "status": "processed",
                        "incident_id": incident.external_id,
                        "severity": incident.severity,
                        "correlation_id": correlation_id
                    },
                    status_code=200
                )
            else:
                # Webhook received but no incident created (normal for non-critical events)
                prometheus_metrics.record_api_request(f"/webhooks/{source}", "POST", 200, processing_time)

                return JSONResponse(
                    content={
                        "status": "received",
                        "message": "Webhook received but no incident created",
                        "correlation_id": correlation_id
                    },
                    status_code=200
                )

        except Exception as e:
            processing_time = time.time() - start_time
            prometheus_metrics.record_api_request(f"/webhooks/{source}", "POST", 500, processing_time)

            logger.log("ERROR", "WebhookAPI", f"Error processing {source} webhook: {e}")

            raise HTTPException(
                status_code=500,
                detail=f"Webhook processing failed: {str(e)}"
            )


@router.get("/health")
async def webhook_health():
    """Health check for webhook service"""
    return {
        "status": "healthy",
        "service": "webhook-service",
        "supported_sources": ["github", "jira", "servicenow", "prometheus"],
        "timestamp": time.time()
    }


@router.get("/stats")
async def webhook_stats():
    """Get webhook processing statistics"""
    # This would integrate with metrics collection
    return {
        "total_webhooks_processed": 0,  # Would be populated from metrics
        "incidents_created": 0,
        "errors": 0,
        "sources": {
            "github": {"processed": 0, "incidents": 0},
            "jira": {"processed": 0, "incidents": 0},
            "servicenow": {"processed": 0, "incidents": 0},
            "prometheus": {"processed": 0, "incidents": 0}
        }
    }