terraform {
  required_version = ">= 1.6"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.30"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # Uncomment to store state remotely in S3
  # backend "s3" {
  #   bucket         = "huron-terraform-state"
  #   key            = "huron/terraform.tfstate"
  #   region         = "us-east-1"
  #   encrypt        = true
  #   dynamodb_table = "huron-terraform-locks"
  # }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "huron-genai"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}
