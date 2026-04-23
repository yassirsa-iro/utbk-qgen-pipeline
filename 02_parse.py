"""
02_parse.py — Step 2: Parsing & Tagging Soal → Dataset Acuan
=============================================================
Membaca semua file JSON dari data/raw_extracted/
Menggunakan Claude untuk parsing struktur soal dan tagging metadata
Output: /data/dataset_referensi/dataset_YYYY-MM-DD.json
"""

import os
import json
import anthropic
from pathlib import Path
from datetime import datetime

# ── Konfigurasi Path ──────────────────────────────────────────────────────────
INPUT_DIR  = Path("data/raw_extracted")
OUTPUT_DIR = Path("data/dataset_referensi")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Client Anthropic ──────────────────────────────────────────────────────────
client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

PROMPT_PARSE = """
Kamu adalah sistem analisis soal UTBK/SNBT yang sangat teliti.

Diberikan teks hasil ekstraksi soal di bawah ini. Tugasmu:
1. Identifikasi dan pisahkan setiap butir soal.
2. Tentukan metadata setiap soal.
3. Kembalikan hasilnya sebagai JSON array yang valid.

Format output WAJIB berupa JSON array seperti ini (tanpa markdown, langsung JSON):
[
  {
    "nomor": 1,
    "teks_soal": "Isi soal lengkap dengan LaTeX jika ada rumus",
    "pilihan_jawaban": {
      "A": "pilihan A",
      "B": "pilihan B",
      "C": "pilihan C",
      "D": "pilihan D",
      "E": "pilihan E"
    },
    "kunci_jawaban": "A",
    "jenis_soal": "TPS|TKA_Saintek|TKA_Soshum",
    "sub_topik": "contoh: Penalaran Umum / Matematika / Fisika / Biologi / Kimia / Ekonomi / Geografi / Sejarah / dll",
    "tingkat_kesulitan": "mudah|sedang|sulit",
    "ada_gambar": false,
    "deskripsi_gambar": null,
    "ada_rumus_latex": false,
    "catatan": "catatan tambahan jika ada (atau null)"
  }
]

Jika kunci jawaban tidak ditemukan dalam teks, isi dengan null.
Jika soal tidak berbentuk pilihan ganda, tetap strukturkan sebaik mungkin.
PENTING: Output hanya JSON array, tidak ada teks pengantar apapun.

Teks soal:
"""

# ── Fungsi Parsing ────────────────────────────────────────────────────────────

def parse_soal(teks_mentah: str, file_asal: str) -> list[dict]:
    """Kirim teks ke Claude untuk diparse menjadi struktur soal"""
    print(f"  → Mengirim ke Claude untuk parsing...")

    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=8192,
        messages=[
            {
                "role": "user",
                "content": PROMPT_PARSE + teks_mentah
            }
        ]
    )

    raw_response = message.content[0].text.strip()

    # Bersihkan jika ada markdown code block
    if raw_response.startswith("```"):
        raw_response = raw_response.split("```")[1]
        if raw_response.startswith("json"):
            raw_response = raw_response[4:]

    try:
        soal_list = json.loads(raw_response)
        # Tambahkan metadata sumber
        for soal in soal_list:
            soal["file_asal"] = file_asal
            soal["waktu_parsing"] = datetime.now().isoformat()
        return soal_list
    except json.JSONDecodeError as e:
        print(f"  ⚠️  Gagal parse JSON dari Claude: {e}")
        print(f"  Raw response (100 char pertama): {raw_response[:100]}")
        return []


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  Step 2: Parsing & Tagging Soal")
    print("=" * 60)

    json_files = list(INPUT_DIR.glob("*.json"))

    if not json_files:
        print("\n⚠️  Tidak ada file di data/raw_extracted/. Jalankan Step 1 dulu.")
        return

    print(f"\n📂 Ditemukan {len(json_files)} file untuk di-parse.\n")

    semua_soal = []
    total_soal = 0

    for json_file in json_files:
        print(f"\n📋 File: {json_file.name}")

        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        teks = data.get("teks_mentah", "")
        if not teks.strip():
            print("  ⚠️  Teks kosong, dilewati.")
            continue

        soal_list = parse_soal(teks, data.get("file_asal", json_file.name))

        if soal_list:
            semua_soal.extend(soal_list)
            total_soal += len(soal_list)
            print(f"  ✅ Berhasil parse {len(soal_list)} soal.")
        else:
            print(f"  ❌ Gagal parse soal dari file ini.")

    if not semua_soal:
        print("\n❌ Tidak ada soal yang berhasil di-parse.")
        return

    # Simpan dataset acuan
    tanggal = datetime.now().strftime("%Y-%m-%d")
    output_path = OUTPUT_DIR / f"dataset_{tanggal}.json"

    dataset = {
        "tanggal_dibuat": datetime.now().isoformat(),
        "total_soal": total_soal,
        "soal": semua_soal
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)

    # Rekap per jenis soal
    rekap = {}
    for soal in semua_soal:
        jenis = soal.get("jenis_soal", "Tidak diketahui")
        rekap[jenis] = rekap.get(jenis, 0) + 1

    print(f"\n{'='*60}")
    print(f"  ✅ Step 2 Selesai — {total_soal} soal berhasil di-parse.")
    print(f"  📊 Rekap per jenis:")
    for jenis, jumlah in rekap.items():
        print(f"     • {jenis}: {jumlah} soal")
    print(f"  💾 Tersimpan: {output_path}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
