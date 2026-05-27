import argparse
import json
import sys

from harness.match import run_batch


def add_shared_harness_args(p: argparse.ArgumentParser) -> None:
    """Options common to default mode and ``compare``."""
    p.add_argument("--dim", type=int, default=6, choices=(6, 8))
    p.add_argument("--max-plies", type=int, default=800, help="Hard fuse: abort as draw after this many plies")
    p.add_argument(
        "--adjudicate-plies",
        type=int,
        default=150,
        help="Declare draw if no winner after this many plies (prints a stderr line each time a game hits this fuse)",
    )
    p.add_argument(
        "--no-timing",
        action="store_true",
        help="Disable per-game timing (omit timing fields and stderr summary)",
    )
    p.add_argument(
        "--outcome-log",
        metavar="PATH",
        default=None,
        help="Append one JSON object per line per game (result, reason, plies, black_bot, white_bot)",
    )
    p.add_argument(
        "--print-outcomes",
        action="store_true",
        help="Print each game outcome to stderr as one line (same fields as --outcome-log)",
    )
    p.add_argument(
        "--random-opening",
        action="store_true",
        help="Play one uniformly random legal Black move from the standard start, then let bots play (breaks duplicate deterministic games; Black still moves first in LOA).",
    )
    p.add_argument(
        "--opening-seed",
        type=int,
        default=None,
        metavar="N",
        help="With --random-opening, per-game RNG uses seed N + game_index (omit for a random base each batch, stored in JSON opening_seed_base).",
    )


def run_harness_batch(args, bot_a_id: str, bot_b_id: str, games: int) -> dict:
    stats = run_batch(
        bot_a_id,
        bot_b_id,
        args.dim,
        games,
        max_plies=args.max_plies,
        adjudicate_plies=args.adjudicate_plies,
        time_games=not args.no_timing,
        outcome_log_path=args.outcome_log,
        print_outcomes=args.print_outcomes,
        random_opening=args.random_opening,
        opening_seed=args.opening_seed,
    )
    timing = stats.get("timing")
    if timing is not None:
        print(
            f"harness timing: {games} games, play_one_game sum {timing['total_s']:.3f}s "
            f"(mean {timing['mean_s']:.3f}s/game, min {timing['min_s']:.3f}s, max {timing['max_s']:.3f}s; "
            f"full batch wall {timing['batch_wall_s']:.3f}s incl. bot setup)",
            file=sys.stderr,
        )
    print(json.dumps(stats, indent=2))
    return stats


def main_compare(argv: list[str] | None = None) -> None:
    """
    Champion vs challenger: same as ``--a champion --b challenger`` with ``--games rounds``.
    Even ``--rounds`` ⇒ colours swap each game (A Black on even game indices).
    """
    prog = "python -m harness compare"
    p = argparse.ArgumentParser(
        prog=prog,
        description="Balanced match: champion is bot A, challenger is bot B; use an even "
        "--rounds so each plays half the games as Black.",
    )
    add_shared_harness_args(p)
    p.add_argument("--champion", required=True, metavar="BOT_ID", help="Registry id (scores as harness 'a_wins')")
    p.add_argument("--challenger", required=True, metavar="BOT_ID", help="Registry id (scores as harness 'b_wins')")
    p.add_argument(
        "--rounds",
        type=int,
        default=100,
        metavar="N",
        help="Number of games (>=1); use an even N>1 for colour balance (default: 100)",
    )
    args = p.parse_args(argv)

    if args.rounds < 1:
        p.error("--rounds must be at least 1")
    if args.rounds >= 2 and args.rounds % 2 != 0:
        p.error("--rounds must be even when >1 so each side plays Black equally often")
    if args.rounds == 1:
        print(
            f"harness compare: --rounds 1 → {args.champion} Black, {args.challenger} White only",
            file=sys.stderr,
        )
    else:
        print(
            f"harness compare: {args.champion} (champion, A) vs {args.challenger} "
            f"(challenger, B) — {args.rounds} games, colours alternate",
            file=sys.stderr,
        )

    stats = run_harness_batch(args, args.champion, args.challenger, args.rounds)
    print(
        f"harness compare result: champion {args.champion} {stats['a_wins']} — "
        f"challenger {args.challenger} {stats['b_wins']} — draws {stats['draws']}",
        file=sys.stderr,
    )


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "compare":
        new_argv = [sys.argv[0]] + sys.argv[2:]
        main_compare(new_argv[1:])
        return

    p = argparse.ArgumentParser(
        description="Lines of Action headless harness. "
        'For championship-style labels: python -m harness compare --champion ID --challenger ID --rounds N'
    )
    add_shared_harness_args(p)
    p.add_argument(
        "--games",
        type=int,
        default=10,
        help="Number of games (>=1). For balanced colour, use an even count: even indices A Black / B White; odd indices swap. With --games 1, only A plays Black (quick smoke test).",
    )
    p.add_argument("--a", required=True, help="Bot A id (see harness/registry.json)")
    p.add_argument("--b", required=True, help="Bot B id")

    args = p.parse_args()
    if args.games < 1:
        p.error("--games must be at least 1")
    if args.games >= 2 and args.games % 2 != 0:
        p.error(
            "--games must be even when >1 so each bot plays the same number of games as Black "
            "and as White."
        )
    if args.games == 1:
        print(
            "harness: --games 1 → A is Black, B is White only (uneven colours; "
            "use an even count for balanced stats)",
            file=sys.stderr,
        )
    run_harness_batch(args, args.a, args.b, args.games)


if __name__ == "__main__":
    main()
