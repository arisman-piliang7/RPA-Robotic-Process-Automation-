"""
Orkestrator utama proses RPA Open Survey Pangkalan DDMS.
Mengkoordinasikan seluruh langkah automasi dari login hingga pelaporan.
"""
import logging
import sys
from pathlib import Path
from typing import Optional

from selenium.webdriver.remote.webdriver import WebDriver

from src.automation.base_page import BasePage
from src.automation.login_page import LoginPage
from src.automation.survey_pangkalan_page import SurveyPangkalanPage, SurveyReport
from src.config import Config
from src.utils.driver_factory import create_driver
from src.utils.logger import get_logger
from src.utils.report_generator import generate_excel_report, generate_text_report

logger = logging.getLogger(__name__)


class DDMSAutomation:
    """
    Kelas utama yang mengorkestrasikan automasi Open Survey Pangkalan DDMS.

    Penggunaan:
        automation = DDMSAutomation()
        report = automation.run()
    """

    def __init__(self, config: type = Config) -> None:
        self.config = config
        self.driver: Optional[WebDriver] = None
        self._logger = get_logger(__name__, config.LOG_DIR, config.LOG_LEVEL)

    # ------------------------------------------------------------------
    # API Publik
    # ------------------------------------------------------------------

    def run(self, pangkalan_id: Optional[str] = None) -> SurveyReport:
        """
        Jalankan proses automasi Open Survey Pangkalan secara lengkap.

        Args:
            pangkalan_id: Jika diisi, hanya proses satu pangkalan dengan ID ini.
                          Jika None, proses semua pangkalan.

        Returns:
            SurveyReport berisi ringkasan dan detail hasil.
        """
        self.config.validate()
        self.config.ensure_dirs()

        logger.info("=" * 60)
        logger.info("Memulai RPA Open Survey Pangkalan DDMS")
        logger.info("URL DDMS  : %s", self.config.DDMS_URL)
        logger.info("Username  : %s", self.config.USERNAME)
        if pangkalan_id:
            logger.info("Target    : Pangkalan ID '%s'", pangkalan_id)
        else:
            logger.info("Target    : Semua pangkalan")
        logger.info("=" * 60)

        try:
            self._setup_driver()
            self._login()
            report = self._open_survey(pangkalan_id)
            self._save_reports(report)
            return report
        except Exception as exc:
            logger.critical("Automasi berhenti karena error: %s", exc, exc_info=True)
            if self.driver and self.config.SCREENSHOT_ON_ERROR:
                base = BasePage(self.driver, self.config)
                base.take_screenshot("critical_error")
            raise
        finally:
            self._teardown_driver()

    # ------------------------------------------------------------------
    # Langkah-langkah Privat
    # ------------------------------------------------------------------

    def _setup_driver(self) -> None:
        """Inisialisasi WebDriver."""
        logger.info("Menginisialisasi browser '%s'...", self.config.BROWSER)
        self.driver = create_driver(self.config)

    def _login(self) -> None:
        """Lakukan login ke DDMS."""
        login_page = LoginPage(self.driver, self.config)
        success = login_page.login(self.config.USERNAME, self.config.PASSWORD)
        if not success:
            raise RuntimeError(
                "Login ke DDMS gagal. Periksa kredensial dan URL di file .env."
            )

    def _open_survey(self, pangkalan_id: Optional[str]) -> SurveyReport:
        """Navigasi ke Survey Pangkalan dan lakukan open survey."""
        survey_page = SurveyPangkalanPage(self.driver, self.config)

        logger.info("Navigasi ke halaman Survey Pangkalan...")
        if not survey_page.navigate_via_menu():
            raise RuntimeError(
                "Gagal navigasi ke halaman Survey Pangkalan. "
                "Periksa apakah URL dan menu DDMS sudah benar."
            )

        survey_page.navigate_to_open_survey()

        if pangkalan_id:
            result = survey_page.open_survey_single(pangkalan_id)
            report = SurveyReport()
            report.add(result)
            return report

        return survey_page.open_survey_all(self.config.AREA_CODE)

    def _save_reports(self, report: SurveyReport) -> None:
        """Simpan laporan hasil ke file Excel dan teks."""
        logger.info("Menyimpan laporan hasil...")
        try:
            excel_path = generate_excel_report(report, self.config.OUTPUT_DIR)
            logger.info("Laporan Excel : %s", excel_path)
        except Exception as exc:
            logger.warning("Gagal membuat laporan Excel: %s", exc)

        txt_path = generate_text_report(report, self.config.OUTPUT_DIR)
        logger.info("Laporan Teks  : %s", txt_path)

        logger.info("-" * 60)
        logger.info("RINGKASAN HASIL:")
        logger.info(report.summary())
        logger.info("-" * 60)

    def _teardown_driver(self) -> None:
        """Tutup browser dan bersihkan driver."""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Browser ditutup.")
            except Exception:
                pass
            self.driver = None

