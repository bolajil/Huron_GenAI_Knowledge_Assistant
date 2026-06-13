# ─────────────────────────────────────────────────────────────────────────────
# Huron GenAI Knowledge Assistant — Azure Deployment
# Resources: Resource Group · VNet · ACR · Container Apps · PostgreSQL ·
#            Redis · Key Vault · Storage Account · Application Insights
# ─────────────────────────────────────────────────────────────────────────────

data "azurerm_client_config" "current" {}

resource "random_string" "suffix" {
  length  = 6
  special = false
  upper   = false
}

locals {
  prefix = "${var.project_name}-${var.environment}"
  suffix = random_string.suffix.result
  common_tags = {
    project     = var.project_name
    environment = var.environment
    managed_by  = "terraform"
  }
}

# ── Resource Group ────────────────────────────────────────────────────────────

resource "azurerm_resource_group" "main" {
  name     = "${local.prefix}-rg"
  location = var.location
  tags     = local.common_tags
}

# ── Virtual Network ───────────────────────────────────────────────────────────

resource "azurerm_virtual_network" "main" {
  name                = "${local.prefix}-vnet"
  address_space       = ["10.0.0.0/16"]
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tags                = local.common_tags
}

resource "azurerm_subnet" "container_apps" {
  name                 = "container-apps-subnet"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.0.0.0/23"]

  delegation {
    name = "Microsoft.App.environments"
    service_delegation {
      name    = "Microsoft.App/environments"
      actions = ["Microsoft.Network/virtualNetworks/subnets/join/action"]
    }
  }
}

resource "azurerm_subnet" "database" {
  name                 = "database-subnet"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.0.4.0/24"]

  delegation {
    name = "Microsoft.DBforPostgreSQL.flexibleServers"
    service_delegation {
      name    = "Microsoft.DBforPostgreSQL/flexibleServers"
      actions = ["Microsoft.Network/virtualNetworks/subnets/join/action"]
    }
  }
}

resource "azurerm_subnet" "redis" {
  name                 = "redis-subnet"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.0.5.0/24"]
}

# ── Azure Container Registry ──────────────────────────────────────────────────

resource "azurerm_container_registry" "main" {
  name                = "${var.project_name}acr${local.suffix}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "Standard"
  admin_enabled       = true
  tags                = local.common_tags
}

# ── Log Analytics (required by Container Apps) ────────────────────────────────

resource "azurerm_log_analytics_workspace" "main" {
  name                = "${local.prefix}-logs"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
  tags                = local.common_tags
}

# ── Application Insights ──────────────────────────────────────────────────────

resource "azurerm_application_insights" "main" {
  name                = "${local.prefix}-appinsights"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  workspace_id        = azurerm_log_analytics_workspace.main.id
  application_type    = "web"
  tags                = local.common_tags
}

# ── Container Apps Environment ────────────────────────────────────────────────

resource "azurerm_container_app_environment" "main" {
  name                       = "${local.prefix}-cae"
  location                   = azurerm_resource_group.main.location
  resource_group_name        = azurerm_resource_group.main.name
  log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id
  # No VNet integration for dev — eliminates subnet provisioning timing issues.
  # For prod: add infrastructure_subnet_id = azurerm_subnet.container_apps.id
  tags                       = local.common_tags

  lifecycle {
    ignore_changes = [tags]
  }
}

# ── PostgreSQL Flexible Server ────────────────────────────────────────────────
# Public access for dev so Container Apps (no VNet) can reach the DB.
# For prod: switch to private + delegated_subnet_id + private DNS zone.

resource "azurerm_postgresql_flexible_server" "main" {
  name                          = "${local.prefix}-postgres-${local.suffix}"
  resource_group_name           = azurerm_resource_group.main.name
  location                      = azurerm_resource_group.main.location
  version                       = "15"
  public_network_access_enabled = true
  administrator_login           = var.postgres_admin_user
  administrator_password        = var.postgres_admin_password
  sku_name                      = var.postgres_sku
  storage_mb                    = var.postgres_storage_mb
  backup_retention_days         = 7
  geo_redundant_backup_enabled  = false
  tags                          = local.common_tags
}

