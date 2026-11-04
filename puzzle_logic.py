import random
import time
import math
import hashlib
from collections import deque
from typing import List, Tuple, Dict, Any, Optional
from game_logic import GameState, Piece, BEATS, PREDATORS
import storage


def puzzle_position_key(board_size: int, pieces, target_coord=None) -> str:
    """Bind a saved verification to this layout and the corner-win rules."""
    target = target_coord or (0, board_size - 1)
    position = ('corner_win_v1', board_size, target, tuple(sorted(tuple(p) for p in pieces)))
    return hashlib.sha256(repr(position).encode()).hexdigest()


def bfs_safe_path(board_size: int, pieces: List[Tuple[int, int, int, str]],
                  start_coord: Tuple[int, int], target_coord: Tuple[int, int],
                  player_type: str = 'H', avoid_predators: bool = True) -> Tuple[Optional[int], List[Tuple[int, int]]]:
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
                            continue
                    elif avoid_predators and (nr, nc) in danger and (nr, nc) != target_coord:
                        continue

                    vis.add((nr, nc))
                    q.append((nr, nc, d + 1, path + [(nr, nc)]))

    return None, []


def verify_puzzle(board_size: int, pieces: List[Tuple[int, int, int, str]],
                  target_coord: Optional[Tuple[int, int]] = None, max_steps: int = 14,
                  time_budget: float = 5.0, node_budget: int = 30000,
                  current_turn: int = 0, cancel_event=None) -> Dict[str, Any]:
    """Prove the shortest forced corner win, or explicitly return an unknown result.

    The bounded search considers every legal defensive reply. A geometric
    certificate handles sparse race puzzles without enumerating equivalent replies.
    """
    target = target_coord or (0, board_size - 1)
    if board_size < 2 or max_steps < 0 or current_turn not in (0, 1):
        raise ValueError("Invalid board size or verification horizon")
    state = GameState(board_size, custom_setup=True)
    state.current_turn = current_turn
    state.target_corners[0] = target
    occupied = set()
    for r, c, owner, pt in pieces:
        if (not state.is_valid_coordinate(r, c) or (r, c) in occupied
                or owner not in (0, 1) or pt not in BEATS):
            raise ValueError("Invalid or overlapping puzzle pieces")
        occupied.add((r, c))
        state.board[r][c] = Piece(owner, pt)
    if not state.is_valid_coordinate(*target):
        raise ValueError("Invalid target coordinate")
    deadline = time.perf_counter() + max(0.0, time_budget)
    cache = {}
    expanded = 0
    generated = evaluated = pruned = 0

    def outcome(status, steps=None, path=None, moves=None, method='', reason=''):
        policy = {}
        if status != 'UNVERIFIED':
            for (cells, turn, horizon), (value, line, _) in cache.items():
                if (turn != 1 or not line or line[0][0] != 1
                        or ((current_turn == 0 or status == 'VERIFIED') and math.isinf(value))):
                    continue
                key = puzzle_position_key(board_size, cells, target)
                distance = None if math.isinf(value) else int(value)
                previous = policy.get(key)
                if (previous is None or (previous['steps'] is None and distance is not None)
                        or (previous['steps'] is None and distance is None
                            and horizon > previous['remaining'])):
                    policy[key] = {'move': line[0][1:], 'steps': distance, 'remaining': horizon}
        result = dict(status=status, steps=steps, path=path or [], moves=moves or [],
                      method=method, reason=reason, defender_policy=policy,
                      nodes_generated=generated, nodes_evaluated=evaluated, nodes_pruned=pruned)
        if status == 'VERIFIED':
            result['position_key'] = puzzle_position_key(board_size, pieces, target)
        return result

    def solve(position, remaining):
        nonlocal expanded, generated, evaluated, pruned
        if ((cancel_event is not None and cancel_event.is_set())
                or time.perf_counter() >= deadline or expanded >= node_budget):
            raise TimeoutError
        cells = tuple((r, c, p.owner, p.p_type) for r, row in enumerate(position.board)
                      for c, p in enumerate(row) if p)
        key = (cells, position.current_turn, remaining)
        if key in cache:
            return cache[key]
        expanded += 1
        players = [(r, c, pt) for r, c, owner, pt in cells if owner == 0]
        defenders = [(r, c, pt) for r, c, owner, pt in cells if owner == 1]
        if any((r, c) == target for r, c, _ in players):
            return 0, [], 'adversarial'
        if (position.winner == 1 or not players
                or any((r, c) == position.target_corners[1] for r, c, _ in defenders)):
            return math.inf, [], 'adversarial'
        lower_bound = min(max(abs(r - target[0]), abs(c - target[1])) for r, c, _ in players)
        if remaining < lower_bound:
            return math.inf, [], 'adversarial'

        # A lone attacker can capture every defender, and wins the race even
        # against the fastest possible reply. Distance proves minimality.
        if (position.current_turn == 0 and len(players) == 1
                and all(pt == BEATS[players[0][2]]
                        and max(abs(r - position.target_corners[1][0]),
                                abs(c - position.target_corners[1][1])) >= lower_bound
                        for r, c, pt in defenders)):
            coord = players[0][:2]
            trail = []
            while coord != target:
                dest = tuple(a + (b > a) - (b < a) for a, b in zip(coord, target))
                trail.append((0, coord, dest))
                coord = dest
            return lower_bound, trail, 'race_certificate'

        turn = position.current_turn
        moves = position.get_valid_moves(turn)
        if not moves:
            if turn == 0:
                return math.inf, [], 'adversarial'
            position = position.clone()
            position.current_turn = 0
            position.winner = None
            return solve(position, remaining)
        cost = 1 if turn == 0 else 0
        if remaining < cost:
            return math.inf, [], 'adversarial'
        if turn == 0:
            moves.sort(key=lambda m: max(abs(m[1][0] - target[0]), abs(m[1][1] - target[1])))
        else:
            home = position.target_corners[1]
            moves.sort(key=lambda m: (m[1] != home, position.get_piece(*m[1]) is None,
                                      max(abs(m[1][0] - home[0]), abs(m[1][1] - home[1]))))
        generated += len(moves)
        best = math.inf if turn == 0 else -math.inf
        trail = []
        for index, (start, end) in enumerate(moves):
            evaluated += 1
            child = position.clone()
            child.make_move(start, end)
            # Capturing the final defender does not replace the corner objective.
            if child.winner == 0 and end != target:
                child.winner = None
            value, continuation, _ = solve(child, remaining - cost)
            value += cost
            if (turn == 0 and value < best) or (turn == 1 and value > best):
                best, trail = value, [(turn, start, end)] + continuation
            if (turn == 0 and best == lower_bound) or (turn == 1 and math.isinf(best)):
                pruned += len(moves) - index - 1
                break
        cache[key] = (best, trail, 'adversarial')
        return cache[key]

    try:
        first_horizon = min((max(abs(r - target[0]), abs(c - target[1]))
                             for r, c, owner, _ in pieces if owner == 0), default=0)
        steps, moves, method = math.inf, [], 'adversarial'
        for horizon in range(first_horizon, max_steps + 1):
            steps, moves, method = solve(state, horizon)
            if not math.isinf(steps):
                break
    except TimeoutError:
        return outcome('UNVERIFIED', reason='Verification time or node budget exhausted')
    if math.isinf(steps):
        return outcome('NO_WIN_WITHIN_LIMIT', moves=moves,
                       reason=f'No forced corner win within {max_steps} player moves')
    player_moves = [(start, end) for owner, start, end in moves if owner == 0]
    path = [player_moves[0][0]] + [end for _, end in player_moves] if player_moves else [target]
    if any(a[1] != b[0] for a, b in zip(player_moves, player_moves[1:])):
        path = []  # A coordinate route cannot represent switches between player pieces.
    return outcome('VERIFIED', int(steps), path, moves, method,
                   'Forced corner win verified against all legal replies')


