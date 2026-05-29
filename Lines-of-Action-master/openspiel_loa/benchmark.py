"""
Sanity checks and timing for OpenSpiel LOA + our teacher bot.

Run from Lines-of-Action-master::

    SDL_VIDEODRIVER=dummy python -m openspiel_loa.benchmark
    SDL_VIDEODRIVER=dummy python -m openspiel_loa.benchmark --games 10 --trace out.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import uuid

import pyspiel

from LOA.constants import Dims
from LOA.board import Board

from .bridge import action_to_grid_move, observation_to_grid, record_step
from .teacher import LoaTeacherBot, default_teacher_weights


def _check_legal_moves_match(state: pyspiel.State) -> bool:
    """True if our ``getValidMoves`` agrees with OpenSpiel on this state."""
    grid = observation_to_grid(state)
    Dims.generateDims(8)
    board = Board(8)
    board.simpleBoard = [list(row) for row in grid]
    stm = "B" if state.current_player() == 0 else "W"
    our_moves = set()
    for r in range(8):
        for c in range(8):
            if grid[r][c] != stm:
                continue
            for r1, c1 in board.getValidMoves(r, c):
                our_moves.add((r, c, r1, c1))
    os_moves = {action_to_grid_move(a) for a in state.legal_actions()}
    return our_moves == os_moves


def sanity_checks() -> None:
    print("=== OpenSpiel LOA sanity ===")
    game = pyspiel.load_game("lines_of_action")
    state = game.new_initial_state()
    print("game:", game)
    print("initial legal actions:", len(state.legal_actions()))
    print("obs shape:", game.observation_tensor_shape())
    assert _check_legal_moves_match(state), "legal moves mismatch at start"

    mismatches = 0
    plies = 0
    while not state.is_terminal() and plies < 100:
        if not _check_legal_moves_match(state):
            mismatches += 1
        action = state.legal_actions()[0]
        state.apply_action(action)
        plies += 1
    print(f"deterministic walk: {plies} plies, legal mismatches: {mismatches}")

    bot0 = LoaTeacherBot(0)
    bot1 = LoaTeacherBot(1)
    state = game.new_initial_state()
    while not state.is_terminal():
        bot = bot0 if state.current_player() == 0 else bot1
        action = bot.step(state)
        assert action in state.legal_actions(), f"illegal teacher action {action}"
        state.apply_action(action)
    print("teacher self-play finished, returns:", state.returns())
    print("weights:", default_teacher_weights())
    print("sanity OK\n")


def play_teacher_vs_random(
    games: int,
    seed: int,
    *,
    trace_path: str | None = None,
) -> dict:
    game = pyspiel.load_game("lines_of_action")
    teacher = LoaTeacherBot(0)
    rng_bot = pyspiel.make_uniform_random_bot(1, seed)
    teacher_wins = opp_wins = draws = 0
    per_game_s: list[float] = []
    trace_f = open(trace_path, "w", encoding="utf-8") if trace_path else None

    try:
        for g in range(games):
            episode_id = f"{seed}-{g}"
            state = game.new_initial_state()
            t0 = time.perf_counter()
            move_index = 0
            while not state.is_terminal():
                player = state.current_player()
                if player == 0:
                    action = teacher.step(state)
                else:
                    action = rng_bot.step(state)
                if trace_f is not None:
                    trace_f.write(
                        json.dumps(
                            record_step(
                                state,
                                action,
                                episode_id=episode_id,
                                move_index=move_index,
                            )
                        )
                        + "\n"
                    )
                state.apply_action(action)
                move_index += 1
            elapsed = time.perf_counter() - t0
            per_game_s.append(elapsed)
            rets = state.returns()
            if rets[0] > 0:
                teacher_wins += 1
            elif rets[0] < 0:
                opp_wins += 1
            else:
                draws += 1
            if trace_f:
                trace_f.flush()
    finally:
        if trace_f:
            trace_f.close()

    total = sum(per_game_s)
    return {
        "games": games,
        "teacher_wins": teacher_wins,
        "random_wins": opp_wins,
        "draws": draws,
        "timing": {
            "total_s": round(total, 3),
            "mean_s": round(total / games, 3) if games else 0,
            "min_s": round(min(per_game_s), 3) if per_game_s else 0,
            "max_s": round(max(per_game_s), 3) if per_game_s else 0,
        },
        "trace_path": trace_path,
    }


def play_teacher_self_play(games: int) -> dict:
    game = pyspiel.load_game("lines_of_action")
    bot0 = LoaTeacherBot(0, bot_id="strong_enc1")
    bot1 = LoaTeacherBot(1, bot_id="strong_enc1")
    per_game_s: list[float] = []

    for _g in range(games):
        state = game.new_initial_state()
        t0 = time.perf_counter()
        while not state.is_terminal():
            bot = bot0 if state.current_player() == 0 else bot1
            state.apply_action(bot.step(state))
        per_game_s.append(time.perf_counter() - t0)

    total = sum(per_game_s)
    return {
        "games": games,
        "mode": "teacher_self_play",
        "timing": {
            "total_s": round(total, 3),
            "mean_s": round(total / games, 3) if games else 0,
            "min_s": round(min(per_game_s), 3) if per_game_s else 0,
            "max_s": round(max(per_game_s), 3) if per_game_s else 0,
        },
    }


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="OpenSpiel LOA teacher sanity + benchmark")
    p.add_argument("--games", type=int, default=5, help="Games for timing (default 5)")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--trace", metavar="PATH", help="Write JSONL training records here")
    p.add_argument("--skip-sanity", action="store_true")
    p.add_argument(
        "--mode",
        choices=("vs_random", "self_play", "both"),
        default="both",
    )
    args = p.parse_args(argv)

    if not args.skip_sanity:
        sanity_checks()

    results = {}
    if args.mode in ("vs_random", "both"):
        print(f"=== teacher vs random ({args.games} games) ===")
        results["vs_random"] = play_teacher_vs_random(
            args.games, args.seed, trace_path=args.trace
        )
        r = results["vs_random"]
        print(
            f"teacher wins {r['teacher_wins']} — random {r['random_wins']} — "
            f"draws {r['draws']}"
        )
        print(f"timing: mean {r['timing']['mean_s']}s/game "
              f"(min {r['timing']['min_s']}, max {r['timing']['max_s']})")
        if args.trace:
            print(f"trace: {args.trace}")

    if args.mode in ("self_play", "both"):
        print(f"\n=== teacher self-play ({args.games} games) ===")
        results["self_play"] = play_teacher_self_play(args.games)
        t = results["self_play"]["timing"]
        print(f"timing: mean {t['mean_s']}s/game (min {t['min_s']}, max {t['max_s']})")

    print("\n" + json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
