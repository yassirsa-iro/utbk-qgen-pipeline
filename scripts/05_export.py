"""
05_export.py — Step 5: Sinkronisasi ke Google Sheets & Docs
============================================================
- Google Sheets : satu sheet "Bank Soal" dengan semua soal
- Google Docs   : tab terpisah per jenis soal + sub topik
                  Contoh tab: "TPS · Penalaran Umum"
                              "TKA · Matematika"
                              "TKA · Fisika"
"""

import os
import json
import time
from pathlib import Path
from datetime import datetime

import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

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

SHEET_HEADERS = [
    "Tanggal Generate", "Jenis Soal", "Sub Topik", "Tingkat Kesulitan",
    "Teks Soal", "A", "B", "C", "D", "E",
    "Kunci Jawaban", "Pembahasan", "Ada Gambar", "Nama File Gambar", "Status",
]

# ── Helpers ───────────────────────────────────────────────────────────────────

def get_creds():
    return Credentials.from_service_account_file(GOOGLE_SA_PATH, scopes=SCOPES)

def ambil_soal_terbaru():
    files = sorted(INPUT_DIR.glob("soal_*.json"), reverse=True)
    if not files:
        return None
    with open(files[0], "r", encoding="utf-8") as f:
        return json.load(f)

def kelompokkan_soal(soal_list):
    """Kelompokkan soal: { "TPS · Penalaran Umum": [soal, ...], ... }"""
    kelompok = {}
    for soal in soal_list:
        jenis = soal.get("jenis_soal", "Umum").strip()
        sub   = soal.get("sub_topik", "Umum").strip()
        key   = f"{jenis} \u00b7 {sub}"
        kelompok.setdefault(key, []).append(soal)
    return kelompok

# ── Google Sheets ─────────────────────────────────────────────────────────────

def soal_ke_baris(soal):
    pj = soal.get("pilihan_jawaban", {})
    return [
        soal.get("waktu_generate", datetime.now().isoformat())[:10],
        soal.get("jenis_soal", ""),
        soal.get("sub_topik", ""),
        soal.get("tingkat_kesulitan", ""),
        soal.get("teks_soal", ""),
        pj.get("A", ""), pj.get("B", ""), pj.get("C", ""),
        pj.get("D", ""), pj.get("E", ""),
        soal.get("kunci_jawaban", ""),
        soal.get("pembahasan", ""),
        "Ya" if soal.get("ada_gambar") else "Tidak",
        soal.get("nama_file_gambar", ""),
        soal.get("status", "generated"),
    ]

def ekspor_ke_sheets(soal_list):
    creds  = get_creds()
    client = gspread.authorize(creds)
    ss     = client.open_by_key(SHEET_ID)

    try:
        sheet = ss.worksheet("Bank Soal")
    except gspread.WorksheetNotFound:
        sheet = ss.add_worksheet(title="Bank Soal", rows=5000, cols=20)
        print("  -> Sheet 'Bank Soal' dibuat baru.")

    existing = sheet.get_all_values()
    if not existing or existing[0] != SHEET_HEADERS:
        sheet.update("A1", [SHEET_HEADERS])
        existing = [SHEET_HEADERS]

    baris_mulai = len(existing) + 1
    rows = [soal_ke_baris(s) for s in soal_list]
    sheet.update(f"A{baris_mulai}", rows)
    return len(rows)

# ── Google Docs — Tab helpers ─────────────────────────────────────────────────

def get_existing_tabs(docs_service):
    """Return { tab_title: tab_id } dari semua tab yang sudah ada."""
    doc = docs_service.documents().get(
        documentId=DOC_ID,
        includeTabsContent=False
    ).execute()
    result = {}
    for tab in doc.get("tabs", []):
        props = tab.get("tabProperties", {})
        result[props.get("title", "")] = props.get("tabId", "")
    return result

def buat_tab(docs_service, judul):
    """Buat tab baru, return tabId-nya."""
    resp = docs_service.documents().batchUpdate(
        documentId=DOC_ID,
        body={"requests": [{"createTab": {"tabProperties": {"title": judul}}}]}
    ).execute()
    for reply in resp.get("replies", []):
        tab_id = reply.get("createTab", {}).get("tabProperties", {}).get("tabId")
        if tab_id:
            return tab_id
    return ""

