"""
03_generate.py — Step 3: Generate Soal Baru via Claude API
===========================================================
Membaca dataset acuan terbaru dari data/dataset_referensi/
Menggunakan soal asli sebagai few-shot examples
Output: /data/soal_baru/soal_YYYY-MM-DD.json
"""

import os
import json
import anthropic
from pathlib import Path
from datetime import datetime

# ── Konfigurasi ───────────────────────────────────────────────────────────────
INPUT_DIR  = Path("data/dataset_referensi")
OUTPUT_DIR = Path("data/soal_baru")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Berapa soal baru yang di-generate per jenis soal per run
JUMLAH_SOAL_PER_JENIS = 5

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

PROMPT_GENERATE = """
Kamu adalah pembuat soal UTBK/SNBT profesional.

Berikut adalah contoh soal referensi dari database:
{contoh_soal}

---
Berdasarkan contoh di atas, buatkan {jumlah} soal BARU yang:
1. Topik dan jenis soal sama: {jenis_soal} — {sub_topik}
2. Tingkat kesulitan: {tingkat_kesulitan}
3. Soal baru, TIDAK meniru soal referensi secara langsung
4. Semua rumus matematika menggunakan format LaTeX ($...$ atau $$...$$)
5. Jika soal membutuhkan gambar/ilustrasi, deskripsikan dengan: [PERLU_GAMBAR: deskripsi detail dalam bahasa Inggris untuk prompt Gemini]
6. Setiap soal harus memiliki pembahasan langkah demi langkah yang lengkap

Output WAJIB berupa JSON array (tanpa markdown, langsung JSON):
[
  {{
    "nomor": 1,
    "teks_soal": "...",
    "pilihan_jawaban": {{
      "A": "...",
      "B": "...",
      "C": "...",
      "D": "...",
      "E": "..."
    }},
    "kunci_jawaban": "A",
    "pembahasan": "Langkah 1: ...\\nLangkah 2: ...\\nJadi jawaban adalah A karena ...",
    "jenis_soal": "{jenis_soal}",
    "sub_topik": "{sub_topik}",
    "tingkat_kesulitan": "{tingkat_kesulitan}",
    "ada_gambar": false,
    "prompt_gambar_gemini": null
  }}
]
"""

# ── Fungsi ────────────────────────────────────────────────────────────────────

def ambil_dataset_terbaru() -> dict | None:
    """Ambil file dataset acuan yang paling baru"""
    files = sorted(INPUT_DIR.glob("dataset_*.json"), reverse=True)
    if not files:
        return None
    with open(files[0], "r", encoding="utf-8") as f:
        return json.load(f)


def kelompokkan_soal(dataset: dict) -> dict:
    """Kelompokkan soal berdasarkan jenis dan sub-topik"""
    kelompok = {}
    for soal in dataset.get("soal", []):
        jenis = soal.get("jenis_soal", "TPS")
        sub   = soal.get("sub_topik", "Umum")
        key   = f"{jenis}||{sub}"
        if key not in kelompok:
            kelompok[key] = []
        kelompok[key].append(soal)
    return kelompok


def format_contoh_soal(soal_list: list[dict], max_contoh: int = 3) -> str:
    """Format soal referensi menjadi string untuk few-shot prompt"""
    contoh = soal_list[:max_contoh]
    hasil = []
    for s in contoh:
        teks = f"Soal: {s.get('teks_soal', '')}\n"
        pj = s.get("pilihan_jawaban", {})
        for k, v in pj.items():
            teks += f"{k}) {v}\n"
        teks += f"Jawaban: {s.get('kunci_jawaban', '?')}"
        hasil.append(teks)
    return "\n\n---\n\n".join(hasil)


def generate_soal_baru(jenis: str, sub_topik: str, tingkat: str,
                       contoh_soal_str: str) -> list[dict]:
    """Panggil Claude untuk generate soal baru"""
    prompt = PROMPT_GENERATE.format(
        contoh_soal=contoh_soal_str,
        jumlah=JUMLAH_SOAL_PER_JENIS,
        jenis_soal=jenis,
        sub_topik=sub_topik,
        tingkat_kesulitan=tingkat
    )

    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=8192,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = message.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    try:
        soal_list = json.loads(raw)
        for soal in soal_list:
            soal["waktu_generate"] = datetime.now().isoformat()
            soal["status"] = "generated"
        return soal_list
    except json.JSONDecodeError as e:
        print(f"  ⚠️  Gagal parse JSON: {e}")
        return []


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  Step 3: Generate Soal Baru via Claude")
    print("=" * 60)

    dataset = ambil_dataset_terbaru()
    if not dataset:
        print("\n⚠️  Tidak ada dataset acuan. Jalankan Step 2 dulu.")
        return

    total_referensi = dataset.get("total_soal", 0)
    print(f"\n📚 Dataset acuan: {total_referensi} soal referensi.\n")

    kelompok = kelompokkan_soal(dataset)
    print(f"📂 Ditemukan {len(kelompok)} kelompok topik.\n")

    semua_soal_baru = []
    total_baru = 0

    for key, soal_list in kelompok.items():
        jenis, sub_topik = key.split("||")

        # Tentukan tingkat kesulitan berdasarkan komposisi referensi
        tingkat_counts = {}
        for s in soal_list:
            t = s.get("tingkat_kesulitan", "sedang")
            tingkat_counts[t] = tingkat_counts.get(t, 0) + 1
        tingkat = max(tingkat_counts, key=tingkat_counts.get)

        print(f"  🎯 Generate: [{jenis}] {sub_topik} (kesulitan: {tingkat})")
        contoh_str = format_contoh_soal(soal_list)

        soal_baru = generate_soal_baru(jenis, sub_topik, tingkat, contoh_str)

        if soal_baru:
            semua_soal_baru.extend(soal_baru)
            total_baru += len(soal_baru)
            print(f"     ✅ {len(soal_baru)} soal baru di-generate.")
        else:
            print(f"     ❌ Gagal generate untuk topik ini.")

    if not semua_soal_baru:
        print("\n❌ Tidak ada soal baru yang berhasil di-generate.")
        return

    # Simpan output
    tanggal = datetime.now().strftime("%Y-%m-%d")
    output_path = OUTPUT_DIR / f"soal_{tanggal}.json"

    output = {
        "tanggal_generate": datetime.now().isoformat(),
        "total_soal_baru": total_baru,
        "soal": semua_soal_baru
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"  ✅ Step 3 Selesai — {total_baru} soal baru berhasil di-generate.")
    print(f"  💾 Tersimpan: {output_path}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
