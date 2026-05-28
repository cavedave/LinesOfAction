"""
LoAdstone-style static evaluation from Claude Chaunier's ``loadstone.cpp`` (≈2005).

Implements projection counts, ``line_eval``, ``player_eval``, and the non-terminal
branch of ``board_eval`` ((projection terms + enclosed) scaled by MAX_NS·8 plus
mobility delta). Indices follow the original **1-based** row/col ``i,j`` on board
size ``N``: first player = ``0`` (Black ``'B'``), second = ``1`` (White ``'W'``).

Terminal one-component scores (``GAMEOVER_THRESHOLD``) are **not** mapped into this
repo's ``terminal_magnitude``; use :func:`winner` during search instead. Optionally
combine with PST heuristics via :class:`~LOA.heuristic_weights.HeuristicWeights`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from LOA.ai import AI

# Mirrors loadstone.cpp globals used by evaluation.
GAMEOVER_THRESHOLD = 0x40000000
MAX_NS = 64
MAX_N = 16  # author's fixed cap; line_eval uses MAX_N - 2 for min_n_moves cap


def _pid(ch: str) -> int | None:
    """Chaunier player index from cell character."""
    if ch == "B":
        return 0
    if ch == "W":
        return 1
    return None


@dataclass
class ProjectionTables:
    """Eight projection families × two players × line length (same layout as C)."""

    projected_1: List[List[int]]
    projected_2: List[List[int]]
    projected_3: List[List[int]]
    projected_4: List[List[int]]
    projected_01: List[List[int]]
    projected_12: List[List[int]]
    projected_23: List[List[int]]
    projected_34: List[List[int]]

    @staticmethod
    def empty(dim: int) -> "ProjectionTables":
        n = dim
        len_2 = 2 * n - 1
        len_01 = 3 * n - 2

        def zz(length: int) -> List[List[int]]:
            return [[0] * length, [0] * length]

        return ProjectionTables(
            projected_1=zz(n),
            projected_2=zz(len_2),
            projected_3=zz(n),
            projected_4=zz(len_2),
            projected_01=zz(len_01),
            projected_12=zz(len_01),
            projected_23=zz(len_01),
            projected_34=zz(len_01),
        )


def build_projections(board: List[List[str]], dim: int) -> ProjectionTables:
    """
    Fill projection counts for each player (``projected_inc`` per stone, owner only).
    Uses i = r+1, j = c+1 to match Chaunier's ``coord_project_*``.
    """
    pt = ProjectionTables.empty(dim)
    for r in range(dim):
        for c in range(dim):
            p = _pid(board[r][c])
            if p is None:
                continue
            i, j = r + 1, c + 1
            pt.projected_1[p][j - 1] += 1
            pt.projected_2[p][i + j - 2] += 1
            pt.projected_3[p][i - 1] += 1
            pt.projected_4[p][i - j + dim - 1] += 1
            pt.projected_01[p][j * 2 - i + dim - 2] += 1
            pt.projected_12[p][i + j * 2 - 3] += 1
            pt.projected_23[p][i * 2 + j - 3] += 1
            pt.projected_34[p][i * 2 - j + dim - 2] += 1
    return pt


def count_components_8conn(board: List[List[str]], piece: str) -> int:
    """8-neighbour connected components of ``piece`` (same adjacency as LoA)."""
    dim = len(board)
    seen = [[False] * dim for _ in range(dim)]
    ncomp = 0

    for r in range(dim):
        for c in range(dim):
            if board[r][c] != piece or seen[r][c]:
                continue
            ncomp += 1
            stack = [(r, c)]
            seen[r][c] = True
            while stack:
                cr, cc = stack.pop()
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        nr, ncc = cr + dr, cc + dc
                        if (
                            0 <= nr < dim
                            and 0 <= ncc < dim
                            and not seen[nr][ncc]
                            and board[nr][ncc] == piece
                        ):
                            seen[nr][ncc] = True
                            stack.append((nr, ncc))
    return ncomp


def line_eval(
    line: List[int],
    op_line: List[int],
    length: int,
    delta: int,
    real_nc: int,
    enclosed_accum: List[int],
) -> int:
    """
    Exact port of Chaunier's ``line_eval`` (pointer logic → indices).

    ``enclosed_accum`` is a one-element list updated like global ``enclosed`` in C.
    ``real_nc`` is ``nb_of_components[p]`` for the player whose ``line`` this is.
    """
    comp = [0] * (MAX_N * 2)
    nc = 0
    pos = 0
    opos = 0
    len_rem = length

    comp[0] = 0
    while pos < length and line[pos] == 0:
        len_rem -= 1
        if len_rem == 0:
            return 0
        opos += 1
        pos += 1

    while True:
        comp[nc] += line[pos]
        no = op_line[opos]
        opos += 1
        pos += 1
        len_rem -= 1

        while len_rem > 0 and pos < length and line[pos] != 0:
            comp[nc] += line[pos]
            no += op_line[opos]
            opos += 1
            pos += 1
            len_rem -= 1

        nc += 1
        enclosed_accum[0] += no
        if len_rem == 0:
            break

        comp[nc] = 1
        no = op_line[opos]
        opos += 1
        pos += 1
        len_rem -= 1

        while len_rem > 0 and pos < length and line[pos] == 0:
            comp[nc] += 1
            no += op_line[opos]
            opos += 1
            pos += 1
            len_rem -= 1

        if len_rem == 0:
            break

        enclosed_accum[0] += no
        comp[nc] //= delta
        if comp[nc] > 0:
            nc += 1
            comp[nc] = 0
        else:
            nc -= 1

    if nc == 1:
        return real_nc // 2

    comp[nc] = MAX_NS
    min_n_moves = MAX_N - 2

    for s0 in range(0, nc, 2):
        n_moves = 0
        g = s0 + 1
        comp_g = comp[g]
        s = 0
        comp_s = comp[0]

        while s < s0:
            d = min(comp_s, comp_g)
            n_moves += d
            if n_moves >= min_n_moves:
                return min_n_moves
            comp_s -= d
            if comp_s == 0:
                s += 2
                comp_s = comp[s]
            comp_g -= d
            if comp_g == 0:
                g += 2
                comp_g = comp[g]

        s = nc - 1
        comp_s = comp[s]
        while g < s:
            d = min(comp_s, comp_g)
            n_moves += d
            if n_moves >= min_n_moves:
                break
            comp_s -= d
            if comp_s == 0:
                s -= 2
                comp_s = comp[s]
            comp_g -= d
            if comp_g == 0:
                g += 2
                comp_g = comp[g]

        if n_moves < min_n_moves:
            min_n_moves = n_moves

    return min_n_moves


def player_eval(
    p: int,
    pt: ProjectionTables,
    dim: int,
    nb_of_components: List[int],
    enclosed_accum: List[int],
) -> int:
    """Max over eight ``line_eval`` calls (matches ``player_eval`` in C)."""
    real_nc = nb_of_components[p]
    op = p ^ 1
    len_1 = dim
    len_2 = 2 * dim - 1
    len_01 = 3 * dim - 2

    def le(line: List[int], opline: List[int], ln: int, delta: int) -> int:
        return line_eval(line, opline, ln, delta, real_nc, enclosed_accum)

    m1 = le(pt.projected_1[p], pt.projected_1[op], len_1, 1)
    m3 = le(pt.projected_3[p], pt.projected_3[op], len_1, 1)
    m2 = le(pt.projected_2[p], pt.projected_2[op], len_2, 2)
    m4 = le(pt.projected_4[p], pt.projected_4[op], len_2, 2)
    m01 = le(pt.projected_01[p], pt.projected_01[op], len_01, 3)
    m12 = le(pt.projected_12[p], pt.projected_12[op], len_01, 3)
    m23 = le(pt.projected_23[p], pt.projected_23[op], len_01, 3)
    m34 = le(pt.projected_34[p], pt.projected_34[op], len_01, 3)

    return max(max(max(m1, m3), max(m2, m4)), max(max(m01, m12), max(m23, m34)))


def _count_all_moves(ai: AI, board: List[List[str]], player_char: str) -> int:
    total = 0
    dim = len(board)
    for r in range(dim):
        for c in range(dim):
            if board[r][c] != player_char:
                continue
            total += len(ai.getValidMoves(r, c, board))
    return total


def mobility_stm_minus_opponent(ai: AI, board: List[List[str]], stm_char: str) -> int:
    """
    Count of legal moves for side to move minus count for opponent (same machinery as Loadstone mobility).

    Intuitive mobility bonus: positive when ``stm_char`` has more move options than the opponent.

    Chaunier's raw ``board_eval`` uses the opposite difference (opp − stm) inside ``board_eval_normalized``;
    if you blend Loadstone heavily, prefer ``mobility_weight = 0`` unless you deliberately want both.
    """
    opp = "W" if stm_char == "B" else "B"
    return _count_all_moves(ai, board, stm_char) - _count_all_moves(ai, board, opp)


def projection_stm_minus_opponent(
    board: List[List[str]], stm_char: str, dim: int
) -> int:
    """
    Loadstone projection differential ``pe − ope`` for ``stm_char`` (before ×2 and ×512 scaling).

    Uses the same ``player_eval`` order as :func:`board_eval_non_terminal` (opponent first,
    enclosed sign flip, then stm). Returns 0 if either colour has no stones.
    """
    stm_index = 0 if stm_char == "B" else 1
    nb_c = [
        count_components_8conn(board, "B"),
        count_components_8conn(board, "W"),
    ]
    if nb_c[0] == 0 or nb_c[1] == 0:
        return 0
    pt = build_projections(board, dim)
    enclosed: List[int] = [0]
    ope = player_eval(stm_index ^ 1, pt, dim, nb_c, enclosed)
    enclosed[0] = -enclosed[0]
    pe = player_eval(stm_index, pt, dim, nb_c, enclosed)
    return pe - ope


def enclosed_for_stm(board: List[List[str]], stm_char: str, dim: int) -> int:
    """
    Loadstone ``enclosed`` term for ``stm_char`` after opponent-then-stm ``player_eval`` passes.

    Matches the ``enclosed[0]`` used in :func:`board_eval_non_terminal` (before ×512 scaling).
    Returns 0 if either colour has no stones.
    """
    stm_index = 0 if stm_char == "B" else 1
    nb_c = [
        count_components_8conn(board, "B"),
        count_components_8conn(board, "W"),
    ]
    if nb_c[0] == 0 or nb_c[1] == 0:
        return 0
    pt = build_projections(board, dim)
    enclosed: List[int] = [0]
    player_eval(stm_index ^ 1, pt, dim, nb_c, enclosed)
    enclosed[0] = -enclosed[0]
    player_eval(stm_index, pt, dim, nb_c, enclosed)
    return enclosed[0]


def board_eval_terminal_value(
    stm_index: int,
    nb_components: List[int],
    missing_depth: int = 0,
) -> int | None:
    """
    Chaunier's win/loss static scores when either side has a single component.

    ``stm_index`` is side **to move** (0=B, 1=W). Returns ``None`` if not terminal.

    If a colour has no stones, ``nb_components`` is 0; the C original assumes a legal
    filled board, so we skip this rule when either entry is 0.

    Perspective: larger is better for the side to move (``stm_index``).
    """
    if nb_components[0] == 0 or nb_components[1] == 0:
        return None
    if nb_components[0] != 1 and nb_components[1] != 1:
        return None
    opp = stm_index ^ 1
    pack = (15 * (MAX_NS * 16) + missing_depth) * (MAX_NS * 8)
    if nb_components[opp] == 1:
        return GAMEOVER_THRESHOLD + pack + nb_components[stm_index]
    return -GAMEOVER_THRESHOLD - pack - nb_components[opp]


def board_eval_non_terminal(
    stm_index: int,
    nb_components: List[int],
    pt: ProjectionTables,
    dim: int,
    ai: AI,
    board: List[List[str]],
) -> int:
    """
    Chaunier's non-terminal ``board_eval``: ((pe−ope)·2 + enclosed)·512 + mobility.

    ``stm_index``: side to move (0 = Black, 1 = White).
    """
    enclosed: List[int] = [0]
    ope = player_eval(stm_index ^ 1, pt, dim, nb_components, enclosed)
    enclosed[0] = -enclosed[0]
    pe = player_eval(stm_index, pt, dim, nb_components, enclosed)

    stm_ch = "B" if stm_index == 0 else "W"
    opp_ch = "W" if stm_index == 0 else "B"
    mob = _count_all_moves(ai, board, opp_ch) - _count_all_moves(ai, board, stm_ch)

    return ((pe - ope) * 2 + enclosed[0]) * (MAX_NS * 8) + mob


def board_eval_full(
    board: List[List[str]],
    stm_char: str,
    dim: int,
    ai: AI,
    missing_depth: int = 0,
) -> int:
    """
    Full static evaluation from **side to move**'s perspective (Chaunier).

    Uses terminal scores when either colour is one 8-connected component; else
    :func:`board_eval_non_terminal`.
    """
    stm_index = 0 if stm_char == "B" else 1
    nb_c = [
        count_components_8conn(board, "B"),
        count_components_8conn(board, "W"),
    ]
    tv = board_eval_terminal_value(stm_index, nb_c, missing_depth)
    if tv is not None:
        return tv
    pt = build_projections(board, dim)
    return board_eval_non_terminal(stm_index, nb_c, pt, dim, ai, board)


def board_eval_normalized(
    board: List[List[str]],
    stm_char: str,
    dim: int,
    ai: AI,
    *,
    scale: float = 1.0 / float(MAX_NS * 8),
) -> float:
    """Same as :func:`board_eval_full` but scaled to smaller magnitudes (default ÷512)."""
    return float(board_eval_full(board, stm_char, dim, ai)) * scale
