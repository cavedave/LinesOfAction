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
    # Classic PST/COM leaf plus: mobility_weight × (stm_legal_moves − opp_legal_moves).
    # Default 5 (May 2026): harness sweep at depth 3, 8×8, random opening — compared
    # minimax_d3 (classic, weight 0) vs minimax_d3_mobN on opening_seed 42 for
    # N ∈ {1,2,3,5,8}. Low weights (1–3) beat classic by ~52–54% decisive; 5 jumped
    # to 76.5% decisive (75–23, 2 draws). Cross-seeds 7, 99, 1234: mob5 won 69–77%
    # decisive (291/394 ≈ 74% over 400 games). Weight 8 was slightly worse than 5 on
    # seed 42 (73.5% vs 76.5%). Full Loadstone eval at 100% blend was much weaker;
    # this term is the isolated Loadstone-style mobility bonus (stm − opp), not
    # Chaunier's full board_eval. Registry bots can override (e.g. minimax_d3_mob2).
    mobility_weight: int = 5
    # Classic + mobility plus: projection_weight × Loadstone (pe − ope) for side to move.
    # Isolated from enclosed and from full board_eval blend; tune via registry (e.g. strong_proj2).
    projection_weight: int = 0
    # Classic + mobility plus: enclosed_weight × Loadstone enclosed (after pe/ope passes).
    enclosed_weight: int = 0
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
