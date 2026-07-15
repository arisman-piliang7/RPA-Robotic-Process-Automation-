"""
Pengujian unit untuk halaman-halaman automasi DDMS.
Menggunakan mock WebDriver agar tidak memerlukan browser sungguhan.
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


@pytest.fixture
def mock_driver():
    """Buat mock WebDriver untuk pengujian."""
    driver = MagicMock()
    driver.current_url = "https://ddms.pertamina.com/dashboard"
    driver.title = "DDMS Dashboard"
    return driver


@pytest.fixture
def mock_config(tmp_path):
    """Buat konfigurasi mock untuk pengujian."""
    import importlib
    import src.config as cfg_module

    importlib.reload(cfg_module)
    Config = cfg_module.Config
    Config.DDMS_URL = "https://ddms.pertamina.com"
    Config.USERNAME = "testuser"
    Config.PASSWORD = "testpass"
    Config.AREA_CODE = ""
    Config.BROWSER = "chrome"
    Config.HEADLESS = True
    Config.IMPLICIT_WAIT = 5
    Config.EXPLICIT_WAIT = 10
    Config.PAGE_LOAD_TIMEOUT = 30
    Config.OUTPUT_DIR = tmp_path / "output"
    Config.LOG_DIR = tmp_path / "logs"
    Config.SCREENSHOT_DIR = tmp_path / "output" / "screenshots"
    Config.SCREENSHOT_ON_ERROR = False
    Config.LOG_LEVEL = "DEBUG"
    return Config


class TestBasePage:
    """Pengujian kelas BasePage."""

    def test_open_calls_driver_get(self, mock_driver, mock_config):
        """BasePage.open() harus memanggil driver.get() dengan URL yang tepat."""
        from src.automation.base_page import BasePage

        page = BasePage(mock_driver, mock_config)
        page.open("https://example.com/test")
        mock_driver.get.assert_called_once_with("https://example.com/test")

    def test_get_current_url(self, mock_driver, mock_config):
        """BasePage.get_current_url() harus mengembalikan URL dari driver."""
        from src.automation.base_page import BasePage

        mock_driver.current_url = "https://ddms.pertamina.com/survey"
        page = BasePage(mock_driver, mock_config)
        assert page.get_current_url() == "https://ddms.pertamina.com/survey"

    def test_get_title(self, mock_driver, mock_config):
        """BasePage.get_title() harus mengembalikan title dari driver."""
        from src.automation.base_page import BasePage

        mock_driver.title = "Halaman Survey"
        page = BasePage(mock_driver, mock_config)
        assert page.get_title() == "Halaman Survey"

    def test_take_screenshot_saves_file(self, mock_driver, mock_config, tmp_path):
        """BasePage.take_screenshot() harus menyimpan file screenshot."""
        from src.automation.base_page import BasePage

        mock_config.SCREENSHOT_DIR = tmp_path / "screenshots"
        page = BasePage(mock_driver, mock_config)
        path = page.take_screenshot("test_screen")

        assert path.suffix == ".png"
        mock_driver.save_screenshot.assert_called_once_with(str(path))

    def test_js_click_calls_execute_script(self, mock_driver, mock_config):
        """BasePage.js_click() harus memanggil execute_script."""
        from src.automation.base_page import BasePage

        page = BasePage(mock_driver, mock_config)
        element = MagicMock()
        page.js_click(element)
        mock_driver.execute_script.assert_called_once()

    def test_scroll_to_element(self, mock_driver, mock_config):
        """BasePage.scroll_to_element() harus memanggil execute_script."""
        from src.automation.base_page import BasePage

        page = BasePage(mock_driver, mock_config)
        element = MagicMock()
        page.scroll_to_element(element)
        mock_driver.execute_script.assert_called_once()


class TestLoginPage:
    """Pengujian kelas LoginPage."""

    def test_login_url_constructed_correctly(self, mock_driver, mock_config):
        """LoginPage harus membangun URL login dari DDMS_URL + suffix."""
        from src.automation.login_page import LoginPage

        mock_config.DDMS_URL = "https://ddms.pertamina.com"
        page = LoginPage(mock_driver, mock_config)
        assert page._login_url == "https://ddms.pertamina.com/login"

    def test_login_url_with_trailing_slash(self, mock_driver, mock_config):
        """LoginPage harus menangani trailing slash pada DDMS_URL."""
        from src.automation.login_page import LoginPage

        mock_config.DDMS_URL = "https://ddms.pertamina.com/"
        page = LoginPage(mock_driver, mock_config)
        assert page._login_url == "https://ddms.pertamina.com/login"

    def test_navigate_calls_driver_get(self, mock_driver, mock_config):
        """LoginPage.navigate() harus memanggil driver.get() dengan URL login."""
        from src.automation.login_page import LoginPage

        page = LoginPage(mock_driver, mock_config)
        page.navigate()
        mock_driver.get.assert_called_with(page._login_url)


class TestSurveyPangkalanPage:
    """Pengujian kelas SurveyPangkalanPage."""

    def test_survey_url_constructed_correctly(self, mock_driver, mock_config):
        """SurveyPangkalanPage harus membangun URL survey dengan benar."""
        from src.automation.survey_pangkalan_page import SurveyPangkalanPage

        mock_config.DDMS_URL = "https://ddms.pertamina.com"
        page = SurveyPangkalanPage(mock_driver, mock_config)
        assert page._survey_url == "https://ddms.pertamina.com/survey/pangkalan"

    def test_navigate_direct_calls_driver_get(self, mock_driver, mock_config):
        """navigate_direct() harus memanggil driver.get() dengan URL survey."""
        from src.automation.survey_pangkalan_page import SurveyPangkalanPage

        page = SurveyPangkalanPage(mock_driver, mock_config)

        # Mock is_visible untuk mengembalikan True
        with patch.object(page, "is_visible", return_value=True):
            with patch.object(page, "_wait_for_page_load"):
                result = page.navigate_direct()

        mock_driver.get.assert_called_with(page._survey_url)
        assert result is True

    def test_set_area_filter_skips_empty_code(self, mock_driver, mock_config):
        """set_area_filter harus dilewati jika area_code kosong."""
        from src.automation.survey_pangkalan_page import SurveyPangkalanPage

        page = SurveyPangkalanPage(mock_driver, mock_config)
        # Tidak boleh memanggil find() jika area kosong
        with patch.object(page, "find") as mock_find:
            page.set_area_filter("")
            mock_find.assert_not_called()

    def test_open_survey_single_not_found(self, mock_driver, mock_config):
        """open_survey_single harus mengembalikan status skipped jika ID tidak ada."""
        from src.automation.survey_pangkalan_page import SurveyPangkalanPage

        page = SurveyPangkalanPage(mock_driver, mock_config)
        # Tabel kosong dan tidak ada halaman berikutnya
        mock_driver.find_elements.return_value = []

        with patch.object(page, "_go_to_next_page", return_value=False):
            result = page.open_survey_single("99999")

        assert result.status == "skipped"
        assert result.pangkalan_id == "99999"
        assert "tidak ditemukan" in result.message.lower()


class TestMainEntryPoint:
    """Pengujian fungsi main() di main.py."""

    def test_parse_args_defaults(self):
        """parse_args() harus memiliki nilai default yang benar."""
        from main import parse_args

        with patch("sys.argv", ["main.py"]):
            args = parse_args()
        assert args.pangkalan_id is None
        assert args.area_code is None
        assert args.headless is None
        assert args.browser is None

    def test_parse_args_with_id(self):
        """parse_args() harus memetakan --id ke pangkalan_id."""
        from main import parse_args

        with patch("sys.argv", ["main.py", "--id", "12345"]):
            args = parse_args()
        assert args.pangkalan_id == "12345"

    def test_parse_args_headless_flag(self):
        """parse_args() harus menetapkan headless=True saat --headless diberikan."""
        from main import parse_args

        with patch("sys.argv", ["main.py", "--headless"]):
            args = parse_args()
        assert args.headless is True