def solve_adversarial_optimal_path(board_size: int, pieces: List[Tuple[int, int, int, str]],
                                   target_coord: Optional[Tuple[int, int]] = None,
                                   max_depth: int = 14) -> Tuple[Optional[int], List[Tuple[int, int]], Optional[Tuple[int, int, str]]]:
    result = verify_puzzle(board_size, pieces, target_coord, max_steps=max_depth)
    path = result['path']
    lead = next(((r, c, pt) for r, c, owner, pt in pieces
                 if owner == 0 and path and (r, c) == path[0]), None)
    return result['steps'], path, lead


def find_optimal_winning_path(board_size: int, pieces: List[Tuple[int, int, int, str]],
                              target_coord: Optional[Tuple[int, int]] = None) -> Tuple[Optional[int], List[Tuple[int, int]], Optional[Tuple[int, int, str]]]:
    """Shortest piece route through the starting board with all other pieces fixed.

    Prey can be captured; friendly pieces, predators and equal suits block entry.
    This is a static minimum, not a forced-win proof against a moving defender.
    """
    target = target_coord or (0, board_size - 1)
    best_steps, best_path, best_piece = None, [], None
    for r, c, owner, pt in pieces:
        if owner != 0:
            continue
        steps, path = bfs_safe_path(board_size, pieces, (r, c), target, pt,
                                    avoid_predators=False)
        if steps is not None and (best_steps is None or steps < best_steps):
            best_steps, best_path, best_piece = steps, path, (r, c, pt)
    return best_steps, best_path, best_piece


