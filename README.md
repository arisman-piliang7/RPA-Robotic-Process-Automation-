# RPA – Aplikasi Web Automasi DDMS PT Pertamina Patra Niaga

> **Open Survey Pangkalan** – Otomatisasi proses pembukaan survey pangkalan LPG pada portal DDMS (Dealer/Distributor Management System) PT Pertamina Patra Niaga menggunakan Python + Selenium.

---

## Daftar Isi

- [Fitur](#fitur)
- [Prasyarat](#prasyarat)
- [Instalasi](#instalasi)
- [Konfigurasi](#konfigurasi)
- [Penggunaan](#penggunaan)
- [Struktur Proyek](#struktur-proyek)
- [Pengujian](#pengujian)
- [Output](#output)

---

## Fitur

- **Login otomatis** ke portal DDMS PT Pertamina Patra Niaga
- **Navigasi otomatis** ke menu Survey Pangkalan → Open Survey
- **Open survey massal** – memproses seluruh pangkalan di semua halaman
- **Open survey satuan** – proses satu pangkalan berdasarkan ID
- **Filter area/wilayah** untuk membatasi daftar pangkalan yang diproses
- **Laporan Excel & teks** hasil eksekusi (berhasil / gagal / dilewati)
- **Screenshot otomatis** saat terjadi error
- **Headless mode** – jalankan tanpa tampilan browser (cocok untuk server/cron)
- Mendukung **Chrome** dan **Firefox**

---

## Prasyarat

| Kebutuhan     | Versi Minimum |
|---------------|---------------|
| Python        | 3.9+          |
| Google Chrome | terbaru       |
| ChromeDriver  | dikelola otomatis oleh `webdriver-manager` |

---

## Instalasi

```bash
# 1. Clone repositori
git clone https://github.com/arisman-piliang7/RPA-Robotic-Process-Automation-.git
cd RPA-Robotic-Process-Automation-

# 2. Buat virtual environment (disarankan)
python -m venv .venv
source .venv/bin/activate          # Linux/macOS
.venv\Scripts\activate             # Windows

# 3. Install dependensi
pip install -r requirements.txt
```

---

## Konfigurasi

Salin file `.env.example` menjadi `.env`, lalu isi nilai yang sesuai:

```bash
cp .env.example .env
```

Edit file `.env`:

```dotenv
# URL portal DDMS
DDMS_URL=https://ddms.pertamina.com

# Kredensial login DDMS
DDMS_USERNAME=username_anda
DDMS_PASSWORD=password_anda

# Kode area untuk filter pangkalan (kosongkan jika semua area)
AREA_CODE=

# Browser: chrome atau firefox
BROWSER=chrome

# Headless mode: true / false
HEADLESS=false

# Batas waktu (detik)
IMPLICIT_WAIT=10
EXPLICIT_WAIT=30
PAGE_LOAD_TIMEOUT=60
```

> ⚠️ **Jangan pernah meng-commit file `.env`** ke repositori. File ini sudah didaftarkan di `.gitignore`.

---

## Penggunaan

```bash
# Proses semua pangkalan
python main.py

# Proses satu pangkalan (ID: 12345)
python main.py --id 12345

# Filter berdasarkan kode area
python main.py --area 0101

# Jalankan dalam mode headless (tanpa tampilan browser)
python main.py --headless

# Kombinasi: satu pangkalan + headless
python main.py --id 12345 --headless

# Gunakan Firefox
python main.py --browser firefox
```

---

## Struktur Proyek

```
RPA-Robotic-Process-Automation-/
├── main.py                          # Entry point utama
├── requirements.txt                 # Dependensi Python
├── .env.example                     # Template konfigurasi
├── .gitignore
│
├── src/
│   ├── config.py                    # Manajemen konfigurasi (.env)
│   ├── automation/
│   │   ├── base_page.py             # Kelas dasar Page Object
│   │   ├── login_page.py            # Halaman login DDMS
│   │   ├── survey_pangkalan_page.py # Halaman Open Survey Pangkalan
│   │   └── ddms_automation.py      # Orkestrator utama
│   └── utils/
│       ├── driver_factory.py        # Factory WebDriver (Chrome/Firefox)
│       ├── logger.py                # Konfigurasi logging
│       └── report_generator.py     # Generator laporan Excel & teks
│
├── tests/
│   ├── test_config_and_utils.py     # Unit test konfigurasi & utilitas
│   └── test_automation_pages.py    # Unit test halaman automasi
│
├── output/                          # Laporan hasil (diabaikan git)
└── logs/                            # File log eksekusi (diabaikan git)
```

---

## Pengujian

```bash
# Jalankan semua unit test
pytest tests/ -v

# Jalankan dengan laporan coverage
pytest tests/ -v --tb=short
```

> Unit test tidak memerlukan browser sungguhan – menggunakan mock WebDriver.

---

## Output

Setelah eksekusi selesai, laporan disimpan di direktori `output/`:

| File | Keterangan |
|------|------------|
| `laporan_open_survey_YYYYMMDD_HHMMSS.xlsx` | Laporan Excel dengan warna status |
| `laporan_open_survey_YYYYMMDD_HHMMSS.txt`  | Laporan teks ringkas |
| `screenshots/`                              | Screenshot saat terjadi error |

Log eksekusi tersimpan di direktori `logs/`:

| File | Keterangan |
|------|------------|
| `ddms_rpa_YYYYMMDD.log` | Log harian eksekusi automasi |

---

## Alur Automasi

```
[Mulai]
  │
  ▼
[Login DDMS] ──── gagal ──► [Error + Screenshot]
  │
  ▼
[Navigasi Menu Survey Pangkalan]
  │
  ▼
[Filter Area (jika dikonfigurasi)]
  │
  ▼
[Loop: Setiap Pangkalan di Setiap Halaman]
  │  ├─ Klik tombol "Open Survey"
  │  ├─ Konfirmasi dialog
  │  └─ Catat hasil (berhasil/gagal/dilewati)
  │
  ▼
[Simpan Laporan Excel & Teks]
  │
  ▼
[Selesai]
```

---

## Lisensi

Proyek ini dikembangkan untuk keperluan internal PT Pertamina Patra Niaga.
