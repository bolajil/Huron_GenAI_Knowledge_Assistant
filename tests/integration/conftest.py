"""
Integration test fixtures — hit the running backend over HTTP.
In CI: backend runs on the port set by BACKEND_URL env var (default 8004).
Locally with docker compose: set BACKEND_URL=http://localhost:8005 to override.
"""
import os
import pytest
import requests

BASE_URL = os.getenv("BACKEND_URL", "http://localhost:8004")


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
