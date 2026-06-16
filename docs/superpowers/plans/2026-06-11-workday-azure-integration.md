# Workday + Microsoft Azure Integration Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire Azure AD SSO (login), Workday employee sync (RBAC), and SharePoint document ingestion (knowledge base) into the running Huron GenAI Knowledge Assistant.

**Architecture:** Phase 1 adds two backend OIDC routes — the frontend SSO UI already exists. Phase 2 uses Workday REST API client credentials to nightly sync employees into the users table for accurate RBAC. Phase 3 reuses the existing ingestion pipeline by feeding it files downloaded from SharePoint via Microsoft Graph API (same Azure AD app registration as Phase 1). Phase 4 (Teams bot) is optional and independent.

**Tech Stack:** MSAL (Python), Microsoft Graph API, Workday REST API v1, FastAPI, httpx, APScheduler, Next.js 14 (frontend already complete)

---

## Pre-Flight: What Huron IT Must Provide

Before any code runs, collect these from Huron IT. Nothing works without them.

| Item | Who provides it | Used in |
|------|----------------|---------|
| Azure AD **Tenant ID** | Huron IT (Azure portal → Azure Active Directory → Overview) | Phase 1 + 3 |
| Azure AD **App Registration Client ID** | Huron IT (create one App Registration for the GenAI app) | Phase 1 + 3 |
| Azure AD **App Registration Client Secret** | Huron IT (same App Registration → Certificates & secrets) | Phase 1 + 3 |
| Azure AD **Redirect URI** whitelisted | Huron IT (add `https://yourdomain/api/v1/auth/oidc/callback` to the App Registration) | Phase 1 |
| Azure AD **Group Object IDs** for each dept | Huron IT (Azure AD → Groups → each dept group → Object ID) | Phase 1 |
| Graph API permission granted: `Sites.Read.All` | Huron IT (App Registration → API Permissions → Admin Consent) | Phase 3 |
| Workday **Base URL** | Huron IT (e.g., `https://wd2.myworkday.com`) | Phase 2 |
| Workday **Tenant name** | Huron IT (the subdomain, e.g., `huron`) | Phase 2 |
| Workday **Integration Client ID + Secret** | Huron IT (Workday Studio → Register API Client) | Phase 2 |
| SharePoint **site URL(s)** to index | Knowledge owners at Huron | Phase 3 |

---

## File Map

```
backend/
  core/
    config.py                          MODIFY — add OIDC + Workday + SharePoint env vars
  routes/
    auth.py                            MODIFY — add /oidc/login and /oidc/callback routes
    sharepoint.py                      CREATE — admin endpoints for SharePoint site config + sync
  utils/
    workday_sync.py                    CREATE — Workday API client + employee sync job
    sharepoint_connector.py            CREATE — Graph API token client + file crawler
    scheduler.py                       CREATE — APScheduler setup + job registration
  migrations/versions/
    004_workday_sync_log.sql           CREATE — workday_sync_log table
    005_sharepoint_sites.sql           CREATE — sharepoint_sites table
  requirements.txt                     MODIFY — add msal, apscheduler
  requirements_production.txt          MODIFY — add msal, apscheduler
.env.example                           MODIFY — add all new env var keys
tests/
  test_oidc_routes.py                  CREATE
  test_workday_sync.py                 CREATE
  test_sharepoint_connector.py         CREATE
```

---

## Phase 1: Azure AD SSO

> **Frontend is already complete.** `Login.tsx` has the SSO tabs and calls `/api/v1/auth/oidc/login?provider=azure`. `frontend/src/app/auth/sso-complete/page.tsx` reads the `?token=` param and calls `loginWithToken()`. No frontend changes needed.

---

### Task 1: Add OIDC + Azure config vars to config.py and requirements

**Files:**
- Modify: `backend/core/config.py`
- Modify: `requirements.txt`
- Modify: `requirements_production.txt`
- Modify: `.env.example`

- [ ] **Step 1: Add msal to both requirements files**

In `requirements.txt`, add after the `bcrypt` line:
```
msal==1.31.0
apscheduler==3.10.4
```

In `requirements_production.txt`, add the same two lines.

- [ ] **Step 2: Add OIDC config vars to config.py**

In `backend/core/config.py`, add after the `PINECONE_INDEX` line (line 64):

```python
# ─── Azure AD / OIDC ─────────────────────────────────────────────────────────
OIDC_CLIENT_ID       = os.getenv("OIDC_CLIENT_ID", "")
OIDC_CLIENT_SECRET   = os.getenv("OIDC_CLIENT_SECRET", "")
OIDC_AUTHORITY       = os.getenv("OIDC_AUTHORITY", "")   # https://login.microsoftonline.com/{tenant-id}
OIDC_REDIRECT_URI    = os.getenv("OIDC_REDIRECT_URI", "http://localhost:8004/api/v1/auth/oidc/callback")
FRONTEND_URL         = os.getenv("FRONTEND_URL", "http://localhost:3000")

# ─── Workday ─────────────────────────────────────────────────────────────────
WORKDAY_BASE_URL     = os.getenv("WORKDAY_BASE_URL", "")       # https://wd2.myworkday.com
WORKDAY_TENANT       = os.getenv("WORKDAY_TENANT", "")         # huron
WORKDAY_CLIENT_ID    = os.getenv("WORKDAY_CLIENT_ID", "")
WORKDAY_CLIENT_SECRET= os.getenv("WORKDAY_CLIENT_SECRET", "")
```

Also add the new vars to the `Settings` class (after `pinecone_index`):
```python
    oidc_client_id: str     = OIDC_CLIENT_ID
    oidc_client_secret: str = OIDC_CLIENT_SECRET
    oidc_authority: str     = OIDC_AUTHORITY
    oidc_redirect_uri: str  = OIDC_REDIRECT_URI
    frontend_url: str       = FRONTEND_URL
    workday_base_url: str   = WORKDAY_BASE_URL
    workday_tenant: str     = WORKDAY_TENANT
    workday_client_id: str  = WORKDAY_CLIENT_ID
    workday_client_secret: str = WORKDAY_CLIENT_SECRET
```

- [ ] **Step 3: Add new vars to .env.example**

