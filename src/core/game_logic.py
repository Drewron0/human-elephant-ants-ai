"""Board representation, legal moves and win conditions for Chess-Sut."""

from typing import Any

from config import settings

Coord = tuple[int, int]
MoveTuple = tuple[Coord, Coord]
PieceSpec = tuple[int, int, int, str]

PIECE_NAMES: dict[str, str] = {"H": "Human", "E": "Elephant", "A": "Ant"}
BEATS: dict[str, str] = {"H": "A", "A": "E", "E": "H"}
PREDATORS: dict[str, str] = {"A": "H", "E": "A", "H": "E"}


class Piece:
    """An immutable board piece, safe to share between cloned positions."""

    __slots__ = ("owner", "p_type")

    def __init__(self, owner: int, p_type: str) -> None:
        self.owner = owner
        self.p_type = p_type


def coord_label(coord: Coord, board_size: int) -> str:
    """Convert a (row, col) pair into a label such as ``A1``."""
    row, col = coord
    return f"{chr(65 + col)}{board_size - row}"


class Move:
    """A completed move and its algebraic notation."""

    __slots__ = ("start", "end", "piece_type", "is_capture", "board_size")

    def __init__(
        self,
        start: Coord,
        end: Coord,
        piece_type: str,
        is_capture: bool,
        board_size: int,
    ) -> None:
        self.start = start
        self.end = end
        self.piece_type = piece_type
        self.is_capture = is_capture
        self.board_size = board_size

    @property
    def notation(self) -> str:
        """Return notation such as ``H:a1-b2``, with ``x`` marking a capture."""
        separator = "x" if self.is_capture else "-"
        start = coord_label(self.start, self.board_size).lower()
        end = coord_label(self.end, self.board_size).lower()
        return f"{self.piece_type}:{start}{separator}{end}"


class GameState:
    """Mutable game position with undo history."""

    def __init__(
        self, board_size: int = settings.DEFAULT_BOARD_SIZE, custom_setup: bool = False
    ) -> None:
        if board_size < 2:
            raise ValueError("Board size must be at least 2")
        self.board_size = board_size
        self.board: list[list[Piece | None]] = [[None] * board_size for _ in range(board_size)]
        self.current_turn: int = 0
        self.total_turns: int = 0
        self.undos_p1: int = 0
        self.history: list[dict[str, Any]] = []
        self.notation: list[str] = []
        self.winner: int | None = None
        self.target_corners: dict[int, Coord] = {
            0: (0, board_size - 1),
            1: (board_size - 1, 0),
        }
        if not custom_setup:
            self._initialize_board()

    def _initialize_board(self) -> None:
        """Place the starting layout, mirroring player 1 onto the opposite corner."""
        size = self.board_size
        layout = settings.STARTING_LAYOUTS.get(size, ((size - 1, 0, "H"),))
        for row, col, piece_type in layout:
            self.board[row][col] = Piece(0, piece_type)
            self.board[size - 1 - row][size - 1 - col] = Piece(1, piece_type)

    def is_valid_coordinate(self, r: int, c: int) -> bool:
        """Return whether (r, c) lies on the board."""
        return 0 <= r < self.board_size and 0 <= c < self.board_size

    def get_piece(self, r: int, c: int) -> Piece | None:
        """Return the piece at (r, c), or None when empty or off-board."""
        return self.board[r][c] if self.is_valid_coordinate(r, c) else None

    def get_pieces(self) -> list[PieceSpec]:
        """Return every piece as a (row, col, owner, type) tuple."""
        return [
            (r, c, piece.owner, piece.p_type)
            for r, row in enumerate(self.board)
            for c, piece in enumerate(row)
            if piece
        ]

    def get_valid_moves_for_piece(self, r: int, c: int) -> list[MoveTuple]:
        """List one-step moves into empty squares or cyclic captures."""
        piece = self.get_piece(r, c)
        if not piece:
            return []
        valid: list[MoveTuple] = []
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                nr, nc = r + dr, c + dc
                if self.is_valid_coordinate(nr, nc):
                    target = self.board[nr][nc]
                    if target is None or (
                        target.owner != piece.owner and BEATS[piece.p_type] == target.p_type
                    ):
                        valid.append(((r, c), (nr, nc)))
        return valid

    def get_valid_moves(self, player: int) -> list[MoveTuple]:
        """List all legal moves for a player."""
        moves: list[MoveTuple] = []
        for r in range(self.board_size):
            for c in range(self.board_size):
                piece = self.board[r][c]
                if piece and piece.owner == player:
                    moves.extend(self.get_valid_moves_for_piece(r, c))
        return moves

    def make_move(self, start: Coord, end: Coord) -> Move | None:
        """Apply a legal move for the side to play; return None when it is illegal."""
        r1, c1 = start
        r2, c2 = end
        if (
            not self.is_valid_coordinate(r1, c1)
            or not self.is_valid_coordinate(r2, c2)
            or max(abs(r1 - r2), abs(c1 - c2)) != 1
        ):
            return None
        piece = self.board[r1][c1]
        if not piece or piece.owner != self.current_turn:
            return None
        target = self.board[r2][c2]
        if target is not None and (
            target.owner == piece.owner or BEATS[piece.p_type] != target.p_type
        ):
            return None

        self.history.append(
            {
                "board": [row[:] for row in self.board],
                "current_turn": self.current_turn,
                "winner": self.winner,
            }
        )
        move = Move(start, end, piece.p_type, target is not None, self.board_size)
        self.notation.append(move.notation)
        self.board[r2][c2] = piece
        self.board[r1][c1] = None

        if end == self.target_corners[piece.owner]:
            self.winner = piece.owner
        self.current_turn = 1 - self.current_turn
        self.total_turns += 1
        if self.winner is None and not self.get_valid_moves(self.current_turn):
            self.winner = 1 - self.current_turn
        return move

    def undo(self, count_action: bool = True) -> bool:
        """Restore the previous position; a two-ply undo counts as one action."""
        if not self.history:
            return False
        snapshot = self.history.pop()
        self.board = snapshot["board"]
        self.current_turn = snapshot["current_turn"]
        self.winner = snapshot["winner"]
        if self.notation:
            self.notation.pop()
        self.total_turns = max(0, self.total_turns - 1)
        if count_action:
            self.undos_p1 += 1
        return True

    def clone(self) -> "GameState":
        """Copy the position for search, without the undo history."""
        new_state = GameState.__new__(GameState)
        new_state.board_size = self.board_size
        new_state.target_corners = dict(self.target_corners)
        new_state.board = [row[:] for row in self.board]
        new_state.current_turn = self.current_turn
        new_state.total_turns = self.total_turns
        new_state.undos_p1 = self.undos_p1
        new_state.history = []
        new_state.notation = list(self.notation)
        new_state.winner = self.winner
        return new_state
