# Lines of Action AI: Fixes and Improvement Roadmap

Source reviewed: `ai.py` from the `inferiorzoned/Lines-of-Action` repository.

This note is meant to be read away from the computer. It explains the main fixes I would make to the current AI file, in a sensible order, with enough detail to turn each item into a small coding task.

The current file already has the important ingredients of a basic Lines of Action bot:

- board scanning
- legal move generation
- successor generation
- alpha-beta minimax search
- a handcrafted evaluation function
- connectedness/winner detection
- conversion of the chosen board into GUI clicks

The main goal now is not to make it fancy. The goal is to make it **correct, testable, readable, and fast enough to experiment with**.

---

## 1. First priority: separate the AI from the GUI

### Current behaviour

The `AImove(game)` method does two different jobs:

1. It asks the search algorithm to choose a move.
2. It clicks on the Pygame board by calling `game.select(...)` twice.

That means the AI is tightly coupled to the GUI. This makes it harder to test the bot from the command line, generate thousands of games, or later use it as a teacher for reinforcement learning.

### Proposed fix

Make the AI return a move, not perform GUI clicks.

Instead of this:

```python
board_after_move = self.alphaBetaMiniMax()
# infer from/to squares
# call game.select(...)
```

Prefer this:

```python
move = ai.choose_move(board, player="W")
game.apply_move(move)
```

A move can be represented as a small tuple:

```python
Move = tuple[int, int, int, int]
# (from_row, from_col, to_row, to_col)
```

For example:

```python
(0, 3, 3, 6)
```

means:

```text
move the piece from row 0, column 3 to row 3, column 6
```

### Why this matters

Once the AI returns moves, you can:

- test legal move generation without opening a window
- play AI-vs-AI games quickly
- generate training data
- compare two bots
- run profiling
- save games to disk
- later plug the same AI into Pygame, a CLI, or an RL environment

### Difficulty

Low to medium. This is mostly refactoring.

---

## 2. Replace “return board after move” with “return best move”

### Current behaviour

The current search functions return a whole board configuration:

```python
maxVal, boardConfig = self.alphaBetaMax(...)
return boardConfig
```

Then `AImove()` compares the old board to the new board to figure out which piece moved.

This works, but it is indirect.

### Problem

Inferring the move by comparing two boards can break or become awkward when:

- a capture happens
- two squares change in unexpected ways
- a future rule variation is added
- you want to record the actual move chosen
- you want to debug the search

### Proposed fix

Search should return:

```python
(score, best_move)
```

not:

```python
(score, resulting_board)
```

Example:

```python
def choose_move(board, player):
    score, move = negamax(board, depth=3, alpha=-inf, beta=inf, player=player)
    return move
```

### Why this matters

A search engine thinks in moves. Boards are positions. Returning the move is cleaner and makes the engine easier to inspect.

### Difficulty

Medium. It interacts with successor generation.

---

## 3. Generate moves, not successor boards

### Current behaviour

`getSuccessors()` creates a full new board for every legal move:

```python
dummy = [list(x) for x in boardConfig]
...
dummyCopy = [list(x) for x in dummy]
configs.append(dummyCopy)
```

This means that every node in the search tree allocates many new nested lists.

### Problem

Alpha-beta search visits many positions. If each position creates 20–40 copied boards, the program spends a lot of time allocating memory and copying lists.

For depth 3 this may be fine. For depth 5 or 6 it becomes expensive.

### Proposed fix

Split move generation from move application.

Use:

```python
def legal_moves(board, player):
    return list_of_moves
```

Then in the search:

```python
for move in legal_moves(board, player):
    captured = make_move(board, move)
    score = -negamax(board, depth - 1, -beta, -alpha, opponent(player))
    undo_move(board, move, captured)
```

The board is modified in place and then restored.

### Why this matters

This is one of the biggest practical speedups before bitboards.

Expected rough gain: **2× to 10×**, depending on how much time the current program spends copying boards.

### Difficulty

Medium. You need to be careful that `undo_move()` exactly reverses `make_move()`.

---

## 4. Use row-first board scanning for readability

### Current behaviour

The file often scans the board like this:

