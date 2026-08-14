resource "azurerm_role_assignment" "deployer_keyvault_secrets" {
  scope                = azurerm_key_vault.ats.id
  role_definition_name = "Key Vault Secrets Officer"
  principal_id         = data.azurerm_client_config.current.object_id
}

resource "azurerm_role_assignment" "deployer_upload_blobs" {
  scope                = azurerm_storage_container.upload.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = data.azurerm_client_config.current.object_id
}

resource "azurerm_role_assignment" "deployer_download_blobs" {
  scope                = azurerm_storage_container.download.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = data.azurerm_client_config.current.object_id
}

resource "azurerm_role_assignment" "deployer_storage_tables" {
  scope                = azurerm_storage_account.ats.id
  role_definition_name = "Storage Table Data Reader"
  principal_id         = data.azurerm_client_config.current.object_id
}

resource "azurerm_role_assignment" "group_upload_blobs" {
  for_each = var.blob_data_contributor_group_object_ids

  scope                = azurerm_storage_container.upload.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = each.value
  principal_type       = "Group"
}

resource "azurerm_role_assignment" "group_download_blobs" {
  for_each = var.blob_data_contributor_group_object_ids

  scope                = azurerm_storage_container.download.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = each.value
  principal_type       = "Group"
}

resource "azurerm_role_assignment" "group_storage_tables" {
  for_each = var.blob_data_contributor_group_object_ids

  scope                = azurerm_storage_account.ats.id
  role_definition_name = "Storage Table Data Reader"
  principal_id         = each.value
  principal_type       = "Group"
}

moved {
  from = azurerm_role_assignment.deployer_jobs_table
  to   = azurerm_role_assignment.deployer_storage_tables
}

moved {
  from = azurerm_role_assignment.group_jobs_table
  to   = azurerm_role_assignment.group_storage_tables
}
