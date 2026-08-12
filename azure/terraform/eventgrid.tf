resource "azurerm_eventgrid_system_topic" "uploads" {
  name                = "${var.prefix}-uploads-${local.suffix}"
  resource_group_name = azurerm_resource_group.ats.name
  location            = azurerm_resource_group.ats.location
  source_resource_id  = azurerm_storage_account.ats.id
  topic_type          = "Microsoft.Storage.StorageAccounts"
  identity { type = "SystemAssigned" }
  tags = local.tags
}

resource "azurerm_role_assignment" "eventgrid_queue" {
  scope                = azurerm_storage_account.ats.id
  role_definition_name = "Storage Queue Data Message Sender"
  principal_id         = azurerm_eventgrid_system_topic.uploads.identity[0].principal_id
}

resource "azurerm_role_assignment" "eventgrid_deadletter" {
  scope                = azurerm_storage_account.ats.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_eventgrid_system_topic.uploads.identity[0].principal_id
}

resource "azurerm_eventgrid_system_topic_event_subscription" "uploads" {
  name                 = "${var.prefix}-blob-created"
  system_topic         = azurerm_eventgrid_system_topic.uploads.name
  resource_group_name  = azurerm_resource_group.ats.name
  included_event_types = ["Microsoft.Storage.BlobCreated"]
  subject_filter {
    subject_begins_with = "/blobServices/default/containers/${azurerm_storage_container.upload.name}/blobs/"
    case_sensitive      = false
  }
  storage_queue_endpoint {
    storage_account_id                    = azurerm_storage_account.ats.id
    queue_name                            = azurerm_storage_queue.transcription.name
    queue_message_time_to_live_in_seconds = 604800
  }
  delivery_identity { type = "SystemAssigned" }
  dead_letter_identity { type = "SystemAssigned" }
  storage_blob_dead_letter_destination {
    storage_account_id          = azurerm_storage_account.ats.id
    storage_blob_container_name = azurerm_storage_container.deadletter.name
  }
  retry_policy {
    max_delivery_attempts = 10
    event_time_to_live    = 1440
  }
  depends_on = [azurerm_role_assignment.eventgrid_queue, azurerm_role_assignment.eventgrid_deadletter]
}
