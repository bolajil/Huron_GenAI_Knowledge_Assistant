#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Huron GenAI — One-command deploy (Git Bash / Linux / macOS)
# Usage:
#   ./deploy.sh                  # full deploy (build images + apply)
#   ./deploy.sh --skip-build     # skip Docker build (images already in ACR)
#   ./deploy.sh --destroy        # full teardown
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SECRETS_FILE="$SCRIPT_DIR/.secrets.sh"

SKIP_BUILD=false
DESTROY=false

for arg in "$@"; do
  case $arg in
    --skip-build) SKIP_BUILD=true ;;
    --destroy)    DESTROY=true ;;
  esac
done

# ── Helpers ───────────────────────────────────────────────────────────────────
info()    { echo -e "\033[36m$*\033[0m"; }
success() { echo -e "\033[32m$*\033[0m"; }
warn()    { echo -e "\033[33m$*\033[0m"; }
die()     { echo -e "\033[31mERROR: $*\033[0m" >&2; exit 1; }

tf_output() { terraform output -raw "$1" 2>/dev/null; }

# ── Preflight ─────────────────────────────────────────────────────────────────
info "[1/7] Preflight checks..."
command -v az        >/dev/null 2>&1 || die "Azure CLI not found. Install: https://aka.ms/installazurecliwindows"
command -v terraform >/dev/null 2>&1 || die "Terraform not found. Install: https://developer.hashicorp.com/terraform/downloads"
command -v docker    >/dev/null 2>&1 || die "Docker not found. Start Docker Desktop."

ACCOUNT=$(az account show 2>/dev/null) || { warn "Not logged in — running az login..."; az login; ACCOUNT=$(az account show); }
SUB_NAME=$(echo "$ACCOUNT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['name'])")
success "  Subscription: $SUB_NAME"

# ── Destroy mode ─────────────────────────────────────────────────────────────
if $DESTROY; then
  info "[DESTROY] Tearing down all Huron infrastructure..."
  cd "$SCRIPT_DIR"
  terraform destroy -auto-approve
  success "All resources destroyed. Cost: \$0."
  exit 0
fi

# ── Load secrets ─────────────────────────────────────────────────────────────
info "[2/7] Loading secrets..."

if [[ -f "$SECRETS_FILE" ]]; then
  success "  Loading from .secrets.sh"
  # shellcheck disable=SC1090
  source "$SECRETS_FILE"
else
  warn "  No .secrets.sh found — copy .secrets.example.sh to .secrets.sh and fill in values."
  exit 1
fi

# Validate required secrets
for VAR in OPENAI_API_KEY PINECONE_API_KEY JWT_SECRET MCP_ENCRYPTION_KEY POSTGRES_PASSWORD OIDC_CLIENT_ID OIDC_CLIENT_SECRET OIDC_TENANT_ID; do
  [[ -n "${!VAR:-}" ]] || die "Missing required secret: $VAR (set it in .secrets.sh)"
done

# ── Write terraform.tfvars ────────────────────────────────────────────────────
cat > "$SCRIPT_DIR/terraform.tfvars" <<EOF
location     = "West US"
environment  = "dev"
project_name = "huron"

openai_api_key   = "$OPENAI_API_KEY"
pinecone_api_key = "$PINECONE_API_KEY"
pinecone_index   = "huron-enterprise-knowledge"

jwt_secret         = "$JWT_SECRET"
mcp_encryption_key = "$MCP_ENCRYPTION_KEY"
jwt_expiration_hours = 8

postgres_admin_user     = "huron_admin"
postgres_admin_password = "$POSTGRES_PASSWORD"
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

oidc_redirect_uri_override = ""
frontend_url_override      = ""
EOF
success "  terraform.tfvars written."

# ── Terraform init + first apply ─────────────────────────────────────────────
cd "$SCRIPT_DIR"

info "[3/7] terraform init..."
terraform init -upgrade

# ── Step 4a: create ACR + base infra (no Container Apps yet) ─────────────────
info "[4a/7] Creating ACR and base infrastructure..."
terraform apply -auto-approve \
  -target=azurerm_resource_group.main \
  -target=azurerm_container_registry.main \
  -target=azurerm_virtual_network.main \
  -target=azurerm_subnet.container_apps \
  -target=azurerm_subnet.database \
  -target=azurerm_subnet.redis \
  -target=azurerm_log_analytics_workspace.main \
  -target=azurerm_application_insights.main \
  -target=azurerm_container_app_environment.main \
  -target=azurerm_postgresql_flexible_server.main \
  -target=azurerm_postgresql_flexible_server_database.huron \
  -target=azurerm_postgresql_flexible_server_configuration.ssl \
  -target=azurerm_postgresql_flexible_server_firewall_rule.allow_azure \
  -target=azurerm_key_vault.main \
  -target=azurerm_storage_account.main \
  -target=azurerm_storage_container.documents \
  -target=azurerm_user_assigned_identity.backend