class PuzzleScenario:
    def __init__(self, id_str: str, title: str, description: str,
                 board_size: int, s_optimal: Optional[int] = None,
                 pieces: Optional[List[Tuple[int, int, int, str]]] = None,
                 optimal_path: Optional[List[Tuple[int, int]]] = None,
                 is_custom: bool = False, verification_status: str = 'UNVERIFIED',
                 verification_method: str = '', verification_key: str = '',
                 optimal_moves: Optional[List[Any]] = None, move_limit: Optional[int] = None,
                 defender_policy: Optional[Dict[str, Any]] = None, minimum_source: str = ''):
        self.id = id_str
        self.title = title
        self.description = description
        self.board_size = board_size
        self.pieces = pieces or []
        verified = (minimum_source != 'manual' and verification_status == 'VERIFIED'
                    and verification_key == puzzle_position_key(board_size, self.pieces)
                    and type(s_optimal) is int and s_optimal >= 0)
        self.s_optimal = s_optimal if type(s_optimal) is int and s_optimal > 0 else None
        self.minimum_source = minimum_source
        self.optimal_path = (optimal_path or []) if verified else []
        self.optimal_moves = (optimal_moves or []) if verified else []
        self.defender_policy = (defender_policy or {}) if verified else {}
        if self.s_optimal is not None:
            self.s_max = 3 * self.s_optimal
        else:
            self.s_max = move_limit if type(move_limit) is int and move_limit > 0 else 3 * board_size
        self.is_custom = is_custom
        self.verification_status = 'VERIFIED' if verified else 'UNVERIFIED'
        self.verification_method = verification_method if verified else ''
        self.verification_key = verification_key if verified else ''

    @property
    def step_label(self) -> str:
        if self.minimum_source == 'manual':
            return 'Minimum (user-entered)'
        if self.is_custom or self.verification_status != 'VERIFIED':
            return 'Minimum (saved)'
        return 'Minimum (best defense)'

    @property
    def step_summary(self) -> str:
        if self.s_optimal is None:
            return 'Minimum: not set'
        return f'{self.step_label}: {self.s_optimal} steps'

    def create_initial_state(self) -> GameState:
        state = GameState(board_size=self.board_size, custom_setup=True)
        for r, c, owner, pt in self.pieces:
            state.board[r][c] = Piece(owner, pt)
        return state

    def to_dict(self) -> Dict[str, Any]:
        data = {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'board_size': self.board_size,
            's_optimal': self.s_optimal,
            's_max': self.s_max,
            'pieces': self.pieces,
            'optimal_path': self.optimal_path,
            'optimal_moves': self.optimal_moves,
            'is_custom': self.is_custom,
            'verification_status': self.verification_status,
            'verification_method': self.verification_method,
            'verification_key': self.verification_key
        }
        if self.defender_policy:
            data['defender_policy'] = self.defender_policy
        if self.minimum_source == 'manual':
            data['minimum_source'] = 'manual'
        return data

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'PuzzleScenario':
        return PuzzleScenario(
            id_str=data.get('id', 'custom_stage'),
            title=data.get('title', 'Custom Stage'),
            description=data.get('description', ''),
            board_size=data.get('board_size', 6),
            s_optimal=data.get('s_optimal'),
            pieces=[(p[0], p[1], p[2], p[3]) for p in data.get('pieces', [])],
            optimal_path=data.get('optimal_path', []),
            optimal_moves=data.get('optimal_moves', []),
            defender_policy=data.get('defender_policy', {}),
            is_custom=data.get('is_custom', True),
            verification_status=data.get('verification_status', 'UNVERIFIED'),
            verification_method=data.get('verification_method', ''),
            verification_key=data.get('verification_key', ''),
            move_limit=data.get('s_max'),
            minimum_source=data.get('minimum_source', '')
        )


