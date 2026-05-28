"""
Adaptive search depth: shallow (d3) by default, deeper (d4) in sparse or critical positions.

Used by :class:`LOA.ai.AI` (pygame, default on) and :class:`harness.bots.minimax.MinimaxBot`
(registry bot ``best`` / ``minimax_adaptive_mob5``). Triggers are OR'd — any one fires
``depth_deep``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, List

from . import loadstone_eval

if TYPE_CHECKING:
    from LOA.ai import AI


@dataclass(frozen=True)
class AdaptiveDepthConfig:
    """Thresholds for selective deepening (see :func:`choose_search_depth`)."""

    depth_shallow: int = 3
    depth_deep: int = 4
    # Deep search when stone count is at or below this (opening has ~24 on 8×8 olympiad edges).
    max_pieces_for_deep: int = 14
    # Component trigger only when pieces <= this (standard start has 2 components/side but ~24 stones).
    max_pieces_for_component_deep: int = 18
    # Deep search when side to move has at most this many legal moves at the root.
    max_root_moves_for_deep: int = 12
    # Deep search when either colour has at most this many 8-connected components (connect race).
    max_components_for_deep: int = 2
    # Deep search from this ply onward when ``ply`` is known (harness); 0 disables ply trigger.
    min_ply_for_deep: int = 30


def count_pieces(board: List[List[str]]) -> int:
    return sum(1 for row in board for cell in row if cell != "_")


def choose_search_depth(
    ai: AI,
    board: List[List[str]],
    stm_char: str,
    config: AdaptiveDepthConfig,
    *,
    ply: int | None = None,
) -> int:
    """
    Return ``depth_deep`` if the position is sparse or tactically sharp; else ``depth_shallow``.

    ``stm_char`` is ``'B'`` or ``'W'`` (side to move). ``ply`` is optional half-move index from harness.
    """
    pieces = count_pieces(board)

    if pieces <= config.max_pieces_for_deep:
        return config.depth_deep

    root_moves = ai._legal_moves_flat(board, stm_char)
    if len(root_moves) <= config.max_root_moves_for_deep:
        return config.depth_deep

    if pieces <= config.max_pieces_for_component_deep:
        nb_b = loadstone_eval.count_components_8conn(board, "B")
        nb_w = loadstone_eval.count_components_8conn(board, "W")
        if (
            nb_b <= config.max_components_for_deep
            or nb_w <= config.max_components_for_deep
        ):
            return config.depth_deep

    if (
        ply is not None
        and config.min_ply_for_deep > 0
        and ply >= config.min_ply_for_deep
    ):
        return config.depth_deep

    return config.depth_shallow
