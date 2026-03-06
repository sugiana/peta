import os
import time
import csv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import (
    WebDriverWait,
    Select,
    )
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


PROVINCES_FILE = os.path.join('data', 'provinsi.csv')
PROVINCES = dict()

with open(PROVINCES_FILE) as f:
    c = csv.DictReader(f)
    for r in c:
        PROVINCES[r['key']] = r['nama']


def download_geojson(province_code: str, nice_file: str):
    # Setup download directory
    download_dir = os.getcwd()

    # Prune old downloads to avoid confusion
    print("Cleaning up old downloads...")
    for f in os.listdir(download_dir):
        if (f.startswith("gabungan") or f.startswith("peta-gabungan")) and \
                (f.endswith(".json") or f.endswith(".geojson")):
            os.remove(os.path.join(download_dir, f))
            print(f"Removed old file: {f}")

    # Chrome options
    chrome_options = Options()
    # chrome_options.add_argument("--headless")
    prefs = {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    }
    chrome_options.add_experimental_option("prefs", prefs)

    # Initialize WebDriver
    service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        print("Navigating to Petanusa...")
        driver.get("https://www.petanusa.web.id/peta-gabungan")

        # Wait for the page to load
        wait = WebDriverWait(driver, 30)

        # 1. Select Province
        print("Finding Province dropdown...")
        # Find the specific option for province name and ensure it's enabled
        province_option_xpath = f'//option[@value="{province_code}"]'
        wait.until(
            EC.presence_of_element_located((By.XPATH, province_option_xpath)))

        # Now find the parent select
        province_select_element = wait.until(
            EC.presence_of_element_located((
                By.XPATH, province_option_xpath + "/parent::select")))

        print(f"Selecting Province...")
        province_select = Select(province_select_element)

        # Wait until the option is enabled if it's currently disabled
        max_retries = 10
        for i in range(max_retries):
            option = driver.find_element(By.XPATH, province_option_xpath)
            if option.is_enabled():
                break
            print("Option disabled, waiting...")
            time.sleep(1)

        province_select.select_by_value(province_code)
        print("Province selected.")

        # 2. Wait for cities to load and select all items
        print("Waiting for city list to load...")
        # The container for cities usually has a specific class or property
        # Based on previous research, it's a list of labels with checkboxes
        city_list_xpath = '//div[contains(@class, "overflow-y-auto")]//label'
        wait.until(EC.presence_of_element_located((By.XPATH, city_list_xpath)))

        city_labels = driver.find_elements(By.XPATH, city_list_xpath)
        print(f"Found {len(city_labels)} cities/regencies. Selecting all...")

        for label in city_labels:
            try:
                checkbox = label.find_element(By.TAG_NAME, "input")
                # Scroll to item to ensure it's clickable
                driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center'});", label)

                if not checkbox.is_selected():
                    try:
                        label.click()
                    except Exception:
                        driver.execute_script(
                            "arguments[0].click();", checkbox)
            except Exception as e:
                print(f"Skipping a city due to error: {e}")

        print("All available cities selected.")

        # 3. Select granularity: Desa/Kelurahan
        print("Selecting granularity: Desa/Kelurahan...")
        # Wait for the radio options to appear (they might appear after the
        # first selection)
        village_label_xpath = "//label[contains(., 'Desa/Kelurahan')]"
        village_label = wait.until(
            EC.presence_of_element_located((By.XPATH, village_label_xpath)))
        village_radio = village_label.find_element(By.TAG_NAME, "input")

        # Scroll to it
        driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center'});", village_label)
        time.sleep(1)

        if not village_radio.is_selected():
            print("Clicking Desa/Kelurahan option...")
            try:
                village_label.click()
            except Exception:
                driver.execute_script("arguments[0].click();", village_radio)

        # Small wait to ensure state update
        time.sleep(2)  # Give more time as selecting everything might be slow

        # 4. Click Download Gabungan button
        print("Clicking Download button...")
        # Wait for the download button to be enabled/visible
        download_xpath = '//button[contains(., "Download Gabungan")]'
        download_button = wait.until(
            EC.element_to_be_clickable((By.XPATH, download_xpath)))

        # Ensure it's in view
        driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center'});", download_button)
        time.sleep(0.5)
        download_button.click()

        # 5. Wait for download to finish
        print(
            "Waiting for download to complete (this might take several "
            "minutes for large data)...")
        max_wait = 600  # Village data for the whole province is HUGE
        seconds = 0
        downloaded_file = None

        while seconds < max_wait:
            time.sleep(2)  # Wait a bit longer between checks
            # Look for a file that looks like a geojson or json starting with
            # gabungan_ or peta-gabungan
            # Avoid .crdownload files
            files = [
                f for f in os.listdir(download_dir) if
                (f.startswith("gabungan") or f.startswith("peta-gabungan")) and
                (f.endswith(".json") or f.endswith(".geojson"))]
            if files:
                downloaded_file = files[0]
                break
            # Optional: Check if the progress is still visible/changing to
            # avoid true deadlocks
            # But simple timeout is usually fine
            seconds += 2

        if downloaded_file:
            print(f"Successfully downloaded: {downloaded_file}")
            os.rename(downloaded_file, nice_file)
            print(f"Successfully rename to: {nice_file}")
        else:
            print("Download timed out or failed.")
            # Take a screenshot to see what's wrong
            driver.save_screenshot("debug_failure.png")
            print("Saved debug_failure.png")

    except Exception as e:
        print(f"An error occurred: {e}")
        driver.save_screenshot("debug_error.png")
        print("Saved debug_error.png")
    finally:
        # Give some time for background processes to finish before closing
        time.sleep(2)
        driver.quit()


if __name__ == "__main__":
    import sys
    if sys.argv[1:]:
        province_codes = [sys.argv[1]]
    else:
        province_codes = []
        for key, value in PROVINCES.items():
            province_codes.append(key)

    for province_code in province_codes:
        nice_file = province_code + '_'
        nice_file += PROVINCES[province_code].lower().replace(' ', '_')
        nice_file += '.geojson'
        if os.path.exists(nice_file):
            print(f'File {nice_file} sudah ada.')
        else:
            download_geojson(province_code, nice_file)
