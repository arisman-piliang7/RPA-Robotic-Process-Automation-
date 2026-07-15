"""
Modul konfigurasi untuk RPA DDMS PT Pertamina Patra Niaga.
Memuat pengaturan dari file .env atau variabel lingkungan.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Muat file .env dari direktori root proyek
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(_PROJECT_ROOT / ".env")


class Config:
    """Kelas konfigurasi terpusat untuk seluruh modul automasi."""

    # --- URL & Kredensial DDMS ---
    DDMS_URL: str = os.getenv("DDMS_URL", "https://ddms.pertamina.com")
    USERNAME: str = os.getenv("DDMS_USERNAME", "")
    PASSWORD: str = os.getenv("DDMS_PASSWORD", "")
    AREA_CODE: str = os.getenv("AREA_CODE", "")

    # --- Pengaturan Browser ---
    BROWSER: str = os.getenv("BROWSER", "chrome").lower()
    HEADLESS: bool = os.getenv("HEADLESS", "false").lower() == "true"

    # --- Batas Waktu (detik) ---
    IMPLICIT_WAIT: int = int(os.getenv("IMPLICIT_WAIT", "10"))
    EXPLICIT_WAIT: int = int(os.getenv("EXPLICIT_WAIT", "30"))
    PAGE_LOAD_TIMEOUT: int = int(os.getenv("PAGE_LOAD_TIMEOUT", "60"))

    # --- Direktori Output & Log ---
    OUTPUT_DIR: Path = _PROJECT_ROOT / os.getenv("OUTPUT_DIR", "output")
    LOG_DIR: Path = _PROJECT_ROOT / os.getenv("LOG_DIR", "logs")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()

    # --- Tangkapan Layar ---
    SCREENSHOT_ON_ERROR: bool = True
    SCREENSHOT_DIR: Path = _PROJECT_ROOT / "output" / "screenshots"

    @classmethod
    def validate(cls) -> None:
        """Validasi konfigurasi wajib sebelum menjalankan automasi."""
        missing = []
        if not cls.DDMS_URL:
            missing.append("DDMS_URL")
        if not cls.USERNAME:
            missing.append("DDMS_USERNAME")
        if not cls.PASSWORD:
            missing.append("DDMS_PASSWORD")
        if missing:
            raise ValueError(
                f"Konfigurasi wajib belum diatur: {', '.join(missing)}. "
                "Salin .env.example menjadi .env dan isi nilai yang sesuai."
            )

    @classmethod
    def ensure_dirs(cls) -> None:
        """Buat direktori output dan log jika belum ada."""
        cls.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        cls.LOG_DIR.mkdir(parents=True, exist_ok=True)
        cls.SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