```python
[(r, c) for c in range(self.dim) for r in range(self.dim) if boardConfig[r][c] == 'W']
```

This loops through columns first, then rows.

It still checks every square, so it is not wrong. But it is visually surprising because most board code is written row-first.

### Proposed fix

Use this order instead:

```python
[(r, c) for r in range(self.dim) for c in range(self.dim) if boardConfig[r][c] == 'W']
```

### Why this matters

It matches the mental model:

```text
row 0: columns 0..7
row 1: columns 0..7
row 2: columns 0..7
...
```

This does not make the program much faster. It makes it easier to read and less error-prone.

### Difficulty

Low.

---

## 5. Fix and simplify winner detection

### Current behaviour

`winner()` finds the number of white and black pieces, picks a starting piece for each colour, then calls `winDFS()`.

There is a subtle issue in `winDFS()`:

```python
connectedPieces = 0
visited, stack = set(), [(i, j)]
```

The starting square is not immediately added to `visited`, and `connectedPieces` starts at 0. The code increments when neighbours are found.

### Why this is risky

For connected-component counting, the normal pattern is:

```python
visited = {start}
count = 1
```

The current version may still often work because neighbours can cause the start square to be revisited later, but it is nonstandard and easy to reason about incorrectly.

### Proposed fix

Write a general connected-component function:

```python
NEIGHBOURS_8 = [
    (-1, -1), (-1, 0), (-1, 1),
    (0, -1),           (0, 1),
    (1, -1),  (1, 0),  (1, 1),
]


def connected_component_size(board, start, player):
    visited = {start}
    stack = [start]

    while stack:
        r, c = stack.pop()
        for dr, dc in NEIGHBOURS_8:
            nr, nc = r + dr, c + dc
            if not within_board(nr, nc):
                continue
            if (nr, nc) in visited:
                continue
            if board[nr][nc] != player:
                continue
            visited.add((nr, nc))
            stack.append((nr, nc))

    return len(visited)
```

Then winner detection becomes:

```python
def is_connected(board, player):
    pieces = piece_positions(board, player)
    if len(pieces) <= 1:
        return True
    return connected_component_size(board, pieces[0], player) == len(pieces)
```

### Why this matters

Lines of Action is won by connectedness. This is the most important rule to get correct.

### Difficulty

Low to medium. Add tests.

---

## 6. Add tests before changing the engine too much

### Current problem

The code is game code plus AI code plus UI interaction. There are no obvious tests in this file.

Before making the AI faster, add tests for rules.

### Tests I would write first

#### 6.1 Board bounds

```python
assert within_board(0, 0)
assert within_board(7, 7)
assert not within_board(-1, 0)
assert not within_board(8, 0)
assert not within_board(0, 8)
```

#### 6.2 Connected group detection

Use small artificial boards.

```text
W W _ _
_ W _ _
_ _ _ _
_ _ _ _
```

White should be connected.

```text
W _ _ W
_ _ _ _
_ _ _ _
_ _ _ _
```

White should not be connected.

#### 6.3 Lines of Action movement distance

In LOA, a piece moves exactly as many squares as there are pieces on that line.

Test one row, one column, one diagonal.

#### 6.4 Cannot jump over opponent pieces

A move is illegal if an opponent piece lies between the start and destination.

#### 6.5 Can jump over own pieces

A move can pass over friendly pieces.

#### 6.6 Can capture opponent at destination

A move can land on an opponent piece and capture it.

#### 6.7 Cannot land on own piece

A move cannot land on a friendly piece.

### Why this matters

If legal move generation is slightly wrong, the bot will learn or search the wrong game.

For an RL project, rule bugs are disastrous because the agent can exploit them.

### Difficulty

Low. Use `pytest`.

---

## 7. Replace minimax max/min pair with negamax

### Current behaviour

There are two search functions:

```python
def alphaBetaMax(...):
    ...

def alphaBetaMin(...):
    ...
```

They are nearly mirror images.

### Proposed fix

Use one function:

