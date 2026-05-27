from __future__ import annotations

import json
import random
import sys
import time

from LOA.board import Board
from LOA.constants import BLACKID, DRAWID, Dims, WHITEID

DRAW_MAX = 0  # sentinel for draw (adjudication fuse or bot failure)


def _board_tuple(simple_board):
    return tuple(tuple(row) for row in simple_board)


def _opponent_pid(turn):
    return WHITEID if turn == BLACKID else BLACKID


def _pick_and_apply_random_black_opening(board, dim, rng):
    """Uniform random among all legal Black moves from ``board``; mutates ``board``."""
    moves = []
    for r in range(dim):
        for c in range(dim):
            if board.simpleBoard[r][c] != "B":
                continue
            for r1, c1 in board.getValidMoves(r, c):
                moves.append((r, c, r1, c1))
    if not moves:
        raise RuntimeError("harness: no legal Black move in random-opening setup (unexpected)")
    r0, c0, r1, c1 = rng.choice(moves)
    board.apply_move(r0, c0, r1, c1)
    return (r0, c0, r1, c1)


def play_one_game(
    black_bot,
    white_bot,
    dim: int,
    max_plies: int = 800,
    adjudicate_plies: int = 150,
    *,
    opening_rng: random.Random | None = None,
):
    """
    Run one game (Black moves first). Bots implement ``pick_move(board, turn_pid) -> (r0,c0,r1,c1)|None``.

    If ``opening_rng`` is set, the harness plays one uniformly random legal **Black** move
    from the standard start, then bots take over (White to move; one ply on the clock).
    Black still moves first in LOA; this only diversifies the branch played after that.

    Returns ``(result, reason, ply_count, opening_move)`` where ``opening_move`` is
    ``(r0,c0,r1,c1)`` if a random opening was applied, else ``None``.

    Rule 8 (pass) is applied automatically when a side has no legal move.
    Rule 9 (third repetition of position + side to move) yields ``DRAWID``.
    """
    Dims.generateDims(dim)
    board = Board(dim)
    turn = BLACKID
    rep_counts = {}
    ply_count = 0
    opening_move = None
    if opening_rng is not None:
        opening_move = _pick_and_apply_random_black_opening(board, dim, opening_rng)
        turn = WHITEID
        ply_count = 1

    while ply_count < max_plies:
        hw, who = board.winner()
        if hw:
            if who == DRAWID:
                return DRAWID, "simultaneous_connection", ply_count, opening_move
            return who, "win", ply_count, opening_move

        key = (_board_tuple(board.simpleBoard), turn)
        rep_counts[key] = rep_counts.get(key, 0) + 1
        if rep_counts[key] >= 3:
            return DRAWID, "repetition", ply_count, opening_move

        if ply_count >= adjudicate_plies:
            print(
                f"harness: adjudicate fuse — no winner after {adjudicate_plies} plies "
                f"(current ply_count={ply_count}, dim={dim}). Declaring draw (DRAW_MAX).",
                file=sys.stderr,
            )
            return DRAW_MAX, "adjudicate", ply_count, opening_move

        op = _opponent_pid(turn)
        if not board.side_has_legal_move(turn) and not board.side_has_legal_move(op):
            return DRAWID, "stalemate", ply_count, opening_move

        if not board.side_has_legal_move(turn):
            turn = op
            ply_count += 1
            continue

        bot = black_bot if turn == BLACKID else white_bot
        mv = bot.pick_move(board, turn)
        if mv is None:
            print(
                "harness: bot returned no move while a legal move existed — recording DRAW_MAX (illegal_bot_move).",
                file=sys.stderr,
            )
            return DRAW_MAX, "illegal_bot_move", ply_count, opening_move
        r0, c0, r1, c1 = mv
        board.apply_move(r0, c0, r1, c1)
        turn = op
        ply_count += 1

    print(
        f"harness: max_plies fuse — hit max_plies={max_plies} with no terminal (DRAW_MAX).",
        file=sys.stderr,
    )
    return DRAW_MAX, "max_plies", ply_count, opening_move


