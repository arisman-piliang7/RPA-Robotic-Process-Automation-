"""
Otomatisasi Buka Ulang Inputan Survey - Kemitraan Pertamina (GUI)
=====================================================================
Requirements:
    pip install selenium webdriver-manager openpyxl pandas customtkinter

Cara pakai:
    1. Siapkan file Excel (default: data_pangkalan.xlsx) berisi kolom "ID Registrasi"
    2. Jalankan: python survey_ddms3_gui.py
    3. Masukkan Username & Password di panel Login, klik "Login & Mulai"
    4. Selesaikan captcha di browser jika muncul, proses berjalan otomatis
"""

import time
import os
import csv
import glob
import threading
import queue
from datetime import datetime, timedelta

import pandas as pd
import customtkinter as ctk
from tkinter import filedialog, messagebox

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    InvalidSessionIdException,
    WebDriverException,
    StaleElementReferenceException,
    ElementClickInterceptedException,
)
from webdriver_manager.chrome import ChromeDriverManager

# ════════════════════════════════════════════════════════════════════════════
# KONFIGURASI & KONSTAN
# ════════════════════════════════════════════════════════════════════════════
BASE_URL = "https://admin.kemitraan.patraniaga.com/internal"
LOGIN_URL = f"{BASE_URL}/login"
SURVEY_URL = f"{BASE_URL}/ddms-lpg/pso/survey/index"

WAIT = 15
JEDA = 1.5
MAX_RESTART = 50
MAX_RETRY_KLIK = 3

KOLOM_ID = "ID Registrasi"
KOLOM_STATUS = "Status Proses"
KOLOM_WAKTU = "Waktu Proses"
KOLOM_KET = "Keterangan"

XPATH_SEARCH_BOX = (
    "/html/body/div[1]/div[3]/div[1]/div[1]/div[3]/div[2]/div/div[1]/div[1]/label/input"
)
XPATH_DETAIL_ICON = "//*[@id='dataTable']/tbody/tr/td[9]/div/a/i"
XPATH_DETAIL_LINK = "//*[@id='dataTable']/tbody/tr/td[9]/div/a"

CHECKBOXES = [
    "//*[@id='IsNotValidNoKTP']",
    "//*[@id='IsNotValidNamaPemilik']",
    "//*[@id='IsNotValidNoTelpon']",
    "//*[@id='IsNotValidFoto']",
    "//*[@id='IsNotValidAlamat']",
    "//*[@id='IsNotValidFotoKTP']",
    "//*[@id='IsNotValidFotoTabung']",
    "//*[@id='IsNotValidPapanPangkalan']",
    "//*[@id='IsNotValidFileNIBHalamanUtama']",
    "//*[@id='IsNotValidFileNIBHalamanLampiran']",
    "//*[@id='IsNotValidNoNIB']",
]

# Warna tema
WARNA_SUKSES = "#22c55e"
WARNA_GAGAL = "#ef4444"
WARNA_SKIP = "#f59e0b"
WARNA_AKSEN = "#3b82f6"
WARNA_BG_CARD = "#1e1e2e"
WARNA_LOGIN_CARD = "#16213e"


# ════════════════════════════════════════════════════════════════════════════
# HELPER
# ════════════════════════════════════════════════════════════════════════════
def fmt_exc(e: Exception) -> str:
    tipe = type(e).__name__
    pesan = str(e).strip()
    if not pesan:
        pesan = repr(e).strip()
    if not pesan or pesan == tipe:
        pesan = "(tidak ada detail pesan dari WebDriver/ChromeDriver)"
    return f"[{tipe}] {pesan}"


def tunggu_hingga(fungsi_cek, timeout=2.0, interval=0.15, log_func=None, label=None):
    mulai = time.time()
    hasil = fungsi_cek()
    while not hasil and (time.time() - mulai) < timeout:
        time.sleep(interval)
        hasil = fungsi_cek()
    if log_func and label:
        durasi = time.time() - mulai
        if durasi >= 0.3:
            log_func(f"⏱️  {label}: {durasi:.1f}s")
    return hasil


# ════════════════════════════════════════════════════════════════════════════
# LOGIKA SELENIUM
# ════════════════════════════════════════════════════════════════════════════
def klik(driver, xpath, timeout=WAIT, retries=MAX_RETRY_KLIK, log_func=None):
    last_err = None
    for percobaan in range(1, retries + 1):
        try:
            el = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((By.XPATH, xpath))
            )
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
            time.sleep(0.3)
            driver.execute_script("arguments[0].click();", el)
            return el
        except (StaleElementReferenceException, ElementClickInterceptedException) as e:
            last_err = e
            if log_func:
                log_func(
                    f"⚠️  Klik gagal (percobaan {percobaan}/{retries}) pada {xpath}: {fmt_exc(e)}"
                )
            time.sleep(0.8)
            continue
    raise last_err


def ada(driver, xpath, timeout=3):
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.XPATH, xpath))
        )
        return True
    except TimeoutException:
        return False


def catat_log(id_reg, no_agen, nama_agen, status, keterangan=""):
    filename = "log_survey.csv"
    file_exists = os.path.exists(filename)
    with open(filename, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(
                ["Waktu", "ID Registrasi", "No Agen", "Nama Agen", "Status", "Keterangan"]
            )
        writer.writerow(
            [
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                id_reg,
                no_agen,
                nama_agen,
                status,
                keterangan,
            ]
        )


def bersihkan_wdm_lock():
    lock_pattern = os.path.expanduser(r"~\.wdm\.wdm-lock-*")
    for lock_file in glob.glob(lock_pattern):
        try:
            os.remove(lock_file)
        except Exception:
            pass


def buat_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
    options.add_argument("--log-level=3")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)


