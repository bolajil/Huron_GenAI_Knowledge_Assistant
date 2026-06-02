# Huron GenAI — SSO / Active Directory Integration Plan

## Current State

The SSO foundation is partially built. The login UI already has three tabs
(Local, Azure AD, Okta SSO), and the backend has an OIDC skeleton that handles
the authorization code flow. Several gaps prevent it from working end-to-end.

```
Login UI (3 tabs)          Backend OIDC Skeleton          Missing
──────────────────         ──────────────────────         ────────────────────
✅ Local tab               ✅ /api/v1/auth/oidc/login     ❌ sso-complete page
✅ Azure AD tab            ✅ /api/v1/auth/oidc/callback  ❌ URL mismatch
✅ Okta SSO tab            ✅ AD group → role mapping     ❌ oidc_role_mappings table
✅ SSO button UI           ✅ Auto-provision on first      ❌ auth_method in DB
                               login                       ❌ OIDC env vars in infra
                                                           ❌ Okta separate route
```

---

## How SSO Works (the full flow)

```
User clicks "Sign in with Azure AD"
    │
    ▼
Frontend redirects to: /api/v1/auth/oidc/login?provider=azure
    │
    ▼
Backend redirects to: https://login.microsoftonline.com/<tenant>/oauth2/v2.0/authorize
    │  (Microsoft/Okta shows their own login page)
    ▼
User authenticates with corporate credentials + MFA (if configured in Azure)
    │
    ▼
Microsoft redirects back to: /api/v1/auth/oidc/callback?code=xxx
    │
    ▼
Backend exchanges code for ID token
    │  Reads: email, AD groups from token
    │  Maps AD group → Huron role via oidc_role_mappings table
    │  Creates user in DB if first login (auth_method = 'oidc')
    │  Issues Huron JWT
    ▼
Backend redirects to: /auth/sso-complete?token=<huron_jwt>
    │
    ▼
Frontend sso-complete page reads token from URL
    Stores in localStorage/cookie
    Redirects to /dashboard
```

---

## Phase 1 — Fix the Existing Skeleton (Code Gaps)

### 1.1 Fix URL Mismatch

**Problem:** Frontend calls `/api/v1/auth/sso/azure` but backend route is `/api/v1/auth/oidc/login`

**File:** `frontend/src/components/Auth/Login.tsx`

