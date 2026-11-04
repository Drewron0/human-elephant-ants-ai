# Chess-Sut: Human-Elephant-Ant AI Tactical Game

An adversarial tactical board game and AI research framework developed for the Artificial Intelligence course at Universitas Ciputra Surabaya (2026). The defender uses depth-limited Minimax with Alpha-Beta Pruning, move ordering, and non-transitive evaluation. Bounded puzzle verification reports uncertainty explicitly; the playing agent is not a proof of globally optimal defense.

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
- **Puzzle Minimum Steps:** BFS finds the shortest legal route for each player piece through the starting board, then selects the shortest. Other pieces stay fixed for this calculation; friendly pieces and non-capturable enemies block squares, while prey can be captured. Preset and loaded custom stages recompute their minimum and route instead of trusting stored counts. The move limit is three times the calculated minimum. Actual AI replies can change the route during play.
- **Custom Stage Editor:** Verify checks for a legal route with the other pieces fixed, displays its exact minimum, and requires a route before saving. Stages without a route show `No route` and cannot be started. This static route is not a forced-win proof. The separate `verify_puzzle()` adversarial verifier remains available for benchmark certification.
- **Procedural Winnability Generator:** Certified sparse race puzzles, generated in background threads. A single attacker can capture every defender, and geometric distance proves its earliest corner arrival precedes the defender's earliest win. Different sizes provide different exact step counts.
- **Stage Selection and Thumbnails:** Interactive catalog featuring live board thumbnail previews, AI difficulty mode selectors, player selection, and per-stage leaderboard tracking.
- **Spoiler Prevention Toggle:** Toggle search metrics display before playing to prevent move spoilers.

### Adversarial Search Architecture
- **Algorithm:** Minimax Search with Alpha-Beta Pruning, Leaf Node Evaluation, and Dynamic Move Ordering.
- **Non-Transitive Evaluation Function:** Dynamic piece weights computed from opponent's remaining suit distribution combined with corner distance Chebyshev/Manhattan heuristics.
- **Search Budget:** Optimized search uses iterative deepening with a 1.95-second budget and a legal fallback. An interrupted iteration is discarded and the board is restored. Telemetry reports completed depth and timeouts; depth 6 and a hard wall-clock bound are not guaranteed on arbitrary hardware. The vanilla baseline has no time cutoff.

---

## 3. Project Structure

```text
AFL2/
|-- ai_engine.py             # Minimax search, Alpha-Beta pruning, evaluation function
|-- game_logic.py            # Board representation, state transitions, cyclic captures
|-- gui.py                   # Master Tkinter application controller
|-- main.py                  # Application entry point
|-- puzzle_logic.py          # 10 6x6 stages, BFS safe path solver, random generator
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
    |-- stage_editor_view.py # Interactive stage designer with instant BFS solver
    `-- tutorial_view.py     # How-to-play interactive manual
```

---

## 4. Setup and Installation

### Requirements
- Python 3.8+ (Python 3.10+ recommended)
- Standard library dependencies (`tkinter`, `json`, `math`, `threading`, `unittest`)

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
3. Install optional dependencies:
   ```bash
   pip install -r requirements.txt
   ```

---

## 5. Running the Application

### Launch the GUI
```bash
python main.py
```

### Run Stage Winnability Verification
Reports exact bounded verification for legacy boards and 20 generated benchmark puzzles. Exit codes: 0 = verified, 1 = no forced win within the horizon, 2 = verification budget exhausted. To check only generated puzzles:
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