def session_mati(e: Exception) -> bool:
    if isinstance(e, InvalidSessionIdException):
        return True
    pesan = str(e).lower().strip()
    tanda = [
        "invalid session id", "session deleted",
        "disconnected: not connected to devtools",
        "chrome not reachable", "no such window",
        "target window already closed", "unable to connect to renderer",
        "connection refused", "connection reset",
    ]
    if any(t in pesan for t in tanda):
        return True
    if isinstance(e, WebDriverException) and not pesan:
        if not isinstance(
            e,
            (TimeoutException, NoSuchElementException,
             StaleElementReferenceException, ElementClickInterceptedException),
        ):
            return True
    return False


def login(driver, username, password, log_func):
    """Login ke aplikasi. Menunggu user menyelesaikan captcha jika ada."""
    log_func("🔐 Membuka halaman login...")
    driver.get(LOGIN_URL)
    WebDriverWait(driver, WAIT).until(
        lambda d: d.execute_script("return document.readyState") == "complete"
    )
    time.sleep(1.5)

    log_func(f"✏️  Mengisi username: {username}")
    driver.find_element(By.ID, "UserName").send_keys(username)
    driver.find_element(By.ID, "Password").send_keys(password)
    klik(driver, "//*[@id='loginSubmit']", log_func=log_func)

    log_func("⏳ Menunggu redirect login... (selesaikan captcha di browser jika ada, maksimal 5 menit)")
    try:
        WebDriverWait(driver, 60).until(lambda d: "login" not in d.current_url.lower())
    except TimeoutException:
        log_func(
            "⚠️  Captcha terdeteksi / redirect lambat - silakan selesaikan manual di "
            "browser Chrome yang terbuka. Proses akan lanjut otomatis setelah berhasil login."
        )
        WebDriverWait(driver, 300).until(lambda d: "login" not in d.current_url.lower())

    log_func(f"✅ Login berhasil! URL: {driver.current_url}")
    time.sleep(JEDA)


def buka_halaman_survey(driver):
    driver.get(SURVEY_URL)
    WebDriverWait(driver, WAIT).until(
        lambda d: d.execute_script("return document.readyState") == "complete"
    )
    time.sleep(JEDA)


def _ketik_id_di_search_box(driver, id_reg, log_func=None):
    box = WebDriverWait(driver, WAIT).until(
        EC.element_to_be_clickable((By.XPATH, XPATH_SEARCH_BOX))
    )
    box.click()
    time.sleep(0.3)
    box.send_keys(Keys.CONTROL, "a")
    box.send_keys(Keys.DELETE)
    driver.execute_script(
        """
        var el = arguments[0];
        el.value = '';
        el.dispatchEvent(new Event('input', { bubbles: true }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
        """,
        box,
    )
    time.sleep(0.4)
    id_str = str(id_reg).strip()
    for ch in id_str:
        box.send_keys(ch)
        time.sleep(0.05)
    time.sleep(0.8)
    nilai_box = driver.execute_script("return arguments[0].value;", box)
    if nilai_box != id_str and log_func:
        log_func(f"⚠️  Nilai search box ({nilai_box!r}) belum sesuai target ({id_str!r})")
    return nilai_box == id_str


def cari_id_registrasi(driver, id_reg, log_func=None, max_percobaan=3):
    id_str = str(id_reg).strip()
    xpath_td4 = (
        "/html/body/div[1]/div[3]/div[1]/div[1]/div[3]/div[2]/div/div[2]"
        "/table/tbody/tr[1]/td[4]"
    )
    for percobaan in range(1, max_percobaan + 1):
        _ketik_id_di_search_box(driver, id_reg, log_func)
        try:
            WebDriverWait(driver, WAIT).until(
                lambda d: d.find_element(By.XPATH, xpath_td4).text.strip() == id_str
            )
            return
        except TimeoutException:
            if log_func:
                log_func(
                    f"⚠️  Tabel belum menampilkan ID {id_reg} setelah tunggu {WAIT}s "
                    f"(percobaan {percobaan}/{max_percobaan})"
                )
            if percobaan < max_percobaan:
                if log_func:
                    log_func("🔁 Mengulang pencarian dari awal (reload halaman)...")
                buka_halaman_survey(driver)
    time.sleep(JEDA)


def ambil_info_baris_pertama(driver):
    try:
        no_agen = driver.find_element(
            By.XPATH,
            "/html/body/div[1]/div[3]/div[1]/div[1]/div[3]/div[2]/div/div[2]/table/tbody/tr[1]/td[2]",
        ).text.strip()
        nama_agen = driver.find_element(
            By.XPATH,
            "/html/body/div[1]/div[3]/div[1]/div[1]/div[3]/div[2]/div/div[2]/table/tbody/tr[1]/td[3]",
        ).text.strip()
        status = driver.find_element(
            By.XPATH,
            "/html/body/div[1]/div[3]/div[1]/div[1]/div[3]/div[2]/div/div[2]/table/tbody/tr[1]/td[8]",
        ).text.strip()
        return no_agen, nama_agen, status
    except Exception:
        return "-", "-", "-"