def get_all_puzzles() -> Dict[str, PuzzleScenario]:
    """Return only user-created stages from custom-stage storage."""
    all_puzzles = {}
    custom_list = storage.get_custom_stages()
    for item in custom_list:
        try:
            scen = PuzzleScenario.from_dict(item)
            scen.is_custom = True
            all_puzzles[scen.id] = scen
        except Exception as e:
            print(f"Error loading custom stage: {e}")
    return all_puzzles


def generate_benchmark_corpus(num_games: int = 1000, board_size: int = 11,
                               seed: int = 2026) -> List[PuzzleScenario]:
    """Generate the seeded, certified 10-step positions used by the benchmark lab."""
    if num_games < 1 or board_size < 11:
        raise ValueError("Benchmark needs at least one game and a board size of 11 or greater")
    rng = random.Random(seed)
    corpus = []
    for _ in range(num_games):
        steps = rng.randint(10, 10)  # Preserve the RNG stream of existing benchmark seeds.
        suit = rng.choice(list(BEATS))
        start = (steps, rng.randrange(board_size - 1 - steps, board_size))
        columns = rng.sample(range(board_size - 1), rng.randint(1, min(3, board_size - 1)))
        pieces = [(start[0], start[1], 0, suit)] + [(0, c, 1, BEATS[suit]) for c in columns]
        proof = verify_puzzle(board_size, pieces, max_steps=steps)
        if proof['status'] != 'VERIFIED' or proof['steps'] != steps:
            raise RuntimeError("Generated benchmark puzzle failed verification")
        corpus.append(PuzzleScenario(
            id_str=f"race_{board_size}_{start[0]}_{start[1]}_{suit}_{'_'.join(map(str, columns))}",
            title=f"Benchmark Race ({steps} Steps)",
            description=f"Sparse race: a forced corner win in exactly {steps} moves.",
            board_size=board_size, s_optimal=steps, pieces=pieces,
            optimal_path=proof['path'], optimal_moves=proof['moves'],
            verification_status=proof['status'], verification_method=proof['method'],
            verification_key=proof['position_key']))
    return corpus


class PuzzleSession:
    """
    Session Telemetry Manager:
    Tracks current attempt steps, cumulative steps across resets, undo counts,
    delay margin, neutralization rate, and per-turn AI telemetry.
    Supports `show_metrics` toggle to avoid in-game spoilers.
    """
    def __init__(self, scenario: PuzzleScenario, show_metrics: bool = False):
        self.scenario = scenario
        self.show_metrics: bool = show_metrics
        self.current_attempt_steps: int = 0
        self.cumulative_steps: int = 0
        self.resets_count: int = 0
        self.undo_count: int = 0
        self.is_solved: bool = False
        self.is_neutralized: bool = False
        self.neutralization_reason: str = ""
        self.ai_telemetry_history: List[Dict[str, Any]] = []

    @property
    def s_optimal(self) -> Optional[int]:
        return self.scenario.s_optimal

    @property
    def s_max(self) -> int:
        return self.scenario.s_max

    @property
    def delay_margin(self) -> int:
        return max(0, self.current_attempt_steps - self.s_optimal) if self.s_optimal is not None else 0

    def record_player_step(self) -> None:
        self.current_attempt_steps += 1

    def record_undo(self) -> None:
        self.undo_count += 1
        if self.current_attempt_steps > 0:
            self.current_attempt_steps -= 1

    def record_ai_telemetry(self, source_coord: Tuple[int, int], target_coord: Tuple[int, int],
                            eval_score: float, t_turn: float, nodes_gen: int,
                            nodes_eval: int, prune_efficiency: float,
                            completed_depth: int = 0, timed_out: bool = False,
                            proof_horizon: Optional[int] = None) -> None:
        self.ai_telemetry_history.append({
            'action': (source_coord, target_coord),
            'eval_score': eval_score,
            't_turn': t_turn,
            'nodes_gen': nodes_gen,
            'nodes_eval': nodes_eval,
            'prune_efficiency': prune_efficiency,
            'completed_depth': completed_depth, 'timed_out': timed_out,
            'proof_horizon': proof_horizon
        })

    def reset_attempt(self) -> None:
        self.resets_count += 1
        self.cumulative_steps += self.current_attempt_steps
        self.current_attempt_steps = 0
        self.is_solved = False
        self.is_neutralized = False
        self.neutralization_reason = ""

    def evaluate_status(self, state: GameState) -> str:
        self.is_solved = False
        self.is_neutralized = False
        self.neutralization_reason = ''
        target = state.target_corners[0]
        ai_target = state.target_corners[1]

        # Victory check
        for r in range(state.board_size):
            for c in range(state.board_size):
                p = state.board[r][c]
                if p and p.owner == 0 and (r, c) == target:
                    self.is_solved = True
                    return 'SOLVED'

        # Neutralization check: AI Defender reaches player home corner
        for r in range(state.board_size):
            for c in range(state.board_size):
                p = state.board[r][c]
                if p and p.owner == 1 and (r, c) == ai_target:
                    self.is_neutralized = True
                    self.neutralization_reason = "AI reached player home corner"
                    return 'NEUTRALIZED'

        if state.winner == 1:
            self.is_neutralized = True
            self.neutralization_reason = "AI reached home corner"
            return 'NEUTRALIZED'

        # Neutralization step limit check
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

        if self.s_optimal is not None and self.current_attempt_steps > self.s_optimal:
            return 'DELAYED'

        return 'ON_TRACK'


