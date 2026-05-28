# LOA — deferred work

Items we explicitly **postponed** (do the narrow engine/UI seam and harness first; see chat + harness plan).

## Architecture and platform

- [ ] **Bitboards** — replace list-of-lists board representation after the simple headless engine + tests are stable.
- [ ] **Full package split** — separate installable engine package vs Pygame UI; defer until bitboard / RL milestone (not required for in-repo harness).
- [ ] **RL environment** — Gymnasium / PettingZoo / custom env wrapping rules; after batch harness and rule confidence. See **RL / offline training data** below for trace format and pitfalls.

## RL / offline training data (future)

Planned use: **distillation / behavior cloning** plus a **value head**—e.g. store per-ply records with board, optional engineered features, teacher `search_policy` (π over moves), and terminal outcome. A policy transformer head learns π; an eval head learns outcome from state.

### Pitfalls and design checks (do not skip)

- [ ] **Leakage** — engineered features must not encode “cheating” signals: full move history disguised as aggregates, anything that reveals future outcome, or ambiguous definitions that accidentally depend on both players’ private search. Version every feature definition (`feature_schema_version`).
- [ ] **Side to move (`stm`)** — every row must record who is to move; omitting it conflates distinct game states. Align “self” vs “opp” features (or always use Black/White keyed fields) and document the convention.
- [ ] **Perspective for `game_result` / value target** — fix one convention (+1 from mover’s side, or always from learner seat, or always from White) and apply it to **every** row; otherwise value head labels are inconsistent.
- [ ] **`search_policy` semantics** — pure shallow minimax yields a **near-deterministic** π unless you add temperature, stochastic tie-breaks, or MCTS-style visit counts. Record how π was produced (`teacher_id`, depth, seed, temperature).
- [ ] **Stable move vocabulary** — every move in π must map to a reversible encoding: e.g. `(r0,c0,r1,c1)` or flat `from_sq`/`to_sq` with fixed `dim`; never opaque names without a schema. Keep `legal_moves` (or a legality bitvector) when feasible for training masks.
- [ ] **Temporal linkage** — rows should include at least `episode_id` and `move_index` (and optionally `ply_count`) so traces can be grouped and checked for RL transitions later.
- [ ] **Ambiguous feature names** — `projection_score`, `enclosure_score`, etc. need exact definitions in code that writes the trace; avoid dumping numbers without a spec.

### What to store per step (current working idea)

Minimal **v1 record** (extend as needed):

- `schema_version` — integer or string for trace format.
- `episode_id`, `move_index` — tie steps into a game.
- `dim` — board size (e.g. 6 or 8).
- `board` — position only: e.g. `simpleBoard` as a 2D grid of `B`/`W`/`_` (or numeric planes); axis convention matches engine (row, col).
- `stm` — `black` | `white` (or `BLACKID` / `WHITEID` as int).
- `legal_moves` (optional v1) — list of encoded legal moves for the side to move; helps policy masks and audits.
- `search_policy` — dict or sparse list: move encoding → probability or visit count; normalization method noted in schema.
- `engineered_features` (optional) — versioned struct, e.g. component counts, mobility, capture-related counts, centrality; definitions live next to the extractor.
- `game_result` — terminal **z** when the game ends (sparse), or document if you duplicate z on every row of the episode; if duplicated, same convention as value head.
- `terminal` (optional) — boolean on last row of episode.
- **Provenance** — `teacher_bot_id` or `search_config` (depth, heuristic registry id, `--random-opening` seed if used) for reproducibility.

Raw board + `stm` is the **non-negotiable** minimum; features and π are layered for distillation and auxiliary losses.

---

## Recommended near-term order (living plan)

