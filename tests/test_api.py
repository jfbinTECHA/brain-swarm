import requests
import pytest

API_BASE = "http://localhost:8001"

def test_ping():
    """Test API ping endpoint"""
    response = requests.get(f"{API_BASE}/ping")
    assert response.status_code == 200
    data = response.json()
    assert "redis" in data
    assert "duckdb_path" in data

def test_metrics():
    """Test Prometheus metrics endpoint"""
    response = requests.get(f"{API_BASE}/metrics")
    assert response.status_code == 200
    assert "prometheus" in response.text.lower()

if __name__ == "__main__":
    pytest.main([__file__])