# Allow Azure services (Container Apps) to reach PostgreSQL
resource "azurerm_postgresql_flexible_server_firewall_rule" "allow_azure" {
  name             = "allow-azure-services"
  server_id        = azurerm_postgresql_flexible_server.main.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "0.0.0.0"
}

resource "azurerm_postgresql_flexible_server_database" "huron" {
  name      = var.postgres_db_name
  server_id = azurerm_postgresql_flexible_server.main.id
  collation = "en_US.utf8"
  charset   = "utf8"
}

resource "azurerm_postgresql_flexible_server_configuration" "ssl" {
  name      = "require_secure_transport"
  server_id = azurerm_postgresql_flexible_server.main.id
  value     = "on"
}

# ── Azure Cache for Redis ─────────────────────────────────────────────────────

resource "azurerm_redis_cache" "main" {
  count               = var.enable_redis ? 1 : 0
  name                = "${local.prefix}-redis-${local.suffix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  capacity            = 1
  family              = "C"
  sku_name            = "Standard"
  non_ssl_port_enabled = false
  minimum_tls_version = "1.2"
  tags                = local.common_tags

  redis_configuration {
    maxmemory_policy = "allkeys-lru"
  }
}

# ── Key Vault ─────────────────────────────────────────────────────────────────

resource "azurerm_key_vault" "main" {
  name                        = "${var.project_name}-kv-${local.suffix}"
  location                    = azurerm_resource_group.main.location
  resource_group_name         = azurerm_resource_group.main.name
  enabled_for_disk_encryption = false
  tenant_id                   = data.azurerm_client_config.current.tenant_id
  soft_delete_retention_days  = 7
  purge_protection_enabled    = false
  sku_name                    = "standard"
  tags                        = local.common_tags

  access_policy {
    tenant_id = data.azurerm_client_config.current.tenant_id
    object_id = data.azurerm_client_config.current.object_id

    secret_permissions = ["Backup", "Delete", "Get", "List", "Purge", "Recover", "Restore", "Set"]
  }
}

resource "azurerm_key_vault_secret" "openai_key" {
  name         = "openai-api-key"
  value        = var.openai_api_key
  key_vault_id = azurerm_key_vault.main.id
}

resource "azurerm_key_vault_secret" "pinecone_key" {
  name         = "pinecone-api-key"
  value        = var.pinecone_api_key
  key_vault_id = azurerm_key_vault.main.id
}

resource "azurerm_key_vault_secret" "jwt_secret" {
  name         = "jwt-secret"
  value        = var.jwt_secret
  key_vault_id = azurerm_key_vault.main.id
}

resource "azurerm_key_vault_secret" "postgres_password" {
  name         = "postgres-password"
  value        = var.postgres_admin_password
  key_vault_id = azurerm_key_vault.main.id
}

resource "azurerm_key_vault_secret" "mcp_encryption_key" {
  name         = "mcp-encryption-key"
  value        = var.mcp_encryption_key
  key_vault_id = azurerm_key_vault.main.id
}

resource "azurerm_key_vault_secret" "oidc_client_secret" {
  count        = var.oidc_client_secret != "" ? 1 : 0
  name         = "oidc-client-secret"
  value        = var.oidc_client_secret
  key_vault_id = azurerm_key_vault.main.id
}

resource "azurerm_key_vault_secret" "workday_client_secret" {
  count        = var.workday_client_secret != "" ? 1 : 0
  name         = "workday-client-secret"
  value        = var.workday_client_secret
  key_vault_id = azurerm_key_vault.main.id
}

