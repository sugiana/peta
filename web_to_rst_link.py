import sys
import requests
from bs4 import BeautifulSoup


url = sys.argv[1]

headers = {"User-Agent": "Mozilla/5.0 (compatible; TitleFetcher/1.0)"}
response = requests.get(url, headers=headers)
response.raise_for_status()

soup = BeautifulSoup(response.text, "html.parser")
title = soup.find("h1", id="firstHeading").text

print(f'`{title} <{url}>`_')
