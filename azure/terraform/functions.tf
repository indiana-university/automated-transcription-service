resource "azurerm_user_assigned_identity" "functions" {
  name                = "${var.prefix}-functions-${local.suffix}"
  location            = azurerm_resource_group.ats.location
  resource_group_name = azurerm_resource_group.ats.name
  tags                = local.tags
}

locals { function_storage_roles = toset(["Storage Blob Data Owner", "Storage Queue Data Contributor", "Storage Table Data Contributor"]) }

resource "azurerm_role_assignment" "function_storage" {
  for_each             = local.function_storage_roles
  scope                = azurerm_storage_account.ats.id
  role_definition_name = each.value
  principal_id         = azurerm_user_assigned_identity.functions.principal_id
}

resource "azurerm_role_assignment" "function_speech" {
  scope                = azurerm_cognitive_account.speech.id
  role_definition_name = "Cognitive Services Speech User"
  principal_id         = azurerm_user_assigned_identity.functions.principal_id
}

resource "azurerm_role_assignment" "function_keyvault" {
  scope                = azurerm_key_vault.ats.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.functions.principal_id
}

data "archive_file" "functions" {
  type        = "zip"
  source_dir  = "${path.module}/../src/functions"
  output_path = "${path.module}/.terraform/ats-functions.zip"
}

resource "azurerm_service_plan" "functions" {
  name                = "${var.prefix}-flex-${local.suffix}"
  resource_group_name = azurerm_resource_group.ats.name
  location            = azurerm_resource_group.ats.location
  os_type             = "Linux"
  sku_name            = "FC1"
  tags                = local.tags
}

resource "azapi_resource" "function_app" {
  type      = "Microsoft.Web/sites@2024-04-01"
  name      = "${var.prefix}-functions-${local.suffix}"
  parent_id = azurerm_resource_group.ats.id
  location  = azurerm_resource_group.ats.location

  identity {
    type         = "SystemAssigned, UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.functions.id]
  }

  body = {
    kind = "functionapp,linux"
    properties = {
      serverFarmId        = azurerm_service_plan.functions.id
      httpsOnly           = true
      reserved            = true
      publicNetworkAccess = "Enabled"
      siteConfig = {
        minTlsVersion = "1.2"
      }
      functionAppConfig = {
        deployment = {
          storage = {
            type  = "blobContainer"
            value = "${azurerm_storage_account.ats.primary_blob_endpoint}${azurerm_storage_container.deploy.name}"
            authentication = {
              type = "SystemAssignedIdentity"
            }
          }
        }
        runtime = {
          name    = "python"
          version = "3.11"
        }
        scaleAndConcurrency = {
          maximumInstanceCount = 20
          instanceMemoryMB     = 2048
        }
      }
    }
  }

  response_export_values  = ["identity.principalId"]
  ignore_casing           = true
  ignore_missing_property = true
  tags = merge(local.tags, {
    "hidden-link: /app-insights-resource-id" = replace(azurerm_application_insights.ats.id, "Microsoft.Insights", "microsoft.insights")
  })

  depends_on = [azurerm_role_assignment.function_keyvault, azurerm_role_assignment.function_speech, azurerm_role_assignment.function_storage, azurerm_role_assignment.speech_storage]
}

resource "azapi_resource" "function_app_settings" {
  type      = "Microsoft.Web/sites/config@2024-04-01"
  name      = "appsettings"
  parent_id = azapi_resource.function_app.id

  ignore_missing_property = true

  lifecycle {
    ignore_changes = [tags]
  }

  body = {
    properties = {
      APPLICATIONINSIGHTS_CONNECTION_STRING   = azurerm_application_insights.ats.connection_string
      AZURE_CLIENT_ID                         = azurerm_user_assigned_identity.functions.client_id
      AzureWebJobsFeatureFlags                = "EnableWorkerIndexing"
      AzureWebJobsStorage__accountName        = azurerm_storage_account.ats.name
      AzureWebJobsStorage__credential         = "managedidentity"
      AzureWebJobsStorage__clientId           = azurerm_user_assigned_identity.functions.client_id
      EVENT_QUEUE_CONNECTION__queueServiceUri = azurerm_storage_account.ats.primary_queue_endpoint
      EVENT_QUEUE_CONNECTION__credential      = "managedidentity"
      EVENT_QUEUE_CONNECTION__clientId        = azurerm_user_assigned_identity.functions.client_id
      STORAGE_ACCOUNT_URL                     = azurerm_storage_account.ats.primary_blob_endpoint
      DOWNLOAD_CONTAINER                      = azurerm_storage_container.download.name
      JOBS_TABLE                              = azapi_resource.jobs.name
      SPEECH_ENDPOINT                         = azurerm_cognitive_account.speech.endpoint
      SPEECH_API_VERSION                      = "2025-10-15"
      SPEECH_LOCALES                          = join(",", var.speech_locales)
      MAX_SPEAKERS                            = tostring(var.max_speakers)
      POLL_INTERVAL_MINUTES                   = tostring(var.poll_interval_minutes)
      CONFIDENCE                              = tostring(var.confidence_score)
      DOCUMENT_TITLE                          = var.document_title
      KEY_VAULT_URL                           = azurerm_key_vault.ats.vault_uri
      TEAMS_NOTIFICATION                      = tostring(var.teams_webhook != "")
      SLACK_NOTIFICATION                      = tostring(var.slack_webhook != "")
    }
  }
}

resource "azapi_resource" "function_scm_basic_auth" {
  type      = "Microsoft.Web/sites/basicPublishingCredentialsPolicies@2024-04-01"
  name      = "scm"
  parent_id = azapi_resource.function_app.id

  ignore_missing_property = true

  lifecycle {
    ignore_changes = [tags]
  }

  body = {
    properties = {
      allow = true
    }
  }
}

resource "azurerm_role_assignment" "function_deployment_storage" {
  scope                = azurerm_storage_account.ats.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azapi_resource.function_app.identity[0].principal_id
}
