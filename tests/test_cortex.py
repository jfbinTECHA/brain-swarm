import time
import pytest
from unittest.mock import Mock, patch, AsyncMock
from cortex.cortex import KnowledgeCortex
from cortex.schemas import MemoryRecord, QueryRequest
from cortex.incident_broadcast import IncidentEvent, INCIDENT_EVENT
from cortex.api.routes import router as cortex_router


def test_ingest_and_query(tmp_path, monkeypatch):
    """Test basic knowledge ingestion and querying"""
    # Point duckdb/faiss to tmp dir if needed by env vars
    c = KnowledgeCortex()

    rec = MemoryRecord(id="r1", text="The apple grows on a tree.", metadata={"topic": "fruit"}, timestamp=time.time())
    c.store_record(rec)

    out = c.query(QueryRequest(query="Where does an apple grow?", top_k=3))
    assert len(out.hits) >= 1


def test_memory_record_creation():
    """Test creating memory records"""
    timestamp = time.time()
    rec = MemoryRecord(
        id="test_record_001",
        text="This is a test memory record about AI systems.",
        metadata={
            "topic": "ai",
            "category": "technical",
            "importance": "high"
        },
        timestamp=timestamp
    )

    assert rec.id == "test_record_001"
    assert "AI systems" in rec.text
    assert rec.metadata["topic"] == "ai"
    assert rec.timestamp == timestamp


def test_query_request_validation():
    """Test query request validation"""
    # Valid query
    req = QueryRequest(query="What is machine learning?", top_k=5)
    assert req.query == "What is machine learning?"
    assert req.top_k == 5

    # Default top_k
    req2 = QueryRequest(query="Test query")
    assert req2.top_k == 3


@pytest.mark.asyncio
async def test_incident_broadcast():
    """Test incident broadcasting functionality"""
    from cortex.incident_broadcast import broadcast_to_kilo

    incident_data = {
        "id": "incident_123",
        "title": "Test Incident",
        "severity": "critical",
        "description": "Test incident for AI processing"
    }

    # Mock the API call
    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"task_id": "task_456", "status": "accepted"}
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        with patch.dict('os.environ', {
            'BRAIN_SWARM_API_URL': 'http://localhost:8000',
            'BRAIN_SWARM_API_TOKEN': 'test_token'
        }):
            result = await broadcast_to_kilo(incident_data)

            # Verify API call was made
            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            assert 'http://localhost:8000/alerts' in call_args[0][0]
            assert call_args[0][1]['json'] == incident_data
            assert 'Authorization' in call_args[0][1]['headers']


def test_incident_event_metrics():
    """Test incident event metrics recording"""
    # Test creating incident events
    event = IncidentEvent(
        event="created",
        actor="system",
        severity="critical"
    )

    # The event should be recordable
    assert event.event == "created"
    assert event.actor == "system"
    assert event.severity == "critical"


@pytest.mark.asyncio
async def test_cortex_api_routes():
    """Test Cortex API routes"""
    from fastapi.testclient import TestClient
    from fastapi import FastAPI

    # Create test app with cortex router
    app = FastAPI()
    app.include_router(cortex_router)

    client = TestClient(app)

    # Test health endpoint
    response = client.get("/health")
    assert response.status_code == 200

    # Test metrics endpoint
    response = client.get("/metrics")
    assert response.status_code == 200

    # Test alerts endpoint (should return empty for now)
    response = client.get("/alerts")
    assert response.status_code == 200
    data = response.json()
    assert "alerts" in data


def test_knowledge_cortex_initialization():
    """Test KnowledgeCortex initialization"""
    cortex = KnowledgeCortex()

    # Should have required attributes
    assert hasattr(cortex, 'store_record')
    assert hasattr(cortex, 'query')
    assert hasattr(cortex, 'get_stats')


def test_memory_record_serialization():
    """Test memory record JSON serialization"""
    rec = MemoryRecord(
        id="test_123",
        text="Test content",
        metadata={"key": "value"},
        timestamp=1234567890.0
    )

    # Should be JSON serializable
    import json
    json_str = json.dumps(rec.dict())
    parsed = json.loads(json_str)

    assert parsed["id"] == "test_123"
    assert parsed["text"] == "Test content"
    assert parsed["metadata"]["key"] == "value"


