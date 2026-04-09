from loguru import logger as log
import os
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.service import Service


def make_driver(download_dir: Path):
    selenium_url = os.getenv("SELENIUM_URL")

    options = webdriver.ChromeOptions()

    # Pasta de download
    prefs = {
        "download.default_directory": str(download_dir),
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
    }
    options.add_experimental_option("prefs", prefs)

    # FLAGS ESSENCIAIS
    # options.add_argument("--headless=new")  # habilite se quiser headless
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")

    log.info(f"🔧 SELENIUM_URL = {selenium_url}")

    # ===============================
    # SELENIUM REMOTO (Docker / Grid)
    # ===============================
    if selenium_url:
        driver = webdriver.Remote(
            command_executor=selenium_url,
            options=options,
        )
    else:
        # ===============================
        # SELENIUM LOCAL (Windows/Linux)
        # ===============================
        driver = webdriver.Chrome(
            service=Service(), 
            options=options,
        )

    driver.set_page_load_timeout(240)
    driver.implicitly_wait(10)

    return driver
