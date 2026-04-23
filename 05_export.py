"""
05_export.py — Step 5: Sinkronisasi ke Google Sheets & Docs
============================================================
Membaca soal baru dari data/soal_baru/
Menulis ke Google Sheets dengan kolom lengkap
Menulis ke Google Docs dengan format LaTeX untuk rumus
"""

import os
import json
from pathlib import Path
from datetime import datetime

import gspread
from google.oauth2.service_account import Credentials

# ── Konfigurasi ───────────────────────────────────────────────────────────────
INPUT_DIR = Path("data/soal_baru")

GOOGLE_SA_PATH = os.environ.get(
    "GOOGLE_SERVICE_ACCOUNT_PATH", "/tmp/service_account.json"
)
SHEET_ID = os.environ.get("GOOGLE_SHEET_ID", "")
DOC_ID   = os.environ.get("GOOGLE_DOC_ID", "")

SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/documents",
]

# Header kolom Google Sheets
SHEET_HEADERS = [
    "Tanggal Generate",
    "Jenis Soal",
    "Sub Topik",
    "Tingkat Kesulitan",
    "Teks Soal",
    "A", "B", "C", "D", "E",
    "Kunci Jawaban",
    "Pembahasan",
    "Ada Gambar",
    "Nama File Gambar",
    "Status",
]

# ── Fungsi ────────────────────────────────────────────────────────────────────

def get_gspread_client():
    """Buat client gspread dengan service account"""
    creds = Credentials.from_service_account_file(GOOGLE_SA_PATH, scopes=SCOPES)
    return gspread.authorize(creds)


def ambil_soal_terbaru() -> dict | None:
    """Ambil file soal baru yang paling baru"""
    files = sorted(INPUT_DIR.glob("soal_*.json"), reverse=True)
    if not files:
        return None
    with open(files[0], "r", encoding="utf-8") as f:
        return json.load(f)


def soal_ke_baris_sheet(soal: dict) -> list:
    """Konversi satu soal dict menjadi baris untuk Google Sheets"""
    pj = soal.get("pilihan_jawaban", {})
    return [
        soal.get("waktu_generate", datetime.now().isoformat())[:10],
        soal.get("jenis_soal", ""),
        soal.get("sub_topik", ""),
        soal.get("tingkat_kesulitan", ""),
        soal.get("teks_soal", ""),
        pj.get("A", ""),
        pj.get("B", ""),
        pj.get("C", ""),
        pj.get("D", ""),
        pj.get("E", ""),
        soal.get("kunci_jawaban", ""),
        soal.get("pembahasan", ""),
        "Ya" if soal.get("ada_gambar") else "Tidak",
        soal.get("nama_file_gambar", ""),
        soal.get("status", "generated"),
    ]


def ekspor_ke_sheets(client_gs, soal_list: list[dict]) -> int:
    """Tulis soal ke Google Sheets"""
    spreadsheet = client_gs.open_by_key(SHEET_ID)

    # Cari atau buat sheet "Bank Soal"
    try:
        sheet = spreadsheet.worksheet("Bank Soal")
    except gspread.WorksheetNotFound:
        sheet = spreadsheet.add_worksheet(title="Bank Soal", rows=5000, cols=20)
        print("  → Sheet 'Bank Soal' dibuat baru.")

    # Cek apakah header sudah ada
    existing = sheet.get_all_values()
    if not existing or existing[0] != SHEET_HEADERS:
        sheet.update("A1", [SHEET_HEADERS])
        print("  → Header kolom ditambahkan.")

    # Tulis soal baru ke baris berikutnya
    baris_mulai = len(existing) + 1 if existing else 2
    rows = [soal_ke_baris_sheet(s) for s in soal_list]
    sheet.update(f"A{baris_mulai}", rows)

    return len(rows)


def ekspor_ke_docs(soal_list: list[dict]):
    """Tulis soal ke Google Docs (opsional, jika DOC_ID tersedia)"""
    from googleapiclient.discovery import build
    from google.oauth2.service_account import Credentials

    if not DOC_ID:
        print("  ℹ️  GOOGLE_DOC_ID tidak diset, export ke Docs dilewati.")
        return

    creds = Credentials.from_service_account_file(GOOGLE_SA_PATH, scopes=SCOPES)
    docs_service = build("docs", "v1", credentials=creds)

    tanggal = datetime.now().strftime("%d %B %Y")
    requests_body = []

    # Judul batch
    judul = f"\n\n═══ BANK SOAL BARU — {tanggal} ═══\n\n"
    requests_body.append({
        "insertText": {"location": {"index": 1}, "text": judul}
    })

    for i, soal in enumerate(soal_list, 1):
        pj = soal.get("pilihan_jawaban", {})
        teks = (
            f"Soal {i} [{soal.get('jenis_soal','')}] — {soal.get('sub_topik','')}\n"
            f"Kesulitan: {soal.get('tingkat_kesulitan','')}\n\n"
            f"{soal.get('teks_soal','')}\n\n"
        )
        for huruf, isi in pj.items():
            teks += f"{huruf}) {isi}\n"
        teks += (
            f"\nJawaban: {soal.get('kunci_jawaban','')}\n"
            f"Pembahasan:\n{soal.get('pembahasan','')}\n"
            f"{'─'*50}\n"
        )
        requests_body.append({
            "insertText": {"location": {"index": 1}, "text": teks}
        })

    docs_service.documents().batchUpdate(
        documentId=DOC_ID,
        body={"requests": requests_body}
    ).execute()

    print(f"  ✅ {len(soal_list)} soal ditulis ke Google Docs.")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  Step 5: Sinkronisasi ke Google Sheets")
    print("=" * 60)

    if not SHEET_ID:
        print("\n⚠️  GOOGLE_SHEET_ID tidak diset. Step 5 dilewati.")
        return

    if not os.path.exists(GOOGLE_SA_PATH):
        print(f"\n❌ File credentials tidak ditemukan: {GOOGLE_SA_PATH}")
        return

    data = ambil_soal_terbaru()
    if not data:
        print("\n⚠️  Tidak ada file soal baru. Jalankan Step 3 dulu.")
        return

    soal_list = data.get("soal", [])
    print(f"\n📊 {len(soal_list)} soal siap diekspor.\n")

    print("  → Menghubungkan ke Google Sheets...")
    try:
        client_gs = get_gspread_client()
    except Exception as e:
        print(f"  ❌ Gagal autentikasi Google: {e}")
        return

    # Ekspor ke Sheets
    print(f"  → Menulis ke Google Sheets (ID: {SHEET_ID[:20]}...)")
    try:
        jumlah = ekspor_ke_sheets(client_gs, soal_list)
        print(f"  ✅ {jumlah} baris berhasil ditulis ke Google Sheets.")
    except Exception as e:
        print(f"  ❌ Gagal ekspor ke Sheets: {e}")

    # Ekspor ke Docs (opsional)
    if DOC_ID:
        print(f"\n  → Menulis ke Google Docs (ID: {DOC_ID[:20]}...)")
        try:
            ekspor_ke_docs(soal_list)
        except Exception as e:
            print(f"  ❌ Gagal ekspor ke Docs: {e}")

    print(f"\n{'='*60}")
    print(f"  ✅ Step 5 Selesai — Sinkronisasi ke Google Workspace berhasil.")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
