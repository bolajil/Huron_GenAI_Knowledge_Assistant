"""
Integration test fixtures — hit the running backend container over HTTP.
Run `docker compose -f docker-compose.test.yml up -d` before these tests.
Backend is exposed on host port 8005.
"""
import pytest
import requests

BASE_URL = "http://localhost:8005"


@pytest.fixture(scope="session")
def api():
    """HTTP session pointed at the running test container."""
    s = requests.Session()
    s.base_url = BASE_URL
    return s


@pytest.fixture(scope="session")
def auth_headers(api):
    resp = api.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"username": "root", "password": "HuronRoot2026!"},
    )
    assert resp.status_code == 200, f"Root login failed: {resp.text}"
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}
