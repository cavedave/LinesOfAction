from __future__ import annotations

from LOA.ai import AI
from LOA.constants import WHITEID
from LOA.heuristic_weights import HeuristicWeights
from LOA.search_depth import AdaptiveDepthConfig


class MinimaxBot:
    """Alpha-beta (negamax) bot; ``pick_move`` is grid-only (no pygame)."""

    def __init__(
        self,
        dim: int,
        depth: int = 3,
        weights: HeuristicWeights | None = None,
        *,
        depth_deep: int = 4,
        adaptive_depth: bool = False,
        adaptive_config: AdaptiveDepthConfig | None = None,
    ):
        self.dim = dim
        self.depth = depth
        self.depth_deep = depth_deep
        self.adaptive_depth = adaptive_depth
        self._adaptive_config = adaptive_config or AdaptiveDepthConfig(
            depth_shallow=depth,
            depth_deep=depth_deep,
        )
        self._ai = AI(
            dim,
            weights=weights,
            depth=depth,
            adaptive_depth=adaptive_depth,
            depth_deep=depth_deep,
        )
        self._ai._adaptive_config = self._adaptive_config

    def _search_depth(self, board, turn_pid, ply: int | None) -> int:
        stm = "W" if turn_pid == WHITEID else "B"
        cfg = [list(row) for row in board.simpleBoard]
        if not self.adaptive_depth:
            return self.depth
        return self._ai.search_depth_for(cfg, stm, ply=ply)

    def pick_move(self, board, turn_pid, ply: int | None = None):
        self._ai.dim = self.dim
        depth = self._search_depth(board, turn_pid, ply)
        self._ai.depth = depth
        self._ai.simpleBoard = [list(row) for row in board.simpleBoard]
        mover = "W" if turn_pid == WHITEID else "B"
        _sc, mv = self._ai._negamax(
            self._ai.getConfig(), depth, float("-inf"), float("inf"), mover
        )
        return mv
