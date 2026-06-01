# OIDC / Active Directory SSO Setup

**Goal:** Enable "Sign in with Microsoft" so users authenticate via their existing Active Directory accounts. Zero new passwords to manage. Group membership in AD automatically maps to the correct Huron RBAC role.

**Approach:** OAuth 2.0 Authorization Code flow via Microsoft Entra ID (Azure AD). The backend has an OIDC skeleton already in place — you just need to register the app in Entra ID and configure the environment variables.

---

## How it works

```
Browser → /api/v1/auth/oidc/login
        → Redirect to Microsoft login page
        → User signs in with AD credentials
        → Microsoft redirects to /api/v1/auth/oidc/callback?code=...
        → Backend exchanges code for ID token
        → Backend reads AD group memberships from ID token
        → Backend maps AD groups → Huron roles (via oidc_role_mappings table)
        → Backend issues Huron JWT
        → User lands on dashboard (same session as username/password login)
```

New users are auto-provisioned on first SSO login. Existing users (by email) are matched and their role is updated from the AD group mapping.

---

## Step 1 — Register the app in Microsoft Entra ID (Azure Portal)

1. Go to **Azure Portal → Microsoft Entra ID → App registrations → New registration**
2. Fill in:
   - **Name:** `Huron GenAI Knowledge Assistant`
   - **Supported account types:** Accounts in this organizational directory only (Single tenant)
   - **Redirect URI:** Web → `https://api.huronconsultinggroup.com/api/v1/auth/oidc/callback`
   - For dev: also add `http://localhost:8004/api/v1/auth/oidc/callback`
3. Click **Register**
4. Copy the **Application (client) ID** — this is `OIDC_CLIENT_ID`
5. Copy the **Directory (tenant) ID** — used in `OIDC_AUTHORITY`

---

## Step 2 — Create a client secret

1. In the app registration → **Certificates & secrets → New client secret**
2. Description: `huron-backend-prod`, Expires: 24 months
3. Copy the **Value** immediately (shown only once) — this is `OIDC_CLIENT_SECRET`

---

## Step 3 — Configure API permissions

1. **API permissions → Add a permission → Microsoft Graph → Delegated**
2. Add: `openid`, `profile`, `email`, `User.Read`
3. For group membership in the ID token: Add `GroupMember.Read.All`
4. Click **Grant admin consent**

---

## Step 4 — Add groups claim to the token

1. In app registration → **Token configuration → Add groups claim**
2. Select: **Security groups**
3. For ID token, include: **Group ID** (this gives the AD Object ID of each group)

---

## Step 5 — Get AD group Object IDs

For each group you want to map to a Huron role:

1. Azure Portal → **Microsoft Entra ID → Groups → search for your group**
2. Copy the **Object ID** — this is the `ad_group` value in `oidc_role_mappings`

Example groups and roles:
| AD Group Name | Object ID (example) | Huron Role |
|--------------|---------------------|------------|
| Huron-KM-Root | 00000000-0000-0000-0000-000000000001 | root |
| Huron-KM-DeptAdmins | 00000000-0000-0000-0000-000000000002 | dept_admin |
| Huron-KM-PowerUsers | 00000000-0000-0000-0000-000000000003 | power_user |
| Huron-KM-Users | 00000000-0000-0000-0000-000000000004 | user |

---

## Step 6 — Configure environment variables

Add to AWS Secrets Manager (production) or `.env.local` (dev):

```ini
OIDC_CLIENT_ID=<Application (client) ID from Step 1>
OIDC_CLIENT_SECRET=<Value from Step 2>
OIDC_AUTHORITY=https://login.microsoftonline.com/<Directory (tenant) ID>
OIDC_REDIRECT_URI=https://api.huronconsultinggroup.com/api/v1/auth/oidc/callback
FRONTEND_URL=https://huronconsultinggroup.com
```

---

## Step 7 — Create AD group → Role mappings in the database

As root, use the API or connect to the database directly:

```sql
-- Replace with real AD group Object IDs from Step 5
INSERT INTO oidc_role_mappings (ad_group, huron_role, dept_code, description, created_by)
VALUES
  ('00000000-0000-0000-0000-000000000001', 'root',       NULL,     'KM Root Admins',          'setup'),
  ('00000000-0000-0000-0000-000000000002', 'dept_admin', NULL,     'KM Dept Admins',           'setup'),
  ('00000000-0000-0000-0000-000000000003', 'power_user', 'clinical','Clinical Power Users',    'setup'),
  ('00000000-0000-0000-0000-000000000004', 'user',       NULL,     'General KM Users',         'setup');
```

Or via the future admin UI (Route: Admin → SSO → Group Mappings).

---

## Step 8 — Test SSO

1. Visit `https://huronconsultinggroup.com`
2. Click **"Sign in with Microsoft"** (button added to login page)
3. Complete Microsoft authentication
4. You should land on the dashboard with your AD-derived role

If you get a 502/error, check backend logs in CloudWatch for the OIDC callback error message.

---

## Adding the SSO Button to the Login Page

The frontend login page needs a button that calls `GET /api/v1/auth/oidc/login`. If `OIDC_CLIENT_ID` is not set the endpoint returns 501, so the button should only render when SSO is available.

Check `/api/v1/auth/oidc/login` availability on frontend load:

```typescript
// In login page component
const [ssoAvailable, setSsoAvailable] = useState(false);

useEffect(() => {
  fetch('/api/v1/auth/oidc/login', { method: 'HEAD' })
    .then(r => setSsoAvailable(r.status !== 501))
    .catch(() => {});
}, []);

// Then conditionally render:
{ssoAvailable && (
  <a href="/api/v1/auth/oidc/login"
     className="btn-sso">
    Sign in with Microsoft
  </a>
)}
```

---

## Handling the SSO Callback Landing Page

The backend redirects to `FRONTEND_URL/auth/sso-complete?token=<jwt>`. Create this page to complete the login:

```typescript
// frontend/src/app/auth/sso-complete/page.tsx
"use client";
import { useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";

export default function SsoComplete() {
  const router = useRouter();
  const params = useSearchParams();

  useEffect(() => {
    const token = params.get("token");
    if (token) {
      localStorage.setItem("huron_token", token);
      router.push("/dashboard");
    } else {
      router.push("/login?error=sso_failed");
    }
  }, []);

  return <div>Completing sign-in…</div>;
}
```

---

## Security Notes

- The OIDC callback does **not** verify the `state` parameter in the current skeleton — add CSRF state verification before production.
- The JWT issued after SSO has the same 8-hour expiry as password-based JWTs.
- AD group changes take effect on next login (no real-time sync — acceptable for most enterprise deployments).
- The `OIDC_CLIENT_SECRET` must be rotated in Secrets Manager before the Entra ID secret expires (24-month recommendation).