```python
def negamax(board, depth, alpha, beta, player):
    if depth == 0 or game_over(board):
        return evaluate(board, player), None

    best_score = -inf
    best_move = None

    for move in ordered_moves(board, player):
        captured = make_move(board, move)
        score, _ = negamax(board, depth - 1, -beta, -alpha, opponent(player))
        score = -score
        undo_move(board, move, captured)

        if score > best_score:
            best_score = score
            best_move = move

        alpha = max(alpha, score)
        if alpha >= beta:
            break

    return best_score, best_move
```

### Important detail

Evaluation must be from the current player’s point of view.

One clean approach:

```python
def evaluate(board, player):
    white_score = evaluate_white_minus_black(board)
    if player == "W":
        return white_score
    else:
        return -white_score
```

### Why this matters

Negamax does not automatically make the bot stronger. It makes the search code shorter and easier to improve.

### Difficulty

Medium.

---

## 8. Add move ordering

### Current behaviour

The search checks successors in whatever order they are generated.

Alpha-beta pruning is much stronger if good moves are searched first.

### Proposed move ordering ideas for LOA

Search these moves first:

1. Immediate winning moves.
2. Captures.
3. Moves that reduce your number of connected components.
4. Moves that increase your largest connected group.
5. Moves that block opponent connection.
6. Moves toward the centre.
7. Moves that reduce bounding-box area.

Example scoring function:

```python
def move_order_score(board, move, player):
    score = 0

    if move_is_capture(board, move, player):
        score += 100

    if move_lands_near_own_pieces(board, move, player):
        score += 20

    if move_goes_towards_centre(move):
        score += 5

    return score
```

Then:

```python
moves = legal_moves(board, player)
moves.sort(key=lambda m: move_order_score(board, m, player), reverse=True)
```

### Why this matters

Move ordering can change alpha-beta from “barely useful” to “very powerful”.

Expected gain can be huge. In ideal cases, alpha-beta with good move ordering searches roughly the square root of the nodes that plain minimax would search. In practice, for a small game engine, it may feel like getting an extra ply or two.

### Difficulty

Low to medium.

---

## 9. Add iterative deepening

### Current behaviour

The AI searches to a fixed depth:

```python
self.depth = 3
```

### Proposed fix

Search depth 1, then 2, then 3, etc., until time runs out.

```python
def choose_move_with_time_limit(board, player, seconds):
    best_move = None
    depth = 1
    deadline = time.time() + seconds

    while time.time() < deadline:
        score, move = negamax_root(board, depth, player, deadline)
        if time.time() < deadline:
            best_move = move
        depth += 1

    return best_move
```

### Why this matters

Iterative deepening gives you:

- a usable move even if time runs out
- better move ordering from previous depths
- easier time controls
- smoother difficulty settings

### Difficulty

Medium.

---

## 10. Add a transposition table

### Current problem

The same board position can be reached by different move orders.

Alpha-beta may re-search the same position many times.

### Proposed fix

Cache search results in a dictionary:

```python
transposition_table = {}
```

Key:

```python
key = board_to_key(board), player, depth
```

Value:

```python
(score, best_move, depth_searched)
```

Simple first version:

```python
def board_to_key(board):
    return tuple(tuple(row) for row in board)
```

Later, use Zobrist hashing.

### Why this matters

This can save a lot of repeated work.

For board games, transposition tables are one of the standard alpha-beta improvements.

### Difficulty

Medium.

---

## 11. Consider Zobrist hashing after the simple table works

### What is Zobrist hashing?

Zobrist hashing gives each possible piece-on-square fact a random integer.

For example:

```text
white on A1 -> random 64-bit number
black on A1 -> random 64-bit number
white on A2 -> random 64-bit number
...
```

The board hash is the XOR of all relevant numbers.

When a move is made, update the hash by XORing out the old piece position and XORing in the new one.

### Why this matters

A tuple-of-tuples board key is easy and good enough at first.

Zobrist hashing is faster when you are searching many nodes and making/undoing moves in place.

### Difficulty

Medium to high.

Do not start here.

---

## 12. Improve the evaluation function

The current evaluation has these ideas:

- material difference
- density around centre of mass
- bounding-box area
- piece-square table
- terminal win/loss score

These are good first ideas. But LOA is mainly a connection game, so the evaluation should emphasize connectedness more directly.