def proses_satu_id(driver, id_reg, log_func):
    buka_halaman_survey(driver)
    log_func(f"🔎 Mencari ID Registrasi: {id_reg}")
    cari_id_registrasi(driver, id_reg, log_func)

    if not ada(
        driver,
        "/html/body/div[1]/div[3]/div[1]/div[1]/div[3]/div[2]/div/div[2]/table/tbody/tr[1]",
        timeout=5,
    ):
        log_func("⚠️  Data tidak ditemukan di tabel.")
        return False, "Data tidak ditemukan", "-", "-"

    no_agen, nama_agen, status_saat_ini = ambil_info_baris_pertama(driver)

    try:
        id_di_tabel = driver.find_element(
            By.XPATH,
            "/html/body/div[1]/div[3]/div[1]/div[1]/div[3]/div[2]/div/div[2]/table/tbody/tr[1]/td[4]",
        ).text.strip()
        log_func(f"🔍 ID dicari: {id_reg} | ID di tabel: {id_di_tabel}")
        if str(id_reg).strip() != id_di_tabel:
            log_func(
                f"⚠️  ID tidak cocok setelah retry! Dicari: {id_reg}, "
                f"Ditemukan: {id_di_tabel}. Akan dicoba ulang nanti (Gagal, bukan Skip)."
            )
            return (
                False,
                f"Gagal - ID tidak cocok di tabel (ditemukan {id_di_tabel}), perlu dicoba ulang",
                no_agen,
                nama_agen,
            )
    except Exception as e:
        log_func(f"⚠️  Gagal validasi ID di tabel: {fmt_exc(e)}")

    log_func(f"📋 {nama_agen} | Agen: {no_agen} | Status saat ini: {status_saat_ini}")
    log_func("👆 Klik Detail...")

    def _ada_instan(xpath):
        try:
            return len(driver.find_elements(By.XPATH, xpath)) > 0
        except Exception:
            return False

    icon_ada = _ada_instan(XPATH_DETAIL_ICON)
    link_ada = _ada_instan(XPATH_DETAIL_LINK)

    if not icon_ada and not link_ada:
        def _cek_icon_link():
            nonlocal icon_ada, link_ada
            icon_ada = _ada_instan(XPATH_DETAIL_ICON)
            link_ada = _ada_instan(XPATH_DETAIL_LINK)
            return icon_ada or link_ada

        tunggu_hingga(
            _cek_icon_link, timeout=1.5, interval=0.15,
            log_func=log_func, label="Menunggu icon/link Detail muncul",
        )

    if not icon_ada and not link_ada:
        log_func("⏭️  Icon detail tidak ditemukan, skip.")
        catat_log(id_reg, no_agen, nama_agen, "Skip", "Icon detail tidak ditemukan")
        return False, "Skip - Icon detail tidak ditemukan", no_agen, nama_agen

    try:
        if icon_ada:
            klik(driver, XPATH_DETAIL_ICON, log_func=log_func)
        else:
            klik(driver, XPATH_DETAIL_LINK, log_func=log_func)
    except TimeoutException:
        try:
            if icon_ada:
                klik(driver, XPATH_DETAIL_LINK, log_func=log_func)
            else:
                klik(driver, XPATH_DETAIL_ICON, log_func=log_func)
        except TimeoutException:
            log_func("⏭️  Icon detail tidak ditemukan, skip.")
            catat_log(id_reg, no_agen, nama_agen, "Skip", "Icon detail tidak ditemukan")
            return False, "Skip - Icon detail tidak ditemukan", no_agen, nama_agen

    XPATH_TOMBOL_SESUAI = "//*[@id='KunjunganForm']/div[3]/button[1]"
    XPATH_TOMBOL_TIDAK_SESUAI = "//*[@id='KunjunganForm']/div[3]/button[2]"

    def _tombol_muncul():
        return (
            len(driver.find_elements(By.XPATH, XPATH_TOMBOL_TIDAK_SESUAI)) > 0
            or len(driver.find_elements(By.XPATH, XPATH_TOMBOL_SESUAI)) > 0
        )

    ada_tombol = tunggu_hingga(
        _tombol_muncul, timeout=3.0, interval=0.2,
        log_func=log_func, label="Menunggu tombol Sesuai/Tidak Sesuai",
    )

    if not ada_tombol:
        try:
            driver.save_screenshot(f"debug_skip_{id_reg}.png")
            log_func(f"📸 Screenshot disimpan: debug_skip_{id_reg}.png")
        except Exception as ss_err:
            log_func(f"⚠️  Screenshot gagal: {fmt_exc(ss_err)}")
        log_func(
            "⏭️  Tombol Sesuai/Tidak Sesuai tidak ditemukan — kemungkinan sudah "
            "diproses SAR lain. Skip, lanjut ke data berikutnya."
        )
        catat_log(id_reg, no_agen, nama_agen, "Skip", "Tombol Sesuai/Tidak Sesuai tidak ditemukan")
        return False, "Skip - Tombol tidak ditemukan", no_agen, nama_agen

    log_func("🔓 Klik 'Tidak Sesuai' (buka kembali inputan agen)...")

    try:
        elemen_tombol = driver.find_element(By.XPATH, XPATH_TOMBOL_TIDAK_SESUAI)
        tombol_enabled = elemen_tombol.is_enabled()
    except Exception as e:
        tombol_enabled = True
        log_func(f"⚠️  Gagal cek status tombol, lanjut coba klik: {fmt_exc(e)}")

    if not tombol_enabled:
        log_func(
            "⏭️  Tombol 'Tidak Sesuai' ada tapi DISABLED (data kemungkinan sudah "
            "berstatus final/Berhasil). Skip tanpa mencoba klik."
        )
        catat_log(id_reg, no_agen, nama_agen, "Skip", "Tombol disabled - data sudah final")
        return False, "Skip - Tombol disabled (data sudah final)", no_agen, nama_agen

    klik(driver, XPATH_TOMBOL_TIDAK_SESUAI, log_func=log_func)
    time.sleep(JEDA)

    log_func("☑️  Centang semua checkbox...")
    for cb_xpath in CHECKBOXES:
        try:
            cb = driver.find_element(By.XPATH, cb_xpath)
            if not cb.is_selected():
                driver.execute_script("arguments[0].click();", cb)
                time.sleep(0.2)
        except NoSuchElementException:
            log_func(f"⚠️  Checkbox tidak ditemukan: {cb_xpath}")
        except StaleElementReferenceException as e:
            log_func(f"⚠️  Checkbox stale, dilewati: {cb_xpath} ({fmt_exc(e)})")

    time.sleep(0.5)

    log_func("📤 Submit...")
    klik(
        driver,
        "/html/body/div[1]/div[3]/div[1]/div[3]/div/div/div[2]/div/form/div[2]/button[2]",
        log_func=log_func,
    )
    time.sleep(JEDA * 2)

    log_func(f"✅ Selesai! {nama_agen} - {id_reg}")
    catat_log(id_reg, no_agen, nama_agen, "Berhasil", "Inputan Dibuka Ulang")
    return True, "Berhasil", no_agen, nama_agen


