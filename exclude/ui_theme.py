import tkinter as tk

class ModernButton(tk.Button):
    def __init__(self, parent, text, bg_normal, bg_hover, command=None):
        super().__init__(
            parent,
            text=text,
            command=command,
            bg=bg_normal,
            fg="#FFFFFF",
            activebackground=bg_hover,
            activeforeground="#FFFFFF",
            font=("Segoi UI", 10, "bold"),
            relief=tk.FLAT,
            bd=0,
            padx=16,
            pady=8,
            cursor="hand2"
        )

        self.bg_normal = bg_normal
        self.bg_hover = bg_hover

        self.bind("<Enter>", lambda e: self.configure(bg=self.bg_hover))
        self.bind("<Leave>", lambda e: self.configure(bg=self.bg_normal))

root = tk.Tk()
root.configure(bg="#121314")

ModernButton(root, text="Primer", bg_normal="#00B1B2", bg_hover="#006666").pack(pady=20)

root.mainloop