2.2 The Rules
LOA is played on an 8×8 board by two sides, Black and White. Each side has twelve
(checker) pieces at its disposal. In this thesis we are using the rules which are used
at the Computer Olympiads and at the MSO World Championships. Below they
are formulated in 9 rules. In some books, magazines or tournaments, the rules 2, 7,
8, and 9 are different from what is specified here.
1. The black pieces are placed in two rows along the top and bottom of the board,
while the white pieces are placed in two files at the left and right edge of the
board (see Figure 2.1a).
2. The players alternately move a piece, starting with Black.
3. A move takes place in a straight line, exactly as many squares as there are
pieces of either colour anywhere along the line of movement (see Figure 2.1b).
4. A player may jump over its own pieces.
5. A player may not jump over the opponent’s pieces, but can capture them by
landing on them.
6. The goal of a player is to be the first to create a configuration on the board
in which all own pieces are connected in one unit. Connected pieces are on
squares that are adjacent, either orthogonally or diagonally (e.g., see Figure
2.1c). A single piece is a connected unit.
7. In the case of simultaneous connection, the game is drawn.
8. If a player cannot move, this player has to pass.
9. If a position with the same player to move occurs for the third time, the game
is drawn.

---

## Rules this project actually follows

The nine rules above are the Olympiad / MSO formulation we aim to match in the
interactive game and in the headless harness (including rules 7–9).

**10. Ply fuse (harness / batch only, not Olympiad text).**  
If **150 plies** have been played with no winner under rules 1–9, the harness
declares the game drawn and stops. One **ply** is one turn action: either a
legal move or a forced pass (rule 8). This cap avoids infinite matches in
automated runs. The default **150** is configurable (for example
`--adjudicate-plies` in the harness CLI; `max_plies` is a separate hard ceiling).

The pygame client has **no** built-in 150-ply limit unless you add one; only
the harness applies rule 10 by default.