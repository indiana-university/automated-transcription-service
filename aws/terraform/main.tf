terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 4.34.0"
    }
  }
  backend "s3" {
    key    = "terraform.tfstate"
    region = "us-east-1"
  }
}
provider "aws" {
  shared_config_files      = var.config
  shared_credentials_files = var.credentials
  profile                  = var.profile
  region                   = var.region
}
