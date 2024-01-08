import logging
import azure.functions as func
import datetime
import azure.durable_functions as df
from webcrawler import WebCrawler, get_sitemap_urls
from aisearch_utils import AISearchIndexer
import os

app = df.DFApp(http_auth_level=func.AuthLevel.ANONYMOUS)


URL = os.getenv("PROJECT_URL")
PROJECT_NAME = os.getenv("PROJECT_NAME")
SAMPLE_SIZE = int(os.getenv("SAMPLE_SIZE"))
CONTAINER_NAME = os.getenv("STORAGE_CONTAINER_NAME")
STORAGE_CONNECTION = os.getenv("STORAGE_CONNECTION")
SEARCH_SERVICE = os.getenv("SEARCH_SERVICE_NAME")
SEARCH_API_KEY = os.getenv("SEARCH_API_KEY")
SEARCH_INDEX_NAME = os.getenv("SEARCH_INDEX_NAME")
SEARCH_INDEXER_NAME = os.getenv("SEARCH_INDEXER_NAME")
SEARCH_INDEXER_BATCH_SIZE = os.getenv("SEARCH_INDEXER_BATCH_SIZE")
SEARCH_DATASOURCE_NAME = os.getenv("SEARCH_DATASOURCE_NAME")
VECTOR_SKILLSET_NAME = os.getenv("VECTOR_SKILLSET_NAME")
VECTOR_INDEX_NAME = os.getenv("VECTOR_INDEX_NAME")
VECTOR_EMBEDDING_URI = os.getenv("VECTOR_EMBEDDING_URI")
VECTOR_EMBEDDING_API_KEY = os.getenv("VECTOR_EMBEDDING_API_KEY")
VECTOR_EMBEDDING_ID = os.getenv("VECTOR_EMBEDDING_ID")
VECTOR_EMBEDDING_DIMENSION = os.getenv("VECTOR_EMBEDDING_DIMENSION")


@app.schedule(
    schedule="0 0 10 * * *", arg_name="myTimer", run_on_startup=True, use_monitor=False
)
@app.durable_client_input(client_name="client")
async def web_scraper_trigger(
    myTimer: func.TimerRequest, client: df.DurableOrchestrationClient
) -> None:
    """
    Timer trigger function to start the orchestrator.
    Will run every day at 10 AM.
    """
    utc_timestamp = (
        datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc).isoformat()
    )
    logging.info("Python timer trigger function ran at %s", utc_timestamp)
    if myTimer.past_due:
        logging.info("The timer is past due!")
    # client = df.DurableOrchestrationClient(starter)
    instance_id = await client.start_new("web_scraper_orchestrator", None, None)
    logging.info(
        "Python timer trigger function executed. Orchestrator ID: '%s'.", instance_id
    )


@app.orchestration_trigger(context_name="context")
def web_scraper_orchestrator(context: df.DurableOrchestrationContext) -> list:
    """
    Orchestrator function to crawl the website and index the crawled data.
    Will run every day at 10 AM.
    Will parallel process the URLs to crawl.
    Run the indexer after all the URLs have been crawled.
    """
    logging.info("Python orchestrator function started.")

    logging.info(f"Gettnig URLs from sitemap: {URL}/sitemap.xml")
    task_list = get_sitemap_urls(url=URL)
    task_list = task_list[:SAMPLE_SIZE] if SAMPLE_SIZE > 0 else task_list
    logging.info(f"Number of URLs to crawl: {len(task_list)}")

    logging.info("STARTING crawling of the website.")
    results = []
    parallel_tasks = [
        context.call_activity("web_scraper_activity", task) for task in task_list
    ]
    results = yield context.task_all(parallel_tasks)

    logging.info("CRAWLING of the website COMPLETED.")

    yield context.call_activity("search_index_runner", "vector")

    logging.info("Python orchestrator function completed.")
    return results


@app.activity_trigger(input_name="task")
def web_scraper_activity(task: tuple) -> str:
    """
    Scrapes the URL and stores the data in Azure Blob Storage.
    task: tuple of (url, lastmod)
    """
    url, lastmod = task
    logging.info(f"Crawling of URL STARTED. URL={url}")
    crawler = WebCrawler(STORAGE_CONNECTION)
    blob_name = crawler.get_blob_name(
        url=URL, sub_url=url, lastmod=lastmod, project_name=PROJECT_NAME
    )
    crawler.crawl_and_store(
        sub_url=url, container_name=CONTAINER_NAME, blob_name=blob_name
    )
    logging.info(f"Crawling of URL COMPLETED. URL={url}")
    return blob_name


@app.activity_trigger(input_name="indextype")
def search_index_runner(indextype: str) -> bool:
    """
    Runs the search indexer.
    indextype: "search" or "vector"
    """
    logging.info("STARTING indexing of the crawled data.")
    try:
        search_indexer = AISearchIndexer(
            search_service=SEARCH_SERVICE,
            data_source_name=SEARCH_DATASOURCE_NAME,
            search_index_name=SEARCH_INDEX_NAME,
            vector_index_name=VECTOR_INDEX_NAME,
            indexer_name=SEARCH_INDEXER_NAME,
            vector_skillset_name=VECTOR_SKILLSET_NAME,
            api_key=SEARCH_API_KEY,
        )

        # Step 1 - Create the Data Source
        response = search_indexer.create_data_source_blob_storage(
            blob_connection=STORAGE_CONNECTION,
            blob_container_name=CONTAINER_NAME,
            query=PROJECT_NAME,
        )
        logging.info(f"Search Data Source status = {response}.")

        # Step 2 - Create the Keyword Index
        response = search_indexer.create_index(index_type="search")
        logging.info(f"Keyword Search Index status = {response}.")

        # Step 3 - Create the Vector Index (with embedding model)
        response = search_indexer.create_index(
            index_type="vector",
            model_uri=VECTOR_EMBEDDING_URI,
            model_name=VECTOR_EMBEDDING_ID,
            model_api_key=VECTOR_EMBEDDING_API_KEY,
            embedding_dims=VECTOR_EMBEDDING_DIMENSION,
        )
        logging.info(f"Vector Search Index status = {response}.")

        # Step 4 - Create the Vector embedding skillset to enhance the indexer
        response = search_indexer.create_skillset(
            model_uri=VECTOR_EMBEDDING_URI,
            model_name=VECTOR_EMBEDDING_ID,
            model_api_key=VECTOR_EMBEDDING_API_KEY,
        )
        logging.info(f"Vector Skillset status = {response}.")

        # Step 5 - Create the indexer which will ultimately call the vector embedding skillset
        response = search_indexer.create_indexer(
            cache_storage_connection=STORAGE_CONNECTION,
            batch_size=SEARCH_INDEXER_BATCH_SIZE,
        )
        logging.info(f"Search Indexer status = {response}")
        return True
    except Exception as e:
        logging.error(
            "Create/ Update of Index of the crawled data FAILED. Error: %s", e
        )
        return False