resource "azurerm_key_vault_secret" "teams_app_secret" {
  count        = var.teams_app_secret != "" ? 1 : 0
  name         = "teams-app-secret"
  value        = var.teams_app_secret
  key_vault_id = azurerm_key_vault.main.id
}

# ── Storage Account (document blobs) ──────────────────────────────────────────

resource "azurerm_storage_account" "main" {
  name                     = "${var.project_name}stor${local.suffix}"
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  min_tls_version          = "TLS1_2"
  tags                     = local.common_tags

  blob_properties {
    versioning_enabled = true
  }
}

resource "azurerm_storage_container" "documents" {
  name                  = "documents"
  storage_account_name  = azurerm_storage_account.main.name
  container_access_type = "private"
}

# ── Managed Identity for Container Apps ───────────────────────────────────────

resource "azurerm_user_assigned_identity" "backend" {
  name                = "${local.prefix}-backend-identity"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tags                = local.common_tags
}

resource "azurerm_key_vault_access_policy" "backend_identity" {
  key_vault_id = azurerm_key_vault.main.id
  tenant_id    = data.azurerm_client_config.current.tenant_id
  object_id    = azurerm_user_assigned_identity.backend.principal_id

  secret_permissions = ["Get", "List"]
}

resource "azurerm_role_assignment" "acr_pull" {
  scope                = azurerm_container_registry.main.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.backend.principal_id
}

# ── Backend Container App ─────────────────────────────────────────────────────

locals {
  backend_image_ref  = var.backend_image != "" ? var.backend_image : "${azurerm_container_registry.main.login_server}/huron-backend:latest"
  frontend_image_ref = var.frontend_image != "" ? var.frontend_image : "${azurerm_container_registry.main.login_server}/huron-frontend:latest"
  database_url       = "postgresql://${var.postgres_admin_user}:${var.postgres_admin_password}@${azurerm_postgresql_flexible_server.main.fqdn}:5432/${var.postgres_db_name}?sslmode=require"
  redis_url          = var.enable_redis ? "rediss://:${azurerm_redis_cache.main[0].primary_access_key}@${azurerm_redis_cache.main[0].hostname}:${azurerm_redis_cache.main[0].ssl_port}" : ""
  # OIDC redirect URI: empty on first apply → fill oidc_redirect_uri_override after getting backend FQDN from outputs
  oidc_redirect_uri  = var.oidc_redirect_uri_override != "" ? var.oidc_redirect_uri_override : "http://localhost:8004/api/v1/auth/oidc/callback"
  frontend_url       = var.frontend_url_override != "" ? var.frontend_url_override : "http://localhost:3000"
}

