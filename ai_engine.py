import random
from game_logic import GameState

def evaluate_board(state: GameState, player: int):
    if state.winner == player: return 9999
    if state.winner == 1 - player: return -9999

    score = 0
    target = (0, 8) if player == 0 else (8, 0)
    
    for r in range(9):
        for c in range(9):
            p = state.board[r][c]
            if p:
                dist = max(abs(r - target[0]), abs(c - target[1]))
                val = 100 - (dist * 10)
                if p.owner == player:
                    score += val
                else:
                    score -= val
    return score

def minimax(state: GameState, depth: int, alpha: float, beta: float, maximizing: bool, player: int):
    if depth == 0 or state.winner is not None:
        return evaluate_board(state, player), None

    valid_moves = state.get_valid_moves(state.current_turn)
    if not valid_moves:
        return -9999 if maximizing else 9999, None

    best_move = random.choice(valid_moves)

    if maximizing:
        max_eval = -float('inf')
        for move in valid_moves:
            state_copy = copy_state(state)
            state_copy.make_move(move[0], move[1])
            eval_val, _ = minimax(state_copy, depth - 1, alpha, beta, False, player)
            if eval_val > max_eval:
                max_eval = eval_val
                best_move = move
            alpha = max(alpha, eval_val)
            if beta <= alpha: break
        return max_eval, best_move
    else:
        min_eval = float('inf')
        for move in valid_moves:
            state_copy = copy_state(state)
            state_copy.make_move(move[0], move[1])
            eval_val, _ = minimax(state_copy, depth - 1, alpha, beta, True, player)
            if eval_val < min_eval:
                min_eval = eval_val
                best_move = move
            beta = min(beta, eval_val)
            if beta <= alpha: break
        return min_eval, best_move

def copy_state(state: GameState):
    import copy
    new_state = GameState()
    new_state.board = copy.deepcopy(state.board)
    new_state.current_turn = state.current_turn
    new_state.winner = state.winner
    return new_state

def get_ai_move(state: GameState, difficulty=2):
    _, move = minimax(state, depth=difficulty, alpha=-float('inf'), beta=float('inf'), maximizing=True, player=state.current_turn)
    return move