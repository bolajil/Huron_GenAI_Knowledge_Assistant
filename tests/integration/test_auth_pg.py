"""Auth flow integration tests against the running backend container (PostgreSQL + Redis)."""
import pytest
import requests

BASE_URL = "http://localhost:8005"


@pytest.mark.integration
def test_login_root_succeeds():
    resp = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"username": "root", "password": "HuronRoot2026!"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert body["user"]["role"] == "root"


@pytest.mark.integration
def test_login_bad_password_rejected():
    resp = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"username": "root", "password": "wrongpassword"},
    )
    assert resp.status_code == 401


@pytest.mark.integration
def test_login_unknown_user_rejected():
    resp = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"username": "nobody", "password": "anything"},
    )
    assert resp.status_code == 401


@pytest.mark.integration
def test_validate_token(auth_headers):
    resp = requests.get(f"{BASE_URL}/api/v1/auth/validate", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["valid"] is True


@pytest.mark.integration
def test_me_returns_root(auth_headers):
    resp = requests.get(f"{BASE_URL}/api/v1/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["username"] == "root"
    assert body["role"] == "root"


@pytest.mark.integration
def test_protected_route_without_token_is_401():
    resp = requests.get(f"{BASE_URL}/api/v1/auth/me")
    assert resp.status_code == 401


@pytest.mark.integration
def test_logout_blacklists_token_in_redis():
    login = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"username": "root", "password": "HuronRoot2026!"},
    )
    token = login.json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}

    logout = requests.post(f"{BASE_URL}/api/v1/auth/logout", headers=h)
    assert logout.status_code == 200

    validate = requests.get(f"{BASE_URL}/api/v1/auth/validate", headers=h)
    assert validate.status_code == 401
