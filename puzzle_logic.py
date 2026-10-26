import random
import time
from collections import deque
from typing import List, Tuple, Dict, Any, Optional
from game_logic import GameState, Piece, BEATS, PREDATORS


def bfs_safe_path(board_size: int, pieces: List[Tuple[int, int, int, str]],
                  start_coord: Tuple[int, int], target_coord: Tuple[int, int],
                  player_type: str = 'H') -> Tuple[Optional[int], List[Tuple[int, int]]]:
    """
    Computes the shortest safe sequence of moves from start_coord to target_coord
    for a player piece of type `player_type`, avoiding squares covered by defender predators
    unless it can capture prey.
    """
    occupied: Dict[Tuple[int, int], Tuple[int, str]] = {}
    danger: set = set()

    for r, c, owner, pt in pieces:
        occupied[(r, c)] = (owner, pt)
        if owner == 1 and BEATS.get(pt) == player_type:
            # This defender piece defeats the player piece
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < board_size and 0 <= nc < board_size:
                        danger.add((nr, nc))

    q = deque([(start_coord[0], start_coord[1], 0, [start_coord])])
    vis = {start_coord}

    while q:
        r, c, d, path = q.popleft()
        if (r, c) == target_coord:
            return d, path

        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                nr, nc = r + dr, c + dc
                if 0 <= nr < board_size and 0 <= nc < board_size and (nr, nc) not in vis:
                    if (nr, nc) in occupied:
                        occ_owner, occ_type = occupied[(nr, nc)]
                        if occ_owner == 0 or BEATS.get(player_type) != occ_type:
                            continue  # Cannot capture friendly piece or non-prey
                    elif (nr, nc) in danger and (nr, nc) != target_coord:
                        continue  # Threat zone

                    vis.add((nr, nc))
                    q.append((nr, nc, d + 1, path + [(nr, nc)]))

    return None, []


class PuzzleScenario:
    def __init__(self, id_str: str, title: str, description: str,
                 board_size: int, s_optimal: int,
                 pieces: List[Tuple[int, int, int, str]],
                 optimal_path: Optional[List[Tuple[int, int]]] = None):
        self.id = id_str
        self.title = title
        self.description = description
        self.board_size = board_size
        self.s_optimal = s_optimal
        self.s_max = 3 * s_optimal
        self.pieces = pieces  # (r, c, owner, p_type)
        self.optimal_path = optimal_path or []

    def create_initial_state(self) -> GameState:
        state = GameState(board_size=self.board_size, custom_setup=True)
        for r, c, owner, pt in self.pieces:
            state.board[r][c] = Piece(owner, pt)
        return state