resource "azurerm_container_app" "backend" {
  name                         = "${local.prefix}-backend"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"
  tags                         = local.common_tags

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.backend.id]
  }

  registry {
    server   = azurerm_container_registry.main.login_server
    identity = azurerm_user_assigned_identity.backend.id
  }

  ingress {
    external_enabled = true
    target_port      = 8004
    transport        = "http"

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  template {
    min_replicas = var.backend_min_replicas
    max_replicas = var.backend_max_replicas

    http_scale_rule {
      name                = "http-scale"
      concurrent_requests = "50"
    }

    container {
      name   = "backend"
      image  = local.backend_image_ref
      cpu    = var.backend_cpu
      memory = var.backend_memory

      env {
        name  = "OPENAI_API_KEY"
        value = var.openai_api_key
      }
      env {
        name  = "PINECONE_API_KEY"
        value = var.pinecone_api_key
      }
      env {
        name  = "PINECONE_INDEX"
        value = var.pinecone_index
      }
      env {
        name  = "JWT_SECRET"
        value = var.jwt_secret
      }
      env {
        name  = "JWT_EXPIRATION_HOURS"
        value = tostring(var.jwt_expiration_hours)
      }
      env {
        name  = "DATABASE_URL"
        value = local.database_url
      }
      env {
        name  = "REDIS_URL"
        value = local.redis_url
      }
      env {
        name  = "APPLICATIONINSIGHTS_CONNECTION_STRING"
        value = azurerm_application_insights.main.connection_string
      }
      env {
        name  = "MCP_ENCRYPTION_KEY"
        value = var.mcp_encryption_key
      }
      env {
        name  = "PORT"
        value = "8004"
      }

      # ── Azure AD / OIDC SSO ────────────────────────────────────────────────
      env {
        name  = "OIDC_CLIENT_ID"
        value = var.oidc_client_id
      }
      env {
        name  = "OIDC_CLIENT_SECRET"
        value = var.oidc_client_secret
      }
      env {
        name  = "OIDC_AUTHORITY"
        value = var.oidc_authority
      }
      env {
        name  = "OIDC_REDIRECT_URI"
        value = local.oidc_redirect_uri
      }
      env {
        name  = "FRONTEND_URL"
        value = local.frontend_url
      }
      # Graph API re-uses the OIDC app registration credentials
      env {
        name  = "AZURE_TENANT_ID"
        value = var.oidc_authority != "" ? regex("https://login\\.microsoftonline\\.com/([^/]+)", var.oidc_authority)[0] : ""
      }
      env {
        name  = "AZURE_CLIENT_ID"
        value = var.oidc_client_id
      }
      env {
        name  = "AZURE_CLIENT_SECRET"
        value = var.oidc_client_secret
      }

      # ── Workday ───────────────────────────────────────────────────────────
      env {
        name  = "WORKDAY_MOCK_MODE"
        value = tostring(var.workday_mock_mode)
      }
      env {
        name  = "WORKDAY_BASE_URL"
        value = var.workday_base_url
      }
      env {
        name  = "WORKDAY_TENANT"
        value = var.workday_tenant
      }
      env {
        name  = "WORKDAY_CLIENT_ID"
        value = var.workday_client_id
      }
      env {
        name  = "WORKDAY_CLIENT_SECRET"
        value = var.workday_client_secret
      }

      # ── SharePoint ────────────────────────────────────────────────────────
      env {
        name  = "SHAREPOINT_MOCK_MODE"
        value = tostring(var.sharepoint_mock_mode)
      }

      # ── Teams Bot ─────────────────────────────────────────────────────────
      env {
        name  = "TEAMS_APP_ID"
        value = var.teams_app_id
      }
      env {
        name  = "TEAMS_APP_SECRET"
        value = var.teams_app_secret
      }
      env {
        name  = "HURON_INTERNAL_API"
        value = "http://localhost:8004"
      }

      liveness_probe {
        path                    = "/health"
        port                    = 8004
        transport               = "HTTP"
        initial_delay           = 15
        interval_seconds        = 30
        failure_count_threshold = 3
      }

      readiness_probe {
        path                    = "/health"
        port                    = 8004
        transport               = "HTTP"
        interval_seconds        = 10
        failure_count_threshold = 3
      }
    }
  }

  depends_on = [
    azurerm_postgresql_flexible_server_database.huron,
  ]
}

# ── Frontend Container App ────────────────────────────────────────────────────

resource "azurerm_container_app" "frontend" {
  name                         = "${local.prefix}-frontend"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"
  tags                         = local.common_tags

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.backend.id]
  }

  registry {
    server   = azurerm_container_registry.main.login_server
    identity = azurerm_user_assigned_identity.backend.id
  }

  ingress {
    external_enabled = true
    target_port      = 3000
    transport        = "http"

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  template {
    min_replicas = 1
    max_replicas = 5

    container {
      name   = "frontend"
      image  = local.frontend_image_ref
      cpu    = var.frontend_cpu
      memory = var.frontend_memory

      env {
        name  = "BACKEND_URL"
        value = "https://${azurerm_container_app.backend.ingress[0].fqdn}"
      }
      env {
        name  = "NODE_ENV"
        value = "production"
      }
    }
  }

  depends_on = [azurerm_container_app.backend]
}
