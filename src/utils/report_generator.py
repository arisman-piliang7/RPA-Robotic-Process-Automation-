"""
Modul pembuatan laporan hasil automasi Open Survey Pangkalan.
Menghasilkan laporan dalam format Excel dan teks.
"""
import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.automation.survey_pangkalan_page import SurveyReport

logger = logging.getLogger(__name__)


def generate_excel_report(report: "SurveyReport", output_dir: Path) -> Path:
    """
    Buat laporan Excel dari hasil open survey pangkalan.

    Args:
        report: Objek SurveyReport berisi detail hasil.
        output_dir: Direktori tempat menyimpan file laporan.

    Returns:
        Path file Excel yang dihasilkan.
    """
    try:
        import openpyxl
        from openpyxl.styles import Alignment, Font, PatternFill
    except ImportError:
        logger.error("openpyxl tidak terinstall. Jalankan: pip install openpyxl")
        raise

    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = output_dir / f"laporan_open_survey_{timestamp}.xlsx"

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Hasil Open Survey"

    # --- Header ---
    headers = ["No", "ID Pangkalan", "Nama Pangkalan", "Status", "Keterangan"]
    header_fill = PatternFill(patternType="solid", fgColor="1F4E79")
    header_font = Font(bold=True, color="FFFFFF")
    header_align = Alignment(horizontal="center", vertical="center")

    ws.row_dimensions[1].height = 20
    for col_idx, header in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = header_align

    # --- Status color mapping ---
    status_fill = {
        "success": PatternFill(patternType="solid", fgColor="C6EFCE"),
        "failed": PatternFill(patternType="solid", fgColor="FFC7CE"),
        "skipped": PatternFill(patternType="solid", fgColor="FFEB9C"),
    }
    status_label = {
        "success": "Berhasil",
        "failed": "Gagal",
        "skipped": "Dilewati",
    }

    # --- Data rows ---
    for row_idx, result in enumerate(report.results, start=2):
        ws.cell(row=row_idx, column=1, value=row_idx - 1)
        ws.cell(row=row_idx, column=2, value=result.pangkalan_id)
        ws.cell(row=row_idx, column=3, value=result.pangkalan_name)
        status_cell = ws.cell(
            row=row_idx,
            column=4,
            value=status_label.get(result.status, result.status),
        )
        status_cell.fill = status_fill.get(result.status, PatternFill())
        ws.cell(row=row_idx, column=5, value=result.message)

    # --- Kolom lebar otomatis ---
    col_widths = [5, 20, 35, 12, 50]
    for col_idx, width in enumerate(col_widths, start=1):
        ws.column_dimensions[
            openpyxl.utils.get_column_letter(col_idx)
        ].width = width

    # --- Sheet ringkasan ---
    ws_summary = wb.create_sheet("Ringkasan")
    ws_summary.column_dimensions["A"].width = 25
    ws_summary.column_dimensions["B"].width = 15
    summary_data = [
        ("Tanggal Eksekusi", datetime.now().strftime("%d/%m/%Y %H:%M:%S")),
        ("Total Pangkalan", report.total),
        ("Berhasil", report.success),
        ("Gagal", report.failed),
        ("Dilewati", report.skipped),
    ]
    for row_idx, (label, value) in enumerate(summary_data, start=1):
        ws_summary.cell(row=row_idx, column=1, value=label).font = Font(bold=True)
        ws_summary.cell(row=row_idx, column=2, value=value)

    wb.save(filepath)
    logger.info("Laporan Excel disimpan: %s", filepath)
    return filepath


def generate_text_report(report: "SurveyReport", output_dir: Path) -> Path:
    """
    Buat laporan teks ringkas dari hasil open survey pangkalan.

    Args:
        report: Objek SurveyReport.
        output_dir: Direktori tempat menyimpan file laporan.

    Returns:
        Path file teks yang dihasilkan.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = output_dir / f"laporan_open_survey_{timestamp}.txt"

    lines = [
        "=" * 60,
        "LAPORAN OPEN SURVEY PANGKALAN",
        f"Tanggal: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
        "=" * 60,
        f"Total Pangkalan : {report.total}",
        f"Berhasil        : {report.success}",
        f"Gagal           : {report.failed}",
        f"Dilewati        : {report.skipped}",
        "=" * 60,
        "",
        "DETAIL HASIL:",
        "-" * 60,
    ]

    for result in report.results:
        status_str = {
            "success": "BERHASIL",
            "failed": "GAGAL   ",
            "skipped": "DILEWATI",
        }.get(result.status, result.status.upper())

        lines.append(
            f"[{status_str}] {result.pangkalan_id:<15} {result.pangkalan_name:<30}"
            + (f" | {result.message}" if result.message else "")
        )

    lines += ["", "=" * 60]
    content = "\n".join(lines)

    filepath.write_text(content, encoding="utf-8")
    logger.info("Laporan teks disimpan: %s", filepath)
    return filepath