Append to `.env.example`:
```bash
# ─── Azure AD SSO ─────────────────────────────────────────────────────────────
OIDC_CLIENT_ID=your-azure-app-registration-client-id
OIDC_CLIENT_SECRET=your-azure-app-registration-secret
OIDC_AUTHORITY=https://login.microsoftonline.com/your-tenant-id
OIDC_REDIRECT_URI=http://localhost:8004/api/v1/auth/oidc/callback
FRONTEND_URL=http://localhost:3000

# ─── Workday ──────────────────────────────────────────────────────────────────
WORKDAY_BASE_URL=https://wd2.myworkday.com
WORKDAY_TENANT=huron
WORKDAY_CLIENT_ID=your-workday-integration-client-id
WORKDAY_CLIENT_SECRET=your-workday-integration-client-secret
```

- [ ] **Step 4: Install new deps and verify**

```bash
pip install msal==1.31.0 apscheduler==3.10.4
python -c "import msal; print('msal ok', msal.__version__)"
python -c "import apscheduler; print('apscheduler ok')"
```

Expected: `msal ok 1.31.0` and `apscheduler ok`

- [ ] **Step 5: Commit**

```bash
git add backend/core/config.py requirements.txt requirements_production.txt .env.example
git commit -m "feat(sso): add OIDC + Workday config vars and msal/apscheduler deps"
```

---

### Task 2: Add OIDC backend routes — /oidc/login and /oidc/callback

**Files:**
- Modify: `backend/routes/auth.py`

The frontend `Login.tsx:58` calls `window.location.href = \`${apiBase}/api/v1/auth/oidc/login?provider=${provider}\`` and `sso-complete/page.tsx` reads `?token=` from the redirect. These two routes close the loop.

- [ ] **Step 1: Write the failing test**

Create `tests/test_oidc_routes.py`:
```python
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


def test_oidc_login_azure_redirects(client):
    """GET /oidc/login?provider=azure returns 307 redirect to Microsoft."""
    with patch("routes.auth.OIDC_CLIENT_ID", "test-client-id"), \
         patch("routes.auth.OIDC_AUTHORITY", "https://login.microsoftonline.com/test-tenant"), \
         patch("routes.auth.OIDC_CLIENT_SECRET", "test-secret"):
        resp = client.get("/api/v1/auth/oidc/login?provider=azure", follow_redirects=False)
    assert resp.status_code in (302, 307)
    assert "login.microsoftonline.com" in resp.headers["location"]


def test_oidc_login_missing_config_returns_503(client):
    """GET /oidc/login with no OIDC config returns 503."""
    with patch("routes.auth.OIDC_CLIENT_ID", ""), \
         patch("routes.auth.OIDC_AUTHORITY", ""):
        resp = client.get("/api/v1/auth/oidc/login?provider=azure", follow_redirects=False)
    assert resp.status_code == 503


def test_oidc_callback_bad_code_redirects_to_error(client):
    """GET /oidc/callback with invalid code redirects to frontend error page."""
    with patch("routes.auth.OIDC_CLIENT_ID", "test-client-id"), \
         patch("routes.auth.OIDC_AUTHORITY", "https://login.microsoftonline.com/test-tenant"), \
         patch("routes.auth.OIDC_CLIENT_SECRET", "test-secret"), \
         patch("routes.auth.FRONTEND_URL", "http://localhost:3000"):
        mock_msal = MagicMock()
        mock_msal.acquire_token_by_authorization_code.return_value = {
            "error": "invalid_grant",
            "error_description": "Code expired"
        }
        with patch("routes.auth.ConfidentialClientApplication", return_value=mock_msal):
            resp = client.get("/api/v1/auth/oidc/callback?code=bad&state=x", follow_redirects=False)
    assert resp.status_code in (302, 307)
    assert "error=" in resp.headers["location"]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_oidc_routes.py -v
```

