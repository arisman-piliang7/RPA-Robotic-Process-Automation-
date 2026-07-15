"""
Kelas dasar Page Object untuk seluruh halaman DDMS.
Menyediakan metode helper yang digunakan oleh semua halaman turunan.
"""
import logging
from datetime import datetime
from pathlib import Path

from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from src.config import Config

logger = logging.getLogger(__name__)


class BasePage:
    """Kelas dasar yang menyediakan metode bantu umum untuk semua halaman."""

    def __init__(self, driver: WebDriver, config: type = Config) -> None:
        self.driver = driver
        self.config = config
        self.wait = WebDriverWait(driver, config.EXPLICIT_WAIT)

    # ------------------------------------------------------------------
    # Navigasi
    # ------------------------------------------------------------------

    def open(self, url: str) -> None:
        """Buka URL di browser."""
        logger.debug("Membuka URL: %s", url)
        self.driver.get(url)

    def get_current_url(self) -> str:
        """Kembalikan URL halaman saat ini."""
        return self.driver.current_url

    def get_title(self) -> str:
        """Kembalikan judul halaman saat ini."""
        return self.driver.title

    # ------------------------------------------------------------------
    # Interaksi Elemen
    # ------------------------------------------------------------------

    def find(self, by: str, value: str) -> WebElement:
        """Temukan elemen dengan menunggu hingga terlihat."""
        return self.wait.until(
            EC.visibility_of_element_located((by, value)),
            message=f"Elemen tidak ditemukan: [{by}] '{value}'",
        )

    def find_clickable(self, by: str, value: str) -> WebElement:
        """Temukan elemen yang bisa diklik."""
        return self.wait.until(
            EC.element_to_be_clickable((by, value)),
            message=f"Elemen tidak dapat diklik: [{by}] '{value}'",
        )

    def click(self, by: str, value: str) -> None:
        """Klik elemen setelah memastikannya dapat diklik."""
        element = self.find_clickable(by, value)
        element.click()
        logger.debug("Diklik: [%s] '%s'", by, value)

    def type_text(self, by: str, value: str, text: str, clear: bool = True) -> None:
        """Ketik teks ke dalam field input."""
        element = self.find(by, value)
        if clear:
            element.clear()
        element.send_keys(text)
        logger.debug("Mengetik ke [%s] '%s'", by, value)

    def get_text(self, by: str, value: str) -> str:
        """Ambil teks dari elemen."""
        return self.find(by, value).text.strip()

    def is_visible(self, by: str, value: str, timeout: int = 5) -> bool:
        """Periksa apakah elemen terlihat dalam batas waktu tertentu."""
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.visibility_of_element_located((by, value))
            )
            return True
        except TimeoutException:
            return False

    def is_present(self, by: str, value: str) -> bool:
        """Periksa apakah elemen hadir di DOM."""
        try:
            self.driver.find_element(by, value)
            return True
        except NoSuchElementException:
            return False

    def wait_for_url_contains(self, partial_url: str) -> bool:
        """Tunggu hingga URL mengandung string tertentu."""
        try:
            return self.wait.until(EC.url_contains(partial_url))
        except TimeoutException:
            return False

    def wait_for_element_disappear(self, by: str, value: str) -> bool:
        """Tunggu hingga elemen menghilang dari tampilan."""
        try:
            return self.wait.until(
                EC.invisibility_of_element_located((by, value))
            )
        except TimeoutException:
            return False

    def scroll_to_element(self, element: WebElement) -> None:
        """Scroll ke elemen menggunakan JavaScript."""
        self.driver.execute_script("arguments[0].scrollIntoView(true);", element)

    def js_click(self, element: WebElement) -> None:
        """Klik elemen menggunakan JavaScript (untuk elemen yang tertutup overlay)."""
        self.driver.execute_script("arguments[0].click();", element)

    # ------------------------------------------------------------------
    # Tangkapan Layar
    # ------------------------------------------------------------------

    def take_screenshot(self, filename: str = "") -> Path:
        """
        Ambil tangkapan layar dan simpan ke direktori screenshot.

        Args:
            filename: Nama file tanpa ekstensi. Default: timestamp.

        Returns:
            Path file screenshot yang disimpan.
        """
        self.config.ensure_dirs()
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        name = f"{filename}_{ts}" if filename else ts
        path = self.config.SCREENSHOT_DIR / f"{name}.png"
        self.driver.save_screenshot(str(path))
        logger.info("Screenshot disimpan: %s", path)
        return path

    # ------------------------------------------------------------------
    # Alert / Dialog
    # ------------------------------------------------------------------

    def accept_alert(self) -> str:
        """Terima alert browser dan kembalikan teksnya."""
        try:
            alert = self.wait.until(EC.alert_is_present())
            text = alert.text
            alert.accept()
            logger.debug("Alert diterima: %s", text)
            return text
        except TimeoutException:
            return ""

    def dismiss_alert(self) -> str:
        """Tolak alert browser dan kembalikan teksnya."""
        try:
            alert = self.wait.until(EC.alert_is_present())
            text = alert.text
            alert.dismiss()
            logger.debug("Alert ditolak: %s", text)
            return text
        except TimeoutException:
            return ""
