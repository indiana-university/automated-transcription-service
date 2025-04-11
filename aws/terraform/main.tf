terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 4.34.0"
    }
    docker = {
      source  = "kreuzwerker/docker"
      version = ">= 3.0"
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