ACR_SERVER=$(tf_output acr_login_server)
ACR_NAME="${ACR_SERVER%%.*}"
success "  ACR: $ACR_SERVER"

# ── Build and push Docker images ──────────────────────────────────────────────
if $SKIP_BUILD; then
  info "[5/7] Skipping Docker build (--skip-build flag set)."
else
  info "[5/7] Building and pushing Docker images..."
  az acr login --name "$ACR_NAME"

  info "  Building backend..."
  docker build -f "$PROJECT_ROOT/backend/Dockerfile.production" \
    -t "$ACR_SERVER/huron-backend:latest" "$PROJECT_ROOT"
  docker push "$ACR_SERVER/huron-backend:latest"

  info "  Building frontend..."
  # Pass BACKEND_URL so Next.js proxy rewrites point to the real backend at build time.
  BACKEND_URL_VAL="https://$(terraform output -raw backend_fqdn 2>/dev/null || echo 'localhost:8004')"
  docker build -f "$PROJECT_ROOT/frontend/Dockerfile.production" \
    --build-arg BACKEND_URL="$BACKEND_URL_VAL" \
    -t "$ACR_SERVER/huron-frontend:latest" "$PROJECT_ROOT/frontend"
  docker push "$ACR_SERVER/huron-frontend:latest"

  success "  Images pushed."
fi

# ── Wait for CAE to be fully provisioned before creating Container Apps ───────
info "[4b/7] Waiting for Container App Environment to reach Succeeded state..."
CAE_NAME="huron-dev-cae"
RG="huron-dev-rg"
for i in $(seq 1 20); do
  STATE=$(az containerapp env show -n "$CAE_NAME" -g "$RG" \
    --query "properties.provisioningState" -o tsv 2>/dev/null || echo "NotFound")
  echo "  CAE state: $STATE (attempt $i/20)"
  [[ "$STATE" == "Succeeded" ]] && break
  [[ "$STATE" == "Failed" ]] && { die "CAE provisioning failed. Run: terraform taint azurerm_container_app_environment.main"; }
  sleep 30
done

# ── Step 4c: create Container Apps (images now exist, CAE is ready) ──────────
info "[4c/7] Creating Container Apps..."
terraform apply -auto-approve

# ── Capture outputs ───────────────────────────────────────────────────────────
info "[6/7] Reading outputs..."
BACKEND_URL=$(tf_output backend_url)
FRONTEND_URL=$(tf_output frontend_url)
OIDC_CALLBACK=$(tf_output oidc_redirect_uri)

success "  Backend:       $BACKEND_URL"
success "  Frontend:      $FRONTEND_URL"
success "  OIDC callback: $OIDC_CALLBACK"

# ── Auto-register redirect URI in Azure AD ────────────────────────────────────
info "[6b/7] Registering OIDC redirect URI in Azure AD..."
if az ad app update --id "$OIDC_CLIENT_ID" --web-redirect-uris "$OIDC_CALLBACK" 2>/dev/null; then
  success "  Redirect URI registered: $OIDC_CALLBACK"
else
  warn "  Could not auto-register redirect URI. Add manually in portal:"
  warn "  $OIDC_CALLBACK"
fi

# ── Final apply — wire OIDC URLs into Container App env vars ─────────────────
info "[7/7] Final terraform apply (wiring OIDC + frontend URLs)..."

sed -i \
  "s|oidc_redirect_uri_override = \"\"|oidc_redirect_uri_override = \"$OIDC_CALLBACK\"|" \
  "$SCRIPT_DIR/terraform.tfvars"

sed -i \
  "s|frontend_url_override      = \"\"|frontend_url_override      = \"$FRONTEND_URL\"|" \
  "$SCRIPT_DIR/terraform.tfvars"

terraform apply -auto-approve

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║           Huron GenAI — Deployment Complete                  ║"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║  Frontend:  $FRONTEND_URL"
echo "║  API Docs:  $BACKEND_URL/docs"
echo "║  OIDC:      $OIDC_CALLBACK"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║  To tear down:  ./deploy.sh --destroy                        ║"
echo "╚══════════════════════════════════════════════════════════════╝"
