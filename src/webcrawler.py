import requests
import logging
from bs4 import BeautifulSoup
from azure.storage.blob import BlobServiceClient
import time
from datetime import datetime


class WebCrawler:
    def __init__(self, storage_connection_string):
        self.blob_service_client = BlobServiceClient.from_connection_string(
            storage_connection_string
        )
        self.wait_time = 10

    def get_blob_client(self, container_name, blob_name):
        # Check if the container exists
        container_client = self.blob_service_client.get_container_client(container_name)
        if not container_client.exists():
            # Create the container if it does not exist
            self.blob_service_client.create_container(container_name)
        return self.blob_service_client.get_blob_client(container_name, blob_name)

    def get_blob_name(self, url, sub_url, lastmod, project_name="web-scrapper-app"):
        lastmod_formatted = datetime.strptime(lastmod, "%Y-%m-%d").strftime("%Y%m%d")
        url = "" if url == sub_url else url
        blob_name = f"{project_name}/{sub_url.replace(url, '').replace('/','_')}_{lastmod_formatted}.txt"
        return blob_name

    def crawl_and_store(self, sub_url, container_name, blob_name):
        # Send a GET request to the URL
        response = requests.get(sub_url)

        # Parse the HTML content using BeautifulSoup
        soup = BeautifulSoup(response.content, "html.parser")

        # Extract the text content from the HTML
        content = soup.get_text()

        # Create a blob client
        blob_client = self.get_blob_client(
            container_name=container_name, blob_name=blob_name
        )

        # Upload the content to the blob storage
        blob_client.upload_blob(content, overwrite=True)

        logging.info(
            f"URL={sub_url} scraping SUCCESS.\n"
            f"Uploaded to Azure Blob Storage at {blob_name}\n"
            f"Waiting for {self.wait_time} seconds...",
        )
        time.sleep(self.wait_time)


def get_sitemap_urls(url):
    sitemap = requests.get(f"{url}/sitemap.xml").text
    soup = BeautifulSoup(sitemap, "xml")
    return [
        (element.text, element.find_next("lastmod").text)
        for element in soup.find_all("loc")
    ]