1. **Regression safety** — tests for `Board.apply_move` / legality / wins + harness smoke before big eval refactors.
2. **MIA-style eval (modular)** — feature functions (quads subset, weighted mobility, average connectivity, walls later) + normalisation; combine via [`heuristic_weights`](file:///Users/davidcurran/Documents/LOA/Lines-of-Action-master/LOA/heuristic_weights.py)-style scalar weights for tournament/grid tuning.
3. **Mobility weight validation (follow-up)** — confirm default **`mobility_weight: 5`** at depth 4 and bracket the peak:
   - [x] **d4 smoke** — mob5 ahead of mob0 at d4 on seed 42 (50 games, ~61% decisive); full 100×4 deferred (too slow).
   - [ ] **mob4 / mob6 check** — `sweep-mobility --weights 4,5,6` (or manual A/B) on seed 42 at d3.
   - [x] **Adaptive d3→d4** — registry **`strong`**; **`best`/`fast`** = fixed d3 mob5 for RL (~20 s/game self-play at 8×8).
4. **Optional weight-tuning driver** — coordinate or random search over weights vs a fixed baseline (`harness` + `--random-opening`).
5. **RL trace writer (JSONL)** — minimal v1 per §RL / offline (`board`, `stm`, `episode_id`, `move_index`, provenance); extend with π / `legal_moves` when the teacher exposes them.
6. **Transposition table** — dict on `(board_tuple, stm)` first; Zobrist when nodes/sec matter.
7. **Bitboards / package split / multiprocess / UCI** — after core eval + traces feel stable.

---

## UI / presentation

- [ ] **Big `Board` drawing refactor** — keep pygame drawing as-is for now; only the **game driver** needs to be UI-free for batch play. Revisit layout/row-col cleanup when you polish UX.

## Harness and tooling (later phases)

- [ ] **Time limits per move** — for fair engine matches (mentioned in older notes; not implemented in CLI yet).
- [ ] **UCI (or similar) protocol** — only if you want to plug in external engines; in-process Python bots are enough initially.
- [ ] **Multiprocessing for batch games** — optional after single-process harness is correct and logged.
- [ ] **Zobrist hashing** for transposition table — after a working TT keyed by `tuple(tuple(row) for row in board)` (or `(hash, stm)`).

## Docs / assets

- [ ] **`rules-implementation.md`** — keep aligned with harness + pygame (adjudication, random opening, parity).
- [ ] **Optional screenshots** in Readme (`images/ss*.png`) — cosmetic; win banner already optional with text fallback.

---

## Done recently

- Narrow **engine path**: [`Board.apply_move`](file:///Users/davidcurran/Documents/LOA/Lines-of-Action-master/LOA/board.py), [`Game.apply_grid_move`](file:///Users/davidcurran/Documents/LOA/Lines-of-Action-master/LOA/game.py), AI uses grid only via `apply_grid_move` (no pixel `select` in [`AImove`](file:///Users/davidcurran/Documents/LOA/Lines-of-Action-master/LOA/ai.py)).
- **Checkerboard** pixel alignment and **`winDFS`** component count (Board + AI).
- **Olympiad-style rules** in pygame + harness (7–9): simultaneous draw, pass, repetition; **`DRAWID`** handling.
- **Harness**: colour balance with **even `--games` ≥2** (single-game smoke: `--games 1` = A Black only), **timing**, **`outcome_reasons`**, adjudicate fuse logging, **`--random-opening` / `--opening-seed`**.
- **Search**: in-place negamax apply/undo (no per-child full grid copy).
- **Heuristic tunables**: [`heuristic_weights.py`](file:///Users/davidcurran/Documents/LOA/Lines-of-Action-master/LOA/heuristic_weights.py) + registry `heuristic` overrides; example variant bots (e.g. bbox12, density12).
- **Loadstone port** ([`loadstone_eval.py`](file:///Users/davidcurran/Documents/LOA/Lines-of-Action-master/LOA/loadstone_eval.py)): full Chaunier eval optional via `loadstone_blend_pct`; **mobility-only** term (`stm − opp` legal move counts) tuned via harness — **default `mobility_weight: 5`** (see comment in `HeuristicWeights`; sweep seeds 42/7/99/1234 at d3).
- **`harness sweep-mobility`** + registry `minimax_d3_mob*` / `minimax_d4_mob*` ids for A/B tests.
- **Selective depth** ([`search_depth.py`](file:///Users/davidcurran/Documents/LOA/Lines-of-Action-master/LOA/search_depth.py)): registry **`strong`** (adaptive d3→d4); **`best`/`fast`** = fixed d3 mob5 for RL throughput (~20 s/game).
- Minimal **batch harness** + [`registry.json`](file:///Users/davidcurran/Documents/LOA/Lines-of-Action-master/harness/registry.json) bot ids (`minimax_d1`…`d5`, etc.).
- In-repo **[MIA extended abstract PDF](file:///Users/davidcurran/Documents/LOA/Lines-of-Action-master/LOA/MIA%20A%20World%20Champion%20LOA%20Program.pdf)** for eval feature roadmap (quads, walls, mobility weighting, …).

*Immediate next steps: follow **Recommended near-term order** above.*
