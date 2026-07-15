"""
Halaman Survey Pangkalan DDMS PT Pertamina Patra Niaga.
Menangani navigasi dan operasi Open Survey Pangkalan.
"""
import logging
import time
from dataclasses import dataclass, field
from typing import List, Optional

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver

from src.automation.base_page import BasePage
from src.config import Config

logger = logging.getLogger(__name__)

# --- Locator Menu Navigasi ---
_MENU_SURVEY = (By.XPATH, "//a[contains(., 'Survey') or contains(., 'survey')]")
_MENU_SURVEY_PANGKALAN = (
    By.XPATH,
    "//a[contains(., 'Survey Pangkalan') or contains(., 'survey-pangkalan')]",
)
_SUBMENU_OPEN_SURVEY = (
    By.XPATH,
    "//a[contains(., 'Open Survey') or contains(., 'Buka Survey') or contains(., 'open-survey')]",
)

# --- Locator Daftar Pangkalan ---
_TABLE_PANGKALAN = (By.CSS_SELECTOR, "table.table, #tblPangkalan, .pangkalan-table")
_TABLE_ROWS = (By.CSS_SELECTOR, "table.table tbody tr, #tblPangkalan tbody tr")
_PAGINATION_NEXT = (By.CSS_SELECTOR, ".pagination .next a, li.next a, [aria-label='Next']")
_PAGINATION_INFO = (By.CSS_SELECTOR, ".dataTables_info, .pagination-info, #tableInfo")
_AREA_FILTER = (By.CSS_SELECTOR, "select#area, select[name='area'], #ddlArea")
_SEARCH_INPUT = (By.CSS_SELECTOR, "input[type='search'], #searchPangkalan, .search-input")
_LOADING_INDICATOR = (By.CSS_SELECTOR, ".loading, .spinner, #loadingIndicator")

# --- Locator Tombol Open Survey ---
_BTN_OPEN_SURVEY = (
    By.XPATH,
    "//button[contains(., 'Open Survey') or contains(., 'Buka Survey')]"
    " | //a[contains(., 'Open Survey') or contains(., 'Buka Survey')]",
)
_BTN_OPEN_ROW = (
    By.XPATH,
    ".//button[contains(., 'Open') or contains(., 'Buka') or contains(@class, 'btn-open')]"
    " | .//a[contains(., 'Open') or contains(., 'Buka') or contains(@class, 'btn-open')]",
)

# --- Locator Dialog Konfirmasi ---
_CONFIRM_DIALOG = (By.CSS_SELECTOR, ".modal.show, .swal2-container, #confirmModal")
_CONFIRM_YES = (
    By.XPATH,
    "//button[contains(., 'Ya') or contains(., 'Yes') or contains(., 'OK') or contains(., 'Konfirmasi')]",
)
_CONFIRM_CANCEL = (
    By.XPATH,
    "//button[contains(., 'Batal') or contains(., 'Cancel') or contains(., 'Tidak')]",
)

# --- Locator Notifikasi ---
_NOTIFICATION_SUCCESS = (
    By.CSS_SELECTOR,
    ".alert-success, .toast-success, .swal2-success, .notif-success",
)
_NOTIFICATION_ERROR = (
    By.CSS_SELECTOR,
    ".alert-danger, .toast-error, .swal2-error, .notif-error",
)


@dataclass
class SurveyResult:
    """Menyimpan hasil satu proses open survey untuk satu pangkalan."""

    pangkalan_id: str
    pangkalan_name: str
    status: str  # 'success', 'failed', 'skipped'
    message: str = ""
    row_index: int = 0


@dataclass
class SurveyReport:
    """Merangkum seluruh hasil proses open survey."""

    total: int = 0
    success: int = 0
    failed: int = 0
    skipped: int = 0
    results: List[SurveyResult] = field(default_factory=list)

    def add(self, result: SurveyResult) -> None:
        self.results.append(result)
        self.total += 1
        if result.status == "success":
            self.success += 1
        elif result.status == "failed":
            self.failed += 1
        else:
            self.skipped += 1

    def summary(self) -> str:
        return (
            f"Total: {self.total} | Berhasil: {self.success} | "
            f"Gagal: {self.failed} | Dilewati: {self.skipped}"
        )


