import tkinter as tk
from ui_theme import THEME, FONT_NAME, ButtonPrimary, ButtonSecondary, ButtonDanger
import storage


class SavedGamesView(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=THEME['bg'])
        self.app = app
        self._build_ui()

    def _build_ui(self):
        container = tk.Frame(self, bg=THEME['bg'])
        container.pack(fill=tk.BOTH, expand=True, padx=40, pady=24)

        header = tk.Frame(container, bg=THEME['bg'])
        header.pack(fill=tk.X, pady=(0, 16))

        tk.Label(
            header,
            text="Saved Game Slots (PvE Mid-Game)",
            font=(FONT_NAME, 18, "bold"),
            bg=THEME['bg'],
            fg=THEME['text']
        ).pack(side=tk.LEFT)

        ButtonSecondary(header, text="Back to Hub", command=lambda: self.app.show_view('menu')).pack(side=tk.RIGHT)

        self.slots_container = tk.Frame(container, bg=THEME['bg'])
        self.slots_container.pack(fill=tk.BOTH, expand=True)

        self._refresh_slots()

    def _refresh_slots(self):
        for w in self.slots_container.winfo_children():
            w.destroy()

        saves = storage.get_saved_slots()

        for slot_num in range(1, 6):
            slot_id = f"slot_{slot_num}"
            data = saves.get(slot_id)

            card = tk.Frame(
                self.slots_container,
                bg=THEME['surface'],
                bd=1,
                relief=tk.SOLID,
                highlightbackground=THEME['border'],
                highlightthickness=1,
                padx=18,
                pady=10
            )
            card.pack(fill=tk.X, pady=4)

            left_box = tk.Frame(card, bg=THEME['surface'])
            left_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

            if data:
                cfg = data.get('config', {})
                state_data = data.get('state', {})
                diff = cfg.get('difficulty', 'Normal').capitalize()
                turns = state_data.get('total_turns', 0)
                t_str = data.get('timestamp', '')

                tk.Label(
                    left_box,
                    text=f"Slot {slot_num}: PvE Match ({diff})",
                    font=(FONT_NAME, 11, "bold"),
                    bg=THEME['surface'],
                    fg=THEME['accent']
                ).pack(anchor="w")

                detail_text = f"Saved: {t_str} | Turns: {turns} | Undos: {state_data.get('undos_p1', state_data.get('undos', 0))}"
                tk.Label(
                    left_box,
                    text=detail_text,
                    font=(FONT_NAME, 9),
                    bg=THEME['surface'],
                    fg=THEME['text_muted']
                ).pack(anchor="w", pady=(2, 0))

                right_box = tk.Frame(card, bg=THEME['surface'])
                right_box.pack(side=tk.RIGHT)

                def make_load_cmd(s_data=data):
                    self.app.start_game(s_data['config'], saved_state=s_data)

                def make_del_cmd(s_id=slot_id):
                    storage.delete_game_slot(s_id)
                    self._refresh_slots()

                ButtonDanger(right_box, text="Delete Slot", command=make_del_cmd, padx=10, pady=4).pack(side=tk.LEFT, padx=4)
                ButtonPrimary(right_box, text="Load Game", command=make_load_cmd, padx=14, pady=4).pack(side=tk.RIGHT)
            else:
                tk.Label(
                    left_box,
                    text=f"Slot {slot_num}: [Empty Save Slot]",
                    font=(FONT_NAME, 10, "italic"),
                    bg=THEME['surface'],
                    fg=THEME['text_muted']
                ).pack(anchor="w")
