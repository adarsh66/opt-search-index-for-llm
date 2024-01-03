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
CONTAINER_NAME = os.getenv("STORAGE_CONTAINER_NAME")
STORAGE_CONNECTION = os.getenv("STORAGE_CONNECTION")
SEARCH_SERVICE = os.getenv("SEARCH_SERVICE_NAME")
SEARCH_API_KEY = os.getenv("SEARCH_API_KEY")
SEARCH_INDEX = os.getenv("SEARCH_INDEX_NAME")
SEARCH_INDEXER = os.getenv("SEARCH_INDEXER_NAME")
SEARCH_DATASOURCE_NAME = os.getenv("SEARCH_DATASOURCE_NAME")


@app.schedule(
    schedule="* * 10 * * *", arg_name="myTimer", run_on_startup=True, use_monitor=False
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
    logging.info(f"Number of URLs to crawl: {len(task_list)}")

    logging.info("STARTING crawling of the website.")
    parallel_tasks = [
        context.call_activity("web_scraper_activity", task) for task in task_list
    ]
    results = yield context.task_all(parallel_tasks)

    logging.info("CRAWLING of the website COMPLETED.")

    yield context.call_activity("search_index_runner", "search")

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
            index_name=f"{SEARCH_INDEX}-{indextype}",
            indexer_name=f"{SEARCH_INDEXER}-{indextype}",
            api_key=SEARCH_API_KEY,
        )
        search_indexer.create_data_source_blob_storage(
            STORAGE_CONNECTION, CONTAINER_NAME
        )
        search_indexer.create_index(index_type=indextype)
        search_indexer.create_indexer()
        logging.info("INDEXING of the crawled data COMPLETED.")
        return True
    except Exception as e:
        logging.error("INDEXING of the crawled data FAILED. Error: %s", e)
        return False