# Pre-configured benchmark puzzles
PRECONFIGURED_PUZZLES: Dict[str, PuzzleScenario] = {
    'p10_proposal': PuzzleScenario(
        id_str='p10_proposal',
        title='Proposal Benchmark (10-Step Optimal)',
        description='Standard 10-step optimal puzzle as specified in the proposal. AI acts as Optimal Defender.',
        board_size=9,
        s_optimal=10,
        pieces=[
            (8, 0, 0, 'H'),
            (2, 2, 1, 'A'),
            (2, 5, 1, 'E'),
            (4, 3, 1, 'E'),
            (6, 6, 1, 'H')
        ],
        optimal_path=[
            (8, 0), (7, 1), (6, 2), (5, 3), (4, 4),
            (4, 5), (4, 6), (3, 7), (2, 7), (1, 7), (0, 8)
        ]
    ),
    'p6_rush': PuzzleScenario(
        id_str='p6_rush',
        title='Tactical Sprint (6-Step Optimal - 6x6)',
        description='Compact 6x6 tactical race. Navigate past Elephant defense.',
        board_size=6,
        s_optimal=6,
        pieces=[
            (5, 0, 0, 'H'),
            (3, 4, 1, 'A'),
            (5, 5, 1, 'E'),
            (5, 2, 1, 'E')
        ],
        optimal_path=[(5, 0), (4, 0), (3, 1), (2, 2), (1, 3), (0, 4), (0, 5)]
    ),
    'p8_flank': PuzzleScenario(
        id_str='p8_flank',
        title='Flank Corridor (8-Step Optimal - 6x6)',
        description='Maneuver along the outer perimeter to bypass heavy defender presence.',
        board_size=6,
        s_optimal=8,
        pieces=[
            (5, 0, 0, 'H'),
            (0, 3, 1, 'A'),
            (1, 0, 1, 'A'),
            (3, 5, 1, 'E'),
            (3, 2, 1, 'E'),
            (5, 3, 1, 'E')
        ],
        optimal_path=[(5, 0), (4, 0), (3, 0), (2, 0), (1, 1), (0, 2), (0, 3), (0, 4), (0, 5)]
    ),
    'p12_labyrinth': PuzzleScenario(
        id_str='p12_labyrinth',
        title='Grand Labyrinth (12-Step Optimal - 9x9)',
        description='Extended defense perimeter requiring complex evasive pathing.',
        board_size=9,
        s_optimal=12,
        pieces=[
            (8, 0, 0, 'H'),
            (8, 2, 1, 'E'),
            (8, 3, 1, 'A'),
            (3, 5, 1, 'E'),
            (5, 2, 1, 'E')
        ],
        optimal_path=[
            (8, 0), (7, 0), (6, 0), (5, 0), (4, 0),
            (3, 1), (2, 2), (1, 3), (0, 4), (0, 5), (0, 6), (0, 7), (0, 8)
        ]
    )
}


def generate_procedural_puzzle(target_steps: int = 10, board_size: int = 9) -> PuzzleScenario:
    """
    Dynamically generates a randomized N-step puzzle scenario, mathematically
    verified by BFS search to possess an optimal safe solution of `target_steps`.
    """
    target_start = (board_size - 1, 0)
    target_end = (0, board_size - 1)

    for attempt in range(1000):
        num_defs = random.randint(2, 6)
        defs = []
        occupied_coords = {target_start, target_end}

        for _ in range(num_defs):
            r = random.randint(0, board_size - 1)
            c = random.randint(0, board_size - 1)
            if (r, c) not in occupied_coords:
                occupied_coords.add((r, c))
                pt = random.choice(['E', 'A', 'H'])
                defs.append((r, c, pt))

        pieces = [(target_start[0], target_start[1], 0, 'H')]
        for r, c, pt in defs:
            pieces.append((r, c, 1, pt))

        d, path = bfs_safe_path(board_size, pieces, target_start, target_end, 'H')
        if d == target_steps:
            return PuzzleScenario(
                id_str=f"procedural_{target_steps}_{int(time.time())}",
                title=f"Procedural {target_steps}-Step Challenge",
                description=f"Algorithmically generated {board_size}x{board_size} puzzle with verified {target_steps}-step optimal route.",
                board_size=board_size,
                s_optimal=target_steps,
                pieces=pieces,
                optimal_path=path
            )

    # Fallback to pre-configured 10-step proposal benchmark if timeout
    return PRECONFIGURED_PUZZLES['p10_proposal']


