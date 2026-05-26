terraform {
  required_version = ">= 1.6"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.90"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # Uncomment to store state remotely in Azure Blob Storage
  # backend "azurerm" {
  #   resource_group_name  = "huron-tfstate-rg"
  #   storage_account_name = "hurontfstate"
  #   container_name       = "tfstate"
  #   key                  = "huron.terraform.tfstate"
  # }
}

provider "azurerm" {
  features {
    key_vault {
      purge_soft_delete_on_destroy    = true
      recover_soft_deleted_key_vaults = true
    }
  }
}
