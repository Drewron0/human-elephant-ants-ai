# Chess-Sut: Human-Elephant-Ant AI Tactical Game

An adversarial tactical board game and AI research framework developed for the Artificial Intelligence course at Universitas Ciputra Surabaya (2026). Puzzle mode defaults to proven exact defense. Practice and benchmark agents use depth-limited Minimax, Alpha-Beta Pruning, move ordering and non-transitive evaluation. Incomplete exact analysis is reported explicitly and never replaced with a guessed reply.

---

## 1. Game Rules and Mechanics

Chess-Sut transforms the standard piece hierarchy of chess into an Indonesian folk-game cyclic dominance (*Gajah, Orang, Semut*):

- **Elephant (E)** defeats **Human (H)**
- **Human (H)** defeats **Ant (A)**
- **Ant (A)** defeats **Elephant (E)**

### Movement and Objectives
- Pieces move one step in any of the eight adjacent directions, including diagonals, into an empty square or a permitted cyclic capture.
- Pieces cannot capture enemies of the same type or their predator.
- **Victory Condition:** A player wins by navigating any piece to the opponent's starting corner (Player 1 targets top-right, Player 2 targets bottom-left).

---

## 2. Core Features

### Modern Clean Dark Design System
- Built with restrained typography, high-contrast dark system palette (`#121214`, `#1C1C1E`, `#2C2C2E`), and subtle elevation.
- Fluid, interactive splitters (`tk.PanedWindow`) allowing users to resize sidebars while the board dynamically scales to fit the container.

### Tactical Stage Studio & Custom Stage Builder
- **Author-entered Minimum Steps:** The custom stage editor requires a positive whole-number minimum entered by the author. New stages start with a blank field; editing prefills the saved value. Saving and loading preserve this number exactly, without a search, verification button or proof prerequisite. The move limit remains three times the entered minimum.
- **Saved Stage Counts:** User-entered values are labeled `Minimum (user-entered)`, not claimed as algorithmically verified. Older stored counts remain available and editable. A stage without a valid count prompts the author to enter one before play. Saving an edit replaces obsolete automatic-verification metadata with the manual value.
- **Exact Puzzle Defender:** AI move selection remains separate from the manual minimum and cannot change it. The default model analyzes defensive replies exactly within the remaining game move limit, using existing valid cached replies when available. Analysis has the 120-second/3,000,000-node budget. If it is incomplete, the AI pauses with Retry/Undo/Reset available and never falls back to a shallow or random reply. Deliberately weaker practice baselines remain explicit choices, and benchmark agents are unchanged.
- **Recoverable Mistakes:** Losing the puzzle leaves its board and move history available for Undo or Reset. Each successful undo action is counted, including when it restores both the player's move and the AI's reply. Losing a predicted winning strategy does not immediately end play.
- **Custom Stages Only:** The puzzle menu loads stages created and saved by users. Create, edit, delete and play custom stages from one catalog with board thumbnails, AI selection and per-stage records. An empty catalog prompts the user to create a stage; Play stays disabled. Built-in presets, category tabs and random challenges have been removed, including their worker/cache/polling code and launch fallbacks.
- **Spoiler Prevention Toggle:** Toggle search metrics display before playing to prevent move spoilers.

### Adversarial Search Architecture
- **Algorithm:** Minimax Search with Alpha-Beta Pruning, Leaf Node Evaluation, and Dynamic Move Ordering.
- **Non-Transitive Evaluation Function:** Dynamic piece weights computed from opponent's remaining suit distribution combined with corner distance Chebyshev/Manhattan heuristics.
- **Practice/Benchmark Search Budget:** Optimized practice and benchmark search uses iterative deepening with a 1.95-second budget and a legal fallback. An interrupted iteration is discarded and the board is restored. Telemetry reports completed depth and timeouts; depth 6 and a hard wall-clock bound are not guaranteed on arbitrary hardware. The vanilla baseline has no time cutoff. Puzzle mode's default Exact Defender uses the proof solver described above instead.

---

## 3. Project Structure

