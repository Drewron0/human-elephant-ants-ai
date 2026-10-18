import copy
from typing import List, Tuple, Optional, Dict, Any

PIECE_NAMES = {
    'H': 'Human',
    'E': 'Elephant',
    'A': 'Ant'
}

BEATS = {
    'H': 'A',  # Human beats Ant
    'A': 'E',  # Ant beats Elephant
    'E': 'H'   # Elephant beats Human
}

TARGET_CORNERS = {
    0: (0, 8),  # Player 1 (bottom) target is top-right corner
    1: (8, 0)   # Player 2 (top) target is bottom-left corner
}

START_CORNERS = {
    0: (8, 0),  # Player 1 starts around bottom-left
    1: (0, 8)   # Player 2 starts around top-right
}


class Piece:
    __slots__ = ('owner', 'p_type')

    def __init__(self, owner: int, p_type: str):
        self.owner = owner  # 0: Player 1, 1: Player 2
        self.p_type = p_type  # 'H', 'E', 'A'

    def can_capture(self, target: 'Piece') -> bool:
        if target is None:
            return True
        if target.owner == self.owner:
            return False
        return BEATS.get(self.p_type) == target.p_type

    def to_dict(self) -> Dict[str, Any]:
        return {'owner': self.owner, 'p_type': self.p_type}

    @staticmethod
    def from_dict(data: Optional[Dict[str, Any]]) -> Optional['Piece']:
        if not data:
            return None
        return Piece(data['owner'], data['p_type'])

    def clone(self) -> 'Piece':
        return Piece(self.owner, self.p_type)


class Move:
    __slots__ = ('start', 'end', 'piece_type', 'is_capture', 'captured_type')

    def __init__(self, start: Tuple[int, int], end: Tuple[int, int], piece_type: str,
                 is_capture: bool = False, captured_type: Optional[str] = None):
        self.start = start
        self.end = end
        self.piece_type = piece_type
        self.is_capture = is_capture
        self.captured_type = captured_type

    @property
    def notation(self) -> str:
        r1, c1 = self.start
        r2, c2 = self.end
        sep = 'x' if self.is_capture else '-'
        return f"{self.piece_type}:{chr(97 + c1)}{9 - r1}{sep}{chr(97 + c2)}{9 - r2}"


