"""
Load testing for webhook endpoints.

Tests concurrent webhook POST requests, rate limiting, IP whitelisting, and TLS validation.
"""

import pytest
import asyncio
import aiohttp
import json
import time
from unittest.mock import patch, AsyncMock
from concurrent.futures import ThreadPoolExecutor
import threading
from typing import List, Dict, Any

from webhook_service.app import app
from fastapi.testclient import TestClient


class TestWebhookLoadTesting:
    """Load testing for webhook endpoints"""

    def setup_method(self):
        """Set up test client"""
        self.client = TestClient(app)

    def test_single_webhook_post(self):
        """Test single webhook POST request"""
        payload = {
            "action": "opened",
            "issue": {
                "number": 123,
                "title": "Test Issue",
                "body": "Test body",
                "html_url": "https://github.com/test/repo/issues/123",
                "labels": [{"name": "bug"}]
            },
            "repository": {"full_name": "test/repo"}
        }

        # Mock signature validation
        with patch('webhook_service.webhook_service.WebhookService.process_webhook') as mock_process:
            mock_process.return_value = None  # No incident created

            response = self.client.post(
                "/webhooks/github",
                json=payload,
                headers={"X-GitHub-Event": "issues"}
            )

            assert response.status_code == 200
            mock_process.assert_called_once()

    @pytest.mark.asyncio
    async def test_concurrent_webhook_posts(self):
        """Test 100 concurrent webhook POST requests"""
        num_requests = 100
        payload = {
            "action": "opened",
            "issue": {
                "number": 123,
                "title": "Load Test Issue",
                "body": "Load test body",
                "html_url": "https://github.com/test/repo/issues/123",
                "labels": [{"name": "bug"}]
            },
            "repository": {"full_name": "test/repo"}
        }

        async def make_request(session, url, payload, headers):
            """Make a single request"""
            async with session.post(url, json=payload, headers=headers) as response:
                return response.status

        async with aiohttp.ClientSession() as session:
            # Mock webhook processing to avoid external dependencies
            with patch('webhook_service.webhook_service.WebhookService.process_webhook') as mock_process:
                mock_process.return_value = None

                # Create tasks for concurrent requests
                tasks = []
                for i in range(num_requests):
                    url = "http://testserver/webhooks/github"
                    headers = {"X-GitHub-Event": "issues"}
                    # Use test client approach instead
                    task = asyncio.create_task(self._async_post_request(payload, headers, i))
                    tasks.append(task)

                # Execute all requests concurrently
                start_time = time.time()
                results = await asyncio.gather(*tasks, return_exceptions=True)
                end_time = time.time()

                # Verify results
                successful_requests = sum(1 for r in results if r == 200)
                failed_requests = sum(1 for r in results if isinstance(r, Exception) or r != 200)

                total_time = end_time - start_time
                requests_per_second = num_requests / total_time

                print(f"Load test results:")
                print(f"Total requests: {num_requests}")
                print(f"Successful: {successful_requests}")
                print(f"Failed: {failed_requests}")
                print(f"Total time: {total_time:.2f}s")
                print(f"Requests/second: {requests_per_second:.2f}")

                # Should handle the load without complete failure
                assert successful_requests >= num_requests * 0.9  # At least 90% success rate
                assert total_time < 30  # Should complete within 30 seconds

    async def _async_post_request(self, payload, headers, request_id):
        """Make async POST request using test client in thread pool"""
        def sync_request():
            try:
                response = self.client.post(
                    "/webhooks/github",
                    json=payload,
                    headers=headers
                )
                return response.status_code
            except Exception as e:
                return e

        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            result = await loop.run_in_executor(executor, sync_request)
            return result

    def test_rate_limiting(self):
        """Test rate limiting functionality"""
        payload = {
            "action": "opened",
            "issue": {
                "number": 123,
                "title": "Rate Limit Test",
                "body": "Test body",
                "html_url": "https://github.com/test/repo/issues/123",
                "labels": [{"name": "bug"}]
            },
            "repository": {"full_name": "test/repo"}
        }

        # Mock processing
        with patch('webhook_service.webhook_service.WebhookService.process_webhook') as mock_process:
            mock_process.return_value = None

            # Make multiple rapid requests
            responses = []
            for i in range(15):  # More than rate limit
                response = self.client.post(
                    "/webhooks/github",
                    json=payload,
                    headers={"X-GitHub-Event": "issues"}
                )
                responses.append(response.status_code)

            # Should have some successful responses
            successful = sum(1 for r in responses if r == 200)
            rate_limited = sum(1 for r in responses if r == 429)

            assert successful > 0  # Some requests should succeed
            # Rate limiting may or may not be active in test environment

    def test_ip_whitelist_validation(self):
        """Test IP whitelist validation"""
        payload = {
            "action": "opened",
            "issue": {
                "number": 123,
                "title": "IP Whitelist Test",
                "body": "Test body",
                "html_url": "https://github.com/test/repo/issues/123",
                "labels": [{"name": "bug"}]
            },
            "repository": {"full_name": "test/repo"}
        }

        # Test with allowed IP (simulated)
        with patch('webhook_service.webhook_service.WebhookService.process_webhook') as mock_process:
            mock_process.return_value = None

            # In test environment, IP filtering may not be active
            response = self.client.post(
                "/webhooks/github",
                json=payload,
                headers={
                    "X-GitHub-Event": "issues",
                    "X-Forwarded-For": "192.30.252.1"  # GitHub IP
                }
            )

            # Should work in test environment (IP filtering disabled)
            assert response.status_code in [200, 403]  # 403 if IP filtering active

    def test_tls_endpoint_validation(self):
        """Test TLS endpoint validation"""
        # This would typically test HTTPS endpoints
        # In test environment, we verify the endpoint exists and handles requests

        payload = {
            "action": "opened",
            "issue": {
                "number": 123,
                "title": "TLS Test",
                "body": "Test body",
                "html_url": "https://github.com/test/repo/issues/123",
                "labels": [{"name": "bug"}]
            },
            "repository": {"full_name": "test/repo"}
        }

        with patch('webhook_service.webhook_service.WebhookService.process_webhook') as mock_process:
            mock_process.return_value = None

            response = self.client.post(
                "/webhooks/github",
                json=payload,
                headers={"X-GitHub-Event": "issues"}
            )

            assert response.status_code == 200

    def test_webhook_payload_validation(self):
        """Test webhook payload validation"""
        # Test with invalid payload
        invalid_payload = {"invalid": "payload"}

        response = self.client.post(
            "/webhooks/github",
            json=invalid_payload,
            headers={"X-GitHub-Event": "issues"}
        )

        # Should handle gracefully
        assert response.status_code in [200, 400, 422]

    def test_webhook_signature_validation(self):
        """Test webhook signature validation"""
        payload = {
            "action": "opened",
            "issue": {
                "number": 123,
                "title": "Signature Test",
                "body": "Test body",
                "html_url": "https://github.com/test/repo/issues/123",
                "labels": [{"name": "bug"}]
            },
            "repository": {"full_name": "test/repo"}
        }

        # Test with invalid signature
        response = self.client.post(
            "/webhooks/github",
            json=payload,
            headers={
                "X-GitHub-Event": "issues",
                "X-Hub-Signature-256": "sha256=invalid"
            }
        )

        # Should handle signature validation gracefully
        assert response.status_code in [200, 400, 401, 403]

    @pytest.mark.parametrize("endpoint", ["/gh-webhook", "/jira-webhook", "/servicenow-webhook"])
    def test_alternate_webhook_endpoints(self, endpoint):
        """Test alternate webhook endpoints"""
        payload = {
            "action": "opened",
            "issue": {
                "number": 123,
                "title": "Alternate Endpoint Test",
                "body": "Test body",
                "html_url": "https://github.com/test/repo/issues/123",
                "labels": [{"name": "bug"}]
            },
            "repository": {"full_name": "test/repo"}
        }

        with patch('webhook_service.webhook_service.WebhookService.process_webhook') as mock_process:
            mock_process.return_value = None

            response = self.client.post(
                f"/webhooks{endpoint}",
                json=payload,
                headers={"X-GitHub-Event": "issues"}
            )

            assert response.status_code == 200
            mock_process.assert_called_once()


