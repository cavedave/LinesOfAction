"""
OpenSpiel ``pyspiel.Bot`` wrapping our minimax teacher (``strong`` / ``strong_enc1`` eval).
"""

from __future__ import annotations

import pyspiel

from LOA.constants import BLACKID, WHITEID
from LOA.heuristic_weights import HeuristicWeights
from LOA.search_depth import AdaptiveDepthConfig
from harness.bots.minimax import MinimaxBot

from .bridge import _GridView, grid_move_to_action, observation_to_grid, os_player_to_char


def default_teacher_weights() -> HeuristicWeights:
    """
    Current best eval from harness sweeps (May 2026).

    ``strong`` baseline + ``enclosed_weight: 1`` (~55.7% vs strong over 200 games).
    Projection terms rejected (~50/50).
    """
    return HeuristicWeights(mobility_weight=5, enclosed_weight=1)


class LoaTeacherBot(pyspiel.Bot):
    """Minimax teacher using our eval + adaptive depth; plays OpenSpiel ``lines_of_action``."""

    def __init__(
        self,
        player_id: int,
        *,
        weights: HeuristicWeights | None = None,
        depth: int = 3,
        depth_deep: int = 4,
        adaptive_depth: bool = True,
        bot_id: str = "strong_enc1",
    ):
        pyspiel.Bot.__init__(self)
        self._player_id = player_id
        self._bot_id = bot_id
        self._inner = MinimaxBot(
            8,
            depth=depth,
            weights=weights or default_teacher_weights(),
            depth_deep=depth_deep,
            adaptive_depth=adaptive_depth,
        )

    @property
    def bot_id(self) -> str:
        return self._bot_id

    def player_id(self) -> int:
        return self._player_id

    def restart_at(self, state: pyspiel.State) -> None:
        pass

    def inform_action(self, state: pyspiel.State, player_id: int, action: int) -> None:
        pass

    def step(self, state: pyspiel.State) -> int:
        if state.is_terminal():
            raise RuntimeError("LoaTeacherBot.step called on terminal state")
        if state.current_player() != self._player_id:
            raise RuntimeError(
                f"LoaTeacherBot({self._player_id}) asked to move for player "
                f"{state.current_player()}"
            )

        legal = state.legal_actions()
        if not legal:
            raise RuntimeError("LoaTeacherBot: no legal actions (OpenSpiel should be terminal)")

        grid = observation_to_grid(state)
        stm = os_player_to_char(state.current_player())
        turn_pid = BLACKID if stm == "B" else WHITEID
        ply = int(state.move_number())

        view = _GridView(grid)
        move = self._inner.pick_move(view, turn_pid, ply)
        if move is None:
            return int(legal[0])

        action = grid_move_to_action(move, legal)
        if action is not None:
            return int(action)

        # Fallback: first legal (should be rare if move gens match)
        return int(legal[0])
