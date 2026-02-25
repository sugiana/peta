# pip install selenium webdriver-manager parsel jaccard-index
import sys
from time import sleep
from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from parsel import Selector
from jaccard_index.jaccard import jaccard_index


def scrape_google(query: str):
    def scroll(max_count=7, delay=2, height=200):
        x = 0
        while x < max_count:
            script = f'window.scrollTo(0, {height});'
            driver.execute_script(script)
            sleep(delay)
            x += 1
            height += height

    driver_manager = ChromeDriverManager()
    service = Service(driver_manager.install())
    opt = Options()
    driver = webdriver.Chrome(service=service, options=opt)
    search_url = (
        f"https://www.google.com/search?q={query.replace(' ', '+')}&num=15")
    driver.get(search_url)
    WebDriverWait(driver, 60).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "h3")))
    scroll(4)
    sel = Selector(driver.page_source)
    driver.quit()
    last_index = 0
    last_title = ''
    last_url = ''
    for row in sel.xpath('//span/a[@data-ved]'):
        title = row.xpath('h3/text()').extract()
        if not title:
            continue
        title = title[0]
        url = row.xpath('@href').extract()
        if not url:
            continue
        url = url[0]
        index = jaccard_index(title, cari)
        if index > last_index:
            last_index = index
            last_title = title
            last_url = url
    return dict(title=last_title, url=last_url)


if __name__ == "__main__":
    import sys
    import json

    cari = sys.argv[1]
    d = scrape_google(cari)
    s = json.dumps(d, indent=2)
    print(s)
