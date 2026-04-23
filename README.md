# 📚 UTBK QGen Pipeline

Pipeline otomatis untuk membuat bank soal UTBK/TKA/TPS menggunakan AI.

## 🗺️ Arsitektur

```
input_raw/          ← Upload PDF / Word / PNG soal di sini
     ↓  (GitHub Actions: otomatis setiap push atau tiap hari)
scripts/
  01_extract.py     ← Ekstraksi teks + OCR (rumus → LaTeX)
  02_parse.py       ← Parsing & tagging soal → dataset acuan JSON
  03_generate.py    ← Generator soal baru via Claude API
  04_image.py       ← Generate gambar via Gemini API (jika diperlukan)
  05_export.py      ← Sinkronisasi output ke Google Sheets / Docs
     ↓
data/
  raw_extracted/    ← Teks mentah hasil ekstraksi (.json)
  dataset_referensi/← Dataset acuan terstruktur (.json)
  soal_baru/        ← Soal baru lengkap (soal + jawaban + pembahasan)
output_gambar/      ← Gambar hasil generate Gemini
output/             ← Export akhir (PDF / Markdown)
```

## ⚙️ Setup

### 1. Clone repo ini
```bash
git clone https://github.com/USERNAME/utbk-qgen-pipeline.git
cd utbk-qgen-pipeline
```

### 2. Tambahkan API Keys ke GitHub Secrets
Buka: **Settings → Secrets and variables → Actions → New repository secret**

| Secret Name             | Keterangan                              |
|-------------------------|-----------------------------------------|
| `ANTHROPIC_API_KEY`     | API Key Claude (claude.ai / Anthropic)  |
| `GEMINI_API_KEY`        | API Key Google Gemini (untuk gambar)    |
| `GOOGLE_SERVICE_ACCOUNT`| JSON credentials Google Service Account |
| `GOOGLE_SHEET_ID`       | ID Google Spreadsheet tujuan output     |
| `GOOGLE_DOC_ID`         | ID Google Doc tujuan output (opsional)  |

### 3. Install dependensi lokal (untuk testing)
```bash
pip install -r requirements.txt
```

## 🚀 Cara Pakai

1. Taruh file soal (PDF/Word/PNG) ke folder `input_raw/`
2. `git add . && git commit -m "add: soal baru" && git push`
3. GitHub Actions akan otomatis berjalan dan memproses semuanya
4. Cek Google Sheets-mu — soal baru sudah tersinkronisasi!

Pipeline juga berjalan otomatis setiap hari pukul **02.00 WIB**.

## 📁 Struktur Folder

| Folder | Fungsi |
|--------|--------|
| `input_raw/` | Tempat upload soal mentah |
| `data/raw_extracted/` | Hasil ekstraksi teks |
| `data/dataset_referensi/` | Dataset acuan terstruktur |
| `data/soal_baru/` | Bank soal baru hasil generate AI |
| `output_gambar/` | Gambar hasil Gemini |
| `output/` | Ekspor akhir |
| `scripts/` | Semua skrip Python pipeline |
| `.github/workflows/` | Konfigurasi GitHub Actions |
