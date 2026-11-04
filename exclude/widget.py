
board_size = 6
target_corners = {
    0: (0, board_size - 1),  # Sudut kanan-atas untuk Player 0
    1: (board_size - 1, 0)   # Sudut kiri-bawah untuk Player 1
}

# Simulasi state sederhana:
board = [[None for _ in range(board_size)] for _ in range(board_size)]
current_turn = 0
winner = None

# Player 0 memiliki Human di (1, 4), hanya 1 langkah dari target sudut (0, 5)!
board[1][4] = {'owner': 0, 'type': 'H'}

def make_move(start, end):
    global current_turn, winner
    r1, c1 = start
    r2, c2 = end
    p = board[r1][c1]

    # Mutasi posisi di papan
    board[r1][c1] = None
    board[r2][c2] = p

    # Cek Kondisi 1: Apakah bidak menyentuh sudut target?
    if (r2, c2) == target_corners[current_turn]:
        winner = current_turn
        print(f"[VICTORY!] Player {current_turn} MENANG via Invasi Sudut Target di {end}!")
        return

    # Ganti giliran jalan: 0 -> 1 atau 1 -> 0
    current_turn = 1 - current_turn

print("Posisi awal: Bidak di (1, 4), target di (0, 5)")
make_move((1, 4), (0, 5))
print("Pemenang:", winner)