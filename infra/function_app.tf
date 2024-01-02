provider "azurerm" {
  features {}
}

variable "GITHUB_TOKEN" {}

resource "azurerm_resource_group" "search_app" {
  name     = "web-scraper-search-app"
  location = "US East 2"
}

resource "azurerm_storage_account" "search_app" {
  name                     = "searchappstorageacc"
  resource_group_name      = azurerm_resource_group.search_app.name
  location                 = azurerm_resource_group.search_app.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
}

resource "azurerm_storage_container" "search_app" {
  name                  = "webscarpersearchapp"
  storage_account_name  = azurerm_storage_account.search_app.name
  container_access_type = "private"
}

resource "azurerm_app_service_plan" "search_app" {
  name                = "search_app-appserviceplan"
  location            = azurerm_resource_group.search_app.location
  resource_group_name = azurerm_resource_group.search_app.name

  sku {
    tier = "Standard"
    size = "S1"
  }
}

resource "azurerm_function_app" "search_app" {
  name                       = "search_app-functionapp"
  location                   = azurerm_resource_group.search_app.location
  resource_group_name        = azurerm_resource_group.search_app.name
  app_service_plan_id        = azurerm_app_service_plan.search_app.id
  storage_account_name       = azurerm_storage_account.search_app.name
  storage_account_access_key = azurerm_storage_account.search_app.primary_access_key
  version                    = "~2"

  app_settings = {
    "AzureWebJobsStorage" = "DefaultEndpointsProtocol=https;AccountName=${azurerm_storage_account.search_app.name};AccountKey=${azurerm_storage_account.search_app.primary_access_key}"
  }

  source_control {
    repo_url                 = format("https://%s@github.com/adarsh66/repo", var.GITHUB_TOKEN)
    branch                   = "main"
    is_manual_integration    = true
    }
}