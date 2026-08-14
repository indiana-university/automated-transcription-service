terraform {
  required_version = ">= 1.5.7"

  backend "azurerm" {}

  required_providers {
    archive = {
      source  = "hashicorp/archive"
      version = ">= 2.7.1, < 3.0.0"
    }
    azurerm = {
      source  = "hashicorp/azurerm"
      version = ">= 4.81.0, < 5.0.0"
    }
    azapi = {
      source  = "Azure/azapi"
      version = ">= 2.4.0, < 3.0.0"
    }
    random = {
      source  = "hashicorp/random"
      version = ">= 3.7.2, < 4.0.0"
    }
  }
}

provider "azurerm" {
  features {}
  storage_use_azuread = true
}
provider "azapi" {}
data "azurerm_client_config" "current" {}

resource "random_string" "suffix" {
  length  = 8
  lower   = true
  numeric = true
  special = false
  upper   = false
}

locals {
  compact_prefix = substr(lower(replace(var.prefix, "-", "")), 0, 8)
  suffix         = random_string.suffix.result
  storage_name   = "${local.compact_prefix}${local.suffix}"
  tags = {
    Project   = "ATS"
    Terraform = "true"
  }
}

resource "azurerm_resource_group" "ats" {
  name     = "${var.prefix}-rg-${local.suffix}"
  location = var.location
  tags     = local.tags
}