```text
AFL2/
|-- ai_engine.py             # Minimax search, Alpha-Beta pruning, evaluation function
|-- game_logic.py            # Board representation, state transitions, cyclic captures
|-- gui.py                   # Master Tkinter application controller
|-- main.py                  # Application entry point
|-- puzzle_logic.py          # Custom-stage catalog, verification and benchmark simulations
|-- run_benchmark.py         # Automated CLI benchmark runner for research metrics
|-- storage.py               # JSON persistence for profiles, leaderboards, and custom stages
|-- ui_theme.py              # Dark theme definitions, colors, and components
|-- verify_stages.py         # Automated verification suite for stage winnability
|-- tests/
|   |-- test_game.py         # Unit test suite covering mechanics, AI, and CRUD
`-- views/
    |-- benchmark_view.py    # GUI benchmarking and simulation lab
    |-- config_view.py       # Game setup and player preferences
    |-- game_view.py         # Standard match view with resizable paned layout
    |-- leaderboard_view.py  # Global and per-stage records
    |-- menu_view.py         # Main navigation hub
    |-- puzzle_game_view.py  # Puzzle gameplay view with real-time defender AI
    |-- puzzle_select_view.py# Stage selector with thumbnails, AI picker, and leaderboards
    |-- stage_editor_view.py # Stage editor with author-entered minimum steps
    `-- tutorial_view.py     # How-to-play interactive manual
```

---

## 4. Setup and Installation

### Requirements
- Python 3.8+ (Python 3.10+ recommended)
- Standard library dependencies (`tkinter`, `json`, `math`, `threading`, `unittest`)
- Pillow for the Human, Elephant and Ant artwork on boards and previews

### Setup Instructions
1. Clone the repository:
   ```bash
   git clone https://github.com/Drewron0/human-elephant-ants-ai.git
   cd human-elephant-ants-ai
   ```
2. (Optional) Create and activate a virtual environment:
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # macOS / Linux
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

---

## 5. Running the Application

### Launch the GUI
```bash
python main.py
```

### Optional Offline Search Diagnostics
This developer utility reports bounded search results without changing saved author-entered minimums. It is not part of creating, saving or loading a stage. Exit codes: 0 = verified, 1 = no forced win within the horizon, 2 = verification budget exhausted. To check only benchmark puzzles:
```bash
python verify_stages.py
python verify_stages.py --generated-only
```

### Run Algorithmic Benchmark Simulation
The default runs **1,000 games for each of 12 combinations (12,000 games)**: optimized depth 6 and depth 3, vanilla depth 3, and random, each against shortest-path, sub-optimal, and random players. The GUI uses the same defaults and models; its full-table button respects the selected game count.

Every combination receives the same seeded random corpus of certified **10-step, 11x11 sparse race puzzles** (30-step limit). They form a deliberately restricted, cheaply provable family, not a representative sample of arbitrary tactical boards. The attacker needs at least 10 king-like moves; defenders cannot capture it or reach their own goal before its tenth move. This makes the 10-step baseline exact. Results should not be generalized to every puzzle distribution.

The shortest-path player replans an actual shortest legal route on the current frozen board. It does not predict future defender moves. The sub-optimal player chooses a different legal move with probability 25%. Player and defender random streams are separate and reproducible.
```bash
python run_benchmark.py
python run_benchmark.py --games 1 --seed 42 --output-dir benchmark_results_smoke
```

The full experiment can take substantial CPU time. `benchmark_results/` contains `corpus.json`, `results.csv`, and `turns.jsonl` (per-turn actions, evaluation scores, timings, visited/generated nodes, cutoff counts, completed depth, and timeout flags). Completed combinations are saved as they finish; rerunning into the same output directory replaces those reports. The CSV includes a corpus hash, seed, maximum latency, and full-depth completion rate. The GUI exports aggregate CSV results.

Pruning efficiency is `100 * skipped_children_at_alpha_beta_cutoffs / generated_children`, aggregated across turns and deepening iterations. It measures generated child opportunities, not the size of an unbuilt full tree. Timeouts are not pruning, and random and vanilla agents report zero. Delay margin is the mean signed `actual_steps - verified_optimum` over solved games; it is blank/N/A when no games are solved. Capturing the last defender does not end a puzzle: the player must still reach the corner.

### Run Unit Tests
```bash
python -m unittest discover tests
```
