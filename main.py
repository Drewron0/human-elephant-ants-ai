import tkinter as tk
from gui import GameApp

class MainMenu(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("HE&A Launcher")
        self.geometry("300x400")
        self.configure(bg='#1E1E1E')
        
        tk.Label(self, text="Human Elephant Ant", font=("Arial", 16, "bold"), bg='#1E1E1E', fg='#FFF').pack(pady=30)
        
        tk.Button(self, text="PvE (vs AI)", width=20, command=lambda: self.launch('PvE')).pack(pady=10)
        tk.Button(self, text="PvP (Local)", width=20, command=lambda: self.launch('PvP')).pack(pady=10)
        tk.Button(self, text="Exit", width=20, command=self.destroy).pack(pady=10)

    def launch(self, mode):
        self.destroy()
        app = GameApp(mode=mode)
        app.mainloop()

if __name__ == "__main__":
    menu = MainMenu()
    menu.mainloop()