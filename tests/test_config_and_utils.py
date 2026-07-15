"""
Pengujian unit untuk modul konfigurasi dan utilitas.
"""
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Pastikan root proyek ada di path
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


@pytest.fixture
def fresh_config():
    """
    Kembalikan kelas Config yang sudah di-reload agar perubahan env terdeteksi.
    Juga mereset atribut wajib ke string kosong untuk memudahkan pengujian validasi.
    """
    import importlib
    import src.config as cfg_module

    importlib.reload(cfg_module)
    return cfg_module.Config


class TestConfig:
    """Pengujian modul Config."""

    def test_validate_raises_when_username_missing(self, fresh_config):
        """Config.validate() harus raise ValueError jika USERNAME kosong."""
        fresh_config.USERNAME = ""
        fresh_config.PASSWORD = "secret"
        fresh_config.DDMS_URL = "https://example.com"

        with pytest.raises(ValueError, match="DDMS_USERNAME"):
            fresh_config.validate()

    def test_validate_raises_when_password_missing(self, fresh_config):
        """Config.validate() harus raise ValueError jika PASSWORD kosong."""
        fresh_config.USERNAME = "user"
        fresh_config.PASSWORD = ""
        fresh_config.DDMS_URL = "https://example.com"

        with pytest.raises(ValueError, match="DDMS_PASSWORD"):
            fresh_config.validate()

    def test_validate_passes_when_all_set(self, fresh_config):
        """Config.validate() tidak boleh raise jika semua nilai wajib terisi."""
        fresh_config.USERNAME = "user"
        fresh_config.PASSWORD = "pass"
        fresh_config.DDMS_URL = "https://example.com"

        # Tidak boleh raise
        fresh_config.validate()

    def test_ensure_dirs_creates_directories(self, fresh_config, tmp_path):
        """Config.ensure_dirs() harus membuat direktori output, log, dan screenshot."""
        fresh_config.OUTPUT_DIR = tmp_path / "output"
        fresh_config.LOG_DIR = tmp_path / "logs"
        fresh_config.SCREENSHOT_DIR = tmp_path / "output" / "screenshots"

        fresh_config.ensure_dirs()

        assert fresh_config.OUTPUT_DIR.exists()
        assert fresh_config.LOG_DIR.exists()
        assert fresh_config.SCREENSHOT_DIR.exists()

    def test_headless_defaults_to_false(self, fresh_config, monkeypatch):
        """HEADLESS default harus False."""
        monkeypatch.delenv("HEADLESS", raising=False)
        # Default dari getenv dengan fallback "false"
        assert fresh_config.HEADLESS is False

    def test_browser_defaults_to_chrome(self, fresh_config, monkeypatch):
        """BROWSER default harus 'chrome'."""
        monkeypatch.delenv("BROWSER", raising=False)
        assert fresh_config.BROWSER == "chrome"


class TestLogger:
    """Pengujian modul logger."""

    def test_get_logger_creates_log_file(self, tmp_path):
        """get_logger harus membuat file log di direktori yang ditentukan."""
        import logging

        from src.utils.logger import get_logger

        logger = get_logger("test_logger", tmp_path, "DEBUG")

        assert logger is not None
        assert logger.level == logging.DEBUG

        log_files = list(tmp_path.glob("ddms_rpa_*.log"))
        assert len(log_files) >= 1

    def test_get_logger_returns_same_instance(self, tmp_path):
        """get_logger harus mengembalikan instans yang sama untuk nama yang sama."""
        from src.utils.logger import get_logger

        logger1 = get_logger("same_logger_x", tmp_path)
        logger2 = get_logger("same_logger_x", tmp_path)

        assert logger1 is logger2

    def test_get_logger_default_level_is_info(self, tmp_path):
        """Level default logger harus INFO."""
        import logging

        from src.utils.logger import get_logger

        logger = get_logger("default_level_logger", tmp_path)
        assert logger.level == logging.INFO


class TestReportGenerator:
    """Pengujian modul report_generator."""

    def _make_report(self):
        """Buat objek SurveyReport contoh untuk pengujian."""
        from src.automation.survey_pangkalan_page import SurveyReport, SurveyResult

        report = SurveyReport()
        report.add(
            SurveyResult("001", "Pangkalan Maju Jaya", "success", "Survey dibuka")
        )
        report.add(
            SurveyResult("002", "Pangkalan Sejahtera", "failed", "Timeout error")
        )
        report.add(
            SurveyResult("003", "Pangkalan Barokah", "skipped", "Tombol tidak ada")
        )
        return report

    def test_generate_text_report_creates_file(self, tmp_path):
        """generate_text_report harus menghasilkan file .txt."""
        from src.utils.report_generator import generate_text_report

        report = self._make_report()
        path = generate_text_report(report, tmp_path)

        assert path.exists()
        assert path.suffix == ".txt"
        content = path.read_text(encoding="utf-8")
        assert "Pangkalan Maju Jaya" in content
        assert "BERHASIL" in content
        assert "GAGAL" in content

    def test_generate_excel_report_creates_file(self, tmp_path):
        """generate_excel_report harus menghasilkan file .xlsx."""
        pytest.importorskip("openpyxl")
        from src.utils.report_generator import generate_excel_report

        report = self._make_report()
        path = generate_excel_report(report, tmp_path)

        assert path.exists()
        assert path.suffix == ".xlsx"

    def test_report_summary_counts(self):
        """SurveyReport.summary() harus menghitung total, sukses, gagal, dilewati."""
        report = self._make_report()
        assert report.total == 3
        assert report.success == 1
        assert report.failed == 1
        assert report.skipped == 1
        summary = report.summary()
        assert "3" in summary
        assert "1" in summary


class TestSurveyResult:
    """Pengujian dataclass SurveyResult dan SurveyReport."""

    def test_survey_result_defaults(self):
        """SurveyResult harus memiliki nilai default yang benar."""
        from src.automation.survey_pangkalan_page import SurveyResult

        result = SurveyResult(
            pangkalan_id="X01",
            pangkalan_name="Test",
            status="success",
        )
        assert result.message == ""
        assert result.row_index == 0

    def test_survey_report_add(self):
        """SurveyReport.add() harus memperbarui counter dengan benar."""
        from src.automation.survey_pangkalan_page import SurveyReport, SurveyResult

        report = SurveyReport()
        assert report.total == 0

        report.add(SurveyResult("1", "A", "success"))
        report.add(SurveyResult("2", "B", "failed"))
        report.add(SurveyResult("3", "C", "skipped"))

        assert report.total == 3
        assert report.success == 1
        assert report.failed == 1
        assert report.skipped == 1
        assert len(report.results) == 3