# ════════════════════════════════════════════════════════════════════════════
# WORKER THREAD
# ════════════════════════════════════════════════════════════════════════════
class StatusWorker:
    def __init__(self):
        self.pause_event = threading.Event()
        self.pause_event.set()
        self.stop_flag = threading.Event()


def worker_proses(app, excel_path, username, password):
    """Worker thread utama. Username & password diterima dari GUI."""
    q = app.queue
    ctrl = app.ctrl

    def log_func(msg):
        q.put(("log", msg))

    if not username or not password:
        q.put(("error", "Username dan password tidak boleh kosong!"))
        q.put(("selesai", None))
        return

    if not os.path.exists(excel_path):
        q.put(("error", f"File Excel tidak ditemukan: {excel_path}"))
        q.put(("selesai", None))
        return

    try:
        df = pd.read_excel(excel_path)
    except Exception as e:
        q.put(("error", f"Gagal membaca Excel: {fmt_exc(e)}"))
        q.put(("selesai", None))
        return

    if KOLOM_ID not in df.columns:
        q.put((
            "error",
            f"Kolom '{KOLOM_ID}' tidak ditemukan. Kolom tersedia: {list(df.columns)}",
        ))
        q.put(("selesai", None))
        return

    for kolom in (KOLOM_STATUS, KOLOM_WAKTU, KOLOM_KET):
        if kolom not in df.columns:
            df[kolom] = ""
        df[kolom] = df[kolom].astype("object")
        df[kolom] = df[kolom].where(df[kolom].notna(), "")

    total_baris = len(df)
    sisa_index = df[~df[KOLOM_STATUS].isin(["Berhasil", "Skip"])].index.tolist()
    total_sisa = len(sisa_index)

    q.put(("total", (total_baris, total_sisa)))
    log_func(f"📄 Total data di Excel: {total_baris} pangkalan")
    log_func(f"📌 Sisa yang akan diproses: {total_sisa} (skip yang sudah 'Berhasil'/'Skip')")

    if total_sisa == 0:
        log_func("🎉 Semua data sudah selesai diproses sebelumnya!")
        q.put(("selesai", None))
        return

    bersihkan_wdm_lock()
    driver = buat_driver()
    jumlah_restart = 0
    total_sukses = 0
    total_skip = 0
    total_gagal = 0
    waktu_mulai = time.time()

    try:
        login(driver, username, password, log_func)

        for n, idx in enumerate(sisa_index, start=1):
            if ctrl.stop_flag.is_set():
                log_func("⛔ Dihentikan oleh pengguna.")
                break

            while not ctrl.pause_event.is_set():
                q.put(("status_pause", True))
                time.sleep(0.3)
                if ctrl.stop_flag.is_set():
                    break
            if ctrl.stop_flag.is_set():
                log_func("⛔ Dihentikan oleh pengguna.")
                break
            q.put(("status_pause", False))

            id_reg = df.at[idx, KOLOM_ID]
            if pd.isna(id_reg) or str(id_reg).strip() == "":
                continue

            q.put(("current", (n, total_sisa, str(id_reg))))

            try:
                sukses, ket, no_agen, nama_agen = proses_satu_id(driver, id_reg, log_func)
            except Exception as e:
                if session_mati(e):
                    log_func(f"💥 Browser/session mati terdeteksi: {fmt_exc(e)}")
                    jumlah_restart += 1
                    if jumlah_restart > MAX_RESTART:
                        log_func(f"⛔ Batas restart browser ({MAX_RESTART}x) tercapai. Berhenti.")
                        df.to_excel(excel_path, index=False)
                        q.put(("error", f"Batas restart browser tercapai: {fmt_exc(e)}"))
                        break

                    log_func(f"🔄 Restart browser ({jumlah_restart}/{MAX_RESTART}) & login ulang...")
                    try:
                        driver.quit()
                    except Exception:
                        pass
                    time.sleep(3)
                    bersihkan_wdm_lock()
                    driver = buat_driver()
                    # ⚠️ Login ulang menggunakan kredensial yang sama yang diberikan user di GUI
                    login(driver, username, password, log_func)

                    try:
                        sukses, ket, no_agen, nama_agen = proses_satu_id(driver, id_reg, log_func)
                    except Exception as e2:
                        sukses, ket, no_agen, nama_agen = (
                            False, f"Error setelah restart: {fmt_exc(e2)}", "-", "-",
                        )
                        log_func(f"❌ Tetap gagal setelah restart: {fmt_exc(e2)}")
                else:
                    sukses, ket, no_agen, nama_agen = (
                        False, f"Error: {fmt_exc(e)}", "-", "-",
                    )
                    log_func(f"❌ Error saat proses {id_reg}: {fmt_exc(e)}")
                    import traceback as _tb
                    log_func(_tb.format_exc())

            if sukses:
                status_baris = "Berhasil"
            elif ket.startswith("Skip"):
                status_baris = "Skip"
            else:
                status_baris = "Gagal"

            df.at[idx, KOLOM_STATUS] = status_baris
            df.at[idx, KOLOM_WAKTU] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            df.at[idx, KOLOM_KET] = ket

            if status_baris == "Berhasil":
                total_sukses += 1
            elif status_baris == "Skip":
                total_skip += 1
            else:
                total_gagal += 1
                catat_log(id_reg, "-", "-", "Gagal", ket)

            df.to_excel(excel_path, index=False)

            elapsed = time.time() - waktu_mulai
            rata2_per_item = elapsed / n if n > 0 else 0
            sisa_waktu = rata2_per_item * (total_sisa - n)

            q.put((
                "progress",
                {
                    "n": n,
                    "total": total_sisa,
                    "sukses": total_sukses,
                    "skip": total_skip,
                    "gagal": total_gagal,
                    "id_reg": str(id_reg),
                    "nama_agen": nama_agen,
                    "status": status_baris,
                    "keterangan": ket,
                    "eta_detik": sisa_waktu,
                    "elapsed_detik": elapsed,
                },
            ))

        else:
            log_func("🎉 SELESAI! Semua data telah diproses.")

    except Exception as e:
        import traceback
        log_func(f"❌ Error fatal: {fmt_exc(e)}")
        log_func(traceback.format_exc())
        df.to_excel(excel_path, index=False)
        q.put(("error", fmt_exc(e)))
    finally:
        time.sleep(1)
        try:
            driver.quit()
        except Exception:
            pass
        q.put((
            "selesai",
            {"sukses": total_sukses, "skip": total_skip, "gagal": total_gagal},
        ))