# Scripted Players for Baseline Evaluation Framework

class ShortestPathScriptedPlayer:
    """Replan the shortest legal route on the current, frozen board each turn."""
    def select_move(self, state: GameState) -> Optional[Tuple[Tuple[int, int], Tuple[int, int]]]:
        valid_moves = state.get_valid_moves(0)
        if not valid_moves:
            return None

        pieces = [(r, c, p.owner, p.p_type) for r, row in enumerate(state.board)
                  for c, p in enumerate(row) if p]
        routes = [bfs_safe_path(state.board_size, pieces, (r, c), state.target_corners[0],
                                pt, avoid_predators=False)
                  for r, c, owner, pt in pieces if owner == 0]
        routes = [(distance, path) for distance, path in routes if distance is not None and distance > 0]
        if routes:
            _, path = min(routes, key=lambda item: item[0])
            return path[0], path[1]
        return valid_moves[0]  # No route exists until the board changes.


class SubOptimalScriptedPlayer:
    """Follows the shortest route, but occasionally (25%) deviates randomly."""
    def __init__(self, deviation_rate: float = 0.25, rng=None):
        self.deviation_rate = deviation_rate
        self.shortest_player = ShortestPathScriptedPlayer()
        self.rng = rng or random

    def select_move(self, state: GameState) -> Optional[Tuple[Tuple[int, int], Tuple[int, int]]]:
        valid_moves = state.get_valid_moves(0)
        if not valid_moves:
            return None

        shortest = self.shortest_player.select_move(state)
        if self.rng.random() < self.deviation_rate and len(valid_moves) > 1:
            return self.rng.choice([move for move in valid_moves if move != shortest])
        return shortest


class RandomScriptedPlayer:
    """Executes pseudo-random legal moves."""
    def __init__(self, rng=None):
        self.rng = rng or random

    def select_move(self, state: GameState) -> Optional[Tuple[Tuple[int, int], Tuple[int, int]]]:
        valid_moves = state.get_valid_moves(0)
        return self.rng.choice(valid_moves) if valid_moves else None


def make_puzzle_move(state: GameState, start: Tuple[int, int], end: Tuple[int, int]):
    """Puzzle wins require the corner; an eliminated defender simply has no turn."""
    if (start, end) not in state.get_valid_moves(state.current_turn):
        raise ValueError('Illegal puzzle move')
    move = state.make_move(start, end)
    if state.winner == 0 and not (state.board[state.target_corners[0][0]][state.target_corners[0][1]]
                                  and state.board[state.target_corners[0][0]][state.target_corners[0][1]].owner == 0):
        state.winner = None
    if state.winner is None and state.current_turn == 1 and not state.get_valid_moves(1):
        state.current_turn = 0
    return move


BENCHMARK_AGENTS = [
    ('proposed_d6', 6, 'Optimized (Alpha-Beta d=6)'),
    ('proposed_d3', 3, 'Optimized (Alpha-Beta d=3)'),
    ('baseline_2_vanilla', 3, 'Vanilla Minimax (d=3, static)'),
    ('baseline_1_random', 1, 'Random Move Agent'),
]
BENCHMARK_PLAYERS = ['shortest_path', 'sub_optimal', 'random']


