variable "aws_region" {
  description = "AWS region to deploy all resources"
  type        = string
  default     = "us-east-1"
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

# ── Secrets ───────────────────────────────────────────────────────────────────

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

variable "jwt_expiration_hours" {
  description = "JWT token expiration in hours"
  type        = number
  default     = 8
}

# ── RDS ───────────────────────────────────────────────────────────────────────

variable "db_username" {
  description = "RDS master username"
  type        = string
  default     = "huron_admin"
}

variable "db_password" {
  description = "RDS master password"
  type        = string
  sensitive   = true
}

variable "db_name" {
  description = "PostgreSQL database name"
  type        = string
  default     = "huron_db"
}

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.medium"
}

variable "db_allocated_storage" {
  description = "RDS allocated storage in GB"
  type        = number
  default     = 20
}

variable "db_multi_az" {
  description = "Enable Multi-AZ for high availability"
  type        = bool
  default     = true
}

# ── ElastiCache ───────────────────────────────────────────────────────────────

variable "redis_node_type" {
  description = "ElastiCache Redis node type"
  type        = string
  default     = "cache.t3.micro"
}

# ── ECS ───────────────────────────────────────────────────────────────────────

variable "backend_cpu" {
  description = "CPU units for backend Fargate task (2048 = 2 vCPU — minimum for sentence-transformers)"
  type        = number
  default     = 2048
}

variable "backend_memory" {
  description = "Memory (MB) for backend Fargate task (4096 MB minimum for sentence-transformers)"
  type        = number
  default     = 4096
}

variable "frontend_cpu" {
  description = "CPU units for frontend Fargate task"
  type        = number
  default     = 512
}

variable "frontend_memory" {
  description = "Memory (MB) for frontend Fargate task"
  type        = number
  default     = 1024
}

variable "backend_desired_count" {
  description = "Desired number of backend Fargate tasks"
  type        = number
  default     = 2
}

variable "frontend_desired_count" {
  description = "Desired number of frontend Fargate tasks"
  type        = number
  default     = 2
}

# ── Domain (optional) ─────────────────────────────────────────────────────────

variable "domain_name" {
  description = "Custom domain name (leave blank to use ALB/CloudFront URLs)"
  type        = string
  default     = ""
}

variable "certificate_arn" {
  description = "ACM certificate ARN for HTTPS (required if domain_name is set)"
  type        = string
  default     = ""
}

# ── MCP / Security ────────────────────────────────────────────────────────────

variable "mcp_encryption_key" {
  description = "Separate Fernet key for MCP tool credential encryption. Must be distinct from jwt_secret so JWT rotation doesn't invalidate stored tool configs."
  type        = string
  sensitive   = true
}

# ── OIDC / Active Directory SSO ───────────────────────────────────────────────

variable "oidc_client_id" {
  description = "Microsoft Entra ID (Azure AD) application (client) ID for SSO"
  type        = string
  default     = ""
}

variable "oidc_client_secret" {
  description = "Microsoft Entra ID client secret for SSO"
  type        = string
  sensitive   = true
  default     = ""
}

variable "oidc_authority" {
  description = "OIDC authority URL, e.g. https://login.microsoftonline.com/<tenant-id>"
  type        = string
  default     = ""
}

variable "oidc_redirect_uri" {
  description = "OAuth callback URL — must match the redirect URI registered in Entra ID"
  type        = string
  default     = ""
}

# ── Observability ─────────────────────────────────────────────────────────────

variable "sentry_dsn" {
  description = "Sentry DSN for error tracking (leave blank to disable)"
  type        = string
  sensitive   = true
  default     = ""
}

variable "posthog_key" {
  description = "PostHog project API key for product analytics (leave blank to disable)"
  type        = string
  sensitive   = true
  default     = ""
}

# ── Grafana ───────────────────────────────────────────────────────────────────

variable "grafana_workspace_name" {
  description = "Amazon Managed Grafana workspace name"
  type        = string
  default     = "huron-observability"
}

variable "grafana_account_access_type" {
  description = "CURRENT_ACCOUNT or ORGANIZATION"
  type        = string
  default     = "CURRENT_ACCOUNT"
}
