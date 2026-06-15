# ─────────────────────────────────────────────────────────────────────────────
# Copy this file to .secrets.ps1 and fill in your values.
# .secrets.ps1 is in .gitignore — NEVER commit it.
# ─────────────────────────────────────────────────────────────────────────────

$env:OPENAI_API_KEY     = "sk-proj-..."
$env:PINECONE_API_KEY   = "pcsk_..."
$env:JWT_SECRET         = ""   # python -c "import secrets; print(secrets.token_urlsafe(32))"
$env:MCP_ENCRYPTION_KEY = ""   # same command as above
$env:POSTGRES_PASSWORD  = ""   # e.g. HuronXyz2026!

# Azure AD App Registration (portal.azure.com → Entra ID → App registrations)
$env:OIDC_CLIENT_ID     = ""   # Application (client) ID
$env:OIDC_CLIENT_SECRET = ""   # Certificates & secrets → Value
$env:OIDC_TENANT_ID     = ""   # Directory (tenant) ID