def format_isi_tab(judul_tab, soal_list, tanggal):
    """Buat teks lengkap untuk satu tab."""
    sep  = "=" * 55
    sep2 = "-" * 50
    baris = [
        sep,
        f"  {judul_tab}",
        f"  Diperbarui : {tanggal}",
        f"  Total soal : {len(soal_list)}",
        sep + "\n",
    ]
    for i, soal in enumerate(soal_list, 1):
        pj        = soal.get("pilihan_jawaban", {})
        kesulitan = soal.get("tingkat_kesulitan", "-").upper()
        baris += [
            f"SOAL {i}  [{kesulitan}]",
            sep2,
            soal.get("teks_soal", ""),
            "",
        ]
        for huruf in ["A", "B", "C", "D", "E"]:
            isi = pj.get(huruf, "")
            if isi:
                baris.append(f"  {huruf})  {isi}")
        baris += [
            "",
            f"  Jawaban     : {soal.get('kunci_jawaban', '?')}",
            "",
            "  Pembahasan  :",
        ]
        for ln in soal.get("pembahasan", "").splitlines():
            baris.append(f"  {ln}")
        baris.append("\n" + sep2 + "\n")
    return "\n".join(baris)

def tulis_ke_tab(docs_service, tab_id, teks):
    """Hapus isi lama tab, lalu tulis teks baru."""
    doc = docs_service.documents().get(
        documentId=DOC_ID,
        includeTabsContent=True
    ).execute()

    end_index = 1
    for tab in doc.get("tabs", []):
        if tab.get("tabProperties", {}).get("tabId") == tab_id:
            content = tab.get("documentTab", {}).get("body", {}).get("content", [])
            if content:
                end_index = content[-1].get("endIndex", 1) - 1
            break

    requests = []
    if end_index > 1:
        requests.append({
            "deleteContentRange": {
                "range": {"tabId": tab_id, "startIndex": 1, "endIndex": end_index}
            }
        })
    requests.append({
        "insertText": {
            "location": {"tabId": tab_id, "index": 1},
            "text": teks
        }
    })

    docs_service.documents().batchUpdate(
        documentId=DOC_ID,
        body={"requests": requests}
    ).execute()

# ── Google Docs — Main ────────────────────────────────────────────────────────

def ekspor_ke_docs(soal_list):
    if not DOC_ID:
        print("  Info: GOOGLE_DOC_ID tidak diset, export ke Docs dilewati.")
        return

    creds        = get_creds()
    docs_service = build("docs", "v1", credentials=creds)
    tanggal      = datetime.now().strftime("%d %B %Y %H:%M")

    kelompok      = kelompokkan_soal(soal_list)
    existing_tabs = get_existing_tabs(docs_service)

    print(f"  -> {len(kelompok)} tab akan dibuat/diperbarui.")
    print(f"  -> Tab yang sudah ada: {list(existing_tabs.keys()) or 'tidak ada'}")

    for judul_tab, soal_grup in kelompok.items():
        print(f"  -> Tab '{judul_tab}' ({len(soal_grup)} soal)...")

        if judul_tab not in existing_tabs:
            tab_id = buat_tab(docs_service, judul_tab)
            time.sleep(1)
        else:
            tab_id = existing_tabs[judul_tab]

        if not tab_id:
            print(f"     Gagal mendapat tab_id, dilewati.")
            continue

        isi = format_isi_tab(judul_tab, soal_grup, tanggal)
        tulis_ke_tab(docs_service, tab_id, isi)
        print(f"     OK.")
        time.sleep(0.5)

    print(f"  {len(kelompok)} tab berhasil ditulis ke Google Docs.")

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  Step 5: Sinkronisasi ke Google Sheets & Docs")
    print("=" * 60)

    if not SHEET_ID:
        print("\nGoogle Sheet ID tidak diset. Step 5 dilewati.")
        return

    if not os.path.exists(GOOGLE_SA_PATH):
        print(f"\nFile credentials tidak ditemukan: {GOOGLE_SA_PATH}")
        return

    data = ambil_soal_terbaru()
    if not data:
        print("\nTidak ada file soal baru. Jalankan Step 3 dulu.")
        return

    soal_list = data.get("soal", [])
    print(f"\n{len(soal_list)} soal siap diekspor.\n")

    print("  -> Menulis ke Google Sheets...")
    try:
        jumlah = ekspor_ke_sheets(soal_list)
        print(f"  {jumlah} baris ditulis ke Google Sheets.")
    except Exception as e:
        print(f"  Gagal ekspor ke Sheets: {e}")

    if DOC_ID:
        print("\n  -> Menulis ke Google Docs (tab per topik)...")
        try:
            ekspor_ke_docs(soal_list)
        except Exception as e:
            print(f"  Gagal ekspor ke Docs: {e}")
            import traceback; traceback.print_exc()

    print(f"\n{'='*60}")
    print(f"  Step 5 Selesai.")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
