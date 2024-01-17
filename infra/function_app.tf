variable "resource_group_name" {
  description = "Azure Resource group name"
  type        = string
}

variable "resource_location" {
  description = "Azure Resource Region"
  type        = string
}

variable "storage_account_name" {
  description = "Azure Blob storage account name"
  type        = string
}

variable "storage_container_name" {
  description = "Azure Blob storage container name"
  type        = string
}

variable "durable_functions_name" {
  description = "Azure Durable functions (serverless)"
  type        = string
}

variable "search_service_name" {
  description = "Azure AI Search service name"
  type        = string
}

variable "ai_project_name" {
  description = "Azure AI Project name"
  type        = string
}





provider "azurerm" {
  features {}
}

resource "azurerm_resource_group" "search_app" {
  name     = var.resource_group_name
  location = var.resource_location
}

resource "azurerm_storage_account" "search_app" {
  name                     = var.storage_account_name
  resource_group_name      = azurerm_resource_group.search_app.name
  location                 = azurerm_resource_group.search_app.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
}

resource "azurerm_storage_container" "search_app" {
  name                  = var.storage_container_name
  storage_account_name  = azurerm_storage_account.search_app.name
  container_access_type = "private"
}

resource "azurerm_service_plan" "search_app" {
  name                = "search_app-appserviceplan"
  location            = azurerm_resource_group.search_app.location
  resource_group_name = azurerm_resource_group.search_app.name
  os_type             = "Linux"
  sku_name            = "Y1"
}

resource "azurerm_linux_function_app" "search_app" {
  name                       = var.durable_functions_name
  location                   = azurerm_resource_group.search_app.location
  resource_group_name        = azurerm_resource_group.search_app.name
  service_plan_id            = azurerm_service_plan.search_app.id
  storage_account_name       = azurerm_storage_account.search_app.name
  storage_account_access_key = azurerm_storage_account.search_app.primary_access_key
  
  site_config {}

  app_settings = {
    "AzureWebJobsStorage" = "DefaultEndpointsProtocol=https;AccountName=${azurerm_storage_account.search_app.name};AccountKey=${azurerm_storage_account.search_app.primary_access_key}"
  }
}

resource "azurerm_search_service" "ss" {
  name                = var.search_service_name
  resource_group_name = azurerm_resource_group.search_app.name
  location            = azurerm_resource_group.search_app.location
  sku                 = "standard"
}

resource "azurerm_cognitive_account" "ca" {
  name                  = var.ai_project_name
  location              = azurerm_resource_group.search_app.location
  resource_group_name   = azurerm_resource_group.search_app.name
  sku_name              = "S1"
  kind                  = "CognitiveServices"
}
