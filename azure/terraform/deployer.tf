# Terraform needs data-plane permission only when it is asked to create webhook secrets.
resource "azurerm_role_assignment" "deployer_keyvault_secrets" {
  scope                = azurerm_key_vault.ats.id
  role_definition_name = "Key Vault Secrets Officer"
  principal_id         = data.azurerm_client_config.current.object_id
}
