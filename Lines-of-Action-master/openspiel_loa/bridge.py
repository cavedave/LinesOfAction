"""
Convert between OpenSpiel ``lines_of_action`` states and our grid (``B``/``W``/``_``).

OpenSpiel action ids use mixed-radix bases ``[8, 8, 8, 8, 2]`` for
``(from_row, from_col, to_row, to_col, capture)``. Row/col match our ``simpleBoard`` indices.
Player 0 = Black (``x``), player 1 = White (``o``).
"""

from __future__ import annotations

from typing import Any, List, Sequence, Tuple

import numpy as np
import pyspiel

ACTION_BASES = (8, 8, 8, 8, 2)
Grid = List[List[str]]
GridMove = Tuple[int, int, int, int]


def observation_tensor_shape() -> List[int]:
    return [3, 8, 8]


def observation_to_grid(state: pyspiel.State, *, player: int = 0) -> Grid:
    """Build 8×8 ``B``/``W``/``_`` grid from OpenSpiel observation tensor (3×8×8 planes)."""
    shape = observation_tensor_shape()
    obs = np.asarray(state.observation_tensor(player), dtype=np.float64).reshape(shape)
    rows, cols = shape[1], shape[2]
    grid: Grid = []
    for r in range(rows):
        row: List[str] = []
        for c in range(cols):
            if obs[0, r, c] > 0.5:
                row.append("B")
            elif obs[1, r, c] > 0.5:
                row.append("W")
            else:
                row.append("_")
        grid.append(row)
    return grid


def os_player_to_char(player: int) -> str:
    return "B" if player == 0 else "W"


def char_to_os_player(ch: str) -> int:
    return 0 if ch == "B" else 1


def unrank_action(action_id: int) -> Tuple[int, int, int, int, int]:
    n = int(action_id)
    digits: List[int] = []
    for base in reversed(ACTION_BASES):
        digits.append(n % base)
        n //= base
    digits.reverse()
    return digits[0], digits[1], digits[2], digits[3], digits[4]


def rank_action(r0: int, c0: int, r1: int, c1: int, capture: int) -> int:
    digits = (r0, c0, r1, c1, capture)
    n = 0
    for d, base in zip(digits, ACTION_BASES):
        n = n * base + d
    return n


def action_to_grid_move(action_id: int) -> GridMove:
    r0, c0, r1, c1, _cap = unrank_action(action_id)
    return r0, c0, r1, c1


def grid_move_to_action(
    move: GridMove,
    legal_actions: Sequence[int],
) -> int | None:
    """Map ``(r0,c0,r1,c1)`` to an OpenSpiel action id present in ``legal_actions``."""
    r0, c0, r1, c1 = move
    candidates = {rank_action(r0, c0, r1, c1, cap) for cap in (0, 1)}
    legal = set(int(a) for a in legal_actions)
    hit = candidates & legal
    if len(hit) == 1:
        return hit.pop()
    if len(hit) > 1:
        return min(hit)
    return None


class _GridView:
    """Minimal board view for :meth:`harness.bots.minimax.MinimaxBot.pick_move`."""

    __slots__ = ("simpleBoard",)

    def __init__(self, grid: Grid):
        self.simpleBoard = grid


def record_step(
    state: pyspiel.State,
    action: int,
    *,
    schema_version: str = "openspiel_loa_v1",
    rule_set: str = "winands_openspiel",
    episode_id: str | None = None,
    move_index: int | None = None,
) -> dict[str, Any]:
    """One JSON-serializable training record in OpenSpiel-native format."""
    player = state.current_player()
    grid = observation_to_grid(state)
    rec: dict[str, Any] = {
        "schema_version": schema_version,
        "rule_set": rule_set,
        "episode_id": episode_id,
        "move_index": move_index,
        "dim": 8,
        "stm": player,
        "stm_char": os_player_to_char(player),
        "board": grid,
        "observation_tensor": [float(x) for x in state.observation_tensor(player)],
        "observation_tensor_shape": observation_tensor_shape(),
        "legal_actions": [int(a) for a in state.legal_actions()],
        "action": int(action),
        "action_string": state.action_to_string(player, action),
        "grid_move": list(action_to_grid_move(action)),
        "move_number": int(state.move_number()),
    }
    return rec


def state_to_record(state: pyspiel.State, **kwargs) -> dict[str, Any]:
    """Snapshot without an applied action (terminal or mid-game)."""
    player = 0 if state.is_terminal() else state.current_player()
    grid = observation_to_grid(state, player=0)
    rec: dict[str, Any] = {
        "schema_version": kwargs.get("schema_version", "openspiel_loa_v1"),
        "rule_set": kwargs.get("rule_set", "winands_openspiel"),
        "dim": 8,
        "board": grid,
        "observation_tensor": [float(x) for x in state.observation_tensor(0)],
        "observation_tensor_shape": observation_tensor_shape(),
        "is_terminal": state.is_terminal(),
        "returns": list(state.returns()) if state.is_terminal() else None,
        "current_player": None if state.is_terminal() else int(state.current_player()),
        "move_number": int(state.move_number()),
    }
    if not state.is_terminal():
        rec["legal_actions"] = [int(a) for a in state.legal_actions()]
    return rec
