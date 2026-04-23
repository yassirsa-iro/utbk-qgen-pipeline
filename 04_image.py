"""
04_image.py — Step 4: Generate Gambar via Gemini API
=====================================================
Membaca soal baru yang membutuhkan gambar (ada prompt_gambar_gemini)
Memanggil Gemini Imagen untuk generate gambar
Menyimpan gambar ke output_gambar/ dan memperbarui JSON soal
"""

import os
import json
import base64
import requests
from pathlib import Path
from datetime import datetime

# ── Konfigurasi ───────────────────────────────────────────────────────────────
INPUT_DIR   = Path("data/soal_baru")
OUTPUT_DIR  = Path("output_gambar")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# Gemini Imagen API endpoint
IMAGEN_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "imagen-3.0-generate-002:predict"
)

# ── Fungsi ────────────────────────────────────────────────────────────────────

def ambil_soal_terbaru() -> tuple[Path, dict] | tuple[None, None]:
    """Ambil file soal baru yang paling baru"""
    files = sorted(INPUT_DIR.glob("soal_*.json"), reverse=True)
    if not files:
        return None, None
    path = files[0]
    with open(path, "r", encoding="utf-8") as f:
        return path, json.load(f)


def generate_gambar(prompt: str, nama_file: str) -> str | None:
    """Panggil Gemini Imagen untuk generate gambar, return path gambar"""
    payload = {
        "instances": [{"prompt": prompt}],
        "parameters": {
            "sampleCount": 1,
            "aspectRatio": "4:3",
            "safetyFilterLevel": "block_some",
        }
    }

    headers = {"Content-Type": "application/json"}
    url = f"{IMAGEN_URL}?key={GEMINI_API_KEY}"

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=60)
        response.raise_for_status()
        result = response.json()

        # Ambil base64 image dari response
        predictions = result.get("predictions", [])
        if not predictions:
            print("  ⚠️  Gemini tidak mengembalikan gambar.")
            return None

        img_b64 = predictions[0].get("bytesBase64Encoded", "")
        if not img_b64:
            print("  ⚠️  Data gambar kosong.")
            return None

        # Simpan gambar
        img_path = OUTPUT_DIR / nama_file
        with open(img_path, "wb") as f:
            f.write(base64.b64decode(img_b64))

        print(f"  ✅ Gambar tersimpan: {img_path}")
        return str(img_path)

    except requests.exceptions.RequestException as e:
        print(f"  ❌ Error Gemini API: {e}")
        return None


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  Step 4: Generate Gambar via Gemini")
    print("=" * 60)

    if not GEMINI_API_KEY:
        print("\n⚠️  GEMINI_API_KEY tidak ditemukan. Step 4 dilewati.")
        return

    soal_path, data = ambil_soal_terbaru()
    if not data:
        print("\n⚠️  Tidak ada file soal baru. Jalankan Step 3 dulu.")
        return

    soal_list = data.get("soal", [])
    soal_butuh_gambar = [
        (i, s) for i, s in enumerate(soal_list)
        if s.get("ada_gambar") and s.get("prompt_gambar_gemini")
    ]

    if not soal_butuh_gambar:
        print("\n✅ Tidak ada soal yang membutuhkan gambar. Step 4 selesai.")
        return

    print(f"\n🖼️  Ditemukan {len(soal_butuh_gambar)} soal yang butuh gambar.\n")

    tanggal = datetime.now().strftime("%Y%m%d")
    total_berhasil = 0

    for idx, (soal_index, soal) in enumerate(soal_butuh_gambar, 1):
        prompt = soal.get("prompt_gambar_gemini", "")
        jenis  = soal.get("jenis_soal", "soal").replace("/", "_").replace(" ", "_")
        sub    = soal.get("sub_topik", "umum").replace(" ", "_")[:20]
        nama_file = f"{tanggal}_{jenis}_{sub}_{idx:03d}.png"

        print(f"  🎨 [{idx}/{len(soal_butuh_gambar)}] Generating gambar untuk soal {soal_index + 1}...")
        print(f"     Prompt: {prompt[:80]}...")

        img_path = generate_gambar(prompt, nama_file)

        if img_path:
            # Update data soal dengan path gambar
            soal_list[soal_index]["path_gambar"] = img_path
            soal_list[soal_index]["nama_file_gambar"] = nama_file
            total_berhasil += 1

    # Simpan ulang JSON soal yang sudah diperbarui
    data["soal"] = soal_list
    data["tanggal_update_gambar"] = datetime.now().isoformat()

    with open(soal_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"  ✅ Step 4 Selesai — {total_berhasil}/{len(soal_butuh_gambar)} gambar berhasil di-generate.")
    print(f"  💾 Data soal diperbarui: {soal_path}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
