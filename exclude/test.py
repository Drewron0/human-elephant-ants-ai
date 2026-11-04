from cProfile import label
import tkinter as tk
import time



def on_canvas_click(event):
    c = event.x // SQUARE_SIZE
    r = event.y // SQUARE_SIZE

    if 0 <= r < 4 and 0 <= c < 4:
        lbl_info.config(text=f"Klik di baris {r}, kolom {c}, | pixel x {event.x}, y {event.y}")
        draw_grid(selected=(r, c))
        
def draw_grid(selected=None):
    canvas.delete("all")
    for r in range(4):
        for c in range(4):
            x1 = c * SQUARE_SIZE
            y1 = r * SQUARE_SIZE
            x2 = x1 + SQUARE_SIZE
            y2 = y1 + SQUARE_SIZE

            fill_color = "#FFFFFF" if (r + c) % 2 == 0 else "#000000"

            if selected == (r, c):
                fill_color= "#FFFF00"

            canvas.create_rectangle(x1, y1, x2, y2, fill=fill_color, outline="#FF0000")
            canvas.create_text((x1 + x2)/2, (y1 + y2)/2, text=f"({r}, {c})", fill="#00FFFF", font=("Arial", 10))

SQUARE_SIZE = 70
root = tk.Tk()
root.title("Canvas Grid Math")
root.geometry("800x600")

lbl_info = tk.Label(root, text="Klik petak mana pun pada grid di bawah", font=("Segui UI", 10))
lbl_info.pack(pady=10)

canvas = tk.Canvas(root, width=4*SQUARE_SIZE, height=4*SQUARE_SIZE, bg="#121214", highlightthickness=0)
canvas.pack(padx=20, pady=10)
canvas.bind("<Button-1>", on_canvas_click)

draw_grid()
root.mainloop()