class PuzzleSession:
    """
    Session Telemetry Manager:
    Tracks current attempt steps, cumulative steps across resets, undo counts,
    delay margin, neutralization rate, and per-turn AI telemetry.
    """
    def __init__(self, scenario: PuzzleScenario):
        self.scenario = scenario
        self.current_attempt_steps: int = 0
        self.cumulative_steps: int = 0
        self.resets_count: int = 0
        self.undo_count: int = 0
        self.is_solved: bool = False
        self.is_neutralized: bool = False
        self.neutralization_reason: str = ""
        self.ai_telemetry_history: List[Dict[str, Any]] = []

    @property
    def s_optimal(self) -> int:
        return self.scenario.s_optimal

    @property
    def s_max(self) -> int:
        return self.scenario.s_max

    @property
    def delay_margin(self) -> int:
        return max(0, self.current_attempt_steps - self.s_optimal)

    def record_player_step(self):
        self.current_attempt_steps += 1

    def record_undo(self):
        self.undo_count += 1
        if self.current_attempt_steps > 0:
            self.current_attempt_steps -= 1

    def record_ai_telemetry(self, source_coord: Tuple[int, int], target_coord: Tuple[int, int],
                            eval_score: float, t_turn: float, nodes_gen: int,
                            nodes_eval: int, prune_efficiency: float):
        self.ai_telemetry_history.append({
            'action': (source_coord, target_coord),
            'eval_score': eval_score,
            't_turn': t_turn,
            'nodes_gen': nodes_gen,
            'nodes_eval': nodes_eval,
            'prune_efficiency': prune_efficiency
        })

    def reset_attempt(self):
        self.resets_count += 1
        self.cumulative_steps += self.current_attempt_steps
        self.current_attempt_steps = 0
        self.is_solved = False
        self.is_neutralized = False
        self.neutralization_reason = ""

    def evaluate_status(self, state: GameState) -> str:
        """
        Determines current puzzle status:
        - SOLVED: Player reached target corner
        - NEUTRALIZED: Step limit exceeded or player eliminated / blocked
        - DELAYED: Player exceeded optimal path but remains within S_max
        - ON_TRACK: Player on schedule
        """
        target = state.target_corners[0]

        # Victory check
        for r in range(state.board_size):
            for c in range(state.board_size):
                p = state.board[r][c]
                if p and p.owner == 0 and (r, c) == target:
                    self.is_solved = True
                    return 'SOLVED'

        # Neutralization: Step limit exhaustion S_max = 3 * S_optimal
        if self.current_attempt_steps >= self.s_max:
            self.is_neutralized = True
            self.neutralization_reason = f"Step limit exhausted (S_max = {self.s_max} moves)"
            return 'NEUTRALIZED'

        # Check player pieces remaining
        player_pieces = []
        for r in range(state.board_size):
            for c in range(state.board_size):
                p = state.board[r][c]
                if p and p.owner == 0:
                    player_pieces.append(((r, c), p))

        if not player_pieces:
            self.is_neutralized = True
            self.neutralization_reason = "All player pieces captured"
            return 'NEUTRALIZED'

        # Check legal moves
        if state.current_turn == 0 and not state.get_valid_moves(0):
            self.is_neutralized = True
            self.neutralization_reason = "No legal moves available (stalemate / blocked)"
            return 'NEUTRALIZED'

        if self.current_attempt_steps > self.s_optimal:
            return 'DELAYED'

        return 'ON_TRACK'


# Scripted Players for Baseline Evaluation Framework (Table 3)

class ShortestPathScriptedPlayer:
    """Always moves along the shortest route to the target corner."""
    def select_move(self, state: GameState) -> Optional[Tuple[Tuple[int, int], Tuple[int, int]]]:
        valid_moves = state.get_valid_moves(0)
        if not valid_moves:
            return None

        target = state.target_corners[0]

        # Prioritize immediate winning move
        for m in valid_moves:
            if m[1] == target:
                return m

        # Select move that minimizes Chebyshev distance to goal
        def dist_metric(m):
            end = m[1]
            return max(abs(end[0] - target[0]), abs(end[1] - target[1]))

        return min(valid_moves, key=dist_metric)


class SubOptimalScriptedPlayer:
    """Follows the shortest route, but occasionally (25%) deviates randomly."""
    def __init__(self, deviation_rate: float = 0.25):
        self.deviation_rate = deviation_rate
        self.shortest_player = ShortestPathScriptedPlayer()

    def select_move(self, state: GameState) -> Optional[Tuple[Tuple[int, int], Tuple[int, int]]]:
        valid_moves = state.get_valid_moves(0)
        if not valid_moves:
            return None

        target = state.target_corners[0]
        for m in valid_moves:
            if m[1] == target:
                return m

        if random.random() < self.deviation_rate and len(valid_moves) > 1:
            return random.choice(valid_moves)

        return self.shortest_player.select_move(state)