def run_simulation_benchmark(agent_model: str = 'proposed_d6',
                             scripted_player_type: str = 'shortest_path',
                             num_games: int = 1000, depth: int = 6, board_size: int = 11,
                             progress_callback: Optional[Any] = None,
                             corpus: Optional[List[PuzzleScenario]] = None, seed: int = 2026,
                             turn_callback: Optional[Any] = None) -> Dict[str, Any]:
    """Compare defenders on a shared certified corpus; emit optional per-turn records."""
    import hashlib
    import json
    from ai_engine import get_defender_move

    if agent_model not in [model for model, _, _ in BENCHMARK_AGENTS]:
        raise ValueError('Unknown benchmark agent')
    if scripted_player_type not in BENCHMARK_PLAYERS or num_games < 1:
        raise ValueError('Invalid player or game count')
    corpus = corpus if corpus is not None else generate_benchmark_corpus(num_games, board_size, seed)
    if len(corpus) != num_games:
        raise ValueError('Corpus length must equal num_games')
    for scenario in corpus:
        proof = verify_puzzle(scenario.board_size, scenario.pieces, max_steps=10)
        if scenario.board_size != board_size or proof['status'] != 'VERIFIED' or proof['steps'] != 10 or scenario.s_optimal != 10:
            raise ValueError('Benchmark requires verified 10-step puzzles of the selected size')
    corpus_hash = hashlib.sha256(json.dumps([s.to_dict() for s in corpus],
                                           sort_keys=True).encode()).hexdigest()
    neutralized_count = 0
    solved_delays, latencies, completed_depths = [], [], []
    generated = evaluated = pruned = timeout_count = full_depth_count = 0

    for game_idx, scenario in enumerate(corpus):
        rng = random.Random(seed + game_idx)
        defender_rng = random.Random(seed + game_idx + 1000003)
        player = (RandomScriptedPlayer(rng) if scripted_player_type == 'random' else
                  SubOptimalScriptedPlayer(rng=rng) if scripted_player_type == 'sub_optimal' else
                  ShortestPathScriptedPlayer())
        state = scenario.create_initial_state()
        solved = False
        for player_step in range(1, scenario.s_max + 1):
            move = player.select_move(state)
            if move is None:
                break
            make_puzzle_move(state, *move)
            if state.get_piece(*state.target_corners[0]) and state.get_piece(*state.target_corners[0]).owner == 0:
                solved_delays.append(player_step - scenario.s_optimal)
                solved = True
                break
            if state.winner == 1 or player_step == scenario.s_max:
                break
            if state.current_turn == 0:
                continue
            defender_move, score, telemetry = get_defender_move(state, agent_model, depth, rng=defender_rng)
            latencies.append(telemetry.t_turn)
            completed_depths.append(telemetry.completed_depth)
            timeout_count += int(telemetry.timed_out)
            full_depth_count += int(telemetry.completed_depth == depth)
            generated += telemetry.nodes_generated
            evaluated += telemetry.nodes_evaluated
            pruned += telemetry.nodes_pruned
            if turn_callback:
                turn_callback(dict(
                    agent_model=agent_model, scripted_player=scripted_player_type,
                    game=game_idx + 1, puzzle_id=scenario.id, player_step=player_step,
                    action=defender_move, eval_score=score, **vars(telemetry)))
            if defender_move is None:
                state.current_turn = 0
                state.winner = None
                continue
            make_puzzle_move(state, *defender_move)
            if state.winner == 1:
                break
        neutralized_count += int(not solved)
        if progress_callback:
            progress_callback(game_idx + 1, num_games)

    turns = len(latencies)
    return {
        'agent_model': agent_model, 'scripted_player': scripted_player_type,
        'total_games': num_games, 'neutralized_count': neutralized_count,
        'solved_count': len(solved_delays),
        'neutralization_rate': neutralized_count / num_games * 100.0,
        'delay_margin': sum(solved_delays) / len(solved_delays) if solved_delays else None,
        'avg_latency': sum(latencies) / turns if turns else 0.0,
        'max_latency': max(latencies, default=0.0),
        'avg_pruning_efficiency': 100.0 * pruned / generated if generated else 0.0,
        'nodes_generated': generated, 'nodes_evaluated': evaluated, 'nodes_pruned': pruned,
        'timeout_count': timeout_count,
        'avg_completed_depth': sum(completed_depths) / turns if turns else 0.0,
        'full_depth_rate': 100.0 * full_depth_count / turns if turns else 0.0,
        'requested_depth': depth, 'ai_turns': turns, 'seed': seed,
        'board_size': board_size, 's_optimal': 10, 's_max': 30,
        'corpus_hash': corpus_hash, 'corpus_family': 'certified_sparse_race'
    }
