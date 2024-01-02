import azure.functions as func
import requests
import json
import logging
import os

app = func.FunctionApp()
search_service = os.getenv("SEARCH_SERVICE_NAME")
api_key = os.getenv("SEARCH_SERVICE_ADMIN_API_KEY")
blob_storage_connection_string = os.getenv("STORAGE_ACCOUNT_CONNECTION_STRING")
blob_container_name = os.getenv("STORAGE_CONTAINER_NAME")
project_code = os.getenv("PROJECT_CODE")

headers = {"Content-Type": "application/json", "api-key": api_key}

@app.blob_trigger(arg_name="myblob", path="web-scraper-container/telstra",
                               connection="STORAGE_ACCOUNT_CONNECTION_STRING") 
def blob_trigger(myblob: func.InputStream):
    data_source_name = os.getenv("SEARCH_DATASOURCE_NAME")
    index_name = os.getenv("SEARCH_INDEX_NAME")
    indexer_name = os.getenv("SEARCH_INDEXER_NAME")

    # Create data source, index, and indexer
    ai_search_create_data_source(data_source_name)
    ai_search_create_index(index_name)
    ai_search_create_indexer(indexer_name, data_source_name, index_name)

    # Trigger the indexer to start
    response = requests.post(
        f"https://{search_service}.search.windows.net/indexers/{indexer_name}/run?api-version=2020-06-30",
        headers=headers,
    )
    logging.info(response.json())
    logging.info(f"Python blob trigger function processed blob"
                f"Name: {myblob.name}"
                f"Blob Size: {myblob.length} bytes")


def ai_search_create_data_source(data_source_name):
    data_source_payload = {
        "name": data_source_name,
        "description": "Data source for Azure Blob storage container",
        "type": "azureblob",
        "credentials": {"connectionString": blob_storage_connection_string},
        "container": {"name": blob_container_name},
    }
    response = requests.post(
        f"https://{search_service}.search.windows.net/datasources?api-version=2020-06-30",
        headers=headers,
        json=data_source_payload,
    )
    return response.json()


def ai_search_create_index(index_name):
    index_payload = {
        "name": index_name,
        "fields": [
            {"name": "id", "type": "Edm.String", "key": True, "searchable": True},
            {
                "name": "content",
                "type": "Edm.String",
                "searchable": True,
                "filterable": False,
                "sortable": False,
                "facetable": False,
            },
        ],
    }
    response = requests.post(
        f"https://{search_service}.search.windows.net/indexes?api-version=2020-06-30",
        headers=headers,
        json=index_payload,
    )
    return response.json()


def ai_search_create_indexer(indexer_name, data_source_name, index_name):
    indexer_payload = {
        "name": indexer_name,
        "description": "Indexer for Azure Blob storage container",
        "dataSourceName": data_source_name,
        "targetIndexName": index_name,
        "schedule": {"interval": "PT1H", "startTime": "2022-01-01T00:00:00Z"},
    }
    response = requests.post(
        f"https://{search_service}.search.windows.net/indexers?api-version=2020-06-30",
        headers=headers,
        json=indexer_payload,
    )
    return response.json()