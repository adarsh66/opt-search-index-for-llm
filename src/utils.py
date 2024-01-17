import requests
from bs4 import BeautifulSoup


def get_sitemap_urls(url):
    sitemap = requests.get(f"{url}/sitemap.xml").text
    soup = BeautifulSoup(sitemap, "xml")
    return [
        (element.find("loc").text, element.find("lastmod").text)
        for element in soup.find_all("url")
    ]


def compare_task_lists(latest_task_list, cached_task_list):
    """
    Compares the latest task list with the cached task list
    Find the differences and return the list of URLs to add and delete
    """
    latest_set = set(latest_task_list)
    cached_set = set(cached_task_list)

    to_add = list(latest_set - cached_set)
    to_delete = list(cached_set - latest_set)

    return (to_add, to_delete)
