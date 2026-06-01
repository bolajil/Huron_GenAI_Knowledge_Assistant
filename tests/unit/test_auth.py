import pytest


@pytest.mark.unit
def test_login_root_succeeds(client):
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "root", "password": "HuronRoot2026!"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"
    assert body["user"]["username"] == "root"
    assert body["user"]["role"] == "root"


@pytest.mark.unit
def test_login_wrong_password(client):
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "root", "password": "wrongpassword"},
    )
    assert resp.status_code == 401


@pytest.mark.unit
def test_login_unknown_user(client):
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "nobody", "password": "anything"},
    )
    assert resp.status_code == 401


@pytest.mark.unit
def test_login_response_has_permissions(client):
    body = client.post(
        "/api/v1/auth/login",
        json={"username": "root", "password": "HuronRoot2026!"},
    ).json()
    assert "permissions" in body["user"]
    assert isinstance(body["user"]["permissions"], list)


@pytest.mark.unit
def test_validate_with_valid_token(client, auth_headers):
    resp = client.get("/api/v1/auth/validate", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["valid"] is True


@pytest.mark.unit
def test_validate_without_token_is_401(client):
    assert client.get("/api/v1/auth/validate").status_code == 401


@pytest.mark.unit
def test_validate_with_garbage_token_is_401(client):
    h = {"Authorization": "Bearer notavalidtoken"}
    assert client.get("/api/v1/auth/validate", headers=h).status_code == 401


@pytest.mark.unit
def test_me_returns_current_user(client, auth_headers):
    resp = client.get("/api/v1/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["username"] == "root"
    assert body["role"] == "root"
    assert "email" in body


@pytest.mark.unit
def test_me_without_token_is_401(client):
    assert client.get("/api/v1/auth/me").status_code == 401


@pytest.mark.unit
def test_logout_blacklists_token(client):
    login = client.post(
        "/api/v1/auth/login",
        json={"username": "root", "password": "HuronRoot2026!"},
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    assert client.post("/api/v1/auth/logout", headers=headers).status_code == 200
    assert client.get("/api/v1/auth/validate", headers=headers).status_code == 401