### Add connected-component count

A player with fewer groups is closer to winning.

```python
score += (black_components - white_components) * weight
```

From White’s point of view:

- fewer white components is good
- fewer black components is bad

So:

```python
score += 100 * (components_black - components_white)
```

### Add largest connected group

If White has 8 pieces and 5 are already connected, that is promising.

```python
score += 20 * (largest_white_group - largest_black_group)
```

### Add mobility

Mobility is the number of legal moves.

```python
score += 2 * (white_mobility - black_mobility)
```

This should probably be a smaller term than connectedness.

### Add immediate threats

If a player has a move that wins immediately, that should dominate normal positional features.

```python
if has_immediate_win(board, "W"):
    score += 1000
if has_immediate_win(board, "B"):
    score -= 1000
```

### Add distance/compactness features

The current density and bounding-box area are both attempts to measure compactness.

You can keep them, but compare them against connected-component features.

Possible compactness measures:

- average distance to centre of mass
- bounding-box area
- sum of pairwise distances
- distance from each piece to nearest friendly piece
- minimum spanning tree length over pieces

For a first bot, I would use:

1. connected components
2. largest group size
3. bounding-box area
4. mobility
5. material
6. centre table

### Suggested first evaluation formula

```python
score = 0
score += 200 * (components_black - components_white)
score += 40  * (largest_group_white - largest_group_black)
score += 10  * (material_white - material_black)
score += 5   * (mobility_white - mobility_black)
score += 5   * (area_black - area_white)
score += 2   * (centre_score_white - centre_score_black)
```

These numbers are not sacred. They are starting guesses.

### Why this matters

The current evaluation rewards compactness, but a compact blob is not always the same thing as a connected winning structure. Connected-component features are closer to the actual objective.

### Difficulty

Medium.

---

## 13. Be careful with material in Lines of Action

### Current behaviour

The evaluation rewards having more pieces:

```python
score += (NoofWhitePieces - NoofBlackPieces) * 10
```

### Why this is not obviously correct

In many games, material advantage is simply good. In LOA, having fewer pieces can sometimes make it easier to connect all your pieces.

That does not mean material is bad. Capturing removes opponent options and can disrupt their structure. But material should probably not dominate the evaluation.

### Proposed fix

Keep material as a small feature, not a huge one.

Also test whether the bot improves or worsens when material weight is changed.

Example experiment:

```text
Bot A: material weight 0
Bot B: material weight 5
Bot C: material weight 10
Bot D: material weight 20
```

Have them play a round-robin tournament.

### Difficulty

Low.

---

## 14. Add automatic weight tuning later

### Chess analogy

In chess engines, handcrafted features such as bishop value, rook-on-open-file bonuses, king safety, and pawn structure can be tuned from games.

You can do the same for LOA.

### Simple method

Define an evaluation function with weights:

```python
score = (
    w_components * component_feature
    + w_largest_group * largest_group_feature
    + w_mobility * mobility_feature
    + w_area * area_feature
    + w_material * material_feature
    + w_centre * centre_feature
)
```

Then run tournaments between different weight settings.

### Simple hill-climbing

1. Start with hand-chosen weights.
2. Randomly change one weight.
3. Play matches between old and new bot.
4. Keep the new weights if they win.
5. Repeat.

### More advanced methods

- genetic algorithms
- Bayesian optimization
- Texel-style tuning from labelled positions
- reinforcement learning over evaluation weights

### Why this matters

Before neural networks, a tuned alpha-beta bot can become a strong teacher and a useful benchmark.

### Difficulty

Medium to high.

---

## 15. Add a perft-style move-generation test

### What is perft?

In chess programming, `perft` means “performance test”. It counts the number of legal move sequences to a given depth.

For example:

```text
perft(position, 1) = number of legal moves
perft(position, 2) = number of legal move pairs
perft(position, 3) = number of legal move triples
```

### Why this helps

It is a very good way to catch move-generation bugs.

If you change the move generator and `perft` changes unexpectedly, you know something broke.

### Example