```tsx
// CURRENT (broken):
const handleSSOLogin = (provider: "azure" | "okta") => {
  window.location.href = `/api/v1/auth/sso/${provider}`;
};

// FIX:
const handleSSOLogin = (provider: "azure" | "okta") => {
  window.location.href = `${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/oidc/login?provider=${provider}`;
};
```

### 1.2 Create Frontend sso-complete Page

**File:** `frontend/src/app/auth/sso-complete/page.tsx` (create new)

```tsx
"use client";

import { useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "../../../contexts/auth-context";
import { Loader2 } from "lucide-react";

export default function SsoCompletePage() {
  const router = useRouter();
  const params = useSearchParams();
  const { loginWithToken } = useAuth();

  useEffect(() => {
    const token = params.get("token");
    const error = params.get("error");

    if (error) {
      router.replace(`/login?error=${encodeURIComponent(error)}`);
      return;
    }

    if (token) {
      loginWithToken(token);   // store token + fetch user profile
      router.replace("/dashboard");
    } else {
      router.replace("/login?error=sso_failed");
    }
  }, [params, router, loginWithToken]);

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center">
        <Loader2 className="h-8 w-8 animate-spin mx-auto text-primary mb-3" />
        <p className="text-muted-foreground text-sm">Completing sign-in...</p>
      </div>
    </div>
  );
}
```

### 1.3 Add loginWithToken to Auth Context

**File:** `frontend/src/contexts/auth-context.tsx` — add method:

```tsx
const loginWithToken = (token: string) => {
  localStorage.setItem("huron_token", token);
  // fetch /api/v1/auth/me to populate user state
  api.getMe().then(setUser);
};
```

### 1.4 Update Backend — Support provider param

**File:** `backend/main.py` — update `/api/v1/auth/oidc/login`:

```python
@app.get("/api/v1/auth/oidc/login")
async def oidc_login(provider: str = "azure"):
    """Redirect to Azure AD or Okta based on provider param."""
    if provider == "okta":
        authority = os.getenv("OKTA_AUTHORITY", "")
        client_id = os.getenv("OKTA_CLIENT_ID", "")
    else:  # azure (default)
        authority = _OIDC_AUTHORITY
        client_id = _OIDC_CLIENT_ID

    if not (client_id and authority):
        raise HTTPException(status_code=501,
            detail=f"{provider.title()} SSO not configured on this server")

    params = {
        "client_id":     client_id,
        "response_type": "code",
        "redirect_uri":  os.getenv("OIDC_REDIRECT_URI"),
        "scope":         "openid profile email groups",
        "state":         f"{provider}:{secrets.token_urlsafe(16)}",
    }
    return RedirectResponse(url=f"{authority}/oauth2/v2.0/authorize?{urlencode(params)}")
```

### 1.5 Add Database Migration for SSO Tables

**File:** `backend/migrations/versions/003_sso_tables.sql`

```sql
-- Migration 003: SSO / OIDC support tables

-- Track which auth method each user uses
ALTER TABLE users ADD COLUMN IF NOT EXISTS auth_method TEXT DEFAULT 'local';
-- Values: 'local', 'oidc', 'saml'

-- Map Azure AD / Okta group IDs to Huron roles and departments
CREATE TABLE IF NOT EXISTS oidc_role_mappings (
    id          SERIAL PRIMARY KEY,
    provider    TEXT NOT NULL DEFAULT 'azure',  -- 'azure' or 'okta'
    ad_group    TEXT NOT NULL,                  -- Azure group object ID or Okta group name
    huron_role  TEXT NOT NULL,                  -- root/dept_admin/power_user/user/viewer
    dept_code   TEXT,                           -- hr/legal/finance/clinical/etc
    description TEXT,                           -- human-readable note
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (provider, ad_group)
);

CREATE INDEX IF NOT EXISTS idx_oidc_role_mappings_group ON oidc_role_mappings(ad_group);

-- Example seed data (customize with real group IDs from Azure):
-- INSERT INTO oidc_role_mappings (provider, ad_group, huron_role, dept_code, description)
-- VALUES
--   ('azure', 'HR-Team-GroupID',       'user',       'hr',       'HR department users'),
--   ('azure', 'HR-Managers-GroupID',   'dept_admin', 'hr',       'HR managers'),
--   ('azure', 'Legal-Team-GroupID',    'user',       'legal',    'Legal department'),
--   ('azure', 'IT-Admins-GroupID',     'dept_admin', 'it',       'IT team'),
--   ('azure', 'Huron-Admins-GroupID',  'root',       NULL,       'System administrators');
```

---

## Phase 2 — Azure AD App Registration (Huron IT Steps)

These steps are done once by Huron IT in the Azure portal.

### Step 1 — Register the Application

1. Go to **Azure Portal → Azure Active Directory → App registrations → New registration**
2. Name: `Huron GenAI Knowledge Assistant`
3. Supported account types: `Accounts in this organizational directory only`
4. Redirect URI (Web):
   - Staging: `https://staging.huron.ai/api/v1/auth/oidc/callback`
   - Production: `https://app.huron.ai/api/v1/auth/oidc/callback`
   - Local dev: `http://localhost:8004/api/v1/auth/oidc/callback`

### Step 2 — Get Credentials

After registration, collect:
- **Application (client) ID** → `OIDC_CLIENT_ID`
- **Directory (tenant) ID** → used in `OIDC_AUTHORITY`
- **OIDC_AUTHORITY** = `https://login.microsoftonline.com/<tenant-id>`

Create a client secret:
- **Certificates & secrets → New client secret**
- Copy the **Value** immediately → `OIDC_CLIENT_SECRET`

### Step 3 — Add Group Claims

So Huron can map AD groups to roles:
1. **Token configuration → Add groups claim**
2. Select: `Security groups`
3. For ID token: check `Group ID` (returns object IDs)

### Step 4 — Set API Permissions

Add permissions:
- `openid` (sign users in)
- `profile` (read basic profile)
- `email` (read email address)
- `GroupMember.Read.All` (read group memberships)

Click **Grant admin consent**.

### Step 5 — Add to Secrets Manager / tfvars

```hcl
# In staging.tfvars and prod.tfvars:
oidc_client_id     = "<Application Client ID from Azure>"
oidc_client_secret = "<Client Secret Value from Azure>"
oidc_authority     = "https://login.microsoftonline.com/<Tenant ID>"
oidc_redirect_uri  = "https://staging.huron.ai/api/v1/auth/oidc/callback"
frontend_url       = "https://staging.huron.ai"
```

---

## Phase 3 — Okta App Setup (Alternative to Azure AD)

If Huron uses Okta instead of (or in addition to) Azure AD:

### Okta Admin Console Steps

1. **Applications → Create App Integration**
2. Sign-in method: `OIDC - OpenID Connect`
3. Application type: `Web Application`
4. Sign-in redirect URIs:
   - `https://app.huron.ai/api/v1/auth/oidc/callback`
5. Sign-out redirect URIs: `https://app.huron.ai/login`
6. Assignments: assign to the Huron user groups

### Collect from Okta

- **Client ID** → `OKTA_CLIENT_ID`
- **Client Secret** → `OKTA_CLIENT_SECRET`
- **Okta Domain** → `OKTA_AUTHORITY` = `https://<your-domain>.okta.com`

### Group Claims in Okta

1. **Directory → Profile Editor → User (default)**
2. Add attribute: `groups` (array of strings)
3. **Security → API → Authorization Servers → default → Claims**
4. Add claim: name=`groups`, include in=`ID Token`, value=`Groups`

---

## Phase 4 — Role Mapping Configuration (Admin UI)

After SSO is working, admins need a UI to map AD groups to Huron roles
without editing SQL directly.

**Planned endpoint:** `GET/POST/DELETE /api/v1/admin/sso/role-mappings`

**Planned admin UI page:** `frontend/src/app/dashboard/admin/security/page.tsx`
(file already exists — add SSO role mapping table to it)

The UI shows:
| AD Group ID | Provider | Huron Role | Department | Actions |
|-------------|----------|-----------|-----------|---------|
| HR-Team-xxxx | Azure | user | hr | Edit / Delete |
| IT-Admins-xxxx | Azure | dept_admin | it | Edit / Delete |

---

## Phase 5 — Testing the Full Flow

### Local Testing

```bash
# Add to backend/.env for local SSO testing:
OIDC_CLIENT_ID=<from Azure app registration>
OIDC_CLIENT_SECRET=<client secret>
OIDC_AUTHORITY=https://login.microsoftonline.com/<tenant>
OIDC_REDIRECT_URI=http://localhost:8004/api/v1/auth/oidc/callback
FRONTEND_URL=http://localhost:3000
```

Test sequence:
1. Start backend on port 8004
2. Start frontend on port 3000
3. Click "Azure AD" tab on login page
4. Click "Sign in with Azure AD"
5. Should redirect to Microsoft login
6. After Microsoft auth, should return to `/auth/sso-complete`
7. Should end up on dashboard with correct role

### What to Verify

- [ ] User auto-provisioned in `users` table with `auth_method='oidc'`
- [ ] AD group correctly mapped to Huron role
- [ ] Department assigned from group mapping
- [ ] JWT issued and works for all API calls
- [ ] Logout works (token blacklisted)
- [ ] Second login (existing user) doesn't create duplicate

---

## Summary — What to Get from Huron IT

| Item | Purpose |
|------|---------|
| Azure AD Tenant ID | `OIDC_AUTHORITY` URL |
| Azure App Client ID | `OIDC_CLIENT_ID` |
| Azure App Client Secret | `OIDC_CLIENT_SECRET` |
| Azure AD Group Object IDs | For `oidc_role_mappings` table |
| Decision: Azure AD only, or Okta as well? | Determines which routes to build |
| Is Okta used? If yes, Okta domain + Client ID/Secret | `OKTA_*` env vars |

---

## Implementation Checklist

### Code (can do now)
- [ ] Fix URL mismatch in `Login.tsx` (`/api/v1/auth/sso/azure` → `/api/v1/auth/oidc/login?provider=azure`)
- [ ] Create `frontend/src/app/auth/sso-complete/page.tsx`
- [ ] Add `loginWithToken()` to auth context
- [ ] Update backend `/oidc/login` to accept `provider` param
- [ ] Create `backend/migrations/versions/003_sso_tables.sql`

### Requires Huron IT
- [ ] Azure AD app registration + credentials
- [ ] Group claims configured in Azure
- [ ] AD group IDs collected and inserted into `oidc_role_mappings`
- [ ] Okta app setup (if applicable)

### Infrastructure (after credentials received)
- [ ] Add `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET`, `OIDC_AUTHORITY` to Secrets Manager
- [ ] Update `staging.tfvars` and `prod.tfvars` with OIDC variables
- [ ] Add redirect URIs to Azure app registration for staging/prod domains
