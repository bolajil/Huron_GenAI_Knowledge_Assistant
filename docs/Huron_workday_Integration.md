# Huron GenAI — Workday + Microsoft Azure Full Integration Guide

> **This document is the single source of truth for the Workday and Microsoft Azure integration.**
> It covers architecture, step-by-step implementation with code, expected outcomes, and failure recovery options for every step.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Pre-Flight: What Huron IT Must Provide](#2-pre-flight-what-huron-it-must-provide)
3. [Environment Setup](#3-environment-setup)
4. [Phase 1 — Azure AD SSO](#4-phase-1--azure-ad-sso)
5. [Phase 2 — Workday Employee Sync](#5-phase-2--workday-employee-sync)
6. [Phase 3 — SharePoint Document Ingestion](#6-phase-3--sharepoint-document-ingestion)
7. [Phase 4 — Microsoft Teams Bot (Optional)](#7-phase-4--microsoft-teams-bot-optional)
8. [Testing All Integrations End-to-End](#8-testing-all-integrations-end-to-end)
9. [Deployment Checklist](#9-deployment-checklist)
10. [Troubleshooting Reference](#10-troubleshooting-reference)

---

## 1. Architecture Overview

### What Changes

```
TODAY                                AFTER THIS INTEGRATION
─────────────────────────────────    ──────────────────────────────────────────
Manual user creation                 Azure AD: staff log in with Microsoft creds
Manual role assignment               Workday: roles/depts sync nightly at 02:00 UTC
Manual document upload               SharePoint: knowledge indexed weekly (Sunday 03:00 UTC)
Must open web app to query           Teams: query from inside Microsoft Teams
```

### How the Four Integrations Connect

```
                    HURON IT provides ONE Azure App Registration
                    ┌──────────────────────────────────────────────┐
                    │  Client ID + Client Secret + Tenant ID        │
                    │  (used by ALL three Microsoft integrations)   │
                    └──────────┬───────────────────────────────────┘
                               │
              ┌────────────────┼────────────────────────┐
              ▼                ▼                        ▼
        Phase 1            Phase 3                  Phase 4
        Azure AD SSO       SharePoint Ingestion     Teams Bot
        (login flow)       (Graph API crawler)      (webhook)
              │
              │ writes to users table (auth_method='oidc')
              ▼
        Phase 2
        Workday Sync
        (updates same users table: full_name, department, is_active)
              │
              ▼
        RBAC enforcement: every query, agent run, ingest
        checks role + department from users table
```

### What Is Already Built (No Changes Needed)

| Component | File | Status |
|-----------|------|--------|
| SSO login tabs (Azure AD + Okta) | `frontend/src/components/Auth/Login.tsx:18-59` | ✅ Complete |
| SSO complete redirect handler | `frontend/src/app/auth/sso-complete/page.tsx` | ✅ Complete |
| `auth_method` column in users table | `migrations/versions/003_sso_tables.sql:6` | ✅ Complete |
| `oidc_role_mappings` table | `migrations/versions/003_sso_tables.sql:10-19` | ✅ Complete |
| SSO enforcement in login route | `backend/routes/auth.py:36-47` | ✅ Complete |
| RBAC + Pinecone namespace isolation | `backend/core/security.py:27-35` | ✅ Complete |
| Ingestion pipeline (PDF/DOCX/etc.) | `backend/utils/ingestion_service.py` | ✅ Complete |
| `httpx` HTTP client | `requirements.txt` | ✅ Installed |

### What You Build

| Phase | New Files | Modified Files |
|-------|-----------|----------------|
| 1 — Azure AD SSO | `tests/test_oidc_routes.py` | `backend/routes/auth.py`, `backend/core/config.py`, `requirements.txt` |
| 2 — Workday Sync | `backend/utils/workday_sync.py`, `backend/utils/scheduler.py`, `migrations/versions/004_workday_sync_log.sql`, `tests/test_workday_sync.py` | `backend/routes/admin.py`, `backend/main.py`, `requirements.txt` |
| 3 — SharePoint | `backend/utils/sharepoint_connector.py`, `backend/routes/sharepoint.py`, `migrations/versions/005_sharepoint_sites.sql`, `tests/test_sharepoint_connector.py` | `backend/utils/scheduler.py`, `backend/main.py` |
| 4 — Teams Bot | `backend/routes/teams.py`, `tests/test_teams_bot.py` | `backend/main.py`, `requirements.txt` |

---

## 2. Pre-Flight: What Huron IT Must Provide

**Nothing works without these credentials. Collect all of them before writing any code.**

### From Azure IT (Covers Phases 1, 3, 4)

```
Request from Huron IT:
─────────────────────
1. Create an Azure AD App Registration named "Huron GenAI Knowledge Assistant"
   - Account type: Single tenant
   - Redirect URI: https://yourdomain/api/v1/auth/oidc/callback
   - Create a Client Secret (save it — visible only once)
   - Add API Permissions:
       Microsoft Graph > Delegated: openid, email, profile, User.Read
       Microsoft Graph > Application: Sites.Read.All
       → Grant Admin Consent for both
   - Enable Groups claim:
       Token Configuration → Add Groups Claim → Security Groups

2. Provide you with:
   ✅ Application (Client) ID      → OIDC_CLIENT_ID
   ✅ Client Secret value          → OIDC_CLIENT_SECRET
   ✅ Directory (Tenant) ID        → tenant ID inside OIDC_AUTHORITY
   ✅ Object IDs for each department's Azure AD group (for role mapping)

3. For Teams Bot only (Phase 4):
   - Create Azure Bot Registration named "HuronKnowledge"
   - Set Messaging Endpoint: https://yourdomain/api/v1/teams/messages
   ✅ Bot App ID   → TEAMS_APP_ID
   ✅ Bot Secret   → TEAMS_APP_SECRET
```

### From Workday Admin (Phase 2)

```
Request from Huron Workday Admin:
──────────────────────────────────
1. Register an API Client in Workday:
   Workday → Menu → Register API Client
   - Client Name: Huron GenAI Integration
   - Grant Type: Client Credentials
   - Scope: Staffing (read-only)
   → Generate → save Client ID and Secret

2. Confirm the exact department names used in:
   Worker → primarySupervisoryOrganization → orgType → descriptor
   (these must match the DEPT_MAP in workday_sync.py exactly)

3. Provide you with:
   ✅ Workday Base URL             → WORKDAY_BASE_URL  (e.g. https://wd2.myworkday.com)
   ✅ Tenant name                  → WORKDAY_TENANT    (e.g. huron)
   ✅ Integration Client ID        → WORKDAY_CLIENT_ID
   ✅ Integration Client Secret    → WORKDAY_CLIENT_SECRET
```

### From SharePoint Knowledge Owners (Phase 3)

```
Request from dept leads:
─────────────────────────
✅ List of SharePoint site URLs to index, with their department:
   e.g. https://huron.sharepoint.com/sites/HR         → dept: hr
        https://huron.sharepoint.com/sites/Legal      → dept: legal
        https://huron.sharepoint.com/sites/Clinical   → dept: clinical
```

---

## 3. Environment Setup

### Step 3.1 — Install New Dependencies

```bash
cd "C:/Users/bolaf/VoultMIND_lanre/GenAI Knowledge Assistant Huron"
pip install msal==1.31.0 apscheduler==3.10.4
```

**Expected output:**
```
Successfully installed msal-1.31.0
Successfully installed APScheduler-3.10.4
```

**If this fails:**
```
ERROR: Could not find a version that satisfies the requirement msal==1.31.0
→ Fix: pip install msal  (without version pin — use latest)
→ Then check: python -c "import msal; print(msal.__version__)"
```

Add to both `requirements.txt` and `requirements_production.txt`:
```
msal==1.31.0
apscheduler==3.10.4
```

### Step 3.2 — Update config.py

Open `backend/core/config.py`. After line 64 (`PINECONE_INDEX = ...`), add:

```python
# ─── Azure AD / OIDC ─────────────────────────────────────────────────────────
OIDC_CLIENT_ID       = os.getenv("OIDC_CLIENT_ID", "")
OIDC_CLIENT_SECRET   = os.getenv("OIDC_CLIENT_SECRET", "")
OIDC_AUTHORITY       = os.getenv("OIDC_AUTHORITY", "")
OIDC_REDIRECT_URI    = os.getenv("OIDC_REDIRECT_URI", "http://localhost:8004/api/v1/auth/oidc/callback")
FRONTEND_URL         = os.getenv("FRONTEND_URL", "http://localhost:3000")

# ─── Workday ─────────────────────────────────────────────────────────────────
WORKDAY_BASE_URL      = os.getenv("WORKDAY_BASE_URL", "")
WORKDAY_TENANT        = os.getenv("WORKDAY_TENANT", "")
WORKDAY_CLIENT_ID     = os.getenv("WORKDAY_CLIENT_ID", "")
WORKDAY_CLIENT_SECRET = os.getenv("WORKDAY_CLIENT_SECRET", "")
```

Also extend the `Settings` class (after `pinecone_index: str = PINECONE_INDEX`):

```python
    oidc_client_id: str        = OIDC_CLIENT_ID
    oidc_client_secret: str    = OIDC_CLIENT_SECRET
    oidc_authority: str        = OIDC_AUTHORITY
    oidc_redirect_uri: str     = OIDC_REDIRECT_URI
    frontend_url: str          = FRONTEND_URL
    workday_base_url: str      = WORKDAY_BASE_URL
    workday_tenant: str        = WORKDAY_TENANT
    workday_client_id: str     = WORKDAY_CLIENT_ID
    workday_client_secret: str = WORKDAY_CLIENT_SECRET
```

**Expected outcome:** `python -c "from core.config import OIDC_CLIENT_ID; print('config ok')"` prints `config ok`.

**If this fails:**
```
ImportError or AttributeError
→ Check indentation inside the Settings class — Python is whitespace-sensitive
→ Run: cd backend && python -c "from core import config" to see the exact error line
```

### Step 3.3 — Update .env

Add all new variables to your local `.env` file:

```bash
# ─── Azure AD SSO ─────────────────────────────────────────────────────────
OIDC_CLIENT_ID=<paste from IT>
OIDC_CLIENT_SECRET=<paste from IT>
OIDC_AUTHORITY=https://login.microsoftonline.com/<paste-tenant-id>
OIDC_REDIRECT_URI=http://localhost:8004/api/v1/auth/oidc/callback
FRONTEND_URL=http://localhost:3000

# ─── Workday ───────────────────────────────────────────────────────────────
WORKDAY_BASE_URL=https://wd2.myworkday.com
WORKDAY_TENANT=huron
WORKDAY_CLIENT_ID=<paste from Workday admin>
WORKDAY_CLIENT_SECRET=<paste from Workday admin>

# ─── Teams Bot (Phase 4 only) ──────────────────────────────────────────────
TEAMS_APP_ID=<paste from IT>
TEAMS_APP_SECRET=<paste from IT>
```

**If credentials are not available yet:**
Leave the variables blank. The code is written to skip gracefully when variables are empty — the app starts normally and SSO/Workday features simply return a 503 until credentials are added.

### Step 3.4 — Verify Config Loads

```bash
cd backend
python -c "
from core.config import OIDC_CLIENT_ID, OIDC_AUTHORITY, WORKDAY_BASE_URL, FRONTEND_URL
print('OIDC_CLIENT_ID:', OIDC_CLIENT_ID[:8] + '...' if OIDC_CLIENT_ID else 'NOT SET')
print('OIDC_AUTHORITY:', OIDC_AUTHORITY or 'NOT SET')
print('WORKDAY_BASE_URL:', WORKDAY_BASE_URL or 'NOT SET')
print('FRONTEND_URL:', FRONTEND_URL)
"
```

**Expected output (with real credentials):**
```
OIDC_CLIENT_ID: aaaabbbb...
OIDC_AUTHORITY: https://login.microsoftonline.com/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
WORKDAY_BASE_URL: https://wd2.myworkday.com
FRONTEND_URL: http://localhost:3000
```

---

## 4. Phase 1 — Azure AD SSO

### Overview

The frontend already has the SSO tabs and the redirect handler. The only missing pieces are two backend routes:
- `/api/v1/auth/oidc/login` — redirects the browser to Microsoft's login page
- `/api/v1/auth/oidc/callback` — receives the auth code from Microsoft, exchanges it for a token, provisions the user, issues your JWT

### Complete Login Flow

```
1. User clicks "Sign in with Microsoft" on login page
2. Frontend calls: GET /api/v1/auth/oidc/login?provider=azure
3. Backend builds Microsoft authorization URL via MSAL
4. Backend returns 302 → user's browser goes to Microsoft login
5. User enters Huron email + password + Duo MFA on Microsoft's page
6. Microsoft returns 302 → GET /api/v1/auth/oidc/callback?code=xxx&state=yyy
7. Backend exchanges code for tokens (server-to-server call to Microsoft)
8. Backend reads email, name, group IDs from the token
9. Backend looks up groups in oidc_role_mappings → assigns role + dept
10. Backend creates or updates user in database
11. Backend issues your JWT
12. Backend returns 302 → frontend /auth/sso-complete?token={jwt}
13. Frontend reads token, calls /auth/me, stores user, redirects to /dashboard
```

---

### Step 4.1 — Add OIDC Routes to auth.py

Open `backend/routes/auth.py`.

**Add to the imports section at the top:**

```python
import secrets as _secrets
from urllib.parse import urlencode
from fastapi.responses import RedirectResponse
from core.config import (
    OIDC_CLIENT_ID, OIDC_CLIENT_SECRET, OIDC_AUTHORITY,
    OIDC_REDIRECT_URI, FRONTEND_URL,
)
```

**After line 26 (`_APP_ENV = os.getenv(...)`) add:**

```python
# In-memory OIDC state store (CSRF protection).
# Each login attempt generates a unique state token stored here.
# In production with multiple workers, move this to Redis.
_oidc_states: dict[str, bool] = {}
```

**Append both routes at the end of the file:**

```python
# ─── OIDC / Azure AD SSO ─────────────────────────────────────────────────────

@router.get("/oidc/login")
async def oidc_login(provider: str = "azure"):
    """
    Step 1 of SSO: redirect the browser to Microsoft's login page.
    Called by frontend Login.tsx handleSSOLogin().
    """
    if not OIDC_CLIENT_ID or not OIDC_AUTHORITY:
        raise HTTPException(
            status_code=503,
            detail="SSO is not configured on this server. Contact your administrator.",
        )

    try:
        from msal import ConfidentialClientApplication
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="MSAL package is not installed. Run: pip install msal",
        )

    # Generate CSRF state token
    state = _secrets.token_urlsafe(32)
    _oidc_states[state] = True

    # Keep state store bounded (prevent unbounded growth from abandoned logins)
    if len(_oidc_states) > 1000:
        oldest_keys = list(_oidc_states.keys())[:500]
        for k in oldest_keys:
            _oidc_states.pop(k, None)

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
async def oidc_callback(
    code: str = "",
    state: str = "",
    error: str = "",
    error_description: str = "",
):
    """
    Step 2 of SSO: Microsoft redirects here after authentication.
    Exchanges the auth code for a token, provisions the user, issues JWT.
    """
    frontend_base = f"{FRONTEND_URL}/auth/sso-complete"

    # Microsoft returned an error (user cancelled, account disabled, etc.)
    if error:
        msg = error_description or error
        return RedirectResponse(
            url=f"{frontend_base}?error={urlencode({'v': msg})[2:]}",
            status_code=302,
        )

    if not code:
        return RedirectResponse(
            url=f"{frontend_base}?error=no_auth_code_received",
            status_code=302,
        )

    if not OIDC_CLIENT_ID or not OIDC_AUTHORITY:
        return RedirectResponse(
            url=f"{frontend_base}?error=sso_not_configured_on_server",
            status_code=302,
        )

    try:
        from msal import ConfidentialClientApplication
    except ImportError:
        return RedirectResponse(
            url=f"{frontend_base}?error=msal_not_installed",
            status_code=302,
        )

    # Exchange code for tokens
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
        msg = result.get("error_description", result.get("error", "token_exchange_failed"))
        return RedirectResponse(
            url=f"{frontend_base}?error={urlencode({'v': msg})[2:]}",
            status_code=302,
        )

    # Extract identity claims from the ID token
    claims = result.get("id_token_claims", {})
    email  = (
        claims.get("preferred_username")
        or claims.get("upn")
        or claims.get("email", "")
    ).strip().lower()
    name   = claims.get("name", email)
    groups = claims.get("groups", [])   # Azure AD Security Group Object IDs

    if not email:
        return RedirectResponse(
            url=f"{frontend_base}?error=no_email_in_azure_token",
            status_code=302,
        )

    # Upsert user in database
    with db_conn() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE LOWER(email) = ?", (email,)
        ).fetchone()

        if not row:
            # New user — look up role from Azure AD group membership
            role, dept = "user", "company"
            if groups:
                placeholders = ",".join("?" * len(groups))
                mapping = conn.execute(
                    f"SELECT huron_role, dept_code FROM oidc_role_mappings "
                    f"WHERE provider='azure' AND ad_group IN ({placeholders}) LIMIT 1",
                    groups,
                ).fetchone()
                if mapping:
                    role = mapping["huron_role"]
                    dept = mapping["dept_code"] or "company"

            username = email.split("@")[0]
            conn.execute(
                """INSERT INTO users
                   (username, email, full_name, password_hash, role,
                    department, is_active, auth_method, created_by)
                   VALUES (?, ?, ?, '', ?, ?, 1, 'oidc', 'azure_ad')""",
                (username, email, name, role, dept),
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM users WHERE LOWER(email) = ?", (email,)
            ).fetchone()

        if not row["is_active"]:
            return RedirectResponse(
                url=f"{frontend_base}?error=account_deactivated_contact_admin",
                status_code=302,
            )

        # Update profile and mark last login
        conn.execute(
            """UPDATE users
               SET full_name = ?, auth_method = 'oidc', last_login = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (name, row["id"]),
        )
        conn.commit()

    user  = dict(row)
    token = create_token(user)
    write_audit(user["id"], user["username"], "sso_login_azure_ad")

    return RedirectResponse(
        url=f"{FRONTEND_URL}/auth/sso-complete?token={token}",
        status_code=302,
    )
```

---

### Step 4.2 — Add Role Mapping Admin Endpoints

Append to `backend/routes/auth.py`:

```python
# ─── OIDC Role Mapping Management ────────────────────────────────────────────

@router.get("/oidc/role-mappings")
async def list_role_mappings(p: dict = Depends(current_user)):
    """List all Azure AD group → Huron role mappings. dept_admin+ only."""
    if p.get("role") not in ("root", "dept_admin"):
        raise HTTPException(status_code=403, detail="Admin role required")
    with db_conn() as conn:
        rows = conn.execute(
            "SELECT id, provider, ad_group, huron_role, dept_code, description "
            "FROM oidc_role_mappings ORDER BY id"
        ).fetchall()
    return [dict(r) for r in rows]


@router.post("/oidc/role-mappings", status_code=201)
async def create_role_mapping(body: dict, p: dict = Depends(current_user)):
    """Create or update an Azure AD group → role mapping. root only."""
    if p.get("role") != "root":
        raise HTTPException(status_code=403, detail="root role required")

    ad_group   = (body.get("ad_group") or "").strip()
    huron_role = (body.get("huron_role") or "").strip()
    if not ad_group or not huron_role:
        raise HTTPException(status_code=422, detail="ad_group and huron_role are required")

    valid_roles = {"root", "dept_admin", "power_user", "user", "viewer"}
    if huron_role not in valid_roles:
        raise HTTPException(status_code=422, detail=f"huron_role must be one of {sorted(valid_roles)}")

    with db_conn() as conn:
        conn.execute(
            """INSERT INTO oidc_role_mappings (provider, ad_group, huron_role, dept_code, description)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT (provider, ad_group) DO UPDATE SET
                 huron_role  = excluded.huron_role,
                 dept_code   = excluded.dept_code,
                 description = excluded.description""",
            (
                body.get("provider", "azure"),
                ad_group,
                huron_role,
                body.get("dept_code"),
                body.get("description"),
            ),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM oidc_role_mappings WHERE ad_group = ?", (ad_group,)
        ).fetchone()
    return dict(row)


@router.delete("/oidc/role-mappings/{mapping_id}", status_code=204)
async def delete_role_mapping(mapping_id: int, p: dict = Depends(current_user)):
    """Delete a role mapping. root only."""
    if p.get("role") != "root":
        raise HTTPException(status_code=403, detail="root role required")
    with db_conn() as conn:
        conn.execute("DELETE FROM oidc_role_mappings WHERE id = ?", (mapping_id,))
        conn.commit()
```

---

### Step 4.3 — Test Phase 1

Create `tests/test_oidc_routes.py`:

```python
"""Tests for Azure AD OIDC SSO routes."""
import pytest
from unittest.mock import patch, MagicMock


def test_oidc_login_redirects_to_microsoft(client):
    """GET /oidc/login returns 302 pointing to login.microsoftonline.com."""
    with patch("routes.auth.OIDC_CLIENT_ID", "test-client-id"), \
         patch("routes.auth.OIDC_AUTHORITY", "https://login.microsoftonline.com/test-tenant"), \
         patch("routes.auth.OIDC_CLIENT_SECRET", "test-secret"):
        resp = client.get("/api/v1/auth/oidc/login?provider=azure", follow_redirects=False)
    assert resp.status_code in (302, 307)
    assert "login.microsoftonline.com" in resp.headers["location"]


def test_oidc_login_returns_503_when_not_configured(client):
    """GET /oidc/login returns 503 when OIDC_CLIENT_ID is not set."""
    with patch("routes.auth.OIDC_CLIENT_ID", ""), \
         patch("routes.auth.OIDC_AUTHORITY", ""):
        resp = client.get("/api/v1/auth/oidc/login?provider=azure", follow_redirects=False)
    assert resp.status_code == 503


def test_oidc_callback_exchanges_code_and_redirects_with_token(client):
    """GET /oidc/callback with valid code redirects to frontend with JWT token."""
    mock_msal = MagicMock()
    mock_msal.acquire_token_by_authorization_code.return_value = {
        "id_token_claims": {
            "preferred_username": "jane.doe@huron.com",
            "name": "Jane Doe",
            "groups": [],
        },
        "access_token": "graph-access-token",
    }
    with patch("routes.auth.OIDC_CLIENT_ID", "cid"), \
         patch("routes.auth.OIDC_AUTHORITY", "https://login.microsoftonline.com/tid"), \
         patch("routes.auth.OIDC_CLIENT_SECRET", "cs"), \
         patch("routes.auth.FRONTEND_URL", "http://localhost:3000"), \
         patch("routes.auth.ConfidentialClientApplication", return_value=mock_msal):
        resp = client.get(
            "/api/v1/auth/oidc/callback?code=valid-code&state=test-state",
            follow_redirects=False,
        )
    assert resp.status_code in (302, 307)
    location = resp.headers["location"]
    assert "sso-complete" in location
    assert "token=" in location


def test_oidc_callback_microsoft_error_redirects_to_frontend_error(client):
    """GET /oidc/callback with error param redirects to frontend error page."""
    with patch("routes.auth.FRONTEND_URL", "http://localhost:3000"):
        resp = client.get(
            "/api/v1/auth/oidc/callback?error=access_denied&error_description=User+cancelled",
            follow_redirects=False,
        )
    assert resp.status_code in (302, 307)
    assert "sso-complete" in resp.headers["location"]
    assert "error=" in resp.headers["location"]


def test_role_mapping_crud_requires_root(client, admin_token, user_token):
    """Non-root users cannot create role mappings."""
    resp = client.post(
        "/api/v1/auth/oidc/role-mappings",
        json={"ad_group": "aaa-bbb-ccc", "huron_role": "user"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 403


def test_root_can_create_role_mapping(client, root_token):
    """root user can create a role mapping."""
    resp = client.post(
        "/api/v1/auth/oidc/role-mappings",
        json={"ad_group": "aaa-bbb-ccc-ddd", "huron_role": "user",
              "dept_code": "hr", "description": "HR team"},
        headers={"Authorization": f"Bearer {root_token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["huron_role"] == "user"
```

Run:
```bash
pytest tests/test_oidc_routes.py -v
```

**Expected output:**
```
tests/test_oidc_routes.py::test_oidc_login_redirects_to_microsoft        PASSED
tests/test_oidc_routes.py::test_oidc_login_returns_503_when_not_configured PASSED
tests/test_oidc_routes.py::test_oidc_callback_exchanges_code_...         PASSED
tests/test_oidc_routes.py::test_oidc_callback_microsoft_error_...        PASSED
tests/test_oidc_routes.py::test_role_mapping_crud_requires_root          PASSED
tests/test_oidc_routes.py::test_root_can_create_role_mapping             PASSED
6 passed in 0.45s
```

**If tests fail:**

| Error | Cause | Fix |
|-------|-------|-----|
| `ImportError: cannot import name 'ConfidentialClientApplication'` | msal not installed | `pip install msal` |
| `ImportError: cannot import name 'OIDC_CLIENT_ID' from 'core.config'` | config.py not updated | Add the vars in Step 3.2 |
| `404 Not Found` on /oidc/login | Routes not registered in main.py | Check that `auth_router` is included in main.py |
| `AssertionError on status_code` | Route returns wrong code | Print `resp.json()` to see the error detail |

---

### Step 4.4 — Manual End-to-End Test

With real credentials in `.env`:

```bash
# Start the backend
cd backend && uvicorn main:app --reload --port 8004

# Start the frontend
cd frontend && npm run dev
```

1. Open `http://localhost:3000`
2. Click the **Azure AD** tab
3. Click **Sign in with Microsoft**
4. You should be redirected to `login.microsoftonline.com`
5. Enter your Huron credentials
6. After Microsoft login, you should land on `/dashboard`

**If you get redirected to `/auth/sso-complete?error=...`:**
The error message is URL-encoded in the query string. Decode it to diagnose:

| Error message | Cause | Fix |
|--------------|-------|-----|
| `sso_not_configured_on_server` | `OIDC_CLIENT_ID` or `OIDC_AUTHORITY` is empty | Check `.env` is loaded and variables are set |
| `no_email_in_azure_token` | Azure AD token doesn't include email | Huron IT must add `email` claim to Token Configuration |
| `account_deactivated_contact_admin` | User exists in DB with `is_active=0` | Set `is_active=1` in the users table or Workday sync will re-activate if worker is active |
| `AADSTS50011: The reply URL... does not match` | Redirect URI mismatch | Ensure `OIDC_REDIRECT_URI` in `.env` exactly matches what IT registered in Azure |
| `AADSTS700016: Application not found` | Wrong Client ID | Double-check `OIDC_CLIENT_ID` matches the App Registration |

---

### Step 4.5 — Commit Phase 1

```bash
git add backend/routes/auth.py backend/core/config.py requirements.txt requirements_production.txt tests/test_oidc_routes.py
git commit -m "feat(sso): implement Azure AD OIDC login and callback with auto-provisioning"
```

---

## 5. Phase 2 — Workday Employee Sync

### Overview

A background job runs nightly at 02:00 UTC. It calls the Workday REST API, pulls all workers, and upserts them into the `users` table. New hires get created. Terminated employees get `is_active=0` — they cannot log in after the next sync.

### Sync Logic

```
For each worker from Workday API:
  Extract: email, full_name, department, active (bool)
  ┌─────────────────────────────────────────────────────┐
  │ Does user with this email exist in users table?     │
  │                                                     │
  │  NO:  active=True  → INSERT (role=user, auth_method=workday)
  │       active=False → SKIP (don't create terminated users)
  │                                                     │
  │  YES: → UPDATE full_name, department, is_active     │
  │         if active changed True→False → LOG deactivated
  └─────────────────────────────────────────────────────┘
Log sync result to workday_sync_log table
```

---

### Step 5.1 — Create the Sync Log Migration

Create `backend/migrations/versions/004_workday_sync_log.sql`:

```sql
-- Migration 004: Workday sync audit log
-- Records the result of every Workday employee sync run.
CREATE TABLE IF NOT EXISTS workday_sync_log (
    id          SERIAL PRIMARY KEY,
    synced      INTEGER NOT NULL DEFAULT 0,   -- new users created
    updated     INTEGER NOT NULL DEFAULT 0,   -- existing users updated
    deactivated INTEGER NOT NULL DEFAULT 0,   -- users deactivated (terminated)
    skipped     INTEGER NOT NULL DEFAULT 0,   -- workers with no email or already inactive
    error_msg   TEXT,                          -- set if the job failed partway through
    synced_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_workday_sync_log_synced_at ON workday_sync_log(synced_at DESC);
```

---

### Step 5.2 — Create the Workday Sync Module

Create `backend/utils/workday_sync.py`:

```python
"""
Workday employee directory sync.

Pulls all workers from the Workday REST API and upserts them into the
Huron users table. Runs nightly via APScheduler (see utils/scheduler.py).

Authentication: OAuth 2.0 Client Credentials (server-to-server).
Huron IT sets this up in: Workday → Menu → Register API Client.

DEPT_MAP: maps Workday department names to Huron dept codes.
Update this map if Huron's Workday uses different department names.
"""
from __future__ import annotations

import logging
from datetime import datetime

import httpx

from core.config import (
    WORKDAY_BASE_URL,
    WORKDAY_TENANT,
    WORKDAY_CLIENT_ID,
    WORKDAY_CLIENT_SECRET,
)
from core.database import db_conn

logger = logging.getLogger(__name__)

# ─── Department Name Mapping ──────────────────────────────────────────────────
# Keys = Workday orgType.descriptor values (confirm with Huron IT)
# Values = Huron dept codes
DEPT_MAP: dict[str, str] = {
    "Human Resources":        "hr",
    "Finance":                "finance",
    "Legal":                  "legal",
    "Clinical":               "clinical",
    "Operations":             "operations",
    "Information Technology": "it",
    "Marketing":              "marketing",
}


def _get_workday_token() -> str:
    """Obtain an OAuth 2.0 access token from Workday using client credentials."""
    resp = httpx.post(
        f"{WORKDAY_BASE_URL}/ccx/oauth2/{WORKDAY_TENANT}/token",
        data={
            "grant_type":    "client_credentials",
            "client_id":     WORKDAY_CLIENT_ID,
            "client_secret": WORKDAY_CLIENT_SECRET,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def _list_workers(token: str) -> list[dict]:
    """
    Paginate through all workers in Workday.
    Returns a flat list of raw worker objects.
    """
    headers  = {"Authorization": f"Bearer {token}"}
    workers: list[dict] = []
    url: str | None = f"{WORKDAY_BASE_URL}/ccx/api/v1/{WORKDAY_TENANT}/workers"

    while url:
        resp = httpx.get(url, headers=headers, params={"limit": 100}, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        workers.extend(data.get("data", []))
        total = data.get("total", {})
        url   = total.get("nextPage") if isinstance(total, dict) else None

    return workers


def sync_workday_employees() -> dict[str, int]:
    """
    Main sync function. Called by APScheduler and the manual admin endpoint.

    Returns:
        dict with keys: synced, updated, deactivated, skipped
    """
    if not all([WORKDAY_BASE_URL, WORKDAY_TENANT, WORKDAY_CLIENT_ID, WORKDAY_CLIENT_SECRET]):
        logger.warning(
            "Workday sync skipped — one or more WORKDAY_* env vars are not set. "
            "Set WORKDAY_BASE_URL, WORKDAY_TENANT, WORKDAY_CLIENT_ID, WORKDAY_CLIENT_SECRET."
        )
        return {"synced": 0, "updated": 0, "deactivated": 0, "skipped": 0}

    error_msg   = None
    synced      = 0
    updated     = 0
    deactivated = 0
    skipped     = 0

    try:
        token   = _get_workday_token()
        workers = _list_workers(token)

        with db_conn() as conn:
            for worker in workers:
                email = (worker.get("primaryWorkEmail") or "").strip().lower()
                if not email:
                    skipped += 1
                    continue

                first = (
                    worker.get("legalNameData", {})
                    .get("firstNameData", {})
                    .get("value", "")
                )
                last  = (
                    worker.get("legalNameData", {})
                    .get("lastNameData", {})
                    .get("value", "")
                )
                full_name = f"{first} {last}".strip()

                org_desc  = (
                    worker.get("primarySupervisoryOrganization", {})
                    .get("orgType", {})
                    .get("descriptor", "")
                )
                dept_code = DEPT_MAP.get(org_desc, "company")
                is_active = bool(worker.get("active", False))

                row = conn.execute(
                    "SELECT id, is_active FROM users WHERE LOWER(email) = ?", (email,)
                ).fetchone()

                if row:
                    was_active = bool(row["is_active"])
                    conn.execute(
                        "UPDATE users SET full_name = ?, department = ?, is_active = ? WHERE id = ?",
                        (full_name, dept_code, is_active, row["id"]),
                    )
                    if was_active and not is_active:
                        deactivated += 1
                        logger.info("Deactivated terminated employee: %s", email)
                    else:
                        updated += 1
                else:
                    if is_active:
                        username = email.split("@")[0]
                        conn.execute(
                            """INSERT INTO users
                               (username, email, full_name, password_hash, role,
                                department, is_active, auth_method, created_by)
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

    except Exception as exc:
        error_msg = str(exc)
        logger.error("Workday sync failed: %s", exc, exc_info=True)
        try:
            with db_conn() as conn:
                conn.execute(
                    "INSERT INTO workday_sync_log (synced, updated, deactivated, skipped, error_msg) "
                    "VALUES (0, 0, 0, 0, ?)",
                    (error_msg,),
                )
                conn.commit()
        except Exception:
            pass

    logger.info(
        "Workday sync complete: synced=%d updated=%d deactivated=%d skipped=%d error=%s",
        synced, updated, deactivated, skipped, error_msg,
    )
    return {"synced": synced, "updated": updated, "deactivated": deactivated, "skipped": skipped}
```

---

### Step 5.3 — Create APScheduler Setup

Create `backend/utils/scheduler.py`:

```python
"""
APScheduler background job registry.
Start: called in main.py lifespan startup.
Stop:  called in main.py lifespan shutdown.

Add all recurring background jobs here.
"""
from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="UTC")


def register_jobs() -> None:
    """Register all background jobs. Called once at application startup."""

    # ── Workday nightly sync ─────────────────────────────────────────────────
    from utils.workday_sync import sync_workday_employees
    scheduler.add_job(
        sync_workday_employees,
        CronTrigger(hour=2, minute=0),
        id="workday_sync",
        replace_existing=True,
        misfire_grace_time=3600,
        coalesce=True,
    )
    logger.info("Registered: Workday employee sync — daily at 02:00 UTC")

    # ── SharePoint weekly sync (registered in Phase 3) ───────────────────────
    # See utils/scheduler.py Phase 3 section below
```

**Add to `backend/main.py` startup and shutdown:**

Find the startup handler (look for `@app.on_event("startup")` or the `lifespan` context manager). Add:

```python
# In startup:
from utils.scheduler import scheduler, register_jobs
register_jobs()
scheduler.start()
logger.info("APScheduler started with %d jobs", len(scheduler.get_jobs()))

# In shutdown:
from utils.scheduler import scheduler
if scheduler.running:
    scheduler.shutdown(wait=False)
    logger.info("APScheduler stopped")
```

---

### Step 5.4 — Add Manual Sync Endpoint to admin.py

Open `backend/routes/admin.py` and append:

```python
@router.post("/workday/sync")
async def trigger_workday_sync(p: dict = Depends(current_user)):
    """
    Manually trigger a Workday employee sync. root only.
    Returns sync counts: synced, updated, deactivated, skipped.
    """
    if p.get("role") != "root":
        raise HTTPException(status_code=403, detail="root role required")

    from utils.workday_sync import sync_workday_employees
    try:
        result = sync_workday_employees()
        write_audit(p["user_id"], p["sub"], "workday_sync_manual")
        return {"status": "ok", **result}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Workday sync failed: {exc}")


@router.get("/workday/sync-log")
async def get_workday_sync_log(p: dict = Depends(current_user)):
    """Return the last 20 Workday sync runs. root only."""
    if p.get("role") != "root":
        raise HTTPException(status_code=403, detail="root role required")
    with db_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM workday_sync_log ORDER BY synced_at DESC LIMIT 20"
        ).fetchall()
    return [dict(r) for r in rows]
```

---

### Step 5.5 — Test Phase 2

Create `tests/test_workday_sync.py`:

```python
"""Tests for Workday employee sync."""
import pytest
from unittest.mock import patch, MagicMock


def test_get_workday_token_returns_access_token():
    from utils.workday_sync import _get_workday_token
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"access_token": "wday-token-123", "token_type": "Bearer"}
    mock_resp.raise_for_status = MagicMock()
    with patch("utils.workday_sync.httpx.post", return_value=mock_resp), \
         patch("utils.workday_sync.WORKDAY_BASE_URL", "https://wd.example.com"), \
         patch("utils.workday_sync.WORKDAY_TENANT", "huron"), \
         patch("utils.workday_sync.WORKDAY_CLIENT_ID", "cid"), \
         patch("utils.workday_sync.WORKDAY_CLIENT_SECRET", "cs"):
        token = _get_workday_token()
    assert token == "wday-token-123"


def test_sync_skips_when_env_vars_missing():
    from utils.workday_sync import sync_workday_employees
    with patch("utils.workday_sync.WORKDAY_BASE_URL", ""), \
         patch("utils.workday_sync.WORKDAY_TENANT", ""):
        result = sync_workday_employees()
    assert result == {"synced": 0, "updated": 0, "deactivated": 0, "skipped": 0}


def test_sync_inserts_new_active_worker():
    from utils.workday_sync import sync_workday_employees
    workers = [{
        "primaryWorkEmail": "jane.doe@huron.com",
        "legalNameData": {
            "firstNameData": {"value": "Jane"},
            "lastNameData":  {"value": "Doe"},
        },
        "primarySupervisoryOrganization": {"orgType": {"descriptor": "Human Resources"}},
        "active": True,
    }]
    with patch("utils.workday_sync._get_workday_token", return_value="tok"), \
         patch("utils.workday_sync._list_workers", return_value=workers), \
         patch("utils.workday_sync.WORKDAY_BASE_URL", "https://wd.example.com"), \
         patch("utils.workday_sync.WORKDAY_TENANT", "huron"), \
         patch("utils.workday_sync.WORKDAY_CLIENT_ID", "cid"), \
         patch("utils.workday_sync.WORKDAY_CLIENT_SECRET", "cs"):
        result = sync_workday_employees()
    assert result["synced"] == 1


def test_sync_deactivates_terminated_worker():
    from utils.workday_sync import sync_workday_employees
    workers = [{
        "primaryWorkEmail": "terminated@huron.com",
        "legalNameData": {"firstNameData": {"value": "Ex"}, "lastNameData": {"value": "User"}},
        "primarySupervisoryOrganization": {"orgType": {"descriptor": "Finance"}},
        "active": False,
    }]
    with patch("utils.workday_sync._get_workday_token", return_value="tok"), \
         patch("utils.workday_sync._list_workers", return_value=workers), \
         patch("utils.workday_sync.WORKDAY_BASE_URL", "https://wd.example.com"), \
         patch("utils.workday_sync.WORKDAY_TENANT", "huron"), \
         patch("utils.workday_sync.WORKDAY_CLIENT_ID", "cid"), \
         patch("utils.workday_sync.WORKDAY_CLIENT_SECRET", "cs"):
        result = sync_workday_employees()
    # Terminated user doesn't exist yet, so skipped (not deactivated)
    assert result["skipped"] == 1


def test_sync_skips_workers_without_email():
    from utils.workday_sync import sync_workday_employees
    workers = [{"primaryWorkEmail": "", "active": True}]
    with patch("utils.workday_sync._get_workday_token", return_value="tok"), \
         patch("utils.workday_sync._list_workers", return_value=workers), \
         patch("utils.workday_sync.WORKDAY_BASE_URL", "https://wd.example.com"), \
         patch("utils.workday_sync.WORKDAY_TENANT", "huron"), \
         patch("utils.workday_sync.WORKDAY_CLIENT_ID", "cid"), \
         patch("utils.workday_sync.WORKDAY_CLIENT_SECRET", "cs"):
        result = sync_workday_employees()
    assert result["skipped"] == 1
```

Run:
```bash
pytest tests/test_workday_sync.py -v
```

**Expected output:**
```
tests/test_workday_sync.py::test_get_workday_token_returns_access_token   PASSED
tests/test_workday_sync.py::test_sync_skips_when_env_vars_missing         PASSED
tests/test_workday_sync.py::test_sync_inserts_new_active_worker           PASSED
tests/test_workday_sync.py::test_sync_deactivates_terminated_worker       PASSED
tests/test_workday_sync.py::test_sync_skips_workers_without_email         PASSED
5 passed in 0.31s
```

**If tests fail:**

| Error | Cause | Fix |
|-------|-------|-----|
| `ModuleNotFoundError: utils.workday_sync` | File not created yet | Create `backend/utils/workday_sync.py` |
| `httpx.HTTPStatusError: 401` | Wrong client credentials | Confirm `WORKDAY_CLIENT_ID` and `WORKDAY_CLIENT_SECRET` with Huron Workday admin |
| `httpx.HTTPStatusError: 404` | Wrong Workday base URL or tenant | Confirm `WORKDAY_BASE_URL` and `WORKDAY_TENANT` — the token URL must be `{BASE_URL}/ccx/oauth2/{TENANT}/token` |
| `KeyError: 'access_token'` | Workday returned error in body | Print `resp.json()` to see the Workday error message |
| Workers list returns empty `[]` | Workday API scope too narrow | Workday admin must grant Staffing scope on the integration client |
| Dept always maps to `company` | Department names don't match DEPT_MAP | Print `org_desc` and compare to DEPT_MAP keys — update map to match |

---

### Step 5.6 — Commit Phase 2

```bash
git add backend/utils/workday_sync.py \
        backend/utils/scheduler.py \
        backend/routes/admin.py \
        backend/main.py \
        backend/migrations/versions/004_workday_sync_log.sql \
        tests/test_workday_sync.py
git commit -m "feat(workday): nightly employee sync with APScheduler, deactivation on termination"
```

---

## 6. Phase 3 — SharePoint Document Ingestion

### Overview

SharePoint sites contain Huron's internal knowledge. This phase crawls configured sites every Sunday via Microsoft Graph API, downloads the files, and feeds them into the existing ingestion pipeline. The same Azure AD App Registration from Phase 1 is reused — Huron IT only needs to add one extra permission (`Sites.Read.All`).

### File Flow

```
SharePoint site
      │
      ▼  (Graph API — client credentials, same Azure AD app as SSO)
List all files (filter to supported MIME types only)
      │
      ▼
Download each file as raw bytes
      │
      ▼
ingestion_service.ingest_file_bytes(bytes, filename, mime, dept_code)
      │  [existing code — no changes needed]
      ▼
Chunked → Embedded (text-embedding-3-small) → Pinecone upsert
      │
      ▼
Document appears in all 4 tabs: Chat, Query, Agent, Research
```

---

### Step 6.1 — Create the SharePoint Sites Migration

Create `backend/migrations/versions/005_sharepoint_sites.sql`:

```sql
-- Migration 005: SharePoint site configurations
-- Stores which SharePoint sites to crawl and which dept namespace to write to.
CREATE TABLE IF NOT EXISTS sharepoint_sites (
    id           SERIAL PRIMARY KEY,
    site_url     TEXT NOT NULL UNIQUE,
    dept_code    TEXT NOT NULL,
    display_name TEXT NOT NULL DEFAULT '',
    is_active    BOOLEAN NOT NULL DEFAULT TRUE,
    last_synced  TIMESTAMPTZ,
    files_indexed INTEGER NOT NULL DEFAULT 0,
    configured_by TEXT NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sharepoint_sites_dept ON sharepoint_sites(dept_code);
```

---

### Step 6.2 — Create the SharePoint Connector

Create `backend/utils/sharepoint_connector.py`:

```python
"""
Microsoft SharePoint document connector via Graph API.

Uses the SAME Azure AD App Registration as OIDC SSO (Phase 1).
Huron IT must grant: Sites.Read.All (Application permission) with admin consent.

The connector authenticates as the application (client credentials — no user
interaction required), resolves the SharePoint site URL to a Graph site ID,
lists all files in the root drive, and downloads supported file types.

Downloaded bytes are passed to ingestion_service.ingest_file_bytes() unchanged.
"""
from __future__ import annotations

import logging

import httpx

from core.config import OIDC_CLIENT_ID, OIDC_CLIENT_SECRET, OIDC_AUTHORITY

logger = logging.getLogger(__name__)

GRAPH_ENDPOINT = "https://graph.microsoft.com/v1.0"

# Only download file types the ingestion pipeline supports.
SUPPORTED_MIME_TYPES: frozenset[str] = frozenset({
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",   # .docx
    "application/vnd.openxmlformats-officedocument.presentationml.presentation", # .pptx
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",         # .xlsx
    "text/plain",
    "text/html",
    "text/markdown",
    "application/json",
})

MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB guard — skip very large files


def _get_graph_token() -> str:
    """
    Obtain a Graph API access token using client credentials flow.
    This is server-to-server — no user interaction needed.
    """
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
    Return metadata for all supported files in a SharePoint site's root drive.

    site_url format: "https://huron.sharepoint.com/sites/HR"

    Returns list of dicts with keys: id, name, mime, drive_id, size
    """
    token   = _get_graph_token()
    headers = {"Authorization": f"Bearer {token}"}

    # Resolve site URL to a Graph site ID
    url_no_scheme = site_url.replace("https://", "").replace("http://", "")
    parts    = url_no_scheme.split("/", 1)
    hostname = parts[0]
    path     = parts[1] if len(parts) > 1 else ""

    site_resp = httpx.get(
        f"{GRAPH_ENDPOINT}/sites/{hostname}:/{path}",
        headers=headers,
        timeout=30,
    )
    site_resp.raise_for_status()
    site_id = site_resp.json()["id"]

    # List root drive children
    files_resp = httpx.get(
        f"{GRAPH_ENDPOINT}/sites/{site_id}/drive/root/children",
        headers=headers,
        timeout=30,
    )
    files_resp.raise_for_status()
    items = files_resp.json().get("value", [])

    result = []
    for item in items:
        mime = item.get("file", {}).get("mimeType", "")
        size = item.get("size", 0)
        if mime not in SUPPORTED_MIME_TYPES:
            continue
        if size > MAX_FILE_SIZE_BYTES:
            logger.warning("Skipping large file %s (%d bytes > %d limit)",
                           item.get("name"), size, MAX_FILE_SIZE_BYTES)
            continue
        result.append({
            "id":       item["id"],
            "name":     item["name"],
            "mime":     mime,
            "drive_id": item.get("parentReference", {}).get("driveId", ""),
            "size":     size,
        })

    logger.info("Found %d supported files in %s", len(result), site_url)
    return result


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

---

### Step 6.3 — Create SharePoint Admin Routes

Create `backend/routes/sharepoint.py`:

```python
"""
SharePoint integration admin routes.

GET    /api/v1/sharepoint/sites              list registered sites (dept_admin+)
POST   /api/v1/sharepoint/sites              register new site (root)
DELETE /api/v1/sharepoint/sites/{id}         remove a site (root)
POST   /api/v1/sharepoint/sites/{id}/sync    sync one site now (root)
POST   /api/v1/sharepoint/sync-all           sync all active sites now (root)
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from core.database import db_conn, write_audit
from core.security import current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/sharepoint", tags=["sharepoint"])

VALID_DEPT_CODES = frozenset({
    "company", "hr", "legal", "finance", "clinical",
    "operations", "it", "marketing", "external",
})


@router.get("/sites")
async def list_sites(p: dict = Depends(current_user)):
    if p.get("role") not in ("root", "dept_admin"):
        raise HTTPException(status_code=403, detail="Admin role required")
    with db_conn() as conn:
        rows = conn.execute(
            "SELECT id, site_url, dept_code, display_name, is_active, "
            "last_synced, files_indexed FROM sharepoint_sites ORDER BY created_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


@router.post("/sites", status_code=201)
async def add_site(body: dict, p: dict = Depends(current_user)):
    if p.get("role") != "root":
        raise HTTPException(status_code=403, detail="root role required")

    site_url     = (body.get("site_url") or "").strip().rstrip("/")
    dept_code    = (body.get("dept_code") or "").strip()
    display_name = (body.get("display_name") or site_url).strip()

    if not site_url:
        raise HTTPException(status_code=422, detail="site_url is required")
    if not site_url.startswith("https://"):
        raise HTTPException(status_code=422, detail="site_url must start with https://")
    if dept_code not in VALID_DEPT_CODES:
        raise HTTPException(
            status_code=422,
            detail=f"dept_code must be one of: {sorted(VALID_DEPT_CODES)}",
        )

    with db_conn() as conn:
        try:
            conn.execute(
                "INSERT INTO sharepoint_sites (site_url, dept_code, display_name, configured_by) "
                "VALUES (?, ?, ?, ?)",
                (site_url, dept_code, display_name, p["sub"]),
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM sharepoint_sites WHERE site_url = ?", (site_url,)
            ).fetchone()
        except Exception as exc:
            if "UNIQUE" in str(exc).upper():
                raise HTTPException(status_code=409, detail="This site URL is already registered")
            raise

    write_audit(p["user_id"], p["sub"], "sharepoint_site_added", detail=site_url)
    return dict(row)


@router.delete("/sites/{site_id}", status_code=204)
async def remove_site(site_id: int, p: dict = Depends(current_user)):
    if p.get("role") != "root":
        raise HTTPException(status_code=403, detail="root role required")
    with db_conn() as conn:
        conn.execute("DELETE FROM sharepoint_sites WHERE id = ?", (site_id,))
        conn.commit()
    write_audit(p["user_id"], p["sub"], "sharepoint_site_removed", detail=str(site_id))


@router.post("/sites/{site_id}/sync")
async def sync_one_site(site_id: int, p: dict = Depends(current_user)):
    """Immediately crawl and ingest one SharePoint site."""
    if p.get("role") != "root":
        raise HTTPException(status_code=403, detail="root role required")
    with db_conn() as conn:
        row = conn.execute(
            "SELECT * FROM sharepoint_sites WHERE id = ?", (site_id,)
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Site not found")
    write_audit(p["user_id"], p["sub"], "sharepoint_sync_manual", detail=row["site_url"])
    return await _run_site_sync(dict(row), p["sub"])


@router.post("/sync-all")
async def sync_all_sites(p: dict = Depends(current_user)):
    """Immediately crawl and ingest all active SharePoint sites."""
    if p.get("role") != "root":
        raise HTTPException(status_code=403, detail="root role required")
    with db_conn() as conn:
        sites = [dict(r) for r in conn.execute(
            "SELECT * FROM sharepoint_sites WHERE is_active = 1"
        ).fetchall()]
    results = [await _run_site_sync(site, p["sub"]) for site in sites]
    write_audit(p["user_id"], p["sub"], "sharepoint_sync_all")
    return {"sites_attempted": len(results), "results": results}


async def _run_site_sync(site: dict, triggered_by: str) -> dict:
    """Core sync logic — list files, download, ingest. Used by both routes and scheduler."""
    from utils.sharepoint_connector import list_site_files, download_file
    site_url  = site["site_url"]
    dept_code = site["dept_code"]
    files_ok  = 0
    errors    = []

    try:
        files = list_site_files(site_url)
    except Exception as exc:
        logger.error("Failed to list files for %s: %s", site_url, exc)
        return {"site_url": site_url, "error": str(exc), "files_ingested": 0}

    for f in files:
        try:
            content = download_file(f["drive_id"], f["id"])
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
            logger.info("Ingested %s → %s (%d bytes)", f["name"], dept_code, f["size"])
        except Exception as exc:
            logger.warning("Failed to ingest %s: %s", f["name"], exc)
            errors.append({"file": f["name"], "error": str(exc)})

    with db_conn() as conn:
        conn.execute(
            "UPDATE sharepoint_sites SET last_synced = CURRENT_TIMESTAMP, files_indexed = ? WHERE id = ?",
            (files_ok, site["id"]),
        )
        conn.commit()

    return {
        "site_url":       site_url,
        "files_ingested": files_ok,
        "files_failed":   len(errors),
        "errors":         errors,
    }
```

---

### Step 6.4 — Register Router + Add Weekly Scheduler Job

**In `backend/main.py`**, find where other routers are included and add:
```python
from routes.sharepoint import router as sharepoint_router
app.include_router(sharepoint_router)
```

**In `backend/utils/scheduler.py`**, add inside `register_jobs()`:
```python
    # ── SharePoint weekly sync ────────────────────────────────────────────────
    async def _scheduled_sharepoint_sync():
        from core.database import db_conn
        from routes.sharepoint import _run_site_sync
        with db_conn() as conn:
            sites = [dict(r) for r in conn.execute(
                "SELECT * FROM sharepoint_sites WHERE is_active = 1"
            ).fetchall()]
        for site in sites:
            await _run_site_sync(site, "scheduler")

    scheduler.add_job(
        _scheduled_sharepoint_sync,
        CronTrigger(day_of_week="sun", hour=3, minute=0),
        id="sharepoint_sync",
        replace_existing=True,
        misfire_grace_time=3600,
        coalesce=True,
    )
    logger.info("Registered: SharePoint sync — weekly on Sunday at 03:00 UTC")
```

---

### Step 6.5 — Test Phase 3

Create `tests/test_sharepoint_connector.py`:

```python
"""Tests for SharePoint Graph API connector."""
from unittest.mock import patch, MagicMock


def test_get_graph_token_uses_client_credentials():
    from utils.sharepoint_connector import _get_graph_token
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"access_token": "graph-tok-abc"}
    mock_resp.raise_for_status = MagicMock()
    with patch("utils.sharepoint_connector.httpx.post", return_value=mock_resp), \
         patch("utils.sharepoint_connector.OIDC_CLIENT_ID", "cid"), \
         patch("utils.sharepoint_connector.OIDC_CLIENT_SECRET", "cs"), \
         patch("utils.sharepoint_connector.OIDC_AUTHORITY",
               "https://login.microsoftonline.com/test-tenant-id"):
        token = _get_graph_token()
    assert token == "graph-tok-abc"


def test_list_site_files_filters_unsupported_types():
    from utils.sharepoint_connector import list_site_files
    mock_site  = MagicMock()
    mock_site.json.return_value = {"id": "site-abc"}
    mock_site.raise_for_status  = MagicMock()

    mock_files = MagicMock()
    mock_files.json.return_value = {"value": [
        {"id": "f1", "name": "policy.pdf",
         "file": {"mimeType": "application/pdf"},
         "parentReference": {"driveId": "drv1"}, "size": 100},
        {"id": "f2", "name": "photo.png",
         "file": {"mimeType": "image/png"},
         "parentReference": {"driveId": "drv1"}, "size": 200},
        {"id": "f3", "name": "contract.docx",
         "file": {"mimeType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
         "parentReference": {"driveId": "drv1"}, "size": 300},
    ]}
    mock_files.raise_for_status = MagicMock()

    with patch("utils.sharepoint_connector._get_graph_token", return_value="tok"), \
         patch("utils.sharepoint_connector.httpx.get",
               side_effect=[mock_site, mock_files]):
        files = list_site_files("https://huron.sharepoint.com/sites/Legal")

    assert len(files) == 2  # photo.png is filtered out
    assert all(f["mime"] != "image/png" for f in files)


def test_list_site_files_skips_oversized_files():
    from utils.sharepoint_connector import list_site_files, MAX_FILE_SIZE_BYTES
    mock_site  = MagicMock()
    mock_site.json.return_value = {"id": "site-abc"}
    mock_site.raise_for_status  = MagicMock()

    mock_files = MagicMock()
    mock_files.json.return_value = {"value": [
        {"id": "f1", "name": "huge.pdf",
         "file": {"mimeType": "application/pdf"},
         "parentReference": {"driveId": "drv1"},
         "size": MAX_FILE_SIZE_BYTES + 1},
    ]}
    mock_files.raise_for_status = MagicMock()

    with patch("utils.sharepoint_connector._get_graph_token", return_value="tok"), \
         patch("utils.sharepoint_connector.httpx.get",
               side_effect=[mock_site, mock_files]):
        files = list_site_files("https://huron.sharepoint.com/sites/Finance")

    assert len(files) == 0  # oversized file skipped
```

Run:
```bash
pytest tests/test_sharepoint_connector.py -v
```

**Expected output:**
```
tests/test_sharepoint_connector.py::test_get_graph_token_uses_client_credentials PASSED
tests/test_sharepoint_connector.py::test_list_site_files_filters_unsupported_types PASSED
tests/test_sharepoint_connector.py::test_list_site_files_skips_oversized_files    PASSED
3 passed in 0.28s
```

**If tests fail:**

| Error | Cause | Fix |
|-------|-------|-----|
| `httpx.HTTPStatusError: 403 Forbidden` from Graph API | `Sites.Read.All` not granted | Huron IT must grant `Sites.Read.All` Application permission with admin consent |
| `KeyError: 'id'` on site_resp.json() | SharePoint site URL format wrong | URL must be `https://{tenant}.sharepoint.com/sites/{name}` — no trailing slash |
| `httpx.HTTPStatusError: 401` | Wrong Azure AD credentials or token expired | Confirm `OIDC_CLIENT_ID` and `OIDC_CLIENT_SECRET` match the App Registration |
| Files list is empty | Files are in subfolders, not root | Add recursive folder crawl — Graph API supports `$expand=children` |
| `AttributeError: ingest_file_bytes` | Function name wrong in ingestion_service | Check `backend/utils/ingestion_service.py` for the actual function name |

---

### Step 6.6 — Commit Phase 3

```bash
git add backend/utils/sharepoint_connector.py \
        backend/routes/sharepoint.py \
        backend/utils/scheduler.py \
        backend/main.py \
        backend/migrations/versions/005_sharepoint_sites.sql \
        tests/test_sharepoint_connector.py
git commit -m "feat(sharepoint): Graph API crawler with weekly scheduler and admin CRUD"
```

---

## 7. Phase 4 — Microsoft Teams Bot (Optional)

### Overview

Staff send a message to `@HuronKnowledge` inside Teams. The bot receives it via a Bot Framework webhook, queries your existing RAG pipeline, and replies with an Adaptive Card showing the answer and citations.

### Prerequisites

1. Huron IT creates an **Azure Bot Registration** and provides `TEAMS_APP_ID` and `TEAMS_APP_SECRET`
2. Teams Admin Center approves the app for Huron's tenant
3. Messaging endpoint configured to `https://yourdomain/api/v1/teams/messages`

---

### Step 7.1 — Install Bot Framework Dependencies

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
TEAMS_APP_ID=your-azure-bot-app-id
TEAMS_APP_SECRET=your-azure-bot-app-secret
```

---

### Step 7.2 — Create the Teams Bot Route

Create `backend/routes/teams.py`:

```python
"""
Microsoft Teams bot webhook.

Receives Bot Framework Activity objects from Teams, queries the RAG
pipeline, and replies with an Adaptive Card.

Setup:
  1. Huron IT creates Azure Bot Registration
  2. Set Messaging Endpoint: https://yourdomain/api/v1/teams/messages
  3. Add Teams channel in Azure Bot → Channels → Microsoft Teams
  4. Set TEAMS_APP_ID and TEAMS_APP_SECRET in environment
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
    """Build an Adaptive Card payload with answer and source citations."""
    body: list[dict] = [
        {
            "type":   "TextBlock",
            "text":   "Huron Knowledge Assistant",
            "weight": "Bolder",
            "size":   "Medium",
            "color":  "Accent",
        },
        {
            "type": "TextBlock",
            "text": answer,
            "wrap": True,
        },
    ]

    if sources:
        body.append({
            "type": "FactSet",
            "facts": [
                {"title": f"[{i+1}]", "value": src}
                for i, src in enumerate(sources[:5])
            ],
        })

    return {
        "contentType": "application/vnd.microsoft.card.adaptive",
        "content": {
            "type":    "AdaptiveCard",
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "version": "1.4",
            "body":    body,
        },
    }


@router.post("/messages")
async def teams_messages(request: Request):
    """
    Main Teams bot endpoint.
    Must always return HTTP 200 to Bot Framework, even on errors.
    """
    if not TEAMS_APP_ID or not TEAMS_APP_SECRET:
        logger.warning(
            "Teams bot received a message but TEAMS_APP_ID/SECRET are not set. "
            "Set them in .env and restart."
        )
        return Response(status_code=200)

    try:
        from botbuilder.core import BotFrameworkAdapter, BotFrameworkAdapterSettings, TurnContext
        from botbuilder.schema import Activity
    except ImportError:
        logger.error(
            "botbuilder-core is not installed. Run: pip install botbuilder-core==4.14.8"
        )
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

        answer  = "I could not find an answer. Please try rephrasing your question."
        sources = []

        try:
            from agent.tools import rag_search
            result  = rag_search(query=query, dept="company", top_k=5)
            answer  = result.get("answer", answer)
            sources = [s.get("source", "") for s in result.get("sources", []) if s.get("source")]
        except Exception as exc:
            logger.error("Teams bot RAG call failed for query '%s': %s", query[:100], exc)
            answer = (
                "I encountered an error while searching the knowledge base. "
                "Please try again or open the web app at https://huron-knowledge.yourcompany.com"
            )

        card = _build_adaptive_card(answer, sources)

        from botbuilder.core.message_factory import MessageFactory
        reply = MessageFactory.attachment(card)   # type: ignore[arg-type]
        await turn_context.send_activity(reply)

    auth_header = request.headers.get("Authorization", "")
    try:
        await adapter.process_activity(activity, auth_header, _turn_handler)
    except Exception as exc:
        logger.error("Bot Framework adapter error: %s", exc)

    return Response(status_code=200)
```

---

### Step 7.3 — Register Teams Router in main.py

```python
from routes.teams import router as teams_router
app.include_router(teams_router)
```

---

### Step 7.4 — Test Phase 4

Create `tests/test_teams_bot.py`:

```python
"""Tests for Microsoft Teams bot webhook."""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock


def test_teams_messages_returns_200_when_not_configured(client):
    """Webhook always returns 200, even when not configured."""
    with patch("routes.teams.TEAMS_APP_ID", ""), \
         patch("routes.teams.TEAMS_APP_SECRET", ""):
        resp = client.post(
            "/api/v1/teams/messages",
            json={"type": "message", "text": "Hello"},
        )
    assert resp.status_code == 200


def test_build_adaptive_card_includes_answer_and_sources():
    from routes.teams import _build_adaptive_card
    card = _build_adaptive_card(
        answer="PTO is 15 days per year.",
        sources=["HR Policy v2.pdf", "Employee Handbook 2025.docx"],
    )
    assert card["contentType"] == "application/vnd.microsoft.card.adaptive"
    body = card["content"]["body"]
    # Find the answer TextBlock
    texts = [b["text"] for b in body if b["type"] == "TextBlock"]
    assert any("PTO" in t for t in texts)
    # Find the FactSet with citations
    fact_sets = [b for b in body if b["type"] == "FactSet"]
    assert len(fact_sets) == 1
    assert len(fact_sets[0]["facts"]) == 2


def test_build_adaptive_card_limits_sources_to_five():
    from routes.teams import _build_adaptive_card
    card = _build_adaptive_card("Answer", ["src" + str(i) for i in range(10)])
    fact_sets = [b for b in card["content"]["body"] if b["type"] == "FactSet"]
    assert len(fact_sets[0]["facts"]) == 5  # capped at 5
```

Run:
```bash
pytest tests/test_teams_bot.py -v
```

**Expected output:**
```
tests/test_teams_bot.py::test_teams_messages_returns_200_when_not_configured PASSED
tests/test_teams_bot.py::test_build_adaptive_card_includes_answer_and_sources PASSED
tests/test_teams_bot.py::test_build_adaptive_card_limits_sources_to_five      PASSED
3 passed in 0.22s
```

**If tests fail:**

| Error | Cause | Fix |
|-------|-------|-----|
| `ImportError: botbuilder` | Not installed | `pip install botbuilder-core==4.14.8` |
| Bot returns 401 in prod | Wrong App ID/Secret | Confirm `TEAMS_APP_ID` matches the Azure Bot App Registration ID exactly |
| Bot responds but no card renders | Adaptive Card schema wrong | Check the `$schema` URL and `version` — Teams requires version >= 1.0 |
| Bot registered but no response | Messaging endpoint unreachable from Internet | Endpoint must be HTTPS on port 443, publicly accessible — use ngrok for local dev testing |

---

### Step 7.5 — Commit Phase 4

```bash
git add backend/routes/teams.py backend/main.py requirements.txt requirements_production.txt tests/test_teams_bot.py
git commit -m "feat(teams): add Teams bot webhook with Adaptive Card RAG responses"
```

---

## 8. Testing All Integrations End-to-End

### Run Full Test Suite

```bash
cd "C:/Users/bolaf/VoultMIND_lanre/GenAI Knowledge Assistant Huron"
pytest tests/test_oidc_routes.py tests/test_workday_sync.py tests/test_sharepoint_connector.py tests/test_teams_bot.py -v --tb=short
```

**Expected output:**
```
tests/test_oidc_routes.py                6 passed
tests/test_workday_sync.py               5 passed
tests/test_sharepoint_connector.py       3 passed
tests/test_teams_bot.py                  3 passed
========= 17 passed in 1.42s =========
```

### Manual Integration Smoke Tests

| Test | How | Expected |
|------|-----|----------|
| Azure AD login | Open app → Azure AD tab → Sign in | Lands on /dashboard with correct name and dept |
| Wrong Azure group | Log in as user with no group mapping | Assigned role=user, dept=company (default) |
| Workday manual sync | `POST /api/v1/admin/workday/sync` (root token) | `{"status":"ok","synced":N,...}` |
| Workday termination | Set a worker's `active=false` in Workday → run sync | User is_active=0 in DB, cannot log in |
| SharePoint register site | `POST /api/v1/sharepoint/sites` | 201 with site record |
| SharePoint sync | `POST /api/v1/sharepoint/sites/1/sync` | Files appear in Query/Chat tabs |
| Teams message | Send message to bot in Teams | Receives Adaptive Card with answer |

---

## 9. Deployment Checklist

### GitHub Actions Secrets to Add

```
OIDC_CLIENT_ID
OIDC_CLIENT_SECRET
OIDC_AUTHORITY
OIDC_REDIRECT_URI          (update to staging/prod domain)
FRONTEND_URL               (update to staging/prod domain)
WORKDAY_BASE_URL
WORKDAY_TENANT
WORKDAY_CLIENT_ID
WORKDAY_CLIENT_SECRET
TEAMS_APP_ID               (Phase 4 only)
TEAMS_APP_SECRET           (Phase 4 only)
```

### Pre-Launch Checks

- [ ] `OIDC_REDIRECT_URI` in `.env` matches exactly what IT registered in Azure portal
- [ ] `Sites.Read.All` admin consent granted by Huron IT
- [ ] Workday department names in `DEPT_MAP` confirmed with Workday admin
- [ ] `workday_sync_log` table created (migration 004 ran)
- [ ] `sharepoint_sites` table created (migration 005 ran)
- [ ] `oidc_role_mappings` populated with Huron Azure AD Group Object IDs
- [ ] Bot Framework messaging endpoint reachable from the internet (prod only)
- [ ] All 17 integration tests passing in CI

---

## 10. Troubleshooting Reference

### Azure AD SSO

| Symptom | Likely cause | Resolution |
|---------|-------------|------------|
| `/oidc/login` returns 503 | `OIDC_CLIENT_ID` or `OIDC_AUTHORITY` not set | Check `.env` and restart backend |
| Redirect loop on login | Redirect URI mismatch | `OIDC_REDIRECT_URI` must exactly match Azure App Registration — same scheme, domain, path, no trailing slash |
| `AADSTS700016` error | Wrong Client ID | Copy exact value from Azure portal App Registration Overview |
| `AADSTS50011` redirect URI error | URI not whitelisted | Huron IT adds `https://yourdomain/api/v1/auth/oidc/callback` in App Registration |
| User auto-provisioned with wrong role | Groups claim missing | Huron IT enables Groups claim in Token Configuration |
| `preferred_username` is empty | B2B guest account format | Use `claims.get("upn")` or `claims.get("email")` as fallback — already handled in callback code |

### Workday Sync

| Symptom | Likely cause | Resolution |
|---------|-------------|------------|
| Sync skipped, logs say `env vars not set` | Missing WORKDAY_* vars | Add all 4 Workday vars to `.env` |
| `401 Unauthorized` from Workday | Wrong client credentials | Regenerate credentials in Workday → Register API Client |
| `404 Not Found` on token URL | Wrong base URL or tenant | Token URL format: `{WORKDAY_BASE_URL}/ccx/oauth2/{WORKDAY_TENANT}/token` |
| Workers list empty | API scope too narrow | Workday admin must add Staffing scope to the integration client |
| All workers map to `company` dept | Department names don't match | Log the `org_desc` value and update `DEPT_MAP` keys in `workday_sync.py` |
| Sync runs but no DB updates | DB write error | Check `workday_sync_log` for `error_msg`; check DB permissions |

### SharePoint

| Symptom | Likely cause | Resolution |
|---------|-------------|------------|
| `403 Forbidden` from Graph API | `Sites.Read.All` not granted | Huron IT: App Registration → API Permissions → Sites.Read.All → Admin Consent |
| `401 Unauthorized` | Wrong Azure credentials | Confirm `OIDC_CLIENT_ID` and `OIDC_CLIENT_SECRET` from Phase 1 |
| Site URL resolution fails | URL format wrong | Must be `https://{tenant}.sharepoint.com/sites/{name}` exactly |
| No files returned | Files in subfolders | Root drive lists only direct children — extend with recursive Graph API calls if needed |
| Files ingested but not searchable | Pinecone namespace issue | Check that `dept_code` matches one of the 9 valid codes |
| Large files fail | File > 50 MB | Files above `MAX_FILE_SIZE_BYTES` are skipped by design — confirmed in logs |

### Teams Bot

| Symptom | Likely cause | Resolution |
|---------|-------------|------------|
| Bot registered but doesn't respond | Endpoint not reachable | URL must be HTTPS on port 443, Internet-accessible. Test with ngrok locally. |
| `401 Unauthorized` in Bot Framework | Wrong `TEAMS_APP_ID` or `TEAMS_APP_SECRET` | Must match the Azure Bot Registration exactly |
| Card renders but no answer | RAG pipeline error | Check backend logs for the `Teams bot RAG call failed` error line |
| Bot responds in plain text, not card | `MessageFactory.attachment` type error | Ensure botbuilder-core version is 4.14.8 — older versions have different attachment API |
| Bot approved but not visible in Teams | App manifest not uploaded | Teams Admin Center → Manage Apps → Upload custom app → upload `manifest.json` |