class GameState:
    def __init__(self):
        self.board: List[List[Optional[Piece]]] = [[None for _ in range(9)] for _ in range(9)]
        self.current_turn: int = 0
        self.total_turns: int = 0
        self.undos_p1: int = 0
        self.undos_p2: int = 0
        self.history: List[Dict[str, Any]] = []
        self.notation: List[str] = []
        self.winner: Optional[int] = None
        self._initialize_board()

    @property
    def undos(self) -> int:
        return self.undos_p1 + self.undos_p2

    def _initialize_board(self):
        p1_setup = [
            (8, 0, 'H'), (8, 1, 'E'), (8, 2, 'A'), (8, 3, 'E'),
            (7, 0, 'A'), (7, 1, 'H'), (7, 2, 'E'),
            (6, 0, 'E'), (6, 1, 'H'),
            (5, 0, 'A')
        ]
        p2_setup = [
            (0, 8, 'H'), (0, 7, 'E'), (0, 6, 'A'), (0, 5, 'E'),
            (1, 8, 'A'), (1, 7, 'H'), (1, 6, 'E'),
            (2, 8, 'E'), (2, 7, 'H'),
            (3, 8, 'A')
        ]

        for r, c, pt in p1_setup:
            self.board[r][c] = Piece(0, pt)
        for r, c, pt in p2_setup:
            self.board[r][c] = Piece(1, pt)

    def is_valid_coordinate(self, r: int, c: int) -> bool:
        return 0 <= r < 9 and 0 <= c < 9

    def get_piece(self, r: int, c: int) -> Optional[Piece]:
        if self.is_valid_coordinate(r, c):
            return self.board[r][c]
        return None

    def get_valid_moves_for_piece(self, r: int, c: int) -> List[Tuple[Tuple[int, int], Tuple[int, int]]]:
        piece = self.get_piece(r, c)
        if not piece:
            return []

        valid = []
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                nr, nc = r + dr, c + dc
                if self.is_valid_coordinate(nr, nc):
                    target = self.board[nr][nc]
                    if target is None:
                        valid.append(((r, c), (nr, nc)))
                    elif target.owner != piece.owner and BEATS.get(piece.p_type) == target.p_type:
                        valid.append(((r, c), (nr, nc)))
        return valid

    def get_valid_moves(self, player: int) -> List[Tuple[Tuple[int, int], Tuple[int, int]]]:
        moves = []
        for r in range(9):
            for c in range(9):
                piece = self.board[r][c]
                if piece and piece.owner == player:
                    moves.extend(self.get_valid_moves_for_piece(r, c))
        return moves

    def make_move(self, start: Tuple[int, int], end: Tuple[int, int]) -> Optional[Move]:
        r1, c1 = start
        r2, c2 = end
        piece = self.board[r1][c1]
        if not piece or piece.owner != self.current_turn:
            return None

        target = self.board[r2][c2]
        if target is not None:
            if target.owner == piece.owner or BEATS.get(piece.p_type) != target.p_type:
                return None

        board_snapshot = [[(p.clone() if p else None) for p in row] for row in self.board]
        self.history.append({
            'board': board_snapshot,
            'current_turn': self.current_turn,
            'winner': self.winner
        })

        is_capture = (target is not None)
        captured_type = target.p_type if target else None
        move = Move(start, end, piece.p_type, is_capture, captured_type)
        self.notation.append(move.notation)

        self.board[r2][c2] = piece
        self.board[r1][c1] = None

        if piece.owner == 0 and (r2, c2) == TARGET_CORNERS[0]:
            self.winner = 0
        elif piece.owner == 1 and (r2, c2) == TARGET_CORNERS[1]:
            self.winner = 1

        self.current_turn = 1 - self.current_turn
        self.total_turns += 1

        if self.winner is None:
            next_moves = self.get_valid_moves(self.current_turn)
            if not next_moves:
                self.winner = 1 - self.current_turn

        return move

    def undo(self, player_idx: int = 0) -> bool:
        if not self.history:
            return False

        snapshot = self.history.pop()
        self.board = snapshot['board']
        self.current_turn = snapshot['current_turn']
        self.winner = snapshot['winner']
        if self.notation:
            self.notation.pop()
        self.total_turns = max(0, self.total_turns - 1)
        if player_idx == 0:
            self.undos_p1 += 1
        else:
            self.undos_p2 += 1
        return True

    def clone(self) -> 'GameState':
        new_state = GameState.__new__(GameState)
        new_state.board = [[(p.clone() if p else None) for p in row] for row in self.board]
        new_state.current_turn = self.current_turn
        new_state.total_turns = self.total_turns
        new_state.undos_p1 = self.undos_p1
        new_state.undos_p2 = self.undos_p2
        new_state.history = []
        new_state.notation = list(self.notation)
        new_state.winner = self.winner
        return new_state

    def to_dict(self) -> Dict[str, Any]:
        return {
            'board': [[(p.to_dict() if p else None) for p in row] for row in self.board],
            'current_turn': self.current_turn,
            'total_turns': self.total_turns,
            'undos_p1': self.undos_p1,
            'undos_p2': self.undos_p2,
            'notation': list(self.notation),
            'winner': self.winner
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'GameState':
        state = GameState.__new__(GameState)
        state.board = [[(Piece.from_dict(cell) if cell else None) for cell in row] for row in data['board']]
        state.current_turn = data['current_turn']
        state.total_turns = data.get('total_turns', 0)
        state.undos_p1 = data.get('undos_p1', data.get('undos', 0))
        state.undos_p2 = data.get('undos_p2', 0)
        state.notation = list(data.get('notation', []))
        state.winner = data.get('winner', None)
        state.history = []
        return state