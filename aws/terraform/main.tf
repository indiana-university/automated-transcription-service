terraform {
  required_version = ">= 1.5.7"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 6.50.0, < 7.0.0"
    }
    docker = {
      source  = "kreuzwerker/docker"
      version = ">= 4.4.0, < 5.0.0"
    }
    external = {
      source  = "hashicorp/external"
      version = ">= 2.4.0, < 3.0.0"
    }
    local = {
      source  = "hashicorp/local"
      version = ">= 2.9.0, < 3.0.0"
    }
    null = {
      source  = "hashicorp/null"
      version = ">= 3.3.0, < 4.0.0"
    }
  }
}
provider "aws" {
  region = var.region
}

data "aws_caller_identity" "current" {}

locals {
  account = coalesce(var.account, data.aws_caller_identity.current.account_id)
  tags = {
    Environment = "dev"
    Terraform   = "true"
  }
}