CHESS-SUT: TACTICAL BOARD GAME WITH ADVERSARIAL AI
===================================================

Artificial Intelligence (AFL2) Project - Semester 5

Team Members:
  - Felix Richardo (0706012410058)
  - Vallerian Davyne Djunarko (0706012410038)
  - Aaron Hans Adiputra (0706012410059)


1. PROJECT OVERVIEW
-------------------
Chess-Sut is a tactical board game that blends chess-like grid movement with
the traditional Indonesian "Sut" mechanic (Elephant, Human, Ant).

Piece capture rules:
  - Elephant captures Human
  - Human captures Ant
  - Ant captures Elephant

Every piece moves one square in any of the 8 directions (orthogonal and diagonal).
A player wins immediately when any of their pieces reaches the opponent's
target star corner.


2. ARTIFICIAL INTELLIGENCE
--------------------------
Because piece values are non-transitive (cyclic), static piece valuations are
insufficient. The AI implements Minimax with Alpha-Beta Pruning and a dynamic
evaluation function:

  E(s) = wm*M(s) + wc*C(s) + wp*P(s) + wt*T(s)

Where:
  - M(s): Dynamic material value based on active prey and predator counts
  - C(s): Control over center board squares
  - P(s): Piece mobility and forward advancement
  - T(s): Proximity to the goal corner (Chebyshev distance)


3. GAME MODES
-------------
  - Versus AI        : Single player match against Easy, Normal, Hard, or Alpha-Beta
  - Tactical Puzzles : Endgame challenges to breach defensive agents
  - Stage Editor     : Interactive tool to design and save custom puzzle stages
  - Leaderboard      : Local record keeping for puzzle step counts and match histories


4. INSTALLATION & SETUP
-----------------------
1. Ensure Python 3.10 or newer is installed:
     python --version

2. Navigate to the project directory:
     cd AFL2

3. (Optional) Create and activate a virtual environment:
     Windows:
       python -m venv .venv
       .venv\Scripts\activate

     macOS/Linux:
       python3 -m venv .venv
       source .venv/bin/activate

4. Install dependencies:
     pip install -r requirements.txt

5. Run the game:
     python main.py
