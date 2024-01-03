import requests


class AISearchIndexer:
    def __init__(
        self, search_service, data_source_name, index_name, indexer_name, api_key
    ):
        self.search_service = search_service
        self.data_source_name = data_source_name
        self.index_name = index_name
        self.indexer_name = indexer_name
        self.api_key = api_key
        self.headers = {"Content-Type": "application/json", "api-key": self.api_key}

    def create_data_source_blob_storage(self, blob_connection, blob_container_name):
        data_source_payload = {
            "name": self.data_source_name,
            "description": "Data source for Azure Blob storage container",
            "type": "azureblob",
            "credentials": {"connectionString": blob_connection},
            "container": {"name": blob_container_name},
        }
        response = requests.post(
            f"https://{self.search_service}.search.windows.net/datasources?api-version=2020-06-30",
            headers=self.headers,
            json=data_source_payload,
        )
        if response.status_code == 200:
            self.data_source = response.json()
            return True
        else:
            return False

    def check_data_source_exists(self):
        response = requests.get(
            f"https://{self.search_service}.search.windows.net/datasources/{self.data_source_name}?api-version=2020-06-30",
            headers=self.headers,
        )
        return response.status_code == 200

    def create_search_index_payload(self):
        if self.check_data_source_exists():
            index_payload = {
                "name": self.index_name,
                "fields": [
                    {
                        "name": "id",
                        "type": "Edm.String",
                        "key": True,
                        "searchable": True,
                    },
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
            return index_payload
        else:
            return False

    def create_vector_index_payload(self):
        if self.check_data_source_exists():
            index_payload = {
                "name": self.index_name,
                "type": "Collection(Edm.Double)",
                "fields": [
                    {
                        "name": "dim",
                        "type": "Edm.Int32",
                    },
                    {
                        "name": "value",
                        "type": "Edm.Double",
                    },
                ],
                "searchable": False,
                "filterable": False,
                "facetable": False,
                "sortable": False,
            }
            return index_payload
        else:
            return False

    def create_index(self, index_type="search"):
        if self.check_data_source_exists():
            if index_type == "search":
                index_payload = self.create_search_index_payload()
            elif index_type == "vector":
                index_payload = self.create_vector_index_payload()
            response = requests.post(
                f"https://{self.search_service}.search.windows.net/indexes?api-version=2020-06-30",
                headers=self.headers,
                json=index_payload,
            )
            self.index = response.json()
            return True
        else:
            return False

    def create_indexer(self):
        if self.index:
            indexer_payload = {
                "name": self.indexer_name,
                "description": "Indexer for Azure Blob storage container",
                "dataSourceName": self.data_source_name,
                "targetIndexName": self.index_name,
                "schedule": {"interval": "PT1H", "startTime": "2022-01-01T00:00:00Z"},
            }
            response = requests.post(
                f"https://{self.search_service}.search.windows.net/indexers?api-version=2020-06-30",
                headers=self.headers,
                json=indexer_payload,
            )
            self.indexer = response.json()
            return True
        else:
            return False
