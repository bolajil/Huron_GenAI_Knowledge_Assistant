# ─────────────────────────────────────────────────────────────────────────────
# Huron GenAI — One-command deploy script
# Usage:
#   .\deploy.ps1                  # full deploy (build images + apply)
#   .\deploy.ps1 -SkipBuild       # skip Docker build (images already in ACR)
#   .\deploy.ps1 -Destroy         # full teardown
# ─────────────────────────────────────────────────────────────────────────────
param(
    [switch]$SkipBuild,
    [switch]$Destroy
)

$ErrorActionPreference = "Stop"
$ScriptDir = $PSScriptRoot
$ProjectRoot = Resolve-Path "$ScriptDir\..\.."

# ── Secrets file (never committed) ───────────────────────────────────────────
$SecretsFile = "$ScriptDir\.secrets.ps1"

function Read-Secret([string]$Prompt, [string]$EnvVar) {
    $val = [System.Environment]::GetEnvironmentVariable($EnvVar)
    if ($val) { return $val }
    $val = Read-Host "$Prompt"
    if (-not $val) { throw "$Prompt is required." }
    return $val
}

# ── Preflight checks ──────────────────────────────────────────────────────────
Write-Host "`n[1/7] Preflight checks..." -ForegroundColor Cyan

if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
    throw "Azure CLI not found. Install: winget install Microsoft.AzureCLI"
}
if (-not (Get-Command terraform -ErrorAction SilentlyContinue)) {
    throw "Terraform not found. Install: winget install Hashicorp.Terraform"
}
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker not found or not running. Start Docker Desktop."
}

$account = az account show 2>$null | ConvertFrom-Json
if (-not $account) {
    Write-Host "  Not logged in — running az login..." -ForegroundColor Yellow
    az login
    $account = az account show | ConvertFrom-Json
}
Write-Host "  Subscription: $($account.name) ($($account.id))" -ForegroundColor Green

# ── Destroy mode ─────────────────────────────────────────────────────────────
if ($Destroy) {
    Write-Host "`n[DESTROY] Tearing down all Huron infrastructure..." -ForegroundColor Red
    Set-Location $ScriptDir
    terraform destroy -auto-approve
    Write-Host "`nAll resources destroyed. Cost: $0." -ForegroundColor Green
    exit 0
}

# ── Load or prompt for secrets ────────────────────────────────────────────────
Write-Host "`n[2/7] Loading secrets..." -ForegroundColor Cyan

if (Test-Path $SecretsFile) {
    Write-Host "  Loading from .secrets.ps1" -ForegroundColor Green
    . $SecretsFile
} else {
    Write-Host "  No .secrets.ps1 found — prompting for required values." -ForegroundColor Yellow
    Write-Host "  (Tip: copy .secrets.example.ps1 to .secrets.ps1 to skip prompts next time)`n"
}

$OPENAI_API_KEY      = Read-Secret "OpenAI API key"          "OPENAI_API_KEY"
$PINECONE_API_KEY    = Read-Secret "Pinecone API key"         "PINECONE_API_KEY"
$JWT_SECRET          = Read-Secret "JWT secret (32+ chars)"   "JWT_SECRET"
$MCP_KEY             = Read-Secret "MCP encryption key"       "MCP_ENCRYPTION_KEY"
$PG_PASSWORD         = Read-Secret "Postgres admin password"  "POSTGRES_PASSWORD"
$OIDC_CLIENT_ID      = Read-Secret "Azure AD client ID"       "OIDC_CLIENT_ID"
$OIDC_CLIENT_SECRET  = Read-Secret "Azure AD client secret"   "OIDC_CLIENT_SECRET"
$OIDC_TENANT_ID      = Read-Secret "Azure AD tenant ID"       "OIDC_TENANT_ID"

$TF_VARS = @"
location     = "West US"
environment  = "dev"
project_name = "huron"

openai_api_key   = "$OPENAI_API_KEY"
pinecone_api_key = "$PINECONE_API_KEY"
pinecone_index   = "huron-enterprise-knowledge"

jwt_secret         = "$JWT_SECRET"
mcp_encryption_key = "$MCP_KEY"
jwt_expiration_hours = 8

postgres_admin_user     = "huron_admin"
postgres_admin_password = "$PG_PASSWORD"
postgres_db_name        = "huron_db"
postgres_sku            = "B_Standard_B1ms"
postgres_storage_mb     = 32768

backend_cpu          = 1.0
backend_memory       = "2Gi"
frontend_cpu         = 0.5
frontend_memory      = "1Gi"
backend_min_replicas = 1
backend_max_replicas = 10

