"""Scalar weights for :class:`LOA.ai.AI` evaluation (material, density, spread, PST).

These were previously hard-coded literals in ``_heuristic_white_minus_black`` and
``_eval_for_player``. Centralising them makes experiments reproducible and lets the
harness choose variants via ``registry.json`` (``"heuristic": { ... }`` on minimax bots).

**Tuning (separate from naming):** terms are correlated; changing one scalar (e.g.
``piece_count`` 10 → 11) without re-checking others rarely tells you much. Practical
next steps: self-play or harness round-robins at fixed depth, grid/random search over
this small parameter space, and log Elo or win rate — not hand-tweaking a single
coefficient in isolation.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from typing import Any, Mapping


@dataclass(frozen=True)
class HeuristicWeights:
    # _heuristic_white_minus_black
    piece_count: int = 10
    density: int = 10
    bounding_box_area: int = 10
    piece_square_table: int = 2
    # terminal win/loss magnitude before +depth bonus in _eval_for_player
    terminal_magnitude: int = 10000
    # Add mobility_weight × (stm_legal_moves − opp_legal_moves) for side to move; 0 = off
    mobility_weight: int = 0
    # 0 = PST/COM heuristic only; 100 = LoAdstone-normalized scalar only (_eval_for_player)
    loadstone_blend_pct: int = 0

    @classmethod
    def from_mapping(cls, m: Mapping[str, Any] | None) -> HeuristicWeights:
        """Build weights from a dict (e.g. registry JSON); unknown keys ignored."""
        if not m:
            return cls()
        base = asdict(cls())
        allowed = {f.name for f in fields(cls)}
        for k, v in m.items():
            if k in allowed:
                base[k] = int(v)
        return cls(**base)
