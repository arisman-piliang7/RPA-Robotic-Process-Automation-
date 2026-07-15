"""
Entry point utama untuk RPA Open Survey Pangkalan DDMS PT Pertamina Patra Niaga.

Penggunaan:
    python main.py                          # proses semua pangkalan
    python main.py --id 12345               # proses satu pangkalan
    python main.py --area 0101              # filter berdasarkan area
    python main.py --headless               # jalankan tanpa tampilan browser
"""
import argparse
import sys
from pathlib import Path

# Pastikan direktori root proyek ada di sys.path
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.automation.ddms_automation import DDMSAutomation
from src.config import Config
from src.utils.logger import get_logger


def parse_args() -> argparse.Namespace:
    """Parse argumen baris perintah."""
    parser = argparse.ArgumentParser(
        description="RPA Open Survey Pangkalan DDMS PT Pertamina Patra Niaga",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Contoh penggunaan:
  python main.py                          Proses semua pangkalan
  python main.py --id 12345              Proses satu pangkalan (ID: 12345)
  python main.py --area 0101             Filter area kode 0101
  python main.py --headless              Mode tanpa tampilan browser
  python main.py --id 12345 --headless   Kombinasi
        """,
    )
    parser.add_argument(
        "--id",
        dest="pangkalan_id",
        default=None,
        help="ID pangkalan yang akan diproses (kosongkan untuk semua pangkalan)",
    )
    parser.add_argument(
        "--area",
        dest="area_code",
        default=None,
        help="Kode area untuk filter daftar pangkalan",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=None,
        help="Jalankan browser tanpa tampilan (headless mode)",
    )
    parser.add_argument(
        "--browser",
        choices=["chrome", "firefox"],
        default=None,
        help="Pilih browser: chrome (default) atau firefox",
    )
    return parser.parse_args()


def apply_cli_overrides(args: argparse.Namespace) -> None:
    """Terapkan override dari argumen CLI ke Config."""
    if args.headless is not None:
        Config.HEADLESS = args.headless
    if args.browser is not None:
        Config.BROWSER = args.browser
    if args.area_code is not None:
        Config.AREA_CODE = args.area_code


def main() -> int:
    """
    Fungsi utama program.

    Returns:
        Kode keluar: 0 = sukses, 1 = ada kegagalan, 2 = error fatal.
    """
    args = parse_args()
    apply_cli_overrides(args)

    # Setup logging awal
    Config.ensure_dirs()
    logger = get_logger("main", Config.LOG_DIR, Config.LOG_LEVEL)

    logger.info("RPA DDMS - Open Survey Pangkalan PT Pertamina Patra Niaga")
    logger.info("Versi Python  : %s", sys.version.split()[0])

    try:
        automation = DDMSAutomation(config=Config)
        report = automation.run(pangkalan_id=args.pangkalan_id)

        if report.failed > 0:
            logger.warning(
                "Selesai dengan %d kegagalan dari %d total pangkalan.",
                report.failed,
                report.total,
            )
            return 1

        logger.info(
            "Selesai. Semua %d pangkalan berhasil diproses.", report.success
        )
        return 0

    except ValueError as exc:
        logger.error("Konfigurasi tidak valid: %s", exc)
        return 2
    except RuntimeError as exc:
        logger.error("Error runtime: %s", exc)
        return 2
    except KeyboardInterrupt:
        logger.warning("Automasi dibatalkan oleh pengguna (Ctrl+C).")
        return 2
    except Exception as exc:
        logger.critical("Error tidak terduga: %s", exc, exc_info=True)
        return 2


if __name__ == "__main__":
    sys.exit(main())
