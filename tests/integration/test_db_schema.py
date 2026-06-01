"""Verify schema and seed data by querying the running backend's health + admin endpoints."""
import pytest
import requests

BASE_URL = "http://localhost:8005"


@pytest.mark.integration
def test_backend_reachable():
    resp = requests.get(f"{BASE_URL}/health", timeout=5)
    assert resp.status_code == 200


@pytest.mark.integration
def test_health_uses_postgresql():
    body = requests.get(f"{BASE_URL}/health").json()
    assert body["db"]["backend"] == "postgresql", f"Expected postgresql, got: {body['db']}"


@pytest.mark.integration
def test_health_db_ok():
    body = requests.get(f"{BASE_URL}/health").json()
    assert body["db"]["status"] == "ok"


@pytest.mark.integration
def test_health_redis_ok():
    body = requests.get(f"{BASE_URL}/health").json()
    assert body["redis"]["status"] == "ok", "Redis should be active in integration env"


@pytest.mark.integration
def test_overall_status_healthy():
    body = requests.get(f"{BASE_URL}/health").json()
    assert body["status"] == "healthy"
