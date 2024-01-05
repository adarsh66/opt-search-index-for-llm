import requests
import uuid


class AISearchIndexer:
    def __init__(
        self,
        search_service,
        data_source_name,
        search_index_name,
        vector_index_name,
        indexer_name,
        vector_skillset_name,
        api_key,
        api_version="2023-10-01",
    ):
        self.search_service = search_service
        self.data_source_name = data_source_name
        self.search_index_name = search_index_name
        self.vector_index_name = vector_index_name
        self.indexer_name = indexer_name
        self.vector_skillset_name = vector_skillset_name
        self.api_key = api_key
        self.api_version = api_version
        self.headers = {"Content-Type": "application/json", "api-key": self.api_key}
        self.max_service_name_size = 28
        self.vector_search_profile = self.generate_service_name("vector-profile")
        self.vector_search_config = self.generate_service_name("vector-search-config")
        self.vector_search_vectorizer = self.generate_service_name("vectorizer")
        self.semantic_config = self.generate_service_name("semantic-config")

    def generate_service_name(self, service_name_prefix):
        # Generate a UUID
        uuid_str = str(uuid.uuid4())

        # Concatenate the prefix and the UUID
        service_name = service_name_prefix + "-" + uuid_str

        # Truncate the service name to the maximum size if necessary
        if len(service_name) > self.max_service_name_size:
            service_name = service_name[: self.max_service_name_size]

        return service_name

    def create_data_source_blob_storage(
        self, blob_connection, blob_container_name, query
    ):
        data_source_payload = {
            "name": self.data_source_name,
            "description": "Data source for Azure Blob storage container",
            "type": "azureblob",
            "credentials": {"connectionString": blob_connection},
            "container": {"name": blob_container_name, "query": query},
            "dataChangeDetectionPolicy": {
                "@odata.type": "#Microsoft.Azure.Search.NativeBlobSoftDeleteDeletionDetectionPolicy"
            },
        }
        response = requests.post(
            f"https://{self.search_service}.search.windows.net/datasources?{self.api_version}",
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
            f"https://{self.search_service}.search.windows.net/datasources/{self.data_source_name}?{self.api_version}",
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
                        "retrievable": True,
                        "searchable": True,
                        "filterable": False,
                        "sortable": False,
                        "facetable": False,
                    },
                    {
                        "name": "metadata_storage_path",
                        "type": "Edm.String",
                        "retrievable": True,
                        "searchable": False,
                        "filterable": True,
                        "sortable": False,
                        "facetable": False,
                    },
                    {
                        "name": "metadata_storage_name",
                        "type": "Edm.String",
                        "searchable": False,
                        "filterable": True,
                        "sortable": True,
                    },
                    {
                        "name": "metadata_storage_size",
                        "type": "Edm.Int64",
                        "searchable": False,
                        "filterable": True,
                        "sortable": True,
                    },
                    {
                        "name": "metadata_storage_content_type",
                        "type": "Edm.String",
                        "searchable": False,
                        "filterable": True,
                        "sortable": True,
                    },
                ],
            }
            return index_payload
        else:
            return False

    def create_vector_index_payload(
        self, model_uri, model_name, model_api_key, embedding_dims
    ):
        if self.check_data_source_exists():
            index_payload = {
                "name": self.index_name,
                "defaultScoringProfile": "",
                "fields": [
                    {
                        "name": "id",
                        "type": "Edm.String",
                        "searchable": True,
                        "filterable": True,
                        "retrievable": True,
                        "sortable": False,
                        "facetable": False,
                        "key": True,
                        "indexAnalyzer": None,
                        "searchAnalyzer": None,
                        "analyzer": "keyword",
                    },
                    {
                        "name": "chunk",
                        "type": "Edm.String",
                        "searchable": True,
                        "filterable": False,
                        "retrievable": True,
                        "sortable": False,
                        "facetable": False,
                        "key": False,
                        "analyzer": "standard.lucene",
                    },
                    {
                        "name": "parent_key",
                        "type": "Edm.String",
                        "searchable": False,
                        "filterable": True,
                        "retrievable": True,
                        "sortable": False,
                        "facetable": False,
                        "key": False,
                    },
                    {
                        "name": "embedding",
                        "type": "Collection(Edm.Single)",
                        "searchable": True,
                        "filterable": False,
                        "retrievable": True,
                        "sortable": False,
                        "facetable": False,
                        "key": False,
                        "dimensions": embedding_dims,
                        "vectorSearchProfile": self.vector_search_profile,
                        "synonymMaps": [],
                    },
                ],
                "scoringProfiles": [],
                "corsOptions": None,
                "suggesters": [],
                "analyzers": [],
                "normalizers": [],
                "tokenizers": [],
                "tokenFilters": [],
                "charFilters": [],
                "encryptionKey": None,
                "similarity": {
                    "@odata.type": "#Microsoft.Azure.Search.BM25Similarity",
                    "k1": None,
                    "b": None,
                },
                "semantic": {
                    "defaultConfiguration": None,
                    "configurations": [
                        {
                            "name": self.semantic_config,
                            "prioritizedFields": {
                                "titleField": None,
                                "prioritizedContentFields": [{"fieldName": "chunk"}],
                                "prioritizedKeywordsFields": [
                                    {"fieldName": "id"},
                                    {"fieldName": "parent_key"},
                                ],
                            },
                        }
                    ],
                },
                "vectorSearch": {
                    "algorithms": [
                        {
                            "name": self.vector_search_config,
                            "kind": "hnsw",
                            "hnswParameters": {
                                # use cosine similarity when using OpenAI models,
                                # else use the distance metric of the embedding model
                                "metric": "cosine",
                                "m": 4,  # bi-directional link count
                                "efConstruction": 400,  # number of nearest neighbors to consider during indexiing
                                "efSearch": 500,  # number of nearest neighbors to consider during search
                            },
                            "exhaustiveKnnParameters": None,
                        }
                    ],
                    "profiles": [
                        {
                            "name": self.vector_search_profile,
                            "algorithm": self.vector_search_config,
                            "vectorizer": self.vector_search_vectorizer,
                        }
                    ],
                    "vectorizers": [
                        {
                            "name": self.vector_search_vectorizer,
                            "kind": "azureOpenAI",
                            "azureOpenAIParameters": {
                                "resourceUri": model_uri,
                                "deploymentId": model_name,
                                "apiKey": model_api_key,
                                "authIdentity": None,
                            },
                        }
                    ],
                },
            }
            return index_payload
        else:
            return False

    def create_index(self, index_type="search", **kwargs):
        if self.check_data_source_exists():
            if index_type == "search":
                index_payload = self.create_search_index_payload()
            elif index_type == "vector":
                index_payload = self.create_vector_index_payload(**kwargs)
            response = requests.post(
                f"https://{self.search_service}.search.windows.net/indexes?{self.api_version}",
                headers=self.headers,
                json=index_payload,
            )
            self.index = response.json()
            return True
        else:
            return False

    def create_skillset(self, model_uri, model_name, model_api_key):
        """
        Create a skillset for the indexer
        This skillset will be used to enrich the content before indexing
        """
        skillset_payload = {
            "name": self.vector_skillset_name,
            "description": "skills required for vector embedding creation processing",
            "skills": [
                {
                    "@odata.type": "#Microsoft.Skills.Text.SplitSkill",
                    "name": "text-chunking-skill",
                    "description": "Skillset to describe the Text chunking required for vectorization",
                    "context": "/document",
                    "defaultLanguageCode": "en",
                    "textSplitMode": "pages",
                    "maximumPageLength": 2000,
                    "pageOverlapLength": 500,
                    "maximumPagesToTake": 0,
                    "inputs": [{"name": "text", "source": "/document/content"}],
                    "outputs": [{"name": "textItems", "targetName": "chunks"}],
                },
                {
                    "@odata.type": "#Microsoft.Skills.Text.AzureOpenAIEmbeddingSkill",
                    "name": "embedding-generation-skill",
                    "description": "",
                    "context": "/document/chunks/*",
                    "resourceUri": model_uri,
                    "apiKey": model_api_key,
                    "deploymentId": model_name,
                    "inputs": [{"name": "text", "source": "/document/chunks/*"}],
                    "outputs": [{"name": "embedding", "targetName": "embedding"}],
                },
            ],
            "indexProjections": {
                "selectors": [
                    {
                        "targetIndexName": self.vector_index_name,
                        "parentKeyFieldName": "parent_key",
                        "sourceContext": "/document/chunks/*",
                        "mappings": [
                            {
                                "name": "chunk",
                                "source": "/document/chunks/*",
                                "sourceContext": None,
                                "inputs": [],
                            },
                            {
                                "name": "embedding",
                                "source": "/document/chunks/*/embedding",
                                "sourceContext": None,
                                "inputs": [],
                            },
                        ],
                    }
                ],
                "parameters": {},
            },
        }
        response = requests.post(
            f"https://{self.search_service}.search.windows.net/skillsets?{self.api_version}",
            headers=self.headers,
            json=skillset_payload,
        )
        self.skillset = response.json()

    def create_indexer(self, cache_storage_connection, batch_size=100):
        if self.index:
            indexer_payload = {
                "name": self.indexer_name,
                "description": "Indexer for Azure Blob storage container",
                "dataSourceName": self.data_source_name,
                "targetIndexName": self.search_index_name,
                "skillsetName": self.vector_skillset_name,
                "schedule": {"interval": "PT24H", "startTime": "2024-01-01T00:00:00Z"},
                "parameters": {
                    "configuration": {
                        "indexedFileNameExtensions": ".txt",
                        "parsingMode": "text",
                        "dataToExtract": "contentAndMetadata",
                    },
                    "batchSize": batch_size,
                },
                "cache": {
                    "enableReprocessing": True,
                    "storageConnectionString": cache_storage_connection,
                },
            }
            response = requests.post(
                f"https://{self.search_service}.search.windows.net/indexers?{self.api_version}",
                headers=self.headers,
                json=indexer_payload,
            )
            self.indexer = response.json()
            return True
        else:
            return False
