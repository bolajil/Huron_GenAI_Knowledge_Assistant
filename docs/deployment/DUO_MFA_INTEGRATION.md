# Duo MFA Integration — Huron GenAI Knowledge Assistant

**Status:** No code changes required for SSO users — Duo is enforced by Azure AD  
**Confirmed setup:** Huron uses Duo Security as the MFA provider inside Azure AD (Entra ID).  
When any company user authenticates via SSO, Duo Push fires on their enrolled smartphone
before Microsoft issues the OIDC token. The Huron app receives a token that is already MFA-verified.

---

## How It Works End-to-End

```
User visits Huron app → clicks "Sign in with Microsoft"
         ↓
Browser redirects to /api/v1/auth/oidc/login
         ↓
Backend redirects to Microsoft Entra ID login page (Microsoft-hosted)
         ↓
User enters company email + password
         ↓
Azure AD Conditional Access policy triggers Duo MFA requirement
         ↓
Duo Push notification sent to user's enrolled smartphone
         ↓
User taps "Approve" on Duo Mobile app
         ↓ (or taps "Deny" → login blocked, no token issued)
Microsoft issues signed OIDC ID token (contains groups + email)
         ↓
Browser redirects to /api/v1/auth/oidc/callback?code=...
         ↓
Backend exchanges code → reads ID token → maps AD groups → Huron role
         ↓
Backend sets auth_method = 'oidc' and issues Huron JWT
         ↓
User lands on dashboard — fully authenticated with Duo MFA
```

**The Duo challenge is entirely within Microsoft's login page.
The Huron backend never calls Duo APIs directly.**

---

## What Is and Is Not Protected

| Login path | Duo protected? | Reason |
|------------|----------------|--------|
| Sign in with Microsoft (SSO) | ✅ Yes | Azure AD Conditional Access enforces Duo before issuing token |
| Local username + password | ❌ No | Bypasses Azure AD entirely — no Duo trigger |
| Root service account (local) | ❌ No by design | Emergency access — must be kept but access-controlled |

