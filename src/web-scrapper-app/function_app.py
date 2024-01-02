import logging
import azure.functions as func
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from azure.storage.blob import BlobServiceClient
import os
import time

app = func.FunctionApp()


def get_blob_service_client(
    storage_account_name, storage_account_key, azurite_use=False
):
    if azurite_use:
        account_url = f"https://127.0.0.1:10000/{storage_account_name}"
    else:
        account_url = f"https://{storage_account_name}.blob.core.windows.net"
    return BlobServiceClient(
        account_url=account_url,
        credential=storage_account_key,
    )


def get_blob_client(blob_service_client, container_name, blob_name):
    # Check if the container exists
    container_client = blob_service_client.get_container_client(container_name)
    if not container_client.exists():
        # Create the container if it does not exist
        blob_service_client.create_container(container_name)
    blob_client = blob_service_client.get_blob_client(container_name, blob_name)
    return blob_client


def get_blob_name(url, sub_url, lastmod, folder_name="web-scrapper-app"):
    lastmod_formatted = datetime.strptime(lastmod, "%Y-%m-%d").strftime("%Y%m%d")
    url = "" if url == sub_url else url
    blob_name = f"{folder_name}/{sub_url.replace(url, '').replace('/','_')}_{lastmod_formatted}.txt"
    return blob_name


def get_sitemap_urls(url):
    sitemap = requests.get(f"{url}/sitemap.xml").text
    soup = BeautifulSoup(sitemap, "xml")
    return [
        (element.text, element.find_next("lastmod").text)
        for element in soup.find_all("loc")
    ]


def crawl_url(sub_url):
    response = requests.get(sub_url)
    soup = BeautifulSoup(response.text, "html.parser")
    return soup.get_text()


@app.schedule(
    schedule="0 0 10 * *", arg_name="myTimer", run_on_startup=True, use_monitor=False
)
def simple_web_scraper_app(myTimer: func.TimerRequest) -> None:
    if myTimer.past_due:
        logging.info("The timer is past due!")

    logging.info("Python timer trigger function executed.")

    # Define your Azure storage account name and key
    storage_account_name = os.getenv("STORAGE_ACCOUNT_NAME")
    storage_account_key = os.getenv("STORAGE_ACCOUNT_KEY")
    container_name = os.getenv("STORAGE_CONTAINER_NAME")
    azurite_use = os.getenv("AZURITE_USE")
    url = os.getenv("SITE_URL")
    project_code = os.getenv("PROJECT_CODE")
    wait_time = os.getenv("CRAWLER_WAIT_IN_SECONDS")

    # Create a blob service client
    blob_service_client = get_blob_service_client(
        storage_account_name, storage_account_key, False
    )
    # Get the sitemap
    urls = get_sitemap_urls(url)

    # Crawl each URL
    for sub_url, lastmod in urls:
        # Retrieve the text
        text = crawl_url(sub_url)
        logging.info(f"DONE crawling through {sub_url}.")

        # Format blob name with the lastmod timestamp
        blob_name = get_blob_name(url, sub_url, lastmod, folder_name=project_code)
        logging.info(f"blob_name={blob_name}.")
        # Create a blob client
        blob_client = get_blob_client(blob_service_client, container_name, blob_name)
        # Upload the text to Azure Blob Storage
        blob_client.upload_blob(text, overwrite=True)
        logging.info(
            f"Sub URL={sub_url} scraping SUCCESS.\n"
            f"Uploaded to Azure Blob Storage at {blob_name}\n"
            f"Waiting for {wait_time} seconds...",
        )
        time.sleep(int(wait_time))
    logging.info("Python timer trigger function FINISHED.")
