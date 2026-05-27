# LOA rules ([`rules.md`](rules.md)) vs this codebase

Olympiad-style rules from your excerpt, and how the current engine / harness behave.

| Rule | Meaning | Current behaviour | Gap? |
|------|---------|-------------------|------|
| 1 | Setup: Black on two rows (no corners), White on two files | [`Board.addPiecesToBoard`](Lines-of-Action-master/LOA/board.py) matches for 6×6 and 8×8 | OK |
| 2 | Black moves first | [`Game`](Lines-of-Action-master/LOA/game.py) starts `turn = BLACKID`; harness starts Black | OK |
| 3 | Move distance = count of all pieces on the full line (both directions) + moving piece | `getPiecesinPath` / `getNumbers` in Board and AI | OK (still worth more tests) |
| 4 | May jump own pieces | Allowed when opponent count on landing ray is 0 | OK |
| 5 | May not jump opponent; capture by landing | `getOpponentPiecesInPath` + `canJump` | OK |
| 6 | Win = all own pieces one 8-connected unit; one piece counts | `winner` / `winDFS` | OK after `winDFS` counts the start cell |
| 7 | **Simultaneous connection → draw** | `winner()` checks Black first, then White | **Bug:** if both complete a unit on the same ply, one side wins wrongly instead of draw |
| 8 | **If no legal move, must pass** | No `pass` in UI or AI; empty moves treated as leaf eval in search; harness treats `pick_move is None` as draw | **Bug:** should skip turn, not end game |
| 9 | **Third repetition with same player to move → draw** | Not implemented | **Missing** |

## Search performance (not a rules bug)

[`AI._child_positions`](Lines-of-Action-master/LOA/ai.py) still builds a **full new `simpleBoard` list-of-lists per child** (`nb = [list(row) for row in boardConfig]`). Negamax removed the old max/min duplication but **did not** add `make_move` / `undo_move` yet — that is the next performance step in your roadmap.

## Adjudication (harness)

Headless games use **`--adjudicate-plies`** (default **150**): if no winner after that many **half-moves** (each side’s move counts), the game is scored as a **draw** and a **one-line warning** is printed to **stderr**. **`--max-plies`** remains a hard safety cap (default 800).

The **Pygame** UI does not yet show this cap; only the harness enforces it unless you mirror the same counter in `Game`.
