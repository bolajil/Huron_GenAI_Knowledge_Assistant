# Copy this file to .secrets.sh and fill in your values.
# .secrets.sh is in .gitignore — NEVER commit it.

export OPENAI_API_KEY=""
export PINECONE_API_KEY=""
export JWT_SECRET=""        # python3 -c "import secrets; print(secrets.token_urlsafe(32))"
export MCP_ENCRYPTION_KEY=""
export POSTGRES_PASSWORD="" # e.g. HuronXyz2026!

# Azure AD App Registration (portal.azure.com → Entra ID → App registrations)
export OIDC_CLIENT_ID=""    # Application (client) ID
export OIDC_CLIENT_SECRET="" # Certificates & secrets → Value
export OIDC_TENANT_ID=""    # Directory (tenant) ID

# SSO admin promotion — the email that gets root role on every backend startup
export HURON_ADMIN_EMAIL="" # e.g. you@yourdomain.com
