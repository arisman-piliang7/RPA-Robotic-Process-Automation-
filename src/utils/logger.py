"""
Modul utilitas logging untuk RPA DDMS PT Pertamina Patra Niaga.
Menyediakan logger terformat dengan output ke konsol dan file.
"""
import logging
import sys
from datetime import datetime
from pathlib import Path


def get_logger(name: str, log_dir: Path, level: str = "INFO") -> logging.Logger:
    """
    Buat dan kembalikan logger dengan handler konsol dan file.

    Args:
        name: Nama logger (biasanya __name__ modul pemanggil).
        log_dir: Direktori untuk menyimpan file log.
        level: Level logging (DEBUG, INFO, WARNING, ERROR, CRITICAL).

    Returns:
        Instans logging.Logger yang sudah dikonfigurasi.
    """
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(numeric_level)

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)-8s] %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Handler konsol
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Handler file (rotasi harian)
    timestamp = datetime.now().strftime("%Y%m%d")
    log_file = log_dir / f"ddms_rpa_{timestamp}.log"
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(numeric_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
