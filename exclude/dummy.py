import tkinter as tk

# 1. Aturan & Definisi Sut
BEATS = {'H': 'A', 'A': 'E', 'E': 'H'}

class SimplePiece:
    def __init__(self, owner, p_type):
        self.owner = owner      # 0 = Hijau, 1 = Merah
        self.p_type = p_type

board_size = 6
sq_size = 65
target_corners = {0: (0, 5), 1: (5, 0)}  # P1 target di kanan-atas, P2 target di kiri-bawah

# Inisialisasi papan 6x6
board = [[None for _ in range(board_size)] for _ in range(board_size)]
board[5][0] = SimplePiece(0, 'H')  # P1 Orang
board[5][1] = SimplePiece(0, 'E')  # P1 Gajah
board[4][0] = SimplePiece(0, 'A')  # P1 Semut

board[0][5] = SimplePiece(1, 'H')  # P2 Orang
board[0][4] = SimplePiece(1, 'E')  # P2 Gajah
board[1][5] = SimplePiece(1, 'A')  # P2 Semut

current_turn = 0
selected_sq = None
valid_targets = []
winner = None

def get_valid_moves(r, c):
    p = board[r][c]
    if not p: return []
    moves = []
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0: continue
            nr, nc = r + dr, c + dc
            if 0 <= nr < board_size and 0 <= nc < board_size:
                target = board[nr][nc]
                if target is None:
                    moves.append((nr, nc))
                elif target.owner != p.owner and BEATS.get(p.p_type) == target.p_type:
                    moves.append((nr, nc))
    return moves

root = tk.Tk()
root.title("Chess-Sut: Local PvP Arena")

lbl_status = tk.Label(root, text="Giliran: Player 1 (Hijau)", font=("Segoe UI", 12, "bold"))
lbl_status.pack(pady=8)

canvas = tk.Canvas(root, width=board_size * sq_size, height=board_size * sq_size, bg="#121214")
canvas.pack()

def draw():
    canvas.delete("all")
    for r in range(board_size):
        for c in range(board_size):
            x0, y0 = c * sq_size, r * sq_size
            x1, y1 = x0 + sq_size, y0 + sq_size

            # Pola dasar catur
            col = "#E5E5EA" if (r + c) % 2 == 0 else "#AEAEB2"

            # Sorotan sudut target
            if (r, c) == target_corners[0]: col = "#FFE082"
            if (r, c) == target_corners[1]: col = "#FFCDD2"

            # Sorotan petak yang sedang dipilih (Kuning Terang)
            if selected_sq == (r, c):
                col = "#FFF59D"

            # Sorotan petak tangkap musuh (Merah Terang)
            if (r, c) in valid_targets and board[r][c] is not None:
                col = "#FF453A"

            canvas.create_rectangle(x0, y0, x1, y1, fill=col, outline="#636366")

            # Titik hitam pada petak kosong legal
            if (r, c) in valid_targets and board[r][c] is None:
                cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
                canvas.create_oval(cx - 6, cy - 6, cx + 6, cy + 6, fill="#1C1C1E", outline="")

            # Gambar Bidak
            p = board[r][c]
            if p:
                p_col = "#2ECC71" if p.owner == 0 else "#E74C3C"
                pad = 8
                # Drop shadow
                canvas.create_oval(x0 + pad + 1, y0 + pad + 2, x1 - pad + 1, y1 - pad + 2, fill="#151515", outline="")
                # Token bodi
                canvas.create_oval(x0 + pad, y0 + pad, x1 - pad, y1 - pad, fill=p_col, outline="#FFFFFF", width=2)
                # Monogram huruf
                cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
                canvas.create_text(cx, cy, text=p.p_type, font=("Segoe UI", 12, "bold"), fill="#FFFFFF")

def on_click(event):
    global selected_sq, valid_targets, current_turn, winner
    if winner is not None: return

    c = event.x // sq_size
    r = event.y // sq_size
    if not (0 <= r < board_size and 0 <= c < board_size): return

    if selected_sq:
        # FSM Transisi 1: Klik petak legal -> Pindahkan bidak!
        if (r, c) in valid_targets:
            sr, sc = selected_sq
            moving_p = board[sr][sc]
            board[sr][sc] = None
            board[r][c] = moving_p
            selected_sq = None
            valid_targets = []

            # Cek Kemenangan Sudut
            if (r, c) == target_corners[current_turn]:
                winner = current_turn
                lbl_status.config(text=f"PLAYER {winner + 1} MENANG! (Sudut Tercapai)", fg="#FF9F0A")
                draw()
                return

            # Ganti giliran
            current_turn = 1 - current_turn
            p_name = "Player 1 (Hijau)" if current_turn == 0 else "Player 2 (Merah)"
            lbl_status.config(text=f"Giliran: {p_name}")
        else:
            # FSM Transisi 2: Klik bidak kawan yang lain
            p = board[r][c]
            if p and p.owner == current_turn:
                selected_sq = (r, c)
                valid_targets = get_valid_moves(r, c)
            else:
                # FSM Transisi 3: Klik petak kosong/ilegal -> Batalkan seleksi
                selected_sq = None
                valid_targets = []
        draw()
    else:
        # FSM Transisi Awal: Pilih bidak milik pemain aktif
        p = board[r][c]
        if p and p.owner == current_turn:
            selected_sq = (r, c)
            valid_targets = get_valid_moves(r, c)
            draw()

canvas.bind("<Button-1>", on_click)
draw()
root.mainloop()






root = tk.Tk()
root.title("Chess Clock Asinkron")
root.geometry("300x180")

time_p1 = 60
time_p2 = 60
current_turn = 0
timer_job = None

lbl_p1 = tk.Label(root, text="P1: 01:00", font=("Segoe UI", 16, "bold"), fg="#2ECC71")
lbl_p1.pack(pady=8)

lbl_p2 = tk.Label(root, text="P2: 01:00", font=("Segoe UI", 16, "bold"), fg="#8E8E93")
lbl_p2.pack(pady=8)

def format_time(sec):
    return f"{sec // 60:02d}:{sec % 60:02d}"

def tick():
    global time_p1, time_p2, timer_job
    if current_turn == 0:
        time_p1 -= 1
        lbl_p1.config(text=f"P1: {format_time(time_p1)}")
        if time_p1 <= 0:
            print("WAKTU P1 HABIS! P2 MENANG!")
            return
    else:
        time_p2 -= 1
        lbl_p2.config(text=f"P2: {format_time(time_p2)}")
        if time_p2 <= 0:
            print("WAKTU P2 HABIS! P1 MENANG!")
            return

    # Jadwalkan detak berikutnya 1 detik (1000 ms) ke depan:
    timer_job = root.after(1000, tick)

def switch_turn():
    global current_turn
    current_turn = 1 - current_turn
    if current_turn == 0:
        lbl_p1.config(fg="#2ECC71")
        lbl_p2.config(fg="#8E8E93")
    else:
        lbl_p2.config(fg="#E74C3C")
        lbl_p1.config(fg="#8E8E93")

btn_switch = tk.Button(root, text="Tekan untuk Tukar Giliran", command=switch_turn)
btn_switch.pack(pady=10)

# Mulai detak jam:
timer_job = root.after(1000, tick)
root.mainloop()