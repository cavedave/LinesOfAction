from __future__ import annotations

from LOA.ai import AI
from LOA.constants import WHITEID
from LOA.heuristic_weights import HeuristicWeights


class MinimaxBot:
    """Alpha-beta (negamax) bot; ``pick_move`` is grid-only (no pygame)."""

    def __init__(self, dim: int, depth: int = 3, weights: HeuristicWeights | None = None):
        self.dim = dim
        self.depth = depth
        self._ai = AI(dim, weights=weights)
        self._ai.depth = depth

    def pick_move(self, board, turn_pid):
        self._ai.dim = self.dim
        self._ai.depth = self.depth
        self._ai.simpleBoard = [list(row) for row in board.simpleBoard]
        mover = "W" if turn_pid == WHITEID else "B"
        _sc, mv = self._ai._negamax(
            self._ai.getConfig(), self.depth, float("-inf"), float("inf"), mover
        )
        return mv
