# Chess-Sut

Game papan taktis berbasis AI untuk mata kuliah Artificial Intelligence. Permainan catur digabung dengan aturan suit Gajah, Orang, Semut.

## Ide Proyek

Bidak tidak punya tingkatan tetap. Setiap bidak mengalahkan satu jenis dan kalah dari satu jenis lain:

- Gajah mengalahkan Orang
- Orang mengalahkan Semut
- Semut mengalahkan Gajah

Setiap bidak bergerak satu kotak ke 8 arah. Pemain menang jika ada bidak yang mencapai sudut bintang lawan.

Karena nilai bidak berputar seperti ini, penilaian material biasa tidak cukup. AI memakai **Minimax dengan Alpha-Beta Pruning** dan fungsi evaluasi `E(s) = wm*M(s) + wc*C(s) + wp*P(s) + wt*T(s)`. Nilai bidak dihitung dinamis dari jumlah mangsa dan predator yang tersisa.

Mode yang tersedia:

- **Versus AI**: lawan komputer dengan pilihan tingkat kesulitan.
- **Tactical Puzzles**: tembus AI yang bertahan, termasuk Exact Defender yang hanya memakai langkah terbukti terbaik.
- **Stage Editor**: buat puzzle sendiri.
- **Simulation Lab**: bandingkan performa setiap agen AI.

## Library yang Digunakan

| Library | Kegunaan | Instalasi |
| --- | --- | --- |
| Python 3.10+ | Bahasa utama | Dari python.org |
| Tkinter | Antarmuka aplikasi | Sudah termasuk di Python |
| Pillow | Gambar bidak, papan, tombol, dan ikon | `pip install` (langkah 3) |

Library standar lain yang dipakai: `threading`, `json`, `logging`, `random`, `hashlib`.

## Cara Instalasi

**1. Pasang Python 3.10 atau lebih baru.** Unduh dari https://www.python.org/downloads/. Di Windows, centang **Add Python to PATH** saat instalasi. Pastikan versinya benar:

```bash
python --version
```

Di Linux, pasang Tkinter dulu:

```bash
sudo apt install python3-tk
```

**2. Masuk ke folder proyek.** Buka terminal, lalu pindah ke folder ini:

```bash
cd AFL2
```

**3. Buat virtual environment dan pasang library.**

Windows (Command Prompt):

```bash
python -m venv .venv
```

```bash
.venv\Scripts\activate
```

macOS atau Linux:

```bash
python3 -m venv .venv
```

```bash
source .venv/bin/activate
```

Lalu, di semua sistem operasi:

```bash
pip install -r requirements.txt
```

**4. Jalankan game.**

```bash
python main.py
```

Jendela game akan terbuka di menu utama.

## Perintah Tambahan

Menjalankan benchmark singkat lewat terminal:

```bash
python run_benchmark.py --games 1 --output-dir benchmark_results_smoke
```