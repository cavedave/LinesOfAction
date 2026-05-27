import random

from LOA.constants import WHITEID


class RandomBot:
    """Uniform random legal move (for smoke tests)."""

    def __init__(self, dim: int, seed: int = 0):
        self.dim = dim
        self._rng = random.Random(seed)

    def pick_move(self, board, turn_pid):
        char = "W" if turn_pid == WHITEID else "B"
        moves = []
        for r0 in range(self.dim):
            for c0 in range(self.dim):
                if board.simpleBoard[r0][c0] != char:
                    continue
                for r1, c1 in board.getValidMoves(r0, c0):
                    moves.append((r0, c0, r1, c1))
        if not moves:
            return None
        return self._rng.choice(moves)