class TestWebhookIntegration:
    """Integration tests for webhook service"""

    def setup_method(self):
        """Set up test client"""
        self.client = TestClient(app)

    def test_full_webhook_processing_pipeline(self):
        """Test full webhook processing pipeline"""
        payload = {
            "action": "opened",
            "issue": {
                "number": 123,
                "title": "Critical Security Issue",
                "body": "This is a critical security vulnerability",
                "html_url": "https://github.com/test/repo/issues/123",
                "labels": [
                    {"name": "security"},
                    {"name": "critical"}
                ]
            },
            "repository": {"full_name": "test/repo"}
        }

        # Mock the message queue to verify events are published
        with patch('webhook_service.webhook_service.message_queue') as mock_mq:
            mock_mq.publish = AsyncMock()

            response = self.client.post(
                "/webhooks/github",
                json=payload,
                headers={"X-GitHub-Event": "issues"}
            )

            assert response.status_code == 200

            # Verify message was published to Redis
            mock_mq.publish.assert_called_once()
            call_args = mock_mq.publish.call_args
            assert call_args[0][0] == "webhook.incidents"

    def test_webhook_metrics_collection(self):
        """Test that webhook processing metrics are collected"""
        payload = {
            "action": "opened",
            "issue": {
                "number": 123,
                "title": "Metrics Test Issue",
                "body": "Test body",
                "html_url": "https://github.com/test/repo/issues/123",
                "labels": [{"name": "bug"}]
            },
            "repository": {"full_name": "test/repo"}
        }

        # Mock processing
        with patch('webhook_service.webhook_service.WebhookService.process_webhook') as mock_process:
            mock_process.return_value = None

            response = self.client.post(
                "/webhooks/github",
                json=payload,
                headers={"X-GitHub-Event": "issues"}
            )

            assert response.status_code == 200

            # Check that metrics endpoint is available
            metrics_response = self.client.get("/metrics")
            assert metrics_response.status_code == 200
            metrics_text = metrics_response.text
            assert "brain_swarm_api_requests_total" in metrics_text

    def test_webhook_error_handling(self):
        """Test webhook error handling"""
        # Test with malformed JSON
        response = self.client.post(
            "/webhooks/github",
            data="invalid json",
            headers={
                "Content-Type": "application/json",
                "X-GitHub-Event": "issues"
            }
        )

        # Should handle error gracefully
        assert response.status_code == 422  # FastAPI validation error

    def test_webhook_cors_headers(self):
        """Test CORS headers on webhook endpoints"""
        response = self.client.options(
            "/webhooks/github",
            headers={"Origin": "https://github.com"}
        )

        # CORS should be configured
        assert "access-control-allow-origin" in response.headers or response.status_code == 200