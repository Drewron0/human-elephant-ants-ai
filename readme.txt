CHESS-SUT
=========

Game papan taktis berbasis AI untuk mata kuliah Artificial Intelligence.
Permainan catur digabung dengan aturan suit Gajah, Orang, Semut.


IDE PROYEK
----------
Bidak tidak punya tingkatan tetap. Setiap bidak mengalahkan satu jenis dan
kalah dari satu jenis lain:

  - Gajah mengalahkan Orang
  - Orang mengalahkan Semut
  - Semut mengalahkan Gajah

Setiap bidak bergerak satu kotak ke 8 arah. Pemain menang jika ada bidak yang
mencapai sudut bintang lawan.

AI memakai Minimax dengan Alpha-Beta Pruning. Nilai bidak dihitung dinamis dari
jumlah mangsa dan predator yang tersisa, dengan fungsi evaluasi:

  E(s) = wm*M(s) + wc*C(s) + wp*P(s) + wt*T(s)

Mode yang tersedia:

  - Versus AI        : lawan komputer dengan pilihan tingkat kesulitan
  - Tactical Puzzles : tembus AI yang bertahan
  - Stage Editor     : buat puzzle sendiri
  - Simulation Lab   : bandingkan performa setiap agen AI


LIBRARY YANG DIGUNAKAN
----------------------
  - Python 3.10 atau lebih baru : bahasa utama (dari python.org)
  - Tkinter                     : antarmuka, sudah termasuk di Python
  - Pillow                      : gambar bidak, papan, tombol, dan ikon


CARA INSTALASI
--------------
1. Pasang Python 3.10 atau lebih baru dari https://www.python.org/downloads/
   Di Windows, centang "Add Python to PATH" saat instalasi.
   Pastikan versinya benar:

     python --version

   Di Linux, pasang Tkinter dulu:

     sudo apt install python3-tk

2. Buka terminal dan masuk ke folder proyek:

     cd AFL2

3. Buat virtual environment.

   Windows (Command Prompt):

     python -m venv .venv
     .venv\Scripts\activate

   macOS atau Linux:

     python3 -m venv .venv
     source .venv/bin/activate

4. Pasang library:

     pip install -r requirements.txt

5. Jalankan game:

     python main.py

   Jendela game akan terbuka di menu utama.


CATATAN
-------
Tidak ada variabel lingkungan yang wajib diisi. Pengaturan opsional ada di
.env.example, dan semua parameter game ada di config/settings.py.