@pytest.mark.asyncio
async def test_incident_broadcast_error_handling():
    """Test error handling in incident broadcast"""
    from cortex.incident_broadcast import broadcast_to_kilo

    incident_data = {"id": "test"}

    # Mock failed API call
    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client.post.side_effect = Exception("Connection failed")
        mock_client_class.return_value = mock_client

        # Should not raise exception
        await broadcast_to_kilo(incident_data)

        # API call should still have been attempted
        mock_client.post.assert_called_once()


def test_cortex_memory_operations():
    """Test cortex memory operations"""
    cortex = KnowledgeCortex()

    # Test storing multiple records
    records = [
        MemoryRecord(id="rec1", text="First memory", metadata={"type": "test"}, timestamp=time.time()),
        MemoryRecord(id="rec2", text="Second memory", metadata={"type": "test"}, timestamp=time.time()),
        MemoryRecord(id="rec3", text="Third memory", metadata={"type": "reference"}, timestamp=time.time())
    ]

    for rec in records:
        cortex.store_record(rec)

    # Query for test records
    results = cortex.query(QueryRequest(query="test", top_k=5))
    assert len(results.hits) >= 1

    # Query for reference records
    results = cortex.query(QueryRequest(query="reference", top_k=5))
    assert len(results.hits) >= 1


def test_incident_event_labels():
    """Test incident event label generation"""
    # Test different event types
    events = [
        ("created", "system", "critical"),
        ("resolved", "user", "high"),
        ("updated", "webhook", "medium"),
        ("escalated", "ai", "low")
    ]

    for event_type, actor, severity in events:
        event = IncidentEvent(
            event=event_type,
            actor=actor,
            severity=severity
        )

        # Should create valid Prometheus labels
        labels = {
            "event": event.event,
            "actor": event.actor,
            "severity": event.severity
        }

        assert all(isinstance(v, str) for v in labels.values())


@pytest.mark.asyncio
async def test_cortex_api_error_handling():
    """Test error handling in Cortex API"""
    from fastapi.testclient import TestClient
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(cortex_router)

    client = TestClient(app)

    # Test invalid endpoints
    response = client.get("/nonexistent")
    assert response.status_code == 404

    # Test invalid request data
    response = client.post("/alerts", json={"invalid": "data"})
    # Should handle gracefully (implementation dependent)
    assert response.status_code in [200, 400, 422]


def test_memory_record_metadata_filtering():
    """Test filtering memory records by metadata"""
    cortex = KnowledgeCortex()

    # Store records with different metadata
    records = [
        MemoryRecord(id="ai_1", text="AI content 1", metadata={"domain": "ai", "level": "basic"}, timestamp=time.time()),
        MemoryRecord(id="ai_2", text="AI content 2", metadata={"domain": "ai", "level": "advanced"}, timestamp=time.time()),
        MemoryRecord(id="web_1", text="Web content", metadata={"domain": "web", "level": "basic"}, timestamp=time.time())
    ]

    for rec in records:
        cortex.store_record(rec)

    # Query should find relevant records
    results = cortex.query(QueryRequest(query="AI", top_k=5))
    assert len(results.hits) >= 2  # Should find both AI records

    results = cortex.query(QueryRequest(query="web", top_k=5))
    assert len(results.hits) >= 1  # Should find web record


def test_cortex_stats_reporting():
    """Test cortex statistics reporting"""
    cortex = KnowledgeCortex()

    # Add some data
    rec = MemoryRecord(id="stats_test", text="Test for stats", metadata={}, timestamp=time.time())
    cortex.store_record(rec)

    # Should be able to get stats
    stats = cortex.get_stats()
    assert isinstance(stats, dict)
    assert "total_records" in stats or "record_count" in stats  # Implementation dependent


@pytest.mark.asyncio
async def test_incident_broadcast_with_attachments():
    """Test incident broadcast with file attachments"""
    from cortex.incident_broadcast import broadcast_to_kilo

    incident_data = {
        "id": "incident_with_attachment",
        "title": "Incident with logs",
        "severity": "high",
        "description": "Incident with attached log files",
        "attachments": [
            {"name": "error.log", "content": "Error details..."},
            {"name": "metrics.json", "content": '{"cpu": 95}'}
        ]
    }

    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"task_id": "task_789", "status": "accepted"}
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        await broadcast_to_kilo(incident_data)

        # Verify attachments were included in the request
        call_args = mock_client.post.call_args
        payload = call_args[0][1]['json']
        assert 'attachments' in payload
        assert len(payload['attachments']) == 2