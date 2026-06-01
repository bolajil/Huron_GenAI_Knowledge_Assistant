"""
Unit test fixtures — SQLite in a temp dir, no external services required.
Env vars MUST be set before main.py is imported because init_db() runs at module level.
"""
import os
import sys
import tempfile
import pytest

_db_dir = tempfile.mkdtemp()

os.environ["DATABASE_URL"]      = ""
os.environ["SQLITE_DB_PATH"]    = os.path.join(_db_dir, "huron_unit_test.db")
os.environ["JWT_SECRET_KEY"]    = "unit-test-jwt-secret-32-bytes-xx"
os.environ["MCP_ENCRYPTION_KEY"] = "unit-test-mcp-key-32-bytes-xxxxx"
os.environ["VECTOR_BACKEND"]    = "faiss"
os.environ["REDIS_URL"]         = ""
os.environ["OPENAI_API_KEY"]    = "sk-test-placeholder"
os.environ["PINECONE_API_KEY"]  = ""

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../backend"))

from fastapi.testclient import TestClient  # noqa: E402
import main  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(main.app) as c:
        yield c


@pytest.fixture(scope="session")
def auth_headers(client):
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "root", "password": "HuronRoot2026!"},
    )
    assert resp.status_code == 200, f"Root login failed: {resp.text}"
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}