class RandomScriptedPlayer:
    """Executes pseudo-random legal moves."""
    def select_move(self, state: GameState) -> Optional[Tuple[Tuple[int, int], Tuple[int, int]]]:
        valid_moves = state.get_valid_moves(0)
        return random.choice(valid_moves) if valid_moves else None


def run_simulation_benchmark(agent_model: str = 'proposed_d6',
                             scripted_player_type: str = 'shortest_path',
                             num_games: int = 10,
                             depth: int = 6,
                             board_size: int = 9,
                             progress_callback: Optional[Any] = None) -> Dict[str, Any]:
    """
    Executes simulated matches for the Chapter 2.2 / Table 3 evaluation framework.
    Simulates games between Defender AI and Scripted Players, collecting:
    - Turn Execution Latency (Tturn)
    - Pruning Efficiency (prune %)
    - Delay Margin (Delta S)
    - Neutralization Rate (Rneut %)
    """
    from ai_engine import get_defender_move

    # Instantiate scripted player
    if scripted_player_type == 'random':
        player = RandomScriptedPlayer()
    elif scripted_player_type == 'sub_optimal':
        player = SubOptimalScriptedPlayer(deviation_rate=0.25)
    else:
        player = ShortestPathScriptedPlayer()

    total_games = num_games
    neutralized_count = 0
    solved_delays = []
    latencies = []
    pruning_efficiencies = []

    scenario = PRECONFIGURED_PUZZLES.get('p10_proposal') if board_size == 9 else PRECONFIGURED_PUZZLES.get('p6_rush')
    s_optimal = scenario.s_optimal if scenario else 10
    s_max = 3 * s_optimal

    for game_idx in range(num_games):
        # Reset state from scenario
        state = scenario.create_initial_state() if scenario else PRECONFIGURED_PUZZLES['p10_proposal'].create_initial_state()
        steps_player = 0
        game_resolved = False

        while not game_resolved and steps_player < s_max:
            # 1. Player turn
            p_move = player.select_move(state)
            if not p_move:
                neutralized_count += 1
                game_resolved = True
                break

            state.make_move(p_move[0], p_move[1])
            steps_player += 1

            # Check if player won
            if state.winner == 0:
                delay = max(0, steps_player - s_optimal)
                solved_delays.append(delay)
                game_resolved = True
                break

            # 2. Defender AI turn
            def_move, eval_s, tel = get_defender_move(state, agent_model=agent_model, depth=depth)
            latencies.append(tel.t_turn)
            if tel.nodes_generated > 0:
                pruning_efficiencies.append(tel.pruning_efficiency)

            if not def_move:
                # Defender has no moves, player wins
                delay = max(0, steps_player - s_optimal)
                solved_delays.append(delay)
                game_resolved = True
                break

            state.make_move(def_move[0], def_move[1])

            if state.winner == 1:
                # Defender won
                neutralized_count += 1
                game_resolved = True
                break

        if not game_resolved and steps_player >= s_max:
            # Step limit exceeded
            neutralized_count += 1

        if progress_callback:
            progress_callback(game_idx + 1, total_games)

    avg_latency = (sum(latencies) / len(latencies)) if latencies else 0.001
    avg_prune = (sum(pruning_efficiencies) / len(pruning_efficiencies)) if pruning_efficiencies else 0.0
    r_neut = (neutralized_count / total_games) * 100.0 if total_games > 0 else 0.0
    avg_delay = (sum(solved_delays) / len(solved_delays)) if solved_delays else 0.0

    return {
        'agent_model': agent_model,
        'scripted_player': scripted_player_type,
        'total_games': total_games,
        'neutralized_count': neutralized_count,
        'solved_count': len(solved_delays),
        'neutralization_rate': r_neut,
        'delay_margin': avg_delay,
        'avg_latency': avg_latency,
        'avg_pruning_efficiency': avg_prune
    }
