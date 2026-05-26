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
  default     = "GP_Standard_D2ds_v4"
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
