"""
Integration Test: Webhook → Cortex → AI Loop
"""

import pytest, asyncio, httpx

@pytest.mark.asyncio
async def test_webhook_ingest():
    async with httpx.AsyncClient() as client:
        res = await client.post("http://localhost:8000/gh-webhook", json={"action": "opened", "issue": {"title": "test incident"}})
        assert res.status_code == 200