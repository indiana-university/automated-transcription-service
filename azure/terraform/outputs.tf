output "upload_container_url" { value = "${azurerm_storage_account.ats.primary_blob_endpoint}${azurerm_storage_container.upload.name}" }
output "download_container_url" { value = "${azurerm_storage_account.ats.primary_blob_endpoint}${azurerm_storage_container.download.name}" }
output "function_app_name" { value = azapi_resource.function_app.name }
output "resource_group_name" { value = azurerm_resource_group.ats.name }
output "storage_account_name" { value = azurerm_storage_account.ats.name }