class SurveyPangkalanPage(BasePage):
    """
    Halaman Survey Pangkalan DDMS.

    Menyediakan operasi:
    - Navigasi ke menu Survey Pangkalan
    - Filter berdasarkan area
    - Open Survey untuk semua atau satu pangkalan tertentu
    """

    SURVEY_URL_SUFFIX = "/survey/pangkalan"

    def __init__(self, driver: WebDriver, config: type = Config) -> None:
        super().__init__(driver, config)
        self._survey_url = config.DDMS_URL.rstrip("/") + self.SURVEY_URL_SUFFIX

    # ------------------------------------------------------------------
    # Navigasi
    # ------------------------------------------------------------------

    def navigate_via_menu(self) -> bool:
        """
        Navigasi ke halaman Survey Pangkalan melalui menu navigasi.

        Returns:
            True jika berhasil, False jika menu tidak ditemukan.
        """
        logger.info("Membuka menu Survey...")
        try:
            self.click(*_MENU_SURVEY)
            time.sleep(0.5)
            self.click(*_MENU_SURVEY_PANGKALAN)
            logger.info("Menu Survey Pangkalan berhasil dibuka.")
            self._wait_for_page_load()
            return True
        except TimeoutException:
            logger.warning(
                "Menu Survey Pangkalan tidak ditemukan. Mencoba navigasi langsung ke URL."
            )
            return self.navigate_direct()

    def navigate_direct(self) -> bool:
        """
        Navigasi langsung ke URL halaman Survey Pangkalan.

        Returns:
            True jika halaman berhasil dimuat.
        """
        logger.info("Navigasi langsung ke: %s", self._survey_url)
        self.open(self._survey_url)
        self._wait_for_page_load()
        return self.is_visible(*_TABLE_PANGKALAN, timeout=10)

    def navigate_to_open_survey(self) -> bool:
        """
        Navigasi ke sub-menu Open Survey Pangkalan.

        Returns:
            True jika berhasil dinavigasi ke halaman Open Survey.
        """
        logger.info("Membuka sub-menu Open Survey Pangkalan...")
        try:
            if self.is_visible(*_SUBMENU_OPEN_SURVEY, timeout=3):
                self.click(*_SUBMENU_OPEN_SURVEY)
                self._wait_for_page_load()
                logger.info("Halaman Open Survey Pangkalan berhasil dibuka.")
                return True
        except TimeoutException:
            pass
        logger.debug("Sub-menu Open Survey tidak ditemukan. Menggunakan halaman saat ini.")
        return True

    # ------------------------------------------------------------------
    # Filter
    # ------------------------------------------------------------------

    def set_area_filter(self, area_code: str) -> None:
        """
        Set filter area/wilayah untuk daftar pangkalan.

        Args:
            area_code: Kode area yang akan difilter.
        """
        if not area_code:
            logger.debug("Kode area kosong, filter area dilewati.")
            return
        logger.info("Mengatur filter area: %s", area_code)
        try:
            from selenium.webdriver.support.ui import Select

            select_element = self.find(*_AREA_FILTER)
            select = Select(select_element)
            try:
                select.select_by_value(area_code)
            except Exception:
                select.select_by_visible_text(area_code)
            self._wait_for_page_load()
        except TimeoutException:
            logger.warning("Elemen filter area tidak ditemukan.")

    # ------------------------------------------------------------------
    # Open Survey - Operasi Utama
    # ------------------------------------------------------------------

    def open_survey_all(self, area_code: str = "") -> SurveyReport:
        """
        Buka survey untuk semua pangkalan dalam daftar (semua halaman).

        Args:
            area_code: Opsional kode area untuk filter.

        Returns:
            SurveyReport yang berisi ringkasan dan detail hasil.
        """
        report = SurveyReport()

        if area_code:
            self.set_area_filter(area_code)

        page_num = 1
        while True:
            logger.info("Memproses halaman daftar pangkalan ke-%d...", page_num)
            page_results = self._process_current_page()
            for result in page_results:
                report.add(result)

            if not self._go_to_next_page():
                break
            page_num += 1

        logger.info("Proses selesai. %s", report.summary())
        return report

    def open_survey_single(self, pangkalan_id: str) -> SurveyResult:
        """
        Buka survey untuk satu pangkalan berdasarkan ID.

        Args:
            pangkalan_id: ID pangkalan yang akan dibuka surveynya.

        Returns:
            SurveyResult untuk pangkalan tersebut.
        """
        logger.info("Membuka survey untuk pangkalan ID: %s", pangkalan_id)
        rows = self.driver.find_elements(*_TABLE_ROWS)
        for idx, row in enumerate(rows):
            cells = row.find_elements(By.TAG_NAME, "td")
            row_id = cells[0].text.strip() if cells else ""
            row_name = cells[1].text.strip() if len(cells) > 1 else ""
            if row_id == pangkalan_id:
                return self._open_survey_for_row(row, idx, row_id, row_name)

        logger.warning("Pangkalan ID '%s' tidak ditemukan di halaman ini.", pangkalan_id)
        return SurveyResult(
            pangkalan_id=pangkalan_id,
            pangkalan_name="",
            status="skipped",
            message="ID pangkalan tidak ditemukan",
        )

    # ------------------------------------------------------------------
    # Helper Privat
    # ------------------------------------------------------------------

    def _process_current_page(self) -> List[SurveyResult]:
        """Proses semua baris di halaman tabel saat ini."""
        results: List[SurveyResult] = []
        rows = self.driver.find_elements(*_TABLE_ROWS)
        if not rows:
            logger.info("Tidak ada data pangkalan di halaman ini.")
            return results

        logger.info("Ditemukan %d baris pangkalan di halaman ini.", len(rows))
        for idx in range(len(rows)):
            # Ambil ulang rows setiap iterasi karena DOM bisa berubah setelah aksi
            rows = self.driver.find_elements(*_TABLE_ROWS)
            if idx >= len(rows):
                break
            row = rows[idx]
            cells = row.find_elements(By.TAG_NAME, "td")
            pangkalan_id = cells[0].text.strip() if cells else f"row_{idx}"
            pangkalan_name = cells[1].text.strip() if len(cells) > 1 else ""

            result = self._open_survey_for_row(row, idx, pangkalan_id, pangkalan_name)
            results.append(result)

        return results

    def _open_survey_for_row(
        self,
        row,
        idx: int,
        pangkalan_id: str,
        pangkalan_name: str,
    ) -> SurveyResult:
        """Klik tombol Open Survey pada satu baris tabel dan konfirmasi."""
        logger.info(
            "  [%d] Membuka survey: %s - %s", idx + 1, pangkalan_id, pangkalan_name
        )
        try:
            self.scroll_to_element(row)
            btn = row.find_element(*_BTN_OPEN_ROW)
            self.js_click(btn)
            time.sleep(0.3)

            if self._confirm_dialog():
                success_msg = self._get_notification("success")
                logger.info(
                    "  -> Berhasil: %s - %s | %s",
                    pangkalan_id,
                    pangkalan_name,
                    success_msg,
                )
                return SurveyResult(
                    pangkalan_id=pangkalan_id,
                    pangkalan_name=pangkalan_name,
                    status="success",
                    message=success_msg,
                    row_index=idx,
                )
        except Exception as exc:
            logger.error(
                "  -> Gagal: %s - %s | Error: %s",
                pangkalan_id,
                pangkalan_name,
                exc,
            )
            if self.config.SCREENSHOT_ON_ERROR:
                self.take_screenshot(f"error_{pangkalan_id}")
            return SurveyResult(
                pangkalan_id=pangkalan_id,
                pangkalan_name=pangkalan_name,
                status="failed",
                message=str(exc),
                row_index=idx,
            )

        return SurveyResult(
            pangkalan_id=pangkalan_id,
            pangkalan_name=pangkalan_name,
            status="skipped",
            message="Tombol open survey tidak ditemukan",
            row_index=idx,
        )

    def _confirm_dialog(self) -> bool:
        """Tangani dialog konfirmasi jika muncul. Kembalikan True jika dikonfirmasi."""
        if self.is_visible(*_CONFIRM_DIALOG, timeout=3):
            logger.debug("Dialog konfirmasi muncul. Mengklik Ya/OK.")
            try:
                self.click(*_CONFIRM_YES)
                self.wait_for_element_disappear(*_CONFIRM_DIALOG)
                return True
            except TimeoutException:
                logger.warning("Tombol konfirmasi tidak ditemukan.")
                return False
        return True

    def _get_notification(self, kind: str = "success") -> str:
        """Ambil teks notifikasi setelah aksi (success/error)."""
        locator = _NOTIFICATION_SUCCESS if kind == "success" else _NOTIFICATION_ERROR
        if self.is_visible(*locator, timeout=5):
            return self.get_text(*locator)
        return ""

    def _wait_for_page_load(self) -> None:
        """Tunggu halaman selesai dimuat (loading indicator hilang)."""
        time.sleep(0.5)
        if self.is_visible(*_LOADING_INDICATOR, timeout=2):
            self.wait_for_element_disappear(*_LOADING_INDICATOR)

    def _go_to_next_page(self) -> bool:
        """Klik tombol halaman berikutnya jika tersedia. Kembalikan True jika berhasil."""
        try:
            next_btn = self.driver.find_element(*_PAGINATION_NEXT)
            parent_classes = next_btn.find_element(By.XPATH, "..").get_attribute("class") or ""
            if "disabled" in parent_classes:
                logger.debug("Sudah di halaman terakhir.")
                return False
            next_btn.click()
            self._wait_for_page_load()
            return True
        except Exception:
            logger.debug("Tombol pagination tidak ditemukan – hanya satu halaman.")
            return False
