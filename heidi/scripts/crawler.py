import requests
import sys
import os
import time
import variables
from bs4 import BeautifulSoup, Comment
from urllib.parse import urlsplit, urljoin

"""
Downloads all websites containing clinical guidelines found on the website 
https://www.rch.org.au/clinicalguide/". Raw version of each site is saved 
in folder data/raw_docs. Another version where extraneous tags have been 
cleaned from the HTML are saved in the folder data/cleaned_docs
"""


def run_crawler():
    index_url = "https://www.rch.org.au/clinicalguide/"
    urls = extract_all_links(index_url)
    urls = sorted(list(set(urls)))  # remove duplicates and sort alphabetically
    print('Extracted {len(urls)} links from {index_url}')

    download_stats = {"success": [], "fail": []}
    for idx, url in enumerate(urls):
        result = download_webpage(url)
        if result:
            download_stats['success'].append(url)
        else:
            download_stats['fail'].append(url)
        print(f"Downloaded webpage #{idx}: {url}")
        time.sleep(1)

    num_success = len(download_stats['success'])
    num_failed = len(download_stats['fail'])
    print(f"{num_success} files downloaded successfully, {num_failed} download failed.")


def extract_all_links(url: str) -> list[str]:
    """
    Extracts all the <a href> links found in the url, i.e. https://www.rch.org.au/clinicalguide/
    These links all refer to clinical treatment guidelines for paediatric diseases.

    :param:
    url (str): url from which to extract all <a href> links

    :return:
    a list of strings containing urls in the links.
    """
    response = requests.get(url)
    if response.ok is False or "Error: 404" in response.text:
        print(f"cannot download {url}. Check and restart.")
        sys.exit(1)
    soup = BeautifulSoup(response.content, "html.parser")

    base_url = extract_base_url(url)
    links = []
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        if href.startswith("/clinicalguide/guideline_index"):
            absolute_url = urljoin(base_url, href)
            links.append(absolute_url)
    return links


def download_webpage(url: str) -> bool:
    """
    Downloads the contents of a list of webpages and saves each as an .html file in the folder data/raw_docs.
    A second version with various extraneous tags removed is saved in the folder cleaned_html

    :param:
    url (str): url to download

    :return:
    bool. True if download succeeded, otherwise False.
    """
    response = requests.get(url)
    if response.ok is False or "Error: 404" in response.text:
        print(f"Cannot download {url}. Skipping")
        return False

    cleaned_url = clean_url(url)

    filename = os.path.join(variables.RAW_DOCS_DIR, f"{cleaned_url}.html")
    with open(filename, 'wb') as fout:
        fout.write(response.content)

    base_url = extract_base_url(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    soup = convert_relative_to_absolute_links(soup=soup, base_url=base_url)
    soup = clean_html(soup=soup)
    cleaned_html = str(soup)

    filename = os.path.join(variables.CLEANED_DOCS_DIR, f"{cleaned_url}.html")
    with open(filename, 'w') as fout:
        fout.write(cleaned_html)

    return True


def clean_url(url: str) -> str:
    """
    Cleans a URL string.
    1) Removes "https://" prefix and any final "/".
    2) converts all internal "/" into a slash-like character \u29F8
    This is needed to turn the url into a legal savable filename.

    :param:
     url (str) - URL to clean
    :return:
    str - cleaned URL
    """
    if url.startswith("https://"):
        url = url[8:]
    url = url.rstrip('/')

    # forward slash cannot be used in filenames, so replace it with similarly-shaped char called "big solidus"
    url = url.replace('/', "\u29F8")
    return url


def clean_html(soup):
    """
    Remove the <input>, <script> and <noscript> tags from an html doc.

    :param:
    soup obj - original html
    :return:
    soup obj - cleaned html
    """
    # Find and remove all <input> tags
    for input_tag in soup.find_all(['input', 'script', 'noscript']):
        input_tag.decompose()
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()

    return soup


def extract_base_url(full_url: str) -> str:
    """
    Returns the base url from a full url
    e.g. https://www.rch.org.au/clinicalguide/" yields base url "https://www.rch.org.au"
    """
    parts = urlsplit(full_url)
    base_url = parts.scheme + "://" + parts.netloc
    return base_url


def convert_relative_to_absolute_links(soup, base_url):
    for link in soup.find_all('a', href=True):
        relative_url = link['href']
        absolute_url = urljoin(base_url, relative_url)
        link['href'] = absolute_url

    for link in soup.find_all('img', src=True):
        relative_url = link['src']
        absolute_url = urljoin(base_url, relative_url)
        link['src'] = absolute_url

    return soup


if __name__ == '__main__':
    run_crawler()
