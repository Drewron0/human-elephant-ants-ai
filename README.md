# Chess-Sut: Human-Elephant-Ant AI Tactical Game

An adversarial tactical board game and AI research framework developed for the Artificial Intelligence course at Universitas Ciputra Surabaya (2026). The project implements an optimal defender AI agent for tactical puzzle scenarios using Minimax with Alpha-Beta Pruning, Move Ordering, Non-Transitive Cyclic Evaluation, and automated winnability verification.

---

## 1. Game Rules & Mechanics

Chess-Sut transforms the standard piece hierarchy of chess into an Indonesian folk-game cyclic dominance (*Gajah, Orang, Semut*):

- **Elephant (E)** defeats **Human (H)**
- **Human (H)** defeats **Ant (A)**
- **Ant (A)** defeats **Elephant (E)**

### Movement & Objectives
- Pieces move orthogonally (up, down, left, right) one step per turn into an adjacent empty square or to capture an enemy piece according to cyclic dominance.
- Pieces cannot capture enemies of the same type or their predator.
- **Victory Condition:** A player wins by navigating any piece to the opponent's starting corner (Player 1 targets top-right, Player 2 targets bottom-left).

---

## 2. Core Features

### Apple-Inspired Design System
- Built with restrained typography, high-contrast dark system palette (`#121214`, `#1C1C1E`, `#2C2C2E`), and subtle elevation.
- Fluid, interactive splitters (`tk.PanedWindow`) allowing users to resize the sidebars while the board dynamically scales to fit the container.

### Puzzle Mode & Optimal Defender AI
- **10 Preset 6x6 Stages:** Curated tactical scenarios with varying optimal solution lengths ($S_{optimal}$ from 5 to 9 steps) and maximum move limits ($S_{max} = 3 \times S_{optimal}$).
- **Procedural Winnable Puzzle Generator:** Generates custom random boards verified through a Breadth-First Search (BFS) safe-path solver to guarantee $100\%$ mathematical solvability.
- **Custom Stage Editor (Full CRUD):** Create, inspect, test winnability, save, and delete custom stages directly inside the visual canvas editor.
- **Stage Selection & Thumbnails:** Interactive catalog featuring live board thumbnail previews, AI difficulty mode selectors, player selection, and per-stage leaderboard tracking.
- **Spoiler Prevention Toggle:** Toggle search metrics display before playing to prevent move spoilers.

### Adversarial Search Architecture
- **Algorithm:** Minimax Search with Alpha-Beta Pruning, Leaf Node Evaluation, and Dynamic Move Ordering.
- **Non-Transitive Evaluation Function:** Dynamic piece weights computed from opponent's remaining suit distribution combined with corner distance Chebyshev/Manhattan heuristics.
- **Turn Time Guarantee:** Strict time check ensuring all AI moves return in under $2.0$ seconds ($T_{turn} \le 2.0$s).

---

## 3. Project Structure

```
├── ai_engine.py             # Minimax search, Alpha-Beta pruning, evaluation function
├── game_logic.py            # Board representation, state transitions, cyclic captures
├── gui.py                   # Master Tkinter application controller
├── main.py                  # Application entry point
├── network.py               # Local socket multiplayer server/client
├── puzzle_logic.py          # 10 6x6 stages, BFS safe path solver, random generator
├── run_benchmark.py         # Automated CLI benchmark runner for research metrics
├── storage.py               # JSON persistence for profiles, leaderboards, and custom stages
├── ui_theme.py              # Apple-inspired UI theme definitions, colors, and components
├── verify_stages.py         # Automated verification suite for stage winnability
├── tests/
│   └── test_game.py         # Unit test suite covering mechanics, AI, and CRUD
└── views/
    ├── benchmark_view.py    # GUI benchmarking and simulation lab
    ├── config_view.py       # Game setup and player preferences
    ├── game_view.py         # Standard match view with resizable paned layout
    ├── leaderboard_view.py  # Global and per-stage records
    ├── menu_view.py         # Main navigation hub
    ├── puzzle_game_view.py  # Puzzle gameplay view with real-time defender AI
    ├── puzzle_select_view.py# Stage selector with thumbnails, AI picker, & leaderboards
    ├── saves_view.py        # Match save/load manager
    ├── stage_editor_view.py # Interactive stage designer with instant BFS solver
    └── tutorial_view.py     # How-to-play interactive manual
```

---

## 4. Setup & Installation

### Requirements
- Python 3.8+ (Python 3.10+ recommended)
- Standard library dependencies (`tkinter`, `json`, `math`, `socket`, `threading`, `unittest`)

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
Validates that all 10 preset 6x6 stages and 20 procedurally generated random stages are 100% winnable:
```bash
python verify_stages.py
```

### Run Algorithmic Benchmark Simulation
Executes automated AI defender simulations across test positions to evaluate nodes generated, nodes evaluated, pruning efficiency, and execution time:
```bash
python run_benchmark.py
```

### Run Unit Tests
```bash
python -m unittest discover tests
```

---

## 6. Academic Team

- **Felix Richardo** (`frichardo@student.ciputra.ac.id`)
- **Vallerian Davyne Djunarko** (`vdjunarko@student.ciputra.ac.id`)
- **Aaron Hans Adiputra** (`aadiputra@student.ciputra.ac.id`)

*Universitas Ciputra Surabaya — 2026*
