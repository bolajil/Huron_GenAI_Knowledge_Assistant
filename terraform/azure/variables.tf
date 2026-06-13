variable "location" {
  description = "Azure region to deploy all resources"
  type        = string
  default     = "East US 2"
}

variable "environment" {
  description = "Deployment environment (dev, staging, prod)"
  type        = string
  default     = "prod"
}

variable "project_name" {
  description = "Project name used in resource naming"
  type        = string
  default     = "huron"
}

# ── Secrets ──────────────────────────────────────────────────────────────────

variable "openai_api_key" {
  description = "OpenAI API key"
  type        = string
  sensitive   = true
}

variable "pinecone_api_key" {
  description = "Pinecone API key"
  type        = string
  sensitive   = true
}

variable "pinecone_index" {
  description = "Pinecone index name"
  type        = string
  default     = "huron-enterprise-knowledge"
}

variable "jwt_secret" {
  description = "JWT signing secret (minimum 32 characters)"
  type        = string
  sensitive   = true
}

variable "mcp_encryption_key" {
  description = "MCP tool encryption key (minimum 32 characters)"
  type        = string
  sensitive   = true
}

variable "jwt_expiration_hours" {
  description = "JWT token expiration in hours"
  type        = number
  default     = 8
}

# ── PostgreSQL ────────────────────────────────────────────────────────────────

variable "postgres_admin_user" {
  description = "PostgreSQL administrator username"
  type        = string
  default     = "huron_admin"
}

variable "postgres_admin_password" {
  description = "PostgreSQL administrator password"
  type        = string
  sensitive   = true
}

variable "postgres_db_name" {
  description = "Name of the application database"
  type        = string
  default     = "huron_db"
}

variable "postgres_sku" {
  description = "PostgreSQL Flexible Server SKU"
  type        = string
  default     = "B_Standard_B1ms"
}

variable "postgres_storage_mb" {
  description = "PostgreSQL storage in MB"
  type        = number
  default     = 32768
}

# ── Container configuration ───────────────────────────────────────────────────

variable "backend_image" {
  description = "Backend Docker image (leave blank to build from ACR)"
  type        = string
  default     = ""
}

variable "frontend_image" {
  description = "Frontend Docker image (leave blank to build from ACR)"
  type        = string
  default     = ""
}

variable "backend_cpu" {
  description = "vCPU allocated to backend container"
  type        = number
  default     = 1.0
}

variable "backend_memory" {
  description = "Memory (Gi) allocated to backend container"
  type        = string
  default     = "2Gi"
}

variable "frontend_cpu" {
  description = "vCPU allocated to frontend container"
  type        = number
  default     = 0.5
}

variable "frontend_memory" {
  description = "Memory (Gi) allocated to frontend container"
  type        = string
  default     = "1Gi"
}

variable "backend_min_replicas" {
  description = "Minimum backend replica count"
  type        = number
  default     = 1
}

variable "backend_max_replicas" {
  description = "Maximum backend replica count"
  type        = number
  default     = 10
}

# ── Azure AD / OIDC SSO ───────────────────────────────────────────────────────

variable "oidc_client_id" {
  description = "Azure AD App Registration client (application) ID"
  type        = string
  default     = ""
}

variable "oidc_client_secret" {
  description = "Azure AD App Registration client secret value"
  type        = string
  sensitive   = true
  default     = ""
}

variable "oidc_authority" {
  description = "OIDC authority URL — https://login.microsoftonline.com/<tenant-id>"
  type        = string
  default     = ""
}

# ── Workday ───────────────────────────────────────────────────────────────────

variable "workday_base_url" {
  description = "Workday REST API base URL (leave blank to use mock mode)"
  type        = string
  default     = ""
}

variable "workday_tenant" {
  description = "Workday tenant name"
  type        = string
  default     = ""
}

variable "workday_client_id" {
  description = "Workday API client ID"
  type        = string
  default     = ""
}

variable "workday_client_secret" {
  description = "Workday API client secret"
  type        = string
  sensitive   = true
  default     = ""
}

variable "workday_mock_mode" {
  description = "Use mock Workday data instead of live API (true during demo/staging)"
  type        = bool
  default     = true
}

# ── SharePoint / Microsoft Graph ──────────────────────────────────────────────

variable "sharepoint_mock_mode" {
  description = "Use local demo files instead of live SharePoint (true during demo/staging)"
  type        = bool
  default     = true
}

# ── Microsoft Teams Bot ───────────────────────────────────────────────────────

variable "teams_app_id" {
  description = "Bot Framework / Teams app (client) ID"
  type        = string
  default     = ""
}

variable "teams_app_secret" {
  description = "Bot Framework / Teams app client secret"
  type        = string
  sensitive   = true
  default     = ""
}

# ── Post-first-apply overrides ────────────────────────────────────────────────
# Leave blank on first apply. After apply, copy the oidc_redirect_uri and
# frontend_url outputs into these variables, then apply again.

variable "enable_redis" {
  description = "Deploy Azure Cache for Redis. Set false for dev (app uses in-memory fallback). Set true for staging/prod."
  type        = bool
  default     = false
}

variable "oidc_redirect_uri_override" {
  description = "OIDC redirect URI (fill after first apply using the oidc_redirect_uri output)"
  type        = string
  default     = ""
}

variable "frontend_url_override" {
  description = "Frontend public URL (fill after first apply using the frontend_url output)"
  type        = string
  default     = ""
}
