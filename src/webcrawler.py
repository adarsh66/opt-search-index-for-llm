import requests
import logging
from bs4 import BeautifulSoup
from azure.storage.blob import BlobServiceClient
import time
from datetime import datetime
import html2text
import csv
from io import StringIO


class AzureBlobHelper:
    def __init__(self, storage_connection_string):
        self.blob_service_client = BlobServiceClient.from_connection_string(
            storage_connection_string
        )

    def get_blob_client(self, container_name, blob_name):
        # Check if the container exists
        container_client = self.blob_service_client.get_container_client(container_name)
        if not container_client.exists():
            # Create the container if it does not exist
            self.blob_service_client.create_container(container_name)
        return self.blob_service_client.get_blob_client(container_name, blob_name)

    def read_csv_blob(self, container_name, blob_name):
        blob_client = self.get_blob_client(container_name, blob_name)
        if not blob_client.exists():
            return []
        blob_data = blob_client.download_blob().readall()
        csv_text = blob_data.decode("utf-8")

        csv_reader = csv.reader(StringIO(csv_text))
        rows = [tuple(row) for row in csv_reader]

        return rows

    def write_csv_blob(self, container_name, blob_name, data):
        csv_buffer = StringIO()
        csv_writer = csv.writer(csv_buffer)
        csv_writer.writerows(data)

        csv_text = csv_buffer.getvalue()
        csv_bytes = csv_text.encode("utf-8")

        blob_client = self.get_blob_client(container_name, blob_name)
        blob_client.upload_blob(csv_bytes, overwrite=True)

    def get_blob_name(self, url, sub_url, lastmod, project_name="web-scrapper-app"):
        lastmod_formatted = datetime.strptime(lastmod, "%Y-%m-%d").strftime("%Y%m%d")
        url = "" if url == sub_url else url
        blob_name = f"{project_name}/{sub_url.replace(url, '').replace('/','_')}_{lastmod_formatted}.txt"
        return blob_name

    def upload_blob(self, container_name, blob_name, content):
        # Create a blob client
        blob_client = self.get_blob_client(
            container_name=container_name, blob_name=blob_name
        )

        # Upload the content to the blob storage
        blob_client.upload_blob(content, overwrite=True)

        logging.info(f"Uploaded to Azure Blob Storage at {blob_name}\n")

    def delete_blob(self, container_name, blob_name):
        blob_client = self.get_blob_client(container_name, blob_name)

        if blob_client.exists():
            blob_client.delete_blob()
        logging.info(f"Deleted blob {blob_name}\n")


class WebCrawler:
    def __init__(self):
        self.wait_time = 10

    def parse_html_bs4(self, html):
        soup = BeautifulSoup(html, "html.parser")
        return soup.get_text()

    def parse_html_html2text(self, html):
        h = html2text.HTML2Text()
        h.ignore_links = True
        h.ignore_images = True
        h.ignore_emphasis = True
        h.ignore_tables = True
        h.ignore_anchors = True
        return h.handle(html)

    def parse_html(self, html, parser_lib="bs4"):
        if parser_lib == "bs4":
            return self.parse_html_bs4(html)
        elif parser_lib == "html2text":
            html_text = self.parse_html_bs4(html)
            return self.parse_html_html2text(html_text).strip()
        else:
            raise ValueError("Parser library not supported.")

    def crawl_and_store(
        self, sub_url, blob_helper, container_name, blob_name, parser_lib="html2text"
    ):
        # Send a GET request to the URL
        response = requests.get(sub_url)

        # Parse the HTML content using specified parser library
        content = self.parse_html(response.content, parser_lib=parser_lib)

        # Upload the content to the blob storage
        blob_helper.upload_blob(container_name, blob_name, content)

        logging.info(
            f"URL={sub_url} scraping SUCCESS.\n"
            f"Uploaded to Azure Blob Storage at {blob_name}\n"
            f"Waiting for {self.wait_time} seconds...",
        )
        time.sleep(self.wait_time)
