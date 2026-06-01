import pytest


@pytest.mark.unit
def test_health_returns_200(client):
    assert client.get("/health").status_code == 200


@pytest.mark.unit
def test_health_schema(client):
    body = client.get("/health").json()
    assert body["status"] == "healthy"
    assert body["db"]["status"] == "ok"
    assert body["db"]["backend"] == "sqlite"
    assert "version" in body
    assert "timestamp" in body


@pytest.mark.unit
def test_health_redis_disabled_without_url(client):
    assert client.get("/health").json()["redis"]["status"] == "disabled"


@pytest.mark.unit
def test_health_pinecone_status_present(client):
    body = client.get("/health").json()
    assert "pinecone" in body