backend_image  = ""
frontend_image = ""
enable_redis   = false

oidc_client_id     = "$OIDC_CLIENT_ID"
oidc_client_secret = "$OIDC_CLIENT_SECRET"
oidc_authority     = "https://login.microsoftonline.com/$OIDC_TENANT_ID"

workday_mock_mode     = true
workday_base_url      = ""
workday_tenant        = ""
workday_client_id     = ""
workday_client_secret = ""
sharepoint_mock_mode  = true
teams_app_id          = ""
teams_app_secret      = ""

# Overrides — populated automatically by this script after first apply
oidc_redirect_uri_override = ""
frontend_url_override      = ""
"@

Set-Location $ScriptDir
$TF_VARS | Out-File -FilePath "terraform.tfvars" -Encoding utf8 -Force
Write-Host "  terraform.tfvars written." -ForegroundColor Green

# ── Terraform init + first apply ─────────────────────────────────────────────
Write-Host "`n[3/7] terraform init..." -ForegroundColor Cyan
terraform init -upgrade

Write-Host "`n[4/7] First terraform apply (infrastructure)..." -ForegroundColor Cyan
terraform apply -auto-approve

# ── Capture outputs ───────────────────────────────────────────────────────────
Write-Host "`n[5/7] Reading outputs..." -ForegroundColor Cyan
$outputs = terraform output -json | ConvertFrom-Json
$backendFqdn   = $outputs.backend_url.value
$frontendUrl   = $outputs.frontend_url.value
$oidcCallback  = $outputs.oidc_redirect_uri.value
$acrName       = $outputs.acr_login_server.value.Split('.')[0]

Write-Host "  Backend:  $backendFqdn" -ForegroundColor Green
Write-Host "  Frontend: $frontendUrl" -ForegroundColor Green
Write-Host "  OIDC callback: $oidcCallback" -ForegroundColor Green

# ── Auto-register redirect URI in Azure AD ────────────────────────────────────
Write-Host "`n[5b] Registering OIDC redirect URI in Azure AD App Registration..." -ForegroundColor Cyan
try {
    az ad app update --id $OIDC_CLIENT_ID --web-redirect-uris $oidcCallback
    Write-Host "  Redirect URI registered: $oidcCallback" -ForegroundColor Green
} catch {
    Write-Host "  WARNING: Could not auto-register redirect URI. Add manually in portal:" -ForegroundColor Yellow
    Write-Host "  $oidcCallback" -ForegroundColor Yellow
}

# ── Build and push Docker images ──────────────────────────────────────────────
if (-not $SkipBuild) {
    Write-Host "`n[6/7] Building and pushing Docker images..." -ForegroundColor Cyan
    az acr login --name $acrName

    Write-Host "  Building backend..." -ForegroundColor Gray
    docker build -f "$ProjectRoot\backend\Dockerfile.production" -t "$($outputs.acr_login_server.value)/huron-backend:latest" $ProjectRoot
    docker push "$($outputs.acr_login_server.value)/huron-backend:latest"

    Write-Host "  Building frontend..." -ForegroundColor Gray
    docker build -t "$($outputs.acr_login_server.value)/huron-frontend:latest" "$ProjectRoot\frontend"
    docker push "$($outputs.acr_login_server.value)/huron-frontend:latest"
    Write-Host "  Images pushed." -ForegroundColor Green
} else {
    Write-Host "`n[6/7] Skipping Docker build (-SkipBuild flag set)." -ForegroundColor Yellow
}

# ── Second apply — wire OIDC URLs ─────────────────────────────────────────────
Write-Host "`n[7/7] Second terraform apply (wiring OIDC + frontend URLs)..." -ForegroundColor Cyan

(Get-Content "terraform.tfvars") `
    -replace 'oidc_redirect_uri_override = ""', "oidc_redirect_uri_override = `"$oidcCallback`"" `
    -replace 'frontend_url_override      = ""', "frontend_url_override      = `"$frontendUrl`"" |
    Set-Content "terraform.tfvars"

terraform apply -auto-approve

# ── Done ──────────────────────────────────────────────────────────────────────
Write-Host @"

╔══════════════════════════════════════════════════════════════╗
║              Huron GenAI — Deployment Complete               ║
╠══════════════════════════════════════════════════════════════╣
║  Frontend:  $frontendUrl
║  API Docs:  $backendFqdn/docs
║  OIDC:      $oidcCallback
╠══════════════════════════════════════════════════════════════╣
║  To tear down:  .\deploy.ps1 -Destroy                        ║
╚══════════════════════════════════════════════════════════════╝
"@ -ForegroundColor Green
