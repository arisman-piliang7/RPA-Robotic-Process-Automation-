"""
Modul factory untuk membuat instans Selenium WebDriver.
Mendukung Chrome dan Firefox dengan manajemen driver otomatis.
"""
import logging
from typing import Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager

from src.config import Config

logger = logging.getLogger(__name__)


def create_driver(config: Optional[Config] = None) -> webdriver.Remote:
    """
    Buat dan kembalikan instans WebDriver berdasarkan konfigurasi.

    Args:
        config: Objek Config. Jika None, gunakan nilai default Config.

    Returns:
        Instans selenium.webdriver yang sudah dikonfigurasi.

    Raises:
        ValueError: Jika tipe browser tidak didukung.
    """
    cfg = config or Config
    browser = cfg.BROWSER

    if browser == "chrome":
        driver = _create_chrome_driver(cfg)
    elif browser == "firefox":
        driver = _create_firefox_driver(cfg)
    else:
        raise ValueError(
            f"Browser '{browser}' tidak didukung. Gunakan 'chrome' atau 'firefox'."
        )

    driver.set_page_load_timeout(cfg.PAGE_LOAD_TIMEOUT)
    driver.implicitly_wait(cfg.IMPLICIT_WAIT)
    driver.maximize_window()
    logger.info("WebDriver '%s' berhasil dibuat (headless=%s).", browser, cfg.HEADLESS)
    return driver


def _create_chrome_driver(cfg) -> webdriver.Chrome:
    """Buat Chrome WebDriver dengan opsi yang sesuai."""
    options = ChromeOptions()
    if cfg.HEADLESS:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--ignore-certificate-errors")
    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    service = ChromeService(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)


def _create_firefox_driver(cfg) -> webdriver.Firefox:
    """Buat Firefox WebDriver dengan opsi yang sesuai."""
    options = FirefoxOptions()
    if cfg.HEADLESS:
        options.add_argument("--headless")
    options.add_argument("--width=1920")
    options.add_argument("--height=1080")
    service = FirefoxService(GeckoDriverManager().install())
    return webdriver.Firefox(service=service, options=options)
