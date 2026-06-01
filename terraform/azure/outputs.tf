output "frontend_url" {
  description = "Public URL of the Huron frontend"
  value       = "https://${azurerm_container_app.frontend.ingress[0].fqdn}"
}

output "backend_url" {
  description = "Public URL of the Huron backend API"
  value       = "https://${azurerm_container_app.backend.ingress[0].fqdn}"
}

output "api_docs_url" {
  description = "Swagger UI — interactive API documentation"
  value       = "https://${azurerm_container_app.backend.ingress[0].fqdn}/docs"
}

output "acr_login_server" {
  description = "Azure Container Registry login server"
  value       = azurerm_container_registry.main.login_server
}

output "acr_push_commands" {
  description = "Commands to push images to ACR"
  value       = <<-EOT
    az acr login --name ${azurerm_container_registry.main.name}

    # Backend
    docker build -t ${azurerm_container_registry.main.login_server}/huron-backend:latest ./backend
    docker push ${azurerm_container_registry.main.login_server}/huron-backend:latest

    # Frontend
    docker build -t ${azurerm_container_registry.main.login_server}/huron-frontend:latest ./frontend
    docker push ${azurerm_container_registry.main.login_server}/huron-frontend:latest
  EOT
}

output "postgres_fqdn" {
  description = "PostgreSQL Flexible Server FQDN"
  value       = azurerm_postgresql_flexible_server.main.fqdn
}

output "redis_hostname" {
  description = "Redis cache hostname"
  value       = azurerm_redis_cache.main.hostname
}

output "key_vault_uri" {
  description = "Azure Key Vault URI"
  value       = azurerm_key_vault.main.vault_uri
}

output "storage_account_name" {
  description = "Storage account for document blobs"
  value       = azurerm_storage_account.main.name
}

output "application_insights_key" {
  description = "Application Insights instrumentation key"
  value       = azurerm_application_insights.main.instrumentation_key
  sensitive   = true
}

output "resource_group_name" {
  description = "Resource group containing all resources"
  value       = azurerm_resource_group.main.name
}