**Action required:** Enforce SSO-only login for all named company users.
See [Section: Enforcing SSO-Only Login](#enforcing-sso-only-login-for-company-users) below.

---

## Azure AD Conditional Access — Verify Duo Is Enforced for This App

Duo being in the tenant does not automatically mean it fires for every app.
A Conditional Access policy must target the Huron app registration specifically.

### Step 1 — Verify the Conditional Access policy

1. **Azure Portal → Microsoft Entra ID → Security → Conditional Access → Policies**
2. Look for a policy named something like `Require MFA for all apps` or `Duo MFA Policy`
3. Confirm the policy:
   - **Assignments → Users:** includes `All users` or the Huron AD groups
   - **Assignments → Target resources:** includes `All cloud apps` OR specifically
     `Huron GenAI Knowledge Assistant` (your app registration name from OIDC setup)
   - **Access controls → Grant:** `Require multi-factor authentication` is checked
4. Confirm **Policy status:** is `On` (not Report-only)

### Step 2 — If no policy exists targeting this app, create one

1. **New policy** → name: `Huron GenAI — Require Duo MFA`
2. **Assignments → Users:** select the AD groups that map to Huron roles
   (same groups from `OIDC_SSO_SETUP.md` Step 5)
3. **Assignments → Target resources → Cloud apps → Select apps:**
   search for `Huron GenAI Knowledge Assistant` → select it
4. **Access controls → Grant:**
   - Select `Require multi-factor authentication`
   - Grant: `Require all the selected controls`
5. **Session:** leave defaults
6. **Enable policy → On → Save**

### Step 3 — Test the policy

Open an **incognito/private browser window** and go to:
```
https://<backend-fqdn>/api/v1/auth/oidc/login
```

You should see:
1. Redirect to Microsoft login page
2. Enter company email + password
3. **Duo Push appears on your phone**
4. Tap Approve → land on Huron dashboard

If Duo does **not** fire, the Conditional Access policy is not targeting this app — revisit Step 2.

---

## How the Backend Tracks Auth Method

The `users` table stores `auth_method` for every user:

```@backend/main.py:2555-2558
conn.execute(
    "INSERT INTO users (username,email,password_hash,role,department,is_active,auth_method) "
    "VALUES (?,?,?,?,?,1,'oidc')",
    (email.split("@")[0], email, hashed, huron_role, dept_code),
)
```

- Users who log in via SSO → `auth_method = 'oidc'` — **Duo-protected**
- Users who log in via local password → `auth_method = 'local'` — **no Duo**
- The `root` service account → `auth_method = 'local'` — **no Duo by design**

This field is queryable — you can audit which users are and aren't SSO-protected at any time:

```sql
SELECT username, email, role, auth_method, last_login
FROM users
WHERE auth_method != 'oidc'
  AND username != 'root'
ORDER BY last_login DESC;
```

Any result from this query is a user who has **bypassed Duo**.

---

## Enforcing SSO-Only Login for Company Users

**This is already implemented** in `backend/routes/auth.py`.

The enforcement is **environment-gated** — local login works normally in `dev` for
developer convenience. In `staging` and `production`, any user with `auth_method = 'oidc'`
is blocked from the local password endpoint entirely.

### How it works (`backend/routes/auth.py`)

```python
_SSO_ENFORCED_ENVS = {"staging", "production", "prod"}
_APP_ENV = os.getenv("APP_ENV", "dev").lower()

# Inside POST /api/v1/auth/login — runs before bcrypt password check:
if (
    _APP_ENV in _SSO_ENFORCED_ENVS
    and user.get("auth_method") == "oidc"
    and user["username"] != "root"
):
    write_audit(user["id"], user["username"], "local_login_blocked_sso_required")
    raise HTTPException(
        status_code=403,
        detail="This account uses company SSO. Please sign in with Microsoft.",
    )
```

The `get_user_by_login` function in `backend/core/database.py` now includes `auth_method`
in its SELECT so the check always has the value available.

### Behaviour per environment

| `APP_ENV` | SSO user tries local login | Local-only user | root |
|-----------|---------------------------|-----------------|------|
| `dev` | ✅ Allowed (dev convenience) | ✅ Allowed | ✅ Allowed |
| `staging` | ❌ 403 — redirected to SSO | ✅ Allowed | ✅ Allowed |
| `production` | ❌ 403 — redirected to SSO | ✅ Allowed | ✅ Allowed |

### Who is exempt

| Account | auth_method | Exempt from SSO-only? | Reason |
|---------|-------------|----------------------|--------|
| `root` | `local` | Yes | Emergency / initial setup access |
| API service accounts | `local` | Yes | Automated processes, no browser |
| All named company users | `oidc` | No | Must use SSO → Duo fires automatically |

### Frontend handling

When the backend returns `403` with `"Please sign in with Microsoft"`, the login page
should detect this specific message and display the "Sign in with Microsoft" SSO button
instead of a generic error. The `OIDC_SSO_SETUP.md` frontend snippet already conditionally
renders the SSO button when the OIDC endpoint is available.

---

## Root Account — Emergency Access Hardening

The `root` account must remain a local account (no Azure AD dependency for emergencies)
but it needs compensating controls since it has no Duo:

1. **Strong password** — minimum 24 characters, stored only in Azure Key Vault
   ```bash
   az keyvault secret set --vault-name <kv-name> --name "root-password" --value "<24-char-password>"
   ```

2. **IP allowlist for root login** — restrict the local login endpoint for `root` to
   known admin IPs only (configurable in Container Apps ingress or a request middleware):
   ```python
   ADMIN_ALLOWED_IPS = os.getenv("ADMIN_ALLOWED_IPS", "").split(",")
   # Check at login endpoint: if username == "root" and client IP not in allowlist → 403
   ```

3. **Audit log every root login** — already logged via `log_query` but add an explicit
   Sentry alert on root login:
   ```python
   if username == "root":
       sentry_sdk.capture_message("Root login", level="warning",
           extras={"ip": request.client.host})
   ```

4. **Rotate root password after every use** — policy, not code. Document this in your
   security runbook.

---

## Checking Duo Status in the Deep Health Check

Add Duo reachability to the `/health` endpoint so monitoring can detect if the SSO/Duo
chain is broken (separately from the app being up):

```python
# In backend/routes/health.py — add to the checks dict:
async def _check_duo_reachable() -> dict:
    """Verify Microsoft login endpoint is reachable — proxy for SSO/Duo availability."""
    import httpx
    authority = os.getenv("OIDC_AUTHORITY", "")
    if not authority:
        return {"status": "not_configured"}
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{authority}/v2.0/.well-known/openid-configuration")
        return {"status": "ok" if r.status_code == 200 else "degraded",
                "latency_ms": int(r.elapsed.total_seconds() * 1000)}
    except Exception as e:
        return {"status": "unreachable", "error": str(e)}
```

When this check returns `unreachable`, SSO logins fail and all company users are locked out.
Set a Better Stack monitor on `/health` → alert if `sso` check is not `ok`.

---

## Audit Query — MFA Coverage Report

Run this against the production database to confirm MFA coverage:

```sql
SELECT
  auth_method,
  role,
  COUNT(*) AS user_count,
  COUNT(CASE WHEN last_login > datetime('now', '-30 days') THEN 1 END) AS active_last_30d
FROM users
WHERE is_active = 1
GROUP BY auth_method, role
ORDER BY auth_method, role;
```

**Target state:**

| auth_method | Expected users |
|-------------|---------------|
| `oidc` | All named company users — all Duo-protected |
| `local` | Only `root` + any API service accounts |

If you see named company users with `auth_method = 'local'`, those users have not yet
logged in via SSO. Notify them to use "Sign in with Microsoft" on next login — their
`auth_method` will update to `'oidc'` automatically on first SSO login.

---

## Summary Checklist

- [ ] Verify Conditional Access policy exists in Azure AD targeting the Huron app registration
- [ ] Confirm policy status is `On` (not Report-only)
- [ ] Test: SSO login triggers Duo Push on phone before token is issued
- [ ] Implement SSO-only enforcement in `POST /api/v1/auth/login` (block `auth_method = 'oidc'` accounts)
- [ ] Store `root` password in Azure Key Vault
- [ ] Add IP allowlist check for `root` local login
- [ ] Add Sentry alert on root login event
- [ ] Add `sso` reachability check to `/health` endpoint
- [ ] Run MFA coverage audit query — confirm all company users are `auth_method = 'oidc'`
- [ ] Add Better Stack monitor alert for SSO endpoint unreachable

---

## Related Documents

- `docs/deployment/OIDC_SSO_SETUP.md` — Azure AD app registration and group mapping setup
- `docs/deployment/MIGRATION_TO_AZURE.md` — Phase 7 (SSO setup steps for deployment)
- `docs/deployment/MIGRATION_TO_AZURE.md` — Phase 10.1 (Sentry alerts)
- `docs/observability/SETUP.md` — Better Stack monitor configuration

---

*Last updated: 2026-06-08*
