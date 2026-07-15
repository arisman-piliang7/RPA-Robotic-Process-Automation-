"""
Halaman Login DDMS PT Pertamina Patra Niaga.
Menangani proses autentikasi ke portal DDMS.
"""
import logging

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver

from src.automation.base_page import BasePage
from src.config import Config

logger = logging.getLogger(__name__)

# --- Locator ---
_USERNAME_INPUT = (By.CSS_SELECTOR, "input[name='username'], input[id='username'], input[type='text']")
_PASSWORD_INPUT = (By.CSS_SELECTOR, "input[name='password'], input[id='password'], input[type='password']")
_LOGIN_BUTTON = (By.CSS_SELECTOR, "button[type='submit'], input[type='submit'], #btnLogin, .btn-login")
_ERROR_MESSAGE = (By.CSS_SELECTOR, ".alert-danger, .error-message, #errorMsg, .login-error")
_DASHBOARD_INDICATOR = (By.CSS_SELECTOR, ".navbar, .sidebar, .main-menu, #dashboard, .dashboard-content")


class LoginPage(BasePage):
    """
    Halaman login DDMS.
    Menyediakan metode untuk mengisi kredensial dan melakukan login.
    """

    LOGIN_URL_SUFFIX = "/login"

    def __init__(self, driver: WebDriver, config: type = Config) -> None:
        super().__init__(driver, config)
        self._login_url = config.DDMS_URL.rstrip("/") + self.LOGIN_URL_SUFFIX

    def navigate(self) -> None:
        """Navigasi ke halaman login DDMS."""
        logger.info("Membuka halaman login: %s", self._login_url)
        self.open(self._login_url)

    def enter_username(self, username: str) -> None:
        """Isi field username."""
        self.type_text(*_USERNAME_INPUT, text=username)

    def enter_password(self, password: str) -> None:
        """Isi field password."""
        self.type_text(*_PASSWORD_INPUT, text=password)

    def click_login(self) -> None:
        """Klik tombol login."""
        self.click(*_LOGIN_BUTTON)
        logger.info("Tombol login diklik.")

    def login(self, username: str, password: str) -> bool:
        """
        Lakukan proses login lengkap ke DDMS.

        Args:
            username: Username DDMS.
            password: Password DDMS.

        Returns:
            True jika login berhasil, False jika gagal.
        """
        logger.info("Mencoba login sebagai: %s", username)
        self.navigate()
        self.enter_username(username)
        self.enter_password(password)
        self.click_login()

        if self._is_login_successful():
            logger.info("Login berhasil.")
            return True

        error = self._get_error_message()
        logger.error("Login gagal. Pesan error: %s", error)
        if self.config.SCREENSHOT_ON_ERROR:
            self.take_screenshot("login_gagal")
        return False

    def _is_login_successful(self) -> bool:
        """Periksa apakah login berhasil dengan mendeteksi elemen dashboard."""
        try:
            self.wait.until(
                lambda d: (
                    self.is_visible(*_DASHBOARD_INDICATOR, timeout=1)
                    or (
                        self.config.DDMS_URL.rstrip("/") not in d.current_url
                        and "login" not in d.current_url.lower()
                    )
                )
            )
            return "login" not in self.get_current_url().lower()
        except TimeoutException:
            return False

    def _get_error_message(self) -> str:
        """Ambil pesan error login jika ada."""
        if self.is_visible(*_ERROR_MESSAGE, timeout=3):
            return self.get_text(*_ERROR_MESSAGE)
        return "(tidak ada pesan error terdeteksi)"
