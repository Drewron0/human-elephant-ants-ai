# Chess-Sut: Tactical Board Game with Adversarial AI

> **Artificial Intelligence (AFL2) Project - Semester 5**  
>  
> **Team Members:**  
> - Felix Richardo (0706012410058)  
> - Vallerian Davyne Djunarko (0706012410038)  
> - Aaron Hans Adiputra (0706012410059)  

---

## 1. Project Overview

**Chess-Sut** is a turn-based tactical board game that blends traditional chess mechanics with the non-transitive Indonesian "Sut" hand game (Elephant, Human, Ant).

### Core Game Rules:
- **Cyclic Capture System (Rock-Paper-Scissors):**
  - **Elephant (`E`)** captures **Human (`H`)**
  - **Human (`H`)** captures **Ant (`A`)**
  - **Ant (`A`)** captures **Elephant (`E`)**
- **Movement:** Any piece can move exactly 1 square in all 8 directions (orthogonal and diagonal) into an empty tile or to capture an enemy piece according to the Sut cycle. Pieces of the same type cannot capture each other and act as blockers.
- **Winning Condition:** A player wins by successfully moving any piece onto the opponent's star corner (target coordinate).

---

## 2. Artificial Intelligence Architecture

Because piece values are non-transitive (cyclic), standard static piece valuations (like standard chess point systems) fail. The AI evaluates positions dynamically using **Minimax with Alpha-Beta Pruning** and a specialized heuristic evaluation function:

$$E(s) = w_m \cdot M(s) + w_c \cdot C(s) + w_p \cdot P(s) + w_t \cdot T(s)$$

- **$M(s)$ (Dynamic Material Value):** Calculates each piece's current worth dynamically based on the remaining prey and predators alive on the board.
- **$C(s)$ (Center Control):** Rewards positioning pieces in central board squares to maximize board dominance.
- **$P(s)$ (Piece Advancement & Threat):** Measures board pressure and tactical offensive positioning.
- **$T(s)$ (Target Corner Proximity):** Uses Chebyshev distance to reward moves advancing toward the winning goal corner.

### AI Opponents & Difficulty Levels:
- **Easy:** Evaluates surface moves with occasional random mistakes.
- **Normal:** Minimax search with Alpha-Beta pruning (depth 2).
- **Hard:** Minimax search with Alpha-Beta pruning (depth 3).
- **Optimized Alpha-Beta (d=6):** Deep horizon search with move ordering heuristics (MVV-LVA) and transposition hashing.

---

## 3. Game Modes

1. **Versus AI:** Play single-player matches against configurable AI difficulty levels and customizable board options.
2. **Tactical Puzzles:** Curated endgame scenarios where the player must breach a defending AI within strict move constraints.
3. **Stage Editor:** Visual interactive editor to create, test, and save custom puzzle setups.
4. **Leaderboard:** Local record keeping for puzzle step counts and match histories.

---

## 4. Requirements & Installation

### Prerequisites:
- Python 3.10 or newer (ensure Python is added to your system `PATH`)
- `tkinter` (bundled with Python on Windows/macOS; on Linux: `sudo apt install python3-tk`)

### Setup:
1. Navigate to the project directory:
   ```bash
   cd AFL2
   ```

2. (Optional but recommended) Create and activate a virtual environment:
   - **Windows:**
     ```cmd
     python -m venv .venv
     .venv\Scripts\activate
     ```
   - **macOS / Linux:**
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```

3. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

---

## 5. Running the Application

Launch the desktop game interface:
```bash
python main.py
```
This opens the desktop interface with the main menu, navigation hub, and all gameplay modes.

---

## 6. Project Structure

```
AFL2/
├── config/
│   └── settings.py          # Centralized configuration, layouts, and evaluation weights
├── src/
│   ├── core/
│   │   └── game_logic.py    # Game state, board representation, and movement rules
│   ├── ai/
│   │   ├── agents.py        # AI agent registry and specifications
│   │   ├── evaluation.py    # Non-transitive heuristic evaluation functions
│   │   ├── search.py        # Minimax and Alpha-Beta search implementations
│   │   ├── practice.py      # Versus-AI gameplay opponent logic
│   │   └── exact_defender.py# Defense engine for puzzles
│   ├── puzzle/
│   │   ├── scenario.py      # Puzzle stage definitions and attempt session tracking
│   │   └── solver.py        # Solver for puzzle solutions and winnable paths
│   ├── storage.py           # JSON persistence for records and custom stages
│   └── ui/
│       ├── app.py           # Main window application controller
│       ├── theme.py         # Color palette, metrics, and styling configuration
│       ├── art.py           # Pillow image rendering for tokens, board, and icons
│       ├── widgets.py       # Custom UI buttons, inputs, and cards
│       ├── board.py         # Canvas-based game board layer
│       └── views/           # Screen views (menu, game, puzzles, editor)
├── assets/                  # High-resolution piece illustrations (gajah, orang, semut)
├── requirements.txt         # Project dependencies
├── pyproject.toml           # Package metadata
└── main.py                  # Application entry point
```