def run_batch(
    bot_a_id: str,
    bot_b_id: str,
    dim: int,
    games: int,
    max_plies: int = 800,
    adjudicate_plies: int = 150,
    *,
    time_games: bool = True,
    outcome_log_path: str | None = None,
    print_outcomes: bool = False,
    random_opening: bool = False,
    opening_seed: int | None = None,
):
    """
    ``bot_a_id`` / ``bot_b_id`` are harness registry bot ids.

    ``games`` must be **>= 1**. For **even** ``games >= 2``, indices alternate colours:
    even → **A Black** / **B White**; odd → swap, so each bot plays **half** as Black.

    ``games == 1`` runs a single pairing (**A Black**, **B White**) for smoke tests.

    Returns ``{"a_wins": n, "b_wins": n, "draws": n}`` plus optional ``timing`` when
    ``time_games`` is true (``total_s``, ``mean_s``, ``min_s``, ``max_s``, ``per_game_s``).

    If ``random_opening``, applies one uniform random Black first move per game (see
    ``play_one_game``). Per-game RNG seed is ``opening_seed + game_index`` when
    ``opening_seed`` is set; otherwise a random base is chosen once per batch.
    """
    from collections import Counter

    from harness.bots.factory import make_bot

    if games < 1:
        raise ValueError("games must be at least 1")
    if games >= 2 and games % 2 != 0:
        raise ValueError(
            "games must be even when >1 so each bot plays Black and White equally often"
        )

    if random_opening:
        if opening_seed is None:
            opening_base = random.getrandbits(62)
        else:
            opening_base = opening_seed
    else:
        opening_base = None

    a_wins = b_wins = draws = 0
    per_game_s = []
    reason_counts: Counter[str] = Counter()
    t0_batch = time.perf_counter()
    log_f = (
        open(outcome_log_path, "a", encoding="utf-8")
        if outcome_log_path
        else None
    )
    try:
        for g in range(games):
            bot_a = make_bot(bot_a_id, dim)
            bot_b = make_bot(bot_b_id, dim)
            t0 = time.perf_counter()
            opening_rng = random.Random(opening_base + g) if random_opening else None
            if g % 2 == 0:
                r, reason, plies, open_mv = play_one_game(
                    bot_a,
                    bot_b,
                    dim,
                    max_plies=max_plies,
                    adjudicate_plies=adjudicate_plies,
                    opening_rng=opening_rng,
                )
                black_id, white_id = bot_a_id, bot_b_id
            else:
                r, reason, plies, open_mv = play_one_game(
                    bot_b,
                    bot_a,
                    dim,
                    max_plies=max_plies,
                    adjudicate_plies=adjudicate_plies,
                    opening_rng=opening_rng,
                )
                black_id, white_id = bot_b_id, bot_a_id
            if time_games:
                per_game_s.append(time.perf_counter() - t0)

            reason_counts[reason] += 1
            line_obj = {
                "game": g,
                "black_bot": black_id,
                "white_bot": white_id,
                "result": r,
                "reason": reason,
                "plies": plies,
                "opening_move": list(open_mv) if open_mv is not None else None,
            }
            if log_f:
                log_f.write(json.dumps(line_obj) + "\n")
                log_f.flush()
            if print_outcomes:
                print(f"harness outcome: {line_obj}", file=sys.stderr)

            if r == DRAW_MAX or r == DRAWID:
                draws += 1
            elif r == BLACKID:
                if g % 2 == 0:
                    a_wins += 1
                else:
                    b_wins += 1
            else:
                if g % 2 == 0:
                    b_wins += 1
                else:
                    a_wins += 1
    finally:
        if log_f:
            log_f.close()
    out = {
        "a_wins": a_wins,
        "b_wins": b_wins,
        "draws": draws,
        "outcome_reasons": dict(reason_counts),
        "random_opening": random_opening,
        "opening_seed_base": opening_base,
    }
    if time_games and games > 0:
        total_wall = time.perf_counter() - t0_batch
        total_game = sum(per_game_s)
        out["timing"] = {
            "total_s": round(total_game, 6),
            "batch_wall_s": round(total_wall, 6),
            "mean_s": round(total_game / games, 6),
            "min_s": round(min(per_game_s), 6),
            "max_s": round(max(per_game_s), 6),
            "per_game_s": [round(x, 6) for x in per_game_s],
        }
    return out
