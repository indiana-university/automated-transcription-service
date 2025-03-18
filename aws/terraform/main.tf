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
  backend "s3" {
    key    = "terraform.tfstate"
    region = "us-east-1"
  }
}
provider "aws" {
  region = var.region
}

locals {
  tags = {
    Environment = "dev"
    Terraform   = "true"
  }
}