```python
def perft(board, player, depth):
    if depth == 0:
        return 1

    total = 0
    for move in legal_moves(board, player):
        captured = make_move(board, move)
        total += perft(board, opponent(player), depth - 1)
        undo_move(board, move, captured)

    return total
```

Store known counts for a few positions.

### Difficulty

Medium.

---

## 16. Use profiling before heavy optimization

### What to measure

Before bitboards, run Python profiling.

Useful tools:

```bash
python -m cProfile -o profile.out your_script.py
```

Then inspect with:

```bash
python -m pstats profile.out
```

Or use `snakeviz` if installed.

### Likely hotspots in the current file

Expected expensive functions:

- `getSuccessors()`
- board copying
- `getValidMoves()`
- `winner()`
- `winDFS()`
- `eval()`

### Why this matters

You do not want to spend days optimizing something that only uses 3% of the runtime.

### Difficulty

Low.

---

## 17. Bitboards: powerful but not the first fix

### Current representation

The current board is a list of lists containing strings:

```python
board[r][c] in {"W", "B", "_"}
```

This is readable, but each square lookup involves Python list indexing and string comparison.

### Bitboard representation

Use two integers:

```python
white_bits: int
black_bits: int
```

Each bit represents one square.

For an 8×8 board:

```text
bit 0  = square 0
bit 1  = square 1
...
bit 63 = square 63
```

Then:

```python
occupied = white_bits | black_bits
empty = ~occupied
```

### Rough efficiency guess

Compared with the current list-of-lists Python code:

- cached piece lists: maybe **2× to 5× faster**
- make/undo instead of board copying: maybe **2× to 10× faster**
- bitboards in Python: maybe **3× to 20× faster** for board operations
- bitboards in C/C++/Rust: maybe **20× to 100×+ faster** for engine-style search

These are rough guesses, not guarantees.

### Why not start with bitboards?

Bitboards make the code harder to read.

For a learning project, the best order is:

1. correct simple board
2. tested move generator
3. clean negamax search
4. move ordering
5. transposition table
6. profile
7. bitboards if needed

### Difficulty

High.

---

## 18. Cache piece lists or maintain them incrementally

### Current behaviour

The code repeatedly scans the whole board to find pieces:

```python
whitePieces = [(r, c) for r in range(dim) for c in range(dim) if board[r][c] == "W"]
blackPieces = [(r, c) for r in range(dim) for c in range(dim) if board[r][c] == "B"]
```

On an 8×8 board this is only 64 squares, so it is not terrible. But search calls this many times.

### Proposed intermediate fix

Make one helper:

```python
def piece_positions(board, player):
    return [(r, c) for r in range(8) for c in range(8) if board[r][c] == player]
```

Then later, store piece lists in the position object:

```python
@dataclass
class Position:
    board: list[list[str]]
    white_pieces: set[tuple[int, int]]
    black_pieces: set[tuple[int, int]]
    side_to_move: str
```

When a move is made, update the relevant set.

### Why this matters

It reduces repeated scanning and makes evaluation code clearer.

### Difficulty

Low first, medium later.

---

## 19. Make constants explicit

### Current behaviour

The code imports several constants:

```python
from .constants import WHITEID, BLACKID, DIR, DIRECTIONS, DIRX, DIRY, Dims
```

But inside the AI file, it also uses raw strings:

```python
'W'
'B'
'_'
```

### Proposed fix

Define and consistently use:

```python
WHITE = "W"
BLACK = "B"
EMPTY = "_"
PLAYERS = (WHITE, BLACK)
```

Then use:

```python
if board[r][c] == WHITE:
```

instead of:

```python
if board[r][c] == 'W':
```

### Why this matters

It avoids typos and makes later changes easier.

### Difficulty

Low.

---

## 20. Remove unused imports and dead code

### Current imports

The file imports:

```python
import sys
from copy import deepcopy
from .board import Board
```

But these do not seem to be used in the AI file.

### Proposed fix

Remove unused imports.

Also remove old commented-out debugging code once it is no longer useful.

### Why this matters

Small cleanup, but it makes the file less noisy.

### Difficulty

Very low.

---

## 21. Do not shadow Python built-ins

### Current behaviour

The code uses `str` as a variable name:

```python
def __str__(self):
    str = ""
    ...
```

`str` is also the name of Python’s string type.

### Proposed fix

Use:

```python
text = ""
```

or:

```python
lines = []
```

Better:

```python
def __str__(self):
    return "\n".join(" ".join(row) for row in self.simpleBoard)
```

### Why this matters

It avoids confusing bugs and improves style.

### Difficulty

Very low.

---

## 22. Fix `printBoard`

### Current behaviour

`printBoard(config)` is defined inside the class but does not take `self`:

```python
def printBoard(config):
    str = ""
    for r in range(self.dim):
        ...
```

This uses `self.dim`, but `self` is not defined in the function.

### Proposed fix

Either make it a normal method:

```python
def printBoard(self, config):
    ...
```

or a standalone helper:

```python
def print_board(config):
    for row in config:
        print(" ".join(row))
```

### Why this matters

This is a small correctness bug.

### Difficulty

Very low.

---

## 23. Better naming

### Current names

Some names are unclear:

```python
id
op
dummy
dummyCopy
confg
posn
t
areaA
areaB
```

### Proposed names

Use:

```python
player
opponent_player
board_copy
successor_board
child_score
row_index
col_index
white_area
black_area
```

### Why this matters

Search code is naturally tricky. Good names reduce cognitive load.

### Difficulty

Low.

---

## 24. Use a small `Move` type

### Proposed type

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class Move:
    from_row: int
    from_col: int
    to_row: int
    to_col: int
```

This is more readable than plain tuples.

Instead of:

```python
move[0], move[1], move[2], move[3]
```

use:

```python
move.from_row
move.from_col
move.to_row
move.to_col
```

### Why this matters

It makes debugging much easier.

### Difficulty

Low.

---

## 25. Suggested order of work

Do not try to do everything at once.

### Stage 1: Correctness and readability

1. Remove unused imports.
2. Add constants for `WHITE`, `BLACK`, `EMPTY`.
3. Change board scans to row-first order.
4. Fix `winDFS()` to count the starting piece properly.
5. Fix `printBoard()`.
6. Add tests for movement and connectedness.

### Stage 2: Cleaner engine structure

7. Separate AI from GUI clicks.
8. Return moves instead of resulting boards.
9. Generate legal moves instead of successor boards.
10. Add `make_move()` and `undo_move()`.

### Stage 3: Better search

11. Convert alpha-beta max/min into negamax.
12. Add move ordering.
13. Add iterative deepening.
14. Add a transposition table.

### Stage 4: Better evaluation

15. Add connected-component count.
16. Add largest-group size.
17. Add mobility.
18. Add immediate-win/threat detection.
19. Tune evaluation weights through self-play tournaments.

### Stage 5: Performance

20. Profile the code.
21. Cache piece lists or use a `Position` object.
22. Consider Zobrist hashing.
23. Consider bitboards only if the simple engine is too slow.

---

## 26. Minimal target architecture

A nice simple version of the project could look like this:

```text
loa/
  constants.py
  move.py
  board.py
  rules.py
  evaluate.py
  search.py
  cli.py
  pygame_ui.py
  tests/
    test_moves.py
    test_connectedness.py
    test_search.py
```

### `rules.py`

Responsible for:

- legal moves
- move distance
- jump/capture legality
- winner detection

### `evaluate.py`

Responsible for:

- score position
- connectedness features
- mobility features
- area/density features

### `search.py`

Responsible for:

- negamax
- alpha-beta pruning
- move ordering
- iterative deepening
- transposition table

### `pygame_ui.py`

Responsible only for:

- drawing the board
- handling mouse clicks
- calling the AI when needed

This separation will make the code much easier to improve.

---

## 27. Best first version to aim for

The best next bot is not a neural network yet. It is a clean classical engine:

```text
simple 8×8 board
correct legal moves
correct connectedness win detection
negamax alpha-beta
move ordering
handcrafted evaluation
basic tests
```

Once that exists, it can become:

- a strong opponent
- a baseline for MCTS
- a data generator for imitation learning
- a teacher for the first neural network
- a source of tactical test positions

That is the right foundation for a later RL version.

