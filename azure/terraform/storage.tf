resource "azurerm_storage_account" "ats" {
  name                            = local.storage_name
  resource_group_name             = azurerm_resource_group.ats.name
  location                        = azurerm_resource_group.ats.location
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  min_tls_version                 = "TLS1_2"
  allow_nested_items_to_be_public = false
  shared_access_key_enabled       = false
  tags                            = local.tags
}

resource "azurerm_storage_container" "upload" {
  name                  = "upload"
  storage_account_id    = azurerm_storage_account.ats.id
  container_access_type = "private"
}
resource "azurerm_storage_container" "download" {
  name                  = "download"
  storage_account_id    = azurerm_storage_account.ats.id
  container_access_type = "private"
}
resource "azurerm_storage_container" "deploy" {
  name                  = "function-deploy"
  storage_account_id    = azurerm_storage_account.ats.id
  container_access_type = "private"
}
resource "azurerm_storage_container" "deadletter" {
  name                  = "eventgrid-deadletter"
  storage_account_id    = azurerm_storage_account.ats.id
  container_access_type = "private"
}
resource "azurerm_storage_queue" "transcription" {
  name               = "audio-to-transcribe"
  storage_account_id = azurerm_storage_account.ats.id
}
resource "azapi_resource" "jobs" {
  type      = "Microsoft.Storage/storageAccounts/tableServices/tables@2023-04-01"
  name      = "jobs"
  parent_id = "${azurerm_storage_account.ats.id}/tableServices/default"
  body = {
    properties = {
      signedIdentifiers = []
    }
  }
}

resource "azurerm_storage_management_policy" "retention" {
  storage_account_id = azurerm_storage_account.ats.id
  rule {
    name    = "ats-retention"
    enabled = true
    filters {
      blob_types   = ["blockBlob"]
      prefix_match = ["upload/", "download/"]
    }
    actions {
      base_blob {
        delete_after_days_since_modification_greater_than = var.retention_days
      }
    }
  }
}
