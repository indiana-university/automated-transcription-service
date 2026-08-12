resource "azurerm_cognitive_account" "speech" {
  name                  = "${var.prefix}-speech-${local.suffix}"
  location              = azurerm_resource_group.ats.location
  resource_group_name   = azurerm_resource_group.ats.name
  kind                  = "SpeechServices"
  sku_name              = "S0"
  custom_subdomain_name = "${var.prefix}-speech-${local.suffix}"
  local_auth_enabled    = false
  identity { type = "SystemAssigned" }
  storage { storage_account_id = azurerm_storage_account.ats.id }
  tags = local.tags
}

resource "azurerm_role_assignment" "speech_storage" {
  scope                = azurerm_storage_account.ats.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_cognitive_account.speech.identity[0].principal_id
}

resource "azurerm_log_analytics_workspace" "ats" {
  name                = "${var.prefix}-logs-${local.suffix}"
  location            = azurerm_resource_group.ats.location
  resource_group_name = azurerm_resource_group.ats.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
  tags                = local.tags
}

resource "azurerm_application_insights" "ats" {
  name                = "${var.prefix}-insights-${local.suffix}"
  location            = azurerm_resource_group.ats.location
  resource_group_name = azurerm_resource_group.ats.name
  workspace_id        = azurerm_log_analytics_workspace.ats.id
  application_type    = "web"
  tags                = local.tags
}

resource "azurerm_key_vault" "ats" {
  name                       = "${local.compact_prefix}-kv-${local.suffix}"
  location                   = azurerm_resource_group.ats.location
  resource_group_name        = azurerm_resource_group.ats.name
  tenant_id                  = data.azurerm_client_config.current.tenant_id
  sku_name                   = "standard"
  rbac_authorization_enabled = true
  purge_protection_enabled   = true
  soft_delete_retention_days = 7
  tags                       = local.tags
}

resource "azurerm_key_vault_secret" "teams" {
  count        = var.teams_webhook == "" ? 0 : 1
  name         = "teams-webhook"
  value        = var.teams_webhook
  key_vault_id = azurerm_key_vault.ats.id
}
resource "azurerm_key_vault_secret" "slack" {
  count        = var.slack_webhook == "" ? 0 : 1
  name         = "slack-webhook"
  value        = var.slack_webhook
  key_vault_id = azurerm_key_vault.ats.id
}