# ════════════════════════════════════════════════════════════════════════════
# GUI
# ════════════════════════════════════════════════════════════════════════════
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


def format_durasi(detik):
    if detik is None or detik < 0 or detik != detik:
        return "-"
    td = timedelta(seconds=int(detik))
    jam, sisa = divmod(td.seconds, 3600)
    menit, detik = divmod(sisa, 60)
    if td.days > 0:
        return f"{td.days}h {jam}j {menit}m"
    if jam > 0:
        return f"{jam}j {menit}m {detik}d"
    if menit > 0:
        return f"{menit}m {detik}d"
    return f"{detik}d"


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Otomatisasi Survey - Kemitraan Pertamina")
        self.geometry("980x820")
        self.minsize(880, 750)

        self.queue = queue.Queue()
        self.ctrl = StatusWorker()
        self.worker_thread = None
        self.excel_path = (
            os.path.abspath("data_pangkalan.xlsx")
            if os.path.exists("data_pangkalan.xlsx")
            else ""
        )
        self.sedang_pause = False

        self._build_ui()
        self.after(150, self._poll_queue)

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)  # row 3 = body panel

        # ── Header ────────────────────────────────────────────────────────
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 6))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            header, text="🚀 Otomatisasi Buka Ulang Survey",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            header, text="Kemitraan Pertamina · DDMS LPG Pangkalan PSO",
            font=ctk.CTkFont(size=13), text_color="#9ca3af",
        ).grid(row=1, column=0, sticky="w")

        # ── Panel Login ───────────────────────────────────────────────────
        self._build_panel_login()

        # ── File Excel ────────────────────────────────────────────────────
        file_frame = ctk.CTkFrame(self, corner_radius=12)
        file_frame.grid(row=2, column=0, sticky="ew", padx=24, pady=(6, 10))
        file_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(
            file_frame, text="📁 File Excel",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(row=0, column=0, padx=(16, 8), pady=14, sticky="w")
        self.lbl_file = ctk.CTkLabel(
            file_frame,
            text=self.excel_path or "(belum dipilih - default: data_pangkalan.xlsx)",
            font=ctk.CTkFont(size=12), text_color="#9ca3af", anchor="w",
        )
        self.lbl_file.grid(row=0, column=1, padx=8, pady=14, sticky="ew")
        ctk.CTkButton(
            file_frame, text="Pilih File...", width=110, command=self._pilih_file,
        ).grid(row=0, column=2, padx=(8, 16), pady=14)

        # ── Body (log + statistik) ────────────────────────────────────────
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=3, column=0, sticky="nsew", padx=24, pady=(0, 10))
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=2)
        body.grid_rowconfigure(0, weight=1)
        self._build_panel_kiri(body)
        self._build_panel_kanan(body)

        # ── Footer tombol kontrol ─────────────────────────────────────────
        footer = ctk.CTkFrame(self, corner_radius=12)
        footer.grid(row=4, column=0, sticky="ew", padx=24, pady=(0, 20))
        footer.grid_columnconfigure((0, 1, 2), weight=1)

        self.btn_mulai = ctk.CTkButton(
            footer, text="▶  Login & Mulai", height=44,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=WARNA_SUKSES, hover_color="#16a34a",
            command=self._mulai,
        )
        self.btn_mulai.grid(row=0, column=0, padx=16, pady=16, sticky="ew")

        self.btn_pause = ctk.CTkButton(
            footer, text="⏸  Pause", height=44,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=WARNA_SKIP, hover_color="#d97706",
            command=self._toggle_pause, state="disabled",
        )
        self.btn_pause.grid(row=0, column=1, padx=16, pady=16, sticky="ew")

        self.btn_stop = ctk.CTkButton(
            footer, text="⏹  Stop", height=44,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=WARNA_GAGAL, hover_color="#dc2626",
            command=self._stop, state="disabled",
        )
        self.btn_stop.grid(row=0, column=2, padx=16, pady=16, sticky="ew")

    def _build_panel_login(self):
        """Panel isian username & password pengganti .env"""
        login_frame = ctk.CTkFrame(self, corner_radius=12, fg_color=WARNA_LOGIN_CARD)
        login_frame.grid(row=1, column=0, sticky="ew", padx=24, pady=(0, 6))
        login_frame.grid_columnconfigure((1, 3), weight=1)

        ctk.CTkLabel(
            login_frame, text="🔐 Kredensial Login",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(row=0, column=0, columnspan=5, sticky="w", padx=16, pady=(14, 6))

        # Username
        ctk.CTkLabel(
            login_frame, text="Username:", font=ctk.CTkFont(size=12),
        ).grid(row=1, column=0, padx=(16, 6), pady=(0, 14), sticky="w")
        self.entry_username = ctk.CTkEntry(
            login_frame, placeholder_text="Masukkan username...",
            font=ctk.CTkFont(size=12), height=36,
        )
        self.entry_username.grid(row=1, column=1, padx=(0, 20), pady=(0, 14), sticky="ew")

        # Password
        ctk.CTkLabel(
            login_frame, text="Password:", font=ctk.CTkFont(size=12),
        ).grid(row=1, column=2, padx=(0, 6), pady=(0, 14), sticky="w")
        self.entry_password = ctk.CTkEntry(
            login_frame, placeholder_text="Masukkan password...",
            font=ctk.CTkFont(size=12), height=36, show="●",
        )
        self.entry_password.grid(row=1, column=3, padx=(0, 20), pady=(0, 14), sticky="ew")

        # Toggle show/hide password
        self.btn_show_pass = ctk.CTkButton(
            login_frame, text="👁", width=36, height=36,
            font=ctk.CTkFont(size=14),
            fg_color="transparent", border_width=1, border_color="#4b5563",
            hover_color="#374151",
            command=self._toggle_show_password,
        )
        self.btn_show_pass.grid(row=1, column=4, padx=(0, 16), pady=(0, 14))

        self._password_visible = False

        # Catatan kecil
        ctk.CTkLabel(
            login_frame,
            text="ℹ️  Kredensial hanya disimpan di memori selama sesi ini berjalan, tidak tersimpan ke file.",
            font=ctk.CTkFont(size=11), text_color="#6b7280",
        ).grid(row=2, column=0, columnspan=5, sticky="w", padx=16, pady=(0, 10))

    def _toggle_show_password(self):
        self._password_visible = not self._password_visible
        if self._password_visible:
            self.entry_password.configure(show="")
            self.btn_show_pass.configure(text="🙈")
        else:
            self.entry_password.configure(show="●")
            self.btn_show_pass.configure(text="👁")

    def _build_panel_kiri(self, parent):
        panel = ctk.CTkFrame(parent, corner_radius=12)
        panel.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        panel.grid_columnconfigure(0, weight=1)

        proc_frame = ctk.CTkFrame(panel, fg_color=WARNA_BG_CARD, corner_radius=10)
        proc_frame.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 10))
        proc_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            proc_frame, text="SEDANG DIPROSES",
            font=ctk.CTkFont(size=11, weight="bold"), text_color="#9ca3af",
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(12, 0))
        self.lbl_id_sekarang = ctk.CTkLabel(
            proc_frame, text="—", font=ctk.CTkFont(size=20, weight="bold"),
        )
        self.lbl_id_sekarang.grid(row=1, column=0, sticky="w", padx=16, pady=(2, 0))
        self.lbl_nama_sekarang = ctk.CTkLabel(
            proc_frame, text="Menunggu proses dimulai...",
            font=ctk.CTkFont(size=13), text_color="#9ca3af",
            wraplength=420, justify="left", anchor="w",
        )
        self.lbl_nama_sekarang.grid(row=2, column=0, sticky="w", padx=16, pady=(0, 12))

        prog_frame = ctk.CTkFrame(panel, fg_color="transparent")
        prog_frame.grid(row=1, column=0, sticky="ew", padx=16, pady=(4, 10))
        prog_frame.grid_columnconfigure(0, weight=1)
        info_row = ctk.CTkFrame(prog_frame, fg_color="transparent")
        info_row.grid(row=0, column=0, sticky="ew")
        info_row.grid_columnconfigure(0, weight=1)
        info_row.grid_columnconfigure(1, weight=1)
        self.lbl_progress_text = ctk.CTkLabel(
            info_row, text="0 / 0 data (0%)",
            font=ctk.CTkFont(size=13, weight="bold"), anchor="w",
        )
        self.lbl_progress_text.grid(row=0, column=0, sticky="w")
        self.lbl_eta = ctk.CTkLabel(
            info_row, text="Estimasi selesai: -",
            font=ctk.CTkFont(size=12), text_color="#9ca3af", anchor="e",
        )
        self.lbl_eta.grid(row=0, column=1, sticky="e")
        self.progressbar = ctk.CTkProgressBar(prog_frame, height=18, corner_radius=8)
        self.progressbar.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        self.progressbar.set(0)
        self.lbl_elapsed = ctk.CTkLabel(
            prog_frame, text="Berjalan: - · Rata-rata/data: -",
            font=ctk.CTkFont(size=11), text_color="#6b7280", anchor="w",
        )
        self.lbl_elapsed.grid(row=2, column=0, columnspan=2, sticky="w", pady=(6, 0))

        stat_frame = ctk.CTkFrame(panel, fg_color="transparent")
        stat_frame.grid(row=2, column=0, sticky="ew", padx=16, pady=(10, 16))
        stat_frame.grid_columnconfigure((0, 1, 2), weight=1)
        self.kartu_sukses, self.lbl_sukses = self._buat_kartu_statistik(
            stat_frame, "✅ Berhasil", WARNA_SUKSES, 0,
        )
        self.kartu_skip, self.lbl_skip = self._buat_kartu_statistik(
            stat_frame, "⏭️ Skip", WARNA_SKIP, 1,
        )
        self.kartu_gagal, self.lbl_gagal = self._buat_kartu_statistik(
            stat_frame, "❌ Gagal", WARNA_GAGAL, 2,
        )

        total_frame = ctk.CTkFrame(panel, fg_color="transparent")
        total_frame.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 16))
        self.lbl_total_excel = ctk.CTkLabel(
            total_frame,
            text="Total data di Excel: -  |  Sisa diproses: -",
            font=ctk.CTkFont(size=12), text_color="#9ca3af",
        )
        self.lbl_total_excel.pack(anchor="w")

        ket_frame = ctk.CTkFrame(panel, fg_color=WARNA_BG_CARD, corner_radius=10)
        ket_frame.grid(row=4, column=0, sticky="ew", padx=16, pady=(0, 16))
        ket_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            ket_frame, text="KETERANGAN TERAKHIR",
            font=ctk.CTkFont(size=11, weight="bold"), text_color="#9ca3af",
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(12, 0))
        self.lbl_keterangan_terakhir = ctk.CTkLabel(
            ket_frame, text="-", font=ctk.CTkFont(size=13),
            wraplength=420, justify="left", anchor="w",
        )
        self.lbl_keterangan_terakhir.grid(row=1, column=0, sticky="w", padx=16, pady=(2, 12))

    def _buat_kartu_statistik(self, parent, judul, warna, kolom):
        kartu = ctk.CTkFrame(parent, fg_color=WARNA_BG_CARD, corner_radius=10)
        kartu.grid(row=0, column=kolom, sticky="ew", padx=6)
        ctk.CTkLabel(
            kartu, text=judul, font=ctk.CTkFont(size=12, weight="bold"), text_color=warna,
        ).pack(pady=(14, 2))
        lbl_angka = ctk.CTkLabel(kartu, text="0", font=ctk.CTkFont(size=26, weight="bold"))
        lbl_angka.pack(pady=(0, 14))
        return kartu, lbl_angka

    def _build_panel_kanan(self, parent):
        panel = ctk.CTkFrame(parent, corner_radius=12)
        panel.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_rowconfigure(1, weight=1)
        header_row = ctk.CTkFrame(panel, fg_color="transparent")
        header_row.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 8))
        ctk.CTkLabel(
            header_row, text="📜 Log Aktivitas",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(side="left")
        ctk.CTkButton(
            header_row, text="💾 Simpan Log", width=120, height=28,
            font=ctk.CTkFont(size=12), command=self._simpan_log,
        ).pack(side="right")
        self.textbox_log = ctk.CTkTextbox(
            panel, font=ctk.CTkFont(size=11, family="Consolas"),
            wrap="word", corner_radius=10,
        )
        self.textbox_log.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))
        self.textbox_log.configure(state="disabled")

    # ── Aksi ──────────────────────────────────────────────────────────────
    def _pilih_file(self):
        path = filedialog.askopenfilename(
            title="Pilih file Excel data pangkalan",
            filetypes=[("Excel files", "*.xlsx *.xls"), ("Semua file", "*.*")],
        )
        if path:
            self.excel_path = path
            self.lbl_file.configure(text=path)

    def _mulai(self):
        username = self.entry_username.get().strip()
        password = self.entry_password.get().strip()

        if not username:
            messagebox.showerror("Input Tidak Lengkap", "Username tidak boleh kosong!")
            self.entry_username.focus()
            return
        if not password:
            messagebox.showerror("Input Tidak Lengkap", "Password tidak boleh kosong!")
            self.entry_password.focus()
            return

        path = self.excel_path or "data_pangkalan.xlsx"
        if not os.path.exists(path):
            messagebox.showerror(
                "File tidak ditemukan", f"File Excel tidak ditemukan:\n{path}"
            )
            return

        self.ctrl.stop_flag.clear()
        self.ctrl.pause_event.set()
        self._tambah_log(f"▶️  Memulai proses dengan file: {path}")
        self._tambah_log(f"👤 Login sebagai: {username}")

        # Kunci field agar tidak diubah saat proses berjalan
        self.entry_username.configure(state="disabled")
        self.entry_password.configure(state="disabled")
        self.btn_show_pass.configure(state="disabled")

        self.btn_mulai.configure(state="disabled")
        self.btn_pause.configure(state="normal", text="⏸  Pause", fg_color=WARNA_SKIP)
        self.btn_stop.configure(state="normal")

        self.worker_thread = threading.Thread(
            target=worker_proses,
            args=(self, path, username, password),
            daemon=True,
        )
        self.worker_thread.start()

    def _toggle_pause(self):
        if self.ctrl.pause_event.is_set():
            self.ctrl.pause_event.clear()
            self.btn_pause.configure(text="▶  Resume", fg_color=WARNA_AKSEN, hover_color="#2563eb")
            self._tambah_log("⏸️  Dijeda oleh pengguna. Klik Resume untuk melanjutkan.")
        else:
            self.ctrl.pause_event.set()
            self.btn_pause.configure(text="⏸  Pause", fg_color=WARNA_SKIP, hover_color="#d97706")
            self._tambah_log("▶️  Dilanjutkan.")

    def _stop(self):
        if not messagebox.askyesno(
            "Konfirmasi Stop",
            "Hentikan proses sekarang?\n\nProgres yang sudah tersimpan di Excel tidak akan hilang.",
        ):
            return
        self.ctrl.stop_flag.set()
        self.ctrl.pause_event.set()
        self._tambah_log("⏹️  Menghentikan proses... (menunggu langkah saat ini selesai)")
        self.btn_stop.configure(state="disabled")
        self.btn_pause.configure(state="disabled")

    def _poll_queue(self):
        try:
            while True:
                tipe, data = self.queue.get_nowait()
                self._handle_pesan(tipe, data)
        except queue.Empty:
            pass
        self.after(150, self._poll_queue)

    def _handle_pesan(self, tipe, data):
        if tipe == "log":
            self._tambah_log(data)
        elif tipe == "total":
            total_baris, total_sisa = data
            self.lbl_total_excel.configure(
                text=f"Total data di Excel: {total_baris}  |  Sisa diproses: {total_sisa}"
            )
        elif tipe == "current":
            n, total, id_reg = data
            self.lbl_id_sekarang.configure(text=id_reg)
            self.lbl_nama_sekarang.configure(text=f"Memproses data ke-{n} dari {total}...")
        elif tipe == "progress":
            self._update_progress(data)
        elif tipe == "status_pause":
            if data and not self.sedang_pause:
                self.sedang_pause = True
                self.lbl_nama_sekarang.configure(text="⏸️  Dijeda - klik Resume untuk melanjutkan")
            elif not data:
                self.sedang_pause = False
        elif tipe == "error":
            self._tambah_log(f"❌ ERROR: {data}")
            messagebox.showerror("Terjadi Kesalahan", str(data))
        elif tipe == "selesai":
            self._proses_selesai(data)

    def _update_progress(self, d):
        n, total = d["n"], d["total"]
        persen = n / total if total > 0 else 0
        self.progressbar.set(persen)
        self.lbl_progress_text.configure(text=f"{n} / {total} data ({persen*100:.1f}%)")
        self.lbl_sukses.configure(text=str(d["sukses"]))
        self.lbl_skip.configure(text=str(d["skip"]))
        self.lbl_gagal.configure(text=str(d["gagal"]))
        self.lbl_id_sekarang.configure(text=d["id_reg"])
        nama = d["nama_agen"] if d["nama_agen"] and d["nama_agen"] != "-" else "(nama tidak tersedia)"
        warna_status = {
            "Berhasil": WARNA_SUKSES, "Skip": WARNA_SKIP, "Gagal": WARNA_GAGAL,
        }.get(d["status"], "#9ca3af")
        self.lbl_nama_sekarang.configure(text=f"{nama}  ·  Status: {d['status']}")
        self.lbl_keterangan_terakhir.configure(text=d["keterangan"], text_color=warna_status)
        eta_text = format_durasi(d["eta_detik"])
        waktu_selesai = (datetime.now() + timedelta(seconds=d["eta_detik"])).strftime("%H:%M:%S")
        self.lbl_eta.configure(text=f"Estimasi sisa: {eta_text}  (≈ {waktu_selesai})")
        elapsed_text = format_durasi(d["elapsed_detik"])
        rata2 = d["elapsed_detik"] / n if n > 0 else 0
        self.lbl_elapsed.configure(
            text=f"Berjalan: {elapsed_text} · Rata-rata/data: {rata2:.1f} detik"
        )

    def _proses_selesai(self, data):
        self.btn_mulai.configure(state="normal")
        self.btn_pause.configure(state="disabled", text="⏸  Pause", fg_color=WARNA_SKIP)
        self.btn_stop.configure(state="disabled")
        self.lbl_nama_sekarang.configure(text="Proses berhenti / selesai.")
        # Buka kembali field login agar bisa login ulang / ganti akun
        self.entry_username.configure(state="normal")
        self.entry_password.configure(state="normal")
        self.btn_show_pass.configure(state="normal")
        if data:
            self._tambah_log(
                f"🏁 Ringkasan akhir sesi ini -> Sukses: {data['sukses']}, "
                f"Skip: {data['skip']}, Gagal: {data['gagal']}"
            )

    def _tambah_log(self, msg):
        self.textbox_log.configure(state="normal")
        waktu = datetime.now().strftime("%H:%M:%S")
        self.textbox_log.insert("end", f"[{waktu}] {msg}\n")
        self.textbox_log.see("end")
        self.textbox_log.configure(state="disabled")

    def _simpan_log(self):
        isi_log = self.textbox_log.get("1.0", "end-1c")
        if not isi_log.strip():
            messagebox.showinfo("Log Kosong", "Belum ada aktivitas log untuk disimpan.")
            return
        nama_default = f"log_aktivitas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        path = filedialog.asksaveasfilename(
            title="Simpan Log Aktivitas", initialfile=nama_default,
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("Semua file", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(isi_log)
            self._tambah_log(f"💾 Log aktivitas disimpan ke: {path}")
            messagebox.showinfo("Berhasil", f"Log aktivitas berhasil disimpan ke:\n{path}")
        except Exception as e:
            messagebox.showerror("Gagal Menyimpan", f"Gagal menyimpan log:\n{fmt_exc(e)}")


if __name__ == "__main__":
    app = App()
    app.mainloop()