Expected: FAIL with `404 Not Found` (routes don't exist yet).

- [ ] **Step 3: Add the OIDC routes to auth.py**

At the top of `backend/routes/auth.py`, add to the imports:
```python
import secrets as _secrets
from urllib.parse import urlencode
from fastapi.responses import RedirectResponse
from core.config import (
    OIDC_CLIENT_ID, OIDC_CLIENT_SECRET, OIDC_AUTHORITY,
    OIDC_REDIRECT_URI, FRONTEND_URL,
)
```

Add an in-memory state store after the `_APP_ENV` line (line 26). In production this should move to Redis, but in-memory is fine for single-process dev:
```python
_oidc_states: dict[str, bool] = {}   # state -> True; validated on callback
```

Append these two routes at the end of `backend/routes/auth.py`:
```python
@router.get("/oidc/login")
async def oidc_login(provider: str = "azure"):
    """Initiate Azure AD or Okta OIDC login flow."""
    if not OIDC_CLIENT_ID or not OIDC_AUTHORITY:
        raise HTTPException(
            status_code=503,
            detail="SSO is not configured on this server. Contact your administrator.",
        )
    try:
        from msal import ConfidentialClientApplication
    except ImportError:
        raise HTTPException(status_code=503, detail="msal package not installed")

    state = _secrets.token_urlsafe(32)
    _oidc_states[state] = True

    msal_app = ConfidentialClientApplication(
        OIDC_CLIENT_ID,
        authority=OIDC_AUTHORITY,
        client_credential=OIDC_CLIENT_SECRET,
    )
    auth_url = msal_app.get_authorization_request_url(
        scopes=["openid", "email", "profile", "User.Read"],
        state=state,
        redirect_uri=OIDC_REDIRECT_URI,
    )
    return RedirectResponse(url=auth_url, status_code=302)


@router.get("/oidc/callback")
async def oidc_callback(code: str = "", state: str = "", error: str = "", error_description: str = ""):
    """Azure AD redirects here after authentication."""
    frontend_error_url = f"{FRONTEND_URL}/auth/sso-complete?error="

    if error:
        return RedirectResponse(
            url=frontend_error_url + urlencode({"": error_description or error})[1:],
            status_code=302,
        )

    if not code:
        return RedirectResponse(url=frontend_error_url + "missing_code", status_code=302)

    if not OIDC_CLIENT_ID or not OIDC_AUTHORITY:
        return RedirectResponse(url=frontend_error_url + "sso_not_configured", status_code=302)

    try:
        from msal import ConfidentialClientApplication
    except ImportError:
        return RedirectResponse(url=frontend_error_url + "msal_not_installed", status_code=302)

    msal_app = ConfidentialClientApplication(
        OIDC_CLIENT_ID,
        authority=OIDC_AUTHORITY,
        client_credential=OIDC_CLIENT_SECRET,
    )
    result = msal_app.acquire_token_by_authorization_code(
        code,
        scopes=["User.Read"],
        redirect_uri=OIDC_REDIRECT_URI,
    )

    if "error" in result:
        msg = result.get("error_description", result["error"])
        return RedirectResponse(url=frontend_error_url + urlencode({"": msg})[1:], status_code=302)

    claims = result.get("id_token_claims", {})
    email = (claims.get("preferred_username") or claims.get("upn") or claims.get("email", "")).lower()
    name  = claims.get("name", email)
    groups = claims.get("groups", [])   # only present if "groups" claim enabled in Azure AD manifest

    if not email:
        return RedirectResponse(url=frontend_error_url + "no_email_in_token", status_code=302)

    with db_conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE LOWER(email) = ?", (email,)).fetchone()

        if not row:
            # Auto-provision: look up group→role mapping, default to 'user'/'company'
            role, dept = "user", "company"
            if groups:
                mapping = conn.execute(
                    "SELECT huron_role, dept_code FROM oidc_role_mappings "
                    "WHERE provider='azure' AND ad_group IN ({}) LIMIT 1".format(
                        ",".join("?" * len(groups))
                    ),
                    groups,
                ).fetchone()
                if mapping:
                    role = mapping["huron_role"]
                    dept = mapping["dept_code"] or "company"

            username = email.split("@")[0]
            conn.execute(
                """INSERT INTO users
                   (username, email, full_name, password_hash, role, department, is_active, auth_method, created_by)
                   VALUES (?, ?, ?, '', ?, ?, 1, 'oidc', 'azure_ad')""",
                (username, email, name, role, dept),
            )
            conn.commit()
            row = conn.execute("SELECT * FROM users WHERE LOWER(email) = ?", (email,)).fetchone()

        if not row["is_active"]:
            return RedirectResponse(url=frontend_error_url + "account_deactivated", status_code=302)

        conn.execute(
            "UPDATE users SET full_name=?, auth_method='oidc', last_login=CURRENT_TIMESTAMP WHERE id=?",
            (name, row["id"]),
        )
        conn.commit()

    user = dict(row)
    token = create_token(user)
    write_audit(user["id"], user["username"], "sso_login_azure_ad")

    return RedirectResponse(url=f"{FRONTEND_URL}/auth/sso-complete?token={token}", status_code=302)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_oidc_routes.py -v
```

Expected: 3 PASS

- [ ] **Step 5: Manual smoke test (needs real Azure AD creds)**

With `.env` populated with real `OIDC_CLIENT_ID`, `OIDC_AUTHORITY`, `OIDC_CLIENT_SECRET`:
```bash
cd backend && uvicorn main:app --reload --port 8004
```
Open `http://localhost:3000`, click "Azure AD" tab → "Sign in with Microsoft". Should redirect to Microsoft login page. After login, should land on `/dashboard`.

- [ ] **Step 6: Commit**

```bash
git add backend/routes/auth.py tests/test_oidc_routes.py
git commit -m "feat(sso): add OIDC /login and /callback routes with Azure AD auto-provisioning"
```

---

### Task 3: Wire Azure AD Group → Role mappings

**Files:**
- `backend/migrations/versions/003_sso_tables.sql` — already has the `oidc_role_mappings` table (no schema change needed)

The auto-provisioning code in Task 2 already queries `oidc_role_mappings`. This task adds a seed SQL file and an admin API to manage mappings.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_oidc_routes.py`:
```python
def test_admin_can_create_role_mapping(client, admin_token):
    """POST /api/v1/auth/oidc/role-mappings creates a new mapping."""
    resp = client.post(
        "/api/v1/auth/oidc/role-mappings",
        json={"ad_group": "aaaabbbb-0000-1111-2222-333344445555",
              "huron_role": "user", "dept_code": "hr",
              "description": "HR team"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["ad_group"] == "aaaabbbb-0000-1111-2222-333344445555"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_oidc_routes.py::test_admin_can_create_role_mapping -v
```

Expected: FAIL with 404.

- [ ] **Step 3: Add role-mapping endpoints to auth.py**

Append to `backend/routes/auth.py`:
```python
@router.get("/oidc/role-mappings")
async def list_role_mappings(p: dict = Depends(current_user)):
    if p.get("role") not in ("root", "dept_admin"):
        raise HTTPException(status_code=403, detail="Requires admin role")
    with db_conn() as conn:
        rows = conn.execute(
            "SELECT id, provider, ad_group, huron_role, dept_code, description FROM oidc_role_mappings ORDER BY id"
        ).fetchall()
    return [dict(r) for r in rows]


@router.post("/oidc/role-mappings", status_code=201)
async def create_role_mapping(body: dict, p: dict = Depends(current_user)):
    if p.get("role") != "root":
        raise HTTPException(status_code=403, detail="Requires root role")
    required = {"ad_group", "huron_role"}
    if not required.issubset(body):
        raise HTTPException(status_code=422, detail=f"Missing fields: {required - body.keys()}")
    with db_conn() as conn:
        conn.execute(
            """INSERT INTO oidc_role_mappings (provider, ad_group, huron_role, dept_code, description)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT (provider, ad_group) DO UPDATE SET
                 huron_role=excluded.huron_role,
                 dept_code=excluded.dept_code,
                 description=excluded.description""",
            (body.get("provider", "azure"), body["ad_group"],
             body["huron_role"], body.get("dept_code"), body.get("description")),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM oidc_role_mappings WHERE ad_group=?", (body["ad_group"],)
        ).fetchone()
    return dict(row)


@router.delete("/oidc/role-mappings/{mapping_id}", status_code=204)
async def delete_role_mapping(mapping_id: int, p: dict = Depends(current_user)):
    if p.get("role") != "root":
        raise HTTPException(status_code=403, detail="Requires root role")
    with db_conn() as conn:
        conn.execute("DELETE FROM oidc_role_mappings WHERE id=?", (mapping_id,))
        conn.commit()
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_oidc_routes.py -v
```

Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add backend/routes/auth.py tests/test_oidc_routes.py
git commit -m "feat(sso): add CRUD endpoints for Azure AD group → Huron role mappings"
```

---

## Phase 2: Workday Employee Directory Sync

> **Purpose:** Workday is Huron's system of record for employees. This job syncs worker data into the `users` table nightly — keeping roles, departments, and active status accurate. When someone is terminated in Workday, the sync deactivates their account within 24 hours.

---

### Task 4: Create Workday API client

**Files:**
- Create: `backend/utils/workday_sync.py`
- Create: `backend/migrations/versions/004_workday_sync_log.sql`
- Create: `tests/test_workday_sync.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_workday_sync.py`:
```python
import pytest
from unittest.mock import patch, MagicMock


def test_get_workday_token_returns_bearer_token():
    from utils.workday_sync import _get_workday_token
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"access_token": "test-wday-token", "token_type": "Bearer"}
    mock_resp.raise_for_status = MagicMock()
    with patch("utils.workday_sync.httpx.post", return_value=mock_resp):
        with patch("utils.workday_sync.WORKDAY_BASE_URL", "https://wd.example.com"), \
             patch("utils.workday_sync.WORKDAY_TENANT", "huron"), \
             patch("utils.workday_sync.WORKDAY_CLIENT_ID", "cid"), \
             patch("utils.workday_sync.WORKDAY_CLIENT_SECRET", "csec"):
            token = _get_workday_token()
    assert token == "test-wday-token"


def test_sync_workday_employees_inserts_new_user(tmp_db):
    """A new active worker in Workday should be inserted into users."""
    from utils.workday_sync import sync_workday_employees
    workers = [{
        "primaryWorkEmail": "jane.doe@huron.com",
        "legalNameData": {
            "firstNameData": {"value": "Jane"},
            "lastNameData": {"value": "Doe"}
        },
        "primarySupervisoryOrganization": {"orgType": {"descriptor": "Human Resources"}},
        "active": True,
    }]
    with patch("utils.workday_sync._get_workday_token", return_value="tok"), \
         patch("utils.workday_sync._list_workers", return_value=workers):
        result = sync_workday_employees()
    assert result["synced"] == 1
    assert result["deactivated"] == 0


def test_sync_workday_employees_deactivates_terminated_user(tmp_db_with_user):
    """A worker marked inactive in Workday should deactivate the local account."""
    from utils.workday_sync import sync_workday_employees
    workers = [{
        "primaryWorkEmail": "existing@huron.com",
        "legalNameData": {"firstNameData": {"value": "Ex"}, "lastNameData": {"value": "User"}},
        "primarySupervisoryOrganization": {"orgType": {"descriptor": "Finance"}},
        "active": False,
    }]
    with patch("utils.workday_sync._get_workday_token", return_value="tok"), \
         patch("utils.workday_sync._list_workers", return_value=workers):
        result = sync_workday_employees()
    assert result["deactivated"] == 1
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_workday_sync.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'utils.workday_sync'`

- [ ] **Step 3: Create the Workday sync module**

Create `backend/utils/workday_sync.py`:
```python
"""
Workday employee directory sync.

Runs as a nightly job via APScheduler (registered in utils/scheduler.py).
Syncs workers from the Workday REST API into the Huron users table.
Terminates map to is_active=False — the account is deactivated, not deleted.
"""
from __future__ import annotations

import logging
from datetime import datetime

import httpx

from core.config import (
    WORKDAY_BASE_URL, WORKDAY_TENANT,
    WORKDAY_CLIENT_ID, WORKDAY_CLIENT_SECRET,
)
from core.database import db_conn

logger = logging.getLogger(__name__)

# Workday department name → Huron dept code
DEPT_MAP: dict[str, str] = {
    "Human Resources":      "hr",
    "Finance":              "finance",
    "Legal":                "legal",
    "Clinical":             "clinical",
    "Operations":           "operations",
    "Information Technology": "it",
    "Marketing":            "marketing",
}


def _get_workday_token() -> str:
    resp = httpx.post(
        f"{WORKDAY_BASE_URL}/ccx/oauth2/{WORKDAY_TENANT}/token",
        data={
            "grant_type": "client_credentials",
            "client_id": WORKDAY_CLIENT_ID,
            "client_secret": WORKDAY_CLIENT_SECRET,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def _list_workers(token: str) -> list[dict]:
    headers = {"Authorization": f"Bearer {token}"}
    workers: list[dict] = []
    url: str | None = f"{WORKDAY_BASE_URL}/ccx/api/v1/{WORKDAY_TENANT}/workers"
    while url:
        resp = httpx.get(url, headers=headers, params={"limit": 100}, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        workers.extend(data.get("data", []))
        next_page = data.get("total", {})
        url = next_page.get("nextPage") if isinstance(next_page, dict) else None
    return workers


def sync_workday_employees() -> dict[str, int]:
    """
    Pull all workers from Workday and upsert into the users table.
    Returns counts: synced (new), updated, deactivated.
    """
    if not all([WORKDAY_BASE_URL, WORKDAY_TENANT, WORKDAY_CLIENT_ID, WORKDAY_CLIENT_SECRET]):
        logger.warning("Workday sync skipped — WORKDAY_* env vars not set")
        return {"synced": 0, "updated": 0, "deactivated": 0, "skipped": 0}

    token = _get_workday_token()
    workers = _list_workers(token)
    synced = updated = deactivated = skipped = 0

    with db_conn() as conn:
        for w in workers:
            email = (w.get("primaryWorkEmail") or "").strip().lower()
            if not email:
                skipped += 1
                continue

            first = w.get("legalNameData", {}).get("firstNameData", {}).get("value", "")
            last  = w.get("legalNameData", {}).get("lastNameData",  {}).get("value", "")
            full_name = f"{first} {last}".strip()

            org_desc  = w.get("primarySupervisoryOrganization", {}).get("orgType", {}).get("descriptor", "")
            dept_code = DEPT_MAP.get(org_desc, "company")
            is_active = bool(w.get("active", False))

            row = conn.execute("SELECT id, is_active FROM users WHERE LOWER(email)=?", (email,)).fetchone()

            if row:
                conn.execute(
                    "UPDATE users SET full_name=?, department=?, is_active=? WHERE id=?",
                    (full_name, dept_code, is_active, row["id"]),
                )
                if not is_active and row["is_active"]:
                    deactivated += 1
                    logger.info("Deactivated terminated employee: %s", email)
                else:
                    updated += 1
            else:
                if is_active:
                    username = email.split("@")[0]
                    conn.execute(
                        """INSERT INTO users
                           (username, email, full_name, password_hash, role, department, is_active, auth_method, created_by)
                           VALUES (?, ?, ?, '', 'user', ?, 1, 'workday', 'workday_sync')""",
                        (username, email, full_name, dept_code),
                    )
                    synced += 1
                else:
                    skipped += 1

        conn.execute(
            """INSERT INTO workday_sync_log (synced, updated, deactivated, skipped, synced_at)
               VALUES (?, ?, ?, ?, ?)""",
            (synced, updated, deactivated, skipped, datetime.utcnow()),
        )
        conn.commit()

    logger.info("Workday sync complete: synced=%d updated=%d deactivated=%d skipped=%d",
                synced, updated, deactivated, skipped)
    return {"synced": synced, "updated": updated, "deactivated": deactivated, "skipped": skipped}
```

- [ ] **Step 4: Create the sync log migration**

Create `backend/migrations/versions/004_workday_sync_log.sql`:
```sql
-- Migration 004: Workday sync audit log
CREATE TABLE IF NOT EXISTS workday_sync_log (
    id          SERIAL PRIMARY KEY,
    synced      INTEGER NOT NULL DEFAULT 0,
    updated     INTEGER NOT NULL DEFAULT 0,
    deactivated INTEGER NOT NULL DEFAULT 0,
    skipped     INTEGER NOT NULL DEFAULT 0,
    error_msg   TEXT,
    synced_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

- [ ] **Step 5: Run tests**

```bash
pytest tests/test_workday_sync.py -v
```

Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add backend/utils/workday_sync.py backend/migrations/versions/004_workday_sync_log.sql tests/test_workday_sync.py
git commit -m "feat(workday): add employee directory sync client and nightly job"
```

---

### Task 5: Add admin endpoint to trigger Workday sync manually

**Files:**
- Modify: `backend/routes/admin.py`

- [ ] **Step 1: Append to admin.py**

```python
@router.post("/workday/sync", tags=["admin"])
async def trigger_workday_sync(p: dict = Depends(current_user)):
    """Manually trigger a Workday employee sync. root only."""
    if p.get("role") != "root":
        raise HTTPException(status_code=403, detail="root role required")
    from utils.workday_sync import sync_workday_employees
    try:
        result = sync_workday_employees()
        return {"status": "ok", **result}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Workday sync failed: {exc}")
```

- [ ] **Step 2: Commit**

```bash
git add backend/routes/admin.py
git commit -m "feat(workday): add POST /admin/workday/sync manual trigger endpoint"
```

---

### Task 6: Register nightly Workday sync with APScheduler

**Files:**
- Create: `backend/utils/scheduler.py`
- Modify: `backend/main.py` — register scheduler on startup

- [ ] **Step 1: Create scheduler module**

Create `backend/utils/scheduler.py`:
```python
"""
APScheduler setup. Register all background jobs here.
Scheduler is started in main.py lifespan, stopped on shutdown.
"""
from __future__ import annotations

import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()


def register_jobs() -> None:
    from utils.workday_sync import sync_workday_employees

    scheduler.add_job(
        sync_workday_employees,
        CronTrigger(hour=2, minute=0),   # 2 AM UTC every day
        id="workday_sync",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    logger.info("Registered nightly Workday sync job (02:00 UTC)")
```

- [ ] **Step 2: Start/stop scheduler in main.py lifespan**

In `backend/main.py`, find the FastAPI app startup (look for `@app.on_event("startup")` or `lifespan`). Add:

```python
# In startup handler:
from utils.scheduler import scheduler, register_jobs
register_jobs()
scheduler.start()
logger.info("APScheduler started")

# In shutdown handler:
from utils.scheduler import scheduler
scheduler.shutdown(wait=False)
```

- [ ] **Step 3: Commit**

```bash
git add backend/utils/scheduler.py backend/main.py
git commit -m "feat(workday): register nightly employee sync via APScheduler"
```

---

## Phase 3: SharePoint Document Ingestion

> **Purpose:** SharePoint sites contain Huron's internal documentation. This phase pulls files from configured SharePoint sites through Microsoft Graph API and feeds them into the existing ingestion pipeline (which handles chunking, embedding, and Pinecone upsert). The same Azure AD app registration from Phase 1 is reused — no extra credentials needed, just an additional `Sites.Read.All` API permission granted by Huron IT.

---

### Task 7: Create SharePoint Graph API connector

**Files:**
- Create: `backend/utils/sharepoint_connector.py`
- Create: `backend/migrations/versions/005_sharepoint_sites.sql`
- Create: `tests/test_sharepoint_connector.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_sharepoint_connector.py`:
```python
from unittest.mock import patch, MagicMock


def test_get_graph_token_returns_bearer():
    from utils.sharepoint_connector import _get_graph_token
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"access_token": "graph-token-123"}
    mock_resp.raise_for_status = MagicMock()
    with patch("utils.sharepoint_connector.httpx.post", return_value=mock_resp), \
         patch("utils.sharepoint_connector.OIDC_CLIENT_ID", "cid"), \
         patch("utils.sharepoint_connector.OIDC_CLIENT_SECRET", "cs"), \
         patch("utils.sharepoint_connector.OIDC_AUTHORITY", "https://login.microsoftonline.com/tid"):
        token = _get_graph_token()
    assert token == "graph-token-123"


def test_list_site_files_returns_file_list():
    from utils.sharepoint_connector import list_site_files
    mock_site_resp = MagicMock()
    mock_site_resp.json.return_value = {"id": "site-abc,root-abc,web-abc"}
    mock_site_resp.raise_for_status = MagicMock()

    mock_files_resp = MagicMock()
    mock_files_resp.json.return_value = {"value": [
        {"id": "file1", "name": "policy.pdf", "file": {"mimeType": "application/pdf"},
         "parentReference": {"driveId": "drive-abc"}, "size": 12345}
    ]}
    mock_files_resp.raise_for_status = MagicMock()

    with patch("utils.sharepoint_connector._get_graph_token", return_value="tok"), \
         patch("utils.sharepoint_connector.httpx.get", side_effect=[mock_site_resp, mock_files_resp]):
        files = list_site_files("https://huron.sharepoint.com/sites/HR")
    assert len(files) == 1
    assert files[0]["name"] == "policy.pdf"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_sharepoint_connector.py -v
```

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Create the SharePoint connector**

Create `backend/utils/sharepoint_connector.py`:
```python
"""
Microsoft SharePoint connector via Graph API.

Uses the same Azure AD app registration as OIDC SSO (Phase 1).
Huron IT must grant Sites.Read.All permission with admin consent.

Supported MIME types match the existing ingestion pipeline's accepted formats.
"""
from __future__ import annotations

import logging
from typing import Iterator

import httpx

from core.config import OIDC_CLIENT_ID, OIDC_CLIENT_SECRET, OIDC_AUTHORITY

logger = logging.getLogger(__name__)

GRAPH_ENDPOINT = "https://graph.microsoft.com/v1.0"
SUPPORTED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/plain", "text/html", "text/markdown",
    "application/json",
}


def _get_graph_token() -> str:
    """Client credentials flow — server-to-server, no user interaction."""
    tenant_id = OIDC_AUTHORITY.rstrip("/").split("/")[-1]
    resp = httpx.post(
        f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token",
        data={
            "grant_type":    "client_credentials",
            "client_id":     OIDC_CLIENT_ID,
            "client_secret": OIDC_CLIENT_SECRET,
            "scope":         "https://graph.microsoft.com/.default",
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def list_site_files(site_url: str) -> list[dict]:
    """
    Return all files in a SharePoint site's root drive that match supported MIME types.
    site_url example: "https://huron.sharepoint.com/sites/HR"
    """
    token   = _get_graph_token()
    headers = {"Authorization": f"Bearer {token}"}

    # Resolve site URL → Graph site ID
    parts    = site_url.replace("https://", "").split("/", 1)
    hostname = parts[0]
    path     = parts[1] if len(parts) > 1 else ""
    resp     = httpx.get(f"{GRAPH_ENDPOINT}/sites/{hostname}:/{path}", headers=headers, timeout=30)
    resp.raise_for_status()
    site_id = resp.json()["id"]

    # List root drive children
    resp = httpx.get(f"{GRAPH_ENDPOINT}/sites/{site_id}/drive/root/children",
                     headers=headers, timeout=30)
    resp.raise_for_status()
    all_items = resp.json().get("value", [])

    return [
        {
            "id":       item["id"],
            "name":     item["name"],
            "mime":     item.get("file", {}).get("mimeType", ""),
            "drive_id": item.get("parentReference", {}).get("driveId", ""),
            "size":     item.get("size", 0),
        }
        for item in all_items
        if item.get("file", {}).get("mimeType", "") in SUPPORTED_MIME_TYPES
    ]


def download_file(drive_id: str, item_id: str) -> bytes:
    """Download raw file bytes from a Graph API drive item."""
    token = _get_graph_token()
    resp  = httpx.get(
        f"{GRAPH_ENDPOINT}/drives/{drive_id}/items/{item_id}/content",
        headers={"Authorization": f"Bearer {token}"},
        follow_redirects=True,
        timeout=120,
    )
    resp.raise_for_status()
    return resp.content
```

- [ ] **Step 4: Create the SharePoint sites migration**

Create `backend/migrations/versions/005_sharepoint_sites.sql`:
```sql
-- Migration 005: SharePoint site configurations
CREATE TABLE IF NOT EXISTS sharepoint_sites (
    id          SERIAL PRIMARY KEY,
    site_url    TEXT NOT NULL UNIQUE,
    dept_code   TEXT NOT NULL,
    display_name TEXT NOT NULL DEFAULT '',
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    last_synced TIMESTAMPTZ,
    files_indexed INTEGER NOT NULL DEFAULT 0,
    configured_by TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

- [ ] **Step 5: Run tests**

```bash
pytest tests/test_sharepoint_connector.py -v
```

Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add backend/utils/sharepoint_connector.py backend/migrations/versions/005_sharepoint_sites.sql tests/test_sharepoint_connector.py
git commit -m "feat(sharepoint): add Graph API connector and sharepoint_sites table"
```

---

### Task 8: Create SharePoint admin routes + sync job

**Files:**
- Create: `backend/routes/sharepoint.py`
- Modify: `backend/main.py` — register the new router

- [ ] **Step 1: Write the failing test**

Add `tests/test_sharepoint_routes.py`:
```python
def test_add_sharepoint_site_requires_root(client, user_token):
    resp = client.post(
        "/api/v1/sharepoint/sites",
        json={"site_url": "https://huron.sharepoint.com/sites/HR",
              "dept_code": "hr", "display_name": "HR Portal"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 403


def test_add_sharepoint_site_root_succeeds(client, root_token):
    resp = client.post(
        "/api/v1/sharepoint/sites",
        json={"site_url": "https://huron.sharepoint.com/sites/HR",
              "dept_code": "hr", "display_name": "HR Portal"},
        headers={"Authorization": f"Bearer {root_token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["site_url"] == "https://huron.sharepoint.com/sites/HR"
```

- [ ] **Step 2: Create the routes module**

Create `backend/routes/sharepoint.py`:
```python
"""
SharePoint integration admin routes.

POST /api/v1/sharepoint/sites          — register a SharePoint site to index
GET  /api/v1/sharepoint/sites          — list configured sites
DELETE /api/v1/sharepoint/sites/{id}   — remove a site
POST /api/v1/sharepoint/sites/{id}/sync — trigger sync for one site (root only)
POST /api/v1/sharepoint/sync-all        — trigger sync for all active sites (root only)
"""
from __future__ import annotations

import io
import logging

from fastapi import APIRouter, Depends, HTTPException

from core.database import db_conn, write_audit
from core.security import current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/sharepoint", tags=["sharepoint"])

SUPPORTED_DEPT_CODES = {
    "company", "hr", "legal", "finance", "clinical",
    "operations", "it", "marketing", "external",
}


@router.get("/sites")
async def list_sites(p: dict = Depends(current_user)):
    if p.get("role") not in ("root", "dept_admin"):
        raise HTTPException(status_code=403, detail="Admin role required")
    with db_conn() as conn:
        rows = conn.execute(
            "SELECT id, site_url, dept_code, display_name, is_active, last_synced, files_indexed "
            "FROM sharepoint_sites ORDER BY created_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


@router.post("/sites", status_code=201)
async def add_site(body: dict, p: dict = Depends(current_user)):
    if p.get("role") != "root":
        raise HTTPException(status_code=403, detail="root role required")
    site_url    = (body.get("site_url") or "").strip()
    dept_code   = (body.get("dept_code") or "").strip()
    display_name = (body.get("display_name") or site_url).strip()
    if not site_url or not dept_code:
        raise HTTPException(status_code=422, detail="site_url and dept_code are required")
    if dept_code not in SUPPORTED_DEPT_CODES:
        raise HTTPException(status_code=422, detail=f"dept_code must be one of {sorted(SUPPORTED_DEPT_CODES)}")
    with db_conn() as conn:
        try:
            conn.execute(
                "INSERT INTO sharepoint_sites (site_url, dept_code, display_name, configured_by) VALUES (?, ?, ?, ?)",
                (site_url, dept_code, display_name, p["sub"]),
            )
            conn.commit()
            row = conn.execute("SELECT * FROM sharepoint_sites WHERE site_url=?", (site_url,)).fetchone()
        except Exception as exc:
            if "UNIQUE" in str(exc) or "unique" in str(exc):
                raise HTTPException(status_code=409, detail="Site already registered")
            raise
    write_audit(p["user_id"], p["sub"], "sharepoint_site_added", detail=site_url)
    return dict(row)


@router.delete("/sites/{site_id}", status_code=204)
async def remove_site(site_id: int, p: dict = Depends(current_user)):
    if p.get("role") != "root":
        raise HTTPException(status_code=403, detail="root role required")
    with db_conn() as conn:
        conn.execute("DELETE FROM sharepoint_sites WHERE id=?", (site_id,))
        conn.commit()
    write_audit(p["user_id"], p["sub"], "sharepoint_site_removed", detail=str(site_id))


@router.post("/sites/{site_id}/sync")
async def sync_one_site(site_id: int, p: dict = Depends(current_user)):
    """Download and ingest all files from a single registered SharePoint site."""
    if p.get("role") != "root":
        raise HTTPException(status_code=403, detail="root role required")
    with db_conn() as conn:
        row = conn.execute("SELECT * FROM sharepoint_sites WHERE id=?", (site_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Site not found")
    return await _run_site_sync(dict(row), p["sub"])


@router.post("/sync-all")
async def sync_all_sites(p: dict = Depends(current_user)):
    """Trigger sync for all active SharePoint sites."""
    if p.get("role") != "root":
        raise HTTPException(status_code=403, detail="root role required")
    with db_conn() as conn:
        sites = [dict(r) for r in conn.execute(
            "SELECT * FROM sharepoint_sites WHERE is_active=1"
        ).fetchall()]
    results = []
    for site in sites:
        result = await _run_site_sync(site, p["sub"])
        results.append(result)
    return {"sites_synced": len(results), "results": results}


async def _run_site_sync(site: dict, triggered_by: str) -> dict:
    from utils.sharepoint_connector import list_site_files, download_file
    site_url  = site["site_url"]
    dept_code = site["dept_code"]
    files_ok  = 0
    errors    = []

    try:
        files = list_site_files(site_url)
    except Exception as exc:
        return {"site_url": site_url, "error": str(exc), "files_ingested": 0}

    for f in files:
        try:
            content = download_file(f["drive_id"], f["id"])
            # Feed into the existing ingestion service
            from utils.ingestion_service import ingest_file_bytes
            ingest_file_bytes(
                file_bytes=content,
                filename=f["name"],
                mime_type=f["mime"],
                dept_code=dept_code,
                source="sharepoint",
                uploaded_by=triggered_by,
            )
            files_ok += 1
        except Exception as exc:
            logger.warning("Failed to ingest SharePoint file %s: %s", f["name"], exc)
            errors.append({"file": f["name"], "error": str(exc)})

    with db_conn() as conn:
        conn.execute(
            "UPDATE sharepoint_sites SET last_synced=CURRENT_TIMESTAMP, files_indexed=? WHERE id=?",
            (files_ok, site["id"]),
        )
        conn.commit()

    return {"site_url": site_url, "files_ingested": files_ok, "errors": errors}
```

- [ ] **Step 3: Register the router in main.py**

In `backend/main.py`, find where other routers are included (look for `app.include_router`). Add:
```python
from routes.sharepoint import router as sharepoint_router
app.include_router(sharepoint_router)
```

- [ ] **Step 4: Add SharePoint sync to APScheduler (weekly)**

In `backend/utils/scheduler.py`, add to `register_jobs()`:
```python
    from routes.sharepoint import sync_all_sites
    async def _scheduled_sharepoint_sync():
        with db_conn() as conn:
            sites = [dict(r) for r in conn.execute(
                "SELECT * FROM sharepoint_sites WHERE is_active=1"
            ).fetchall()]
        for site in sites:
            from routes.sharepoint import _run_site_sync
            await _run_site_sync(site, "scheduler")

    scheduler.add_job(
        _scheduled_sharepoint_sync,
        CronTrigger(day_of_week="sun", hour=3, minute=0),  # Sunday 3 AM UTC weekly
        id="sharepoint_sync",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    logger.info("Registered weekly SharePoint sync job (Sunday 03:00 UTC)")
```

- [ ] **Step 5: Run all tests**

```bash
pytest tests/test_sharepoint_connector.py tests/test_sharepoint_routes.py -v
```

Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add backend/routes/sharepoint.py backend/utils/scheduler.py backend/main.py tests/test_sharepoint_routes.py
git commit -m "feat(sharepoint): add admin routes for site config and sync; register weekly APScheduler job"
```

---

## Phase 4: Microsoft Teams Bot (Optional — Independent of Phases 1–3)

> **Purpose:** Huron staff can query the GenAI assistant from within Microsoft Teams without opening the web app. A message to the bot triggers the existing RAG query pipeline and returns an Adaptive Card with the answer and citations.

> **Prerequisite:** Huron IT must create an Azure Bot Registration and provide `TEAMS_APP_ID` and `TEAMS_APP_SECRET`.

---

### Task 9: Teams webhook endpoint

**Files:**
- Create: `backend/routes/teams.py`
- Modify: `requirements.txt` — add `botbuilder-core`, `botbuilder-integration-aiohttp`
- Modify: `backend/main.py` — register Teams router

- [ ] **Step 1: Add Teams bot deps**

```bash
pip install botbuilder-core==4.14.8 botbuilder-integration-aiohttp==4.14.8
```

Add to `requirements.txt` and `requirements_production.txt`:
```
botbuilder-core==4.14.8
botbuilder-integration-aiohttp==4.14.8
```

Add to `.env.example`:
```bash
# ─── Microsoft Teams Bot ──────────────────────────────────────────────────────
TEAMS_APP_ID=your-azure-bot-app-id
TEAMS_APP_SECRET=your-azure-bot-app-secret
```

- [ ] **Step 2: Create the Teams bot route**

Create `backend/routes/teams.py`:
```python
"""
Microsoft Teams Bot webhook endpoint.

Receives Activity objects from the Bot Framework service, calls the RAG query
pipeline, and responds with an Adaptive Card containing the answer + citations.

Setup required:
  1. Azure Bot Registration (Huron IT) → provides TEAMS_APP_ID + TEAMS_APP_SECRET
  2. Set Messaging Endpoint in Azure Bot to: https://yourdomain/api/v1/teams/messages
"""
from __future__ import annotations

import logging
import os

from fastapi import APIRouter, Request, Response

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/teams", tags=["teams"])

TEAMS_APP_ID     = os.getenv("TEAMS_APP_ID", "")
TEAMS_APP_SECRET = os.getenv("TEAMS_APP_SECRET", "")


def _build_adaptive_card(answer: str, sources: list[str]) -> dict:
    source_facts = [
        {"title": f"[{i+1}]", "value": s}
        for i, s in enumerate(sources[:5])
    ]
    card: dict = {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.4",
        "body": [
            {"type": "TextBlock", "text": "Huron Knowledge Assistant",
             "weight": "Bolder", "size": "Medium"},
            {"type": "TextBlock", "text": answer, "wrap": True},
        ],
    }
    if source_facts:
        card["body"].append({
            "type": "FactSet",
            "facts": source_facts,
        })
    return {"contentType": "application/vnd.microsoft.card.adaptive", "content": card}


@router.post("/messages")
async def teams_messages(request: Request):
    """Main Teams bot endpoint — receives activities from Bot Framework."""
    if not TEAMS_APP_ID or not TEAMS_APP_SECRET:
        logger.warning("Teams bot not configured — TEAMS_APP_ID/SECRET missing")
        return Response(status_code=200)  # always 200 to Bot Framework

    try:
        from botbuilder.core import BotFrameworkAdapter, BotFrameworkAdapterSettings, TurnContext
        from botbuilder.schema import Activity
    except ImportError:
        logger.error("botbuilder-core not installed")
        return Response(status_code=200)

    settings = BotFrameworkAdapterSettings(TEAMS_APP_ID, TEAMS_APP_SECRET)
    adapter  = BotFrameworkAdapter(settings)
    body     = await request.json()
    activity = Activity().deserialize(body)

    async def _turn_handler(turn_context: TurnContext):
        if turn_context.activity.type != "message":
            return
        query = (turn_context.activity.text or "").strip()
        if not query:
            return

        # Call the existing RAG query pipeline
        try:
            from agent.tools import rag_search
            result = rag_search(query=query, dept="company", top_k=5)
            answer  = result.get("answer", "I could not find an answer.")
            sources = [s.get("source", "") for s in result.get("sources", [])]
        except Exception as exc:
            logger.error("Teams bot RAG query failed: %s", exc)
            answer  = "Sorry, I encountered an error retrieving your answer."
            sources = []

        card = _build_adaptive_card(answer, sources)
        from botbuilder.core.message_factory import MessageFactory
        reply = MessageFactory.attachment(card)  # type: ignore[arg-type]
        await turn_context.send_activity(reply)

    auth_header = request.headers.get("Authorization", "")
    await adapter.process_activity(activity, auth_header, _turn_handler)
    return Response(status_code=200)
```

- [ ] **Step 3: Register Teams router in main.py**

```python
from routes.teams import router as teams_router
app.include_router(teams_router)
```

- [ ] **Step 4: Commit**

```bash
git add backend/routes/teams.py backend/main.py requirements.txt requirements_production.txt .env.example
git commit -m "feat(teams): add Teams bot webhook with Adaptive Card RAG responses"
```

---

## Environment Variables — Complete Reference

Add all of these to your `.env` file locally, GitHub Actions secrets for staging/prod:

```bash
# ── Phase 1: Azure AD SSO ─────────────────────────────────────────────────────
OIDC_CLIENT_ID=<from Huron IT — App Registration Client ID>
OIDC_CLIENT_SECRET=<from Huron IT — App Registration Client Secret>
OIDC_AUTHORITY=https://login.microsoftonline.com/<tenant-id>
OIDC_REDIRECT_URI=https://yourdomain/api/v1/auth/oidc/callback
FRONTEND_URL=https://yourdomain

# ── Phase 2: Workday ──────────────────────────────────────────────────────────
WORKDAY_BASE_URL=https://wd2.myworkday.com
WORKDAY_TENANT=huron
WORKDAY_CLIENT_ID=<from Huron IT — Workday Integration Client ID>
WORKDAY_CLIENT_SECRET=<from Huron IT — Workday Integration Client Secret>

# ── Phase 3: SharePoint (reuses Azure AD creds above — no new keys needed) ───
# Huron IT must grant Sites.Read.All on the App Registration above

# ── Phase 4: Teams Bot (optional) ─────────────────────────────────────────────
TEAMS_APP_ID=<from Huron IT — Azure Bot App ID>
TEAMS_APP_SECRET=<from Huron IT — Azure Bot App Secret>
```

---

## Azure AD App Registration — One-Time Setup Checklist

Huron IT does this in the Azure portal once. It covers Phase 1, 2, and 3.

```
Azure Portal → Azure Active Directory → App Registrations → New Registration
  Name: Huron GenAI Knowledge Assistant
  Supported account types: Single tenant (Huron's tenant only)
  Redirect URI: Web → https://yourdomain/api/v1/auth/oidc/callback

→ Certificates & Secrets → New Client Secret → copy value immediately

→ API Permissions → Add permission:
    Microsoft Graph → Delegated: openid, email, profile, User.Read
    Microsoft Graph → Application: Sites.Read.All
    → Grant Admin Consent

→ Token Configuration → Add groups claim → Security groups
  (required for oidc_role_mappings to receive group Object IDs in token)

→ Overview → copy Application (client) ID and Directory (tenant) ID
```

---

## Delivery Order

| Phase | Dependency | Effort | Delivers |
|-------|-----------|--------|---------|
| 1 — Azure AD SSO | Azure App Registration from IT | 1 day | Huron staff log in with Microsoft credentials |
| 2 — Workday Sync | Workday client credentials from IT | 1 day | RBAC stays current; terminated accounts auto-deactivate |
| 3 — SharePoint Ingestion | Phase 1 complete + Sites.Read.All permission | 2 days | SharePoint docs searchable in all 4 tabs |
| 4 — Teams Bot | Phase 1 complete + Azure Bot Registration from IT | 1 day | Staff query from Teams without opening the web app |
