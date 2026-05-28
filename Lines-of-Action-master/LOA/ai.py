from __future__ import annotations

from math import inf, hypot

from .constants import WHITEID, BLACKID, DRAWID, DIR, DIRECTIONS, DIRX, DIRY, Dims
from .heuristic_weights import HeuristicWeights
from . import loadstone_eval
from .search_depth import AdaptiveDepthConfig, choose_search_depth


def _opponent(player_char):
    return "B" if player_char == "W" else "W"


class AI:
    def __init__(
        self,
        dim,
        weights: HeuristicWeights | None = None,
        *,
        depth: int = 3,
        adaptive_depth: bool = False,
        depth_deep: int = 4,
    ):
        self.depth = depth
        self.depth_deep = depth_deep
        self.adaptive_depth = adaptive_depth
        self._adaptive_config = AdaptiveDepthConfig(
            depth_shallow=depth,
            depth_deep=depth_deep,
        )
        self.ownid = "W"
        self.opid = "B"
        self.dim = dim
        self.weights = weights or HeuristicWeights()

    def search_depth_for(
        self,
        board_config,
        mover: str,
        *,
        ply: int | None = None,
    ) -> int:
        if not self.adaptive_depth:
            return self.depth
        return choose_search_depth(
            self, board_config, mover, self._adaptive_config, ply=ply
        )

    def AImove(self, game):
        if not game.board.side_has_legal_move(game.turn):
            game.apply_pass()
            return
        self.simpleBoard = [list(x) for x in game.board.simpleBoard]
        cfg = self.getConfig()
        mover = "W" if game.turn == WHITEID else "B"
        ply = getattr(game, "ply_count", None)
        depth = self.search_depth_for(cfg, mover, ply=ply)
        _score, move = self._negamax(cfg, depth, -inf, inf, mover)
        if move is None:
            game.apply_pass()
            return
        r0, c0, r1, c1 = move
        game.apply_grid_move(r0, c0, r1, c1)

    def _side_has_legal_moves(self, boardConfig, player_char):
        for r0 in range(self.dim):
            for c0 in range(self.dim):
                if boardConfig[r0][c0] != player_char:
                    continue
                if self.getValidMoves(r0, c0, boardConfig):
                    return True
        return False

    def _legal_moves_flat(self, boardConfig, player_char):
        """All legal moves for ``player_char`` as ``(r0, c0, r1, c1)`` (no board copy)."""
        moves = []
        for r0 in range(self.dim):
            for c0 in range(self.dim):
                if boardConfig[r0][c0] != player_char:
                    continue
                for r1, c1 in self.getValidMoves(r0, c0, boardConfig):
                    moves.append((r0, c0, r1, c1))
        return moves

    def _apply_move_inplace(self, board, r0, c0, r1, c1):
        """Apply move on ``board``; returns undo token. Must pair with ``_undo_move_inplace``."""
        mover = board[r0][c0]
        op = _opponent(mover)
        dst = board[r1][c1]
        if dst != "_" and dst == op:
            board[r1][c1] = "_"
        board[r0][c0], board[r1][c1] = board[r1][c1], board[r0][c0]
        return (r0, c0, r1, c1, dst)

    def _undo_move_inplace(self, board, undo):
        r0, c0, r1, c1, dst = undo
        board[r0][c0], board[r1][c1] = board[r1][c1], board[r0][c0]
        if dst != "_" and dst != board[r0][c0]:
            board[r1][c1] = dst

    def _negamax(self, boardConfig, depth, alpha, beta, player_char):
        hasWon, _ = self.winner(boardConfig)
        if depth == 0 or hasWon:
            return self._eval_for_player(boardConfig, depth, player_char), None

        legal = self._legal_moves_flat(boardConfig, player_char)
        if not legal:
            opp = _opponent(player_char)
            if not self._side_has_legal_moves(boardConfig, opp):
                return 0, None
            score, _ = self._negamax(boardConfig, depth - 1, -beta, -alpha, opp)
            return -score, None

        best_score = -inf
        best_move = None
        opp = _opponent(player_char)

        for r0, c0, r1, c1 in legal:
            undo = self._apply_move_inplace(boardConfig, r0, c0, r1, c1)
            score, _ = self._negamax(boardConfig, depth - 1, -beta, -alpha, opp)
            self._undo_move_inplace(boardConfig, undo)
            score = -score
            if score > best_score:
                best_score = score
                best_move = (r0, c0, r1, c1)
            alpha = max(alpha, best_score)
            if alpha >= beta:
                break
        return best_score, best_move

    def _eval_for_player(self, boardConfig, depth, player_char):
        """Static score from current player_char's perspective (higher is better for them)."""
        hasWon, who = self.winner(boardConfig)
        if hasWon:
            if who == DRAWID:
                return 0
            mag = self.weights.terminal_magnitude + depth
            if who == WHITEID:
                return mag if player_char == "W" else -mag
            return mag if player_char == "B" else -mag
        h = self._heuristic_white_minus_black(boardConfig)
        classic = h if player_char == "W" else -h
        b = max(0, min(100, self.weights.loadstone_blend_pct))
        if b == 0:
            blended = classic
        else:
            ls = loadstone_eval.board_eval_normalized(
                boardConfig, player_char, self.dim, self
            )
            blended = int(round(((100 - b) * classic + b * ls) / 100.0))

        w_m = self.weights.mobility_weight
        if w_m != 0:
            mob = loadstone_eval.mobility_stm_minus_opponent(
                self, boardConfig, player_char
            )
            blended += w_m * mob
        w_p = self.weights.projection_weight
        if w_p != 0:
            proj = loadstone_eval.projection_stm_minus_opponent(
                boardConfig, player_char, self.dim
            )
            blended += w_p * proj
        return blended

    def _heuristic_white_minus_black(self, boardConfig):
        """Heuristic positive when the position favours White (no terminal check)."""
        whitePieces = [(r, c) for c in range(self.dim) for r in range(self.dim) if boardConfig[r][c] == "W"]
        blackPieces = [(r, c) for c in range(self.dim) for r in range(self.dim) if boardConfig[r][c] == "B"]
        NoofWhitePieces = len(whitePieces)
        NoofBlackPieces = len(blackPieces)
        w = self.weights
        score = 0
        score += (NoofWhitePieces - NoofBlackPieces) * w.piece_count
        whiteCOMX = sum(r for (r, c) in whitePieces) / NoofWhitePieces
        whiteCOMY = sum(c for (r, c) in whitePieces) / NoofWhitePieces
        blackCOMX = sum(r for (r, c) in blackPieces) / NoofBlackPieces
        blackCOMY = sum(c for (r, c) in blackPieces) / NoofBlackPieces

        densityW = sum(hypot(whiteCOMX - r, whiteCOMY - c) for (r, c) in whitePieces) / NoofWhitePieces
        densityB = sum(hypot(blackCOMX - r, blackCOMY - c) for (r, c) in blackPieces) / NoofBlackPieces
        score += (densityB - densityW) * w.density

        wx0 = wy1 = bx0 = by1 = -1
        wy0 = wx1 = by0 = bx1 = self.dim + 1
        posn = 0
        t = 0
        for row in boardConfig:
            for col in row:
                if col == "W":
                    wx0 = max(wx0, t)
                    wy0 = min(wy0, posn)
                    wx1 = min(wx1, t)
                    wy1 = max(wy1, posn)
                elif col == "B":
                    bx0 = max(bx0, t)
                    by0 = min(by0, posn)
                    bx1 = min(bx1, t)
                    by1 = max(by1, posn)
                posn += 1
            posn = 0
            t += 1
        areaA = abs(wx0 - wx1) * abs(wy1 - wy0)
        areaB = abs(bx0 - bx1) * abs(by1 - by0)
        score += (areaB - areaA) * w.bounding_box_area

        whitePieceVal = sum(Dims.pieceSquaretable[r][c] for (r, c) in whitePieces)
        blackPieceVal = sum(Dims.pieceSquaretable[r][c] for (r, c) in blackPieces)
        score += (whitePieceVal - blackPieceVal) * w.piece_square_table
        return score

    def getConfig(self):
        return [list(x) for x in self.simpleBoard]

    def getValidMoves(self, r, c, boardConfig):
        validPositions = set()
        for direction in DIRECTIONS:
            dx = DIRX[direction]
            dy = DIRY[direction]
            piecesinBothPaths = self.getPiecesinPath(direction, r, c, boardConfig)
            if self.canJump(piecesinBothPaths, direction, r, c, boardConfig[r][c], dx, dy, boardConfig):
                if self.getOpponentPiecesInPath(piecesinBothPaths, direction, r, c, boardConfig[r][c], dx, dy, boardConfig) == 0:
                    validPositions.add((r + dx * piecesinBothPaths, c + dy * piecesinBothPaths))

            dx = DIRX[direction + 1]
            dy = DIRY[direction + 1]
            if self.canJump(piecesinBothPaths, direction + 1, r, c, boardConfig[r][c], dx, dy, boardConfig):
                if self.getOpponentPiecesInPath(piecesinBothPaths, direction + 1, r, c, boardConfig[r][c], dx, dy, boardConfig) == 0:
                    validPositions.add((r + dx * piecesinBothPaths, c + dy * piecesinBothPaths))
        return validPositions

    def getPiecesinPath(self, direction, r, c, boardConfig):
        return 1 + self.getNumbers(direction, r, c, boardConfig) + self.getNumbers(direction + 1, r, c, boardConfig)

    def getNumbers(self, direction, currRow, currCol, boardConfig):
        numbers = 0
        dx = DIRX[direction]
        dy = DIRY[direction]
        currRow += dx
        currCol += dy
        while self.withinBoard(currRow, currCol):
            if boardConfig[currRow][currCol] != "_":
                numbers += 1
            currRow = currRow + dx
            currCol = currCol + dy
        return numbers

    def getOpponentPiecesInPath(self, jump, direction, currRow, currCol, id, dx, dy, boardConfig):
        opponentPieces = 0
        r = currRow + dx
        c = currCol + dy
        while jump > 1:
            if boardConfig[r][c] != "_" and boardConfig[r][c] != id:
                opponentPieces += 1
            r = r + dx
            c = c + dy
            jump = jump - 1
        return opponentPieces

    def canJump(self, jump, direction, currRow, currCol, id, dx, dy, boardConfig):
        r = currRow + dx * jump
        c = currCol + dy * jump
        if self.withinBoard(r, c) and (boardConfig[r][c] == "_" or boardConfig[r][c] != id):
            return True
        return False

    def winner(self, boardConfig):
        w = [(r, c) for c in range(self.dim) for r in range(self.dim) if boardConfig[r][c] == "W"]
        b = [(r, c) for c in range(self.dim) for r in range(self.dim) if boardConfig[r][c] == "B"]
        w = len(w)
        b = len(b)
        if w == 1:
            return True, WHITEID
        if b == 1:
            return True, BLACKID
        BstartFromRow = BstartFromCol = WstartFromRow = WstartFromCol = None
        firstBlackFound = firstWhiteFound = False
        posn = 0
        t = 0
        for row in boardConfig:
            for col in row:
                r = t
                c = posn
                if col != "_":
                    if col == "B" and not firstBlackFound:
                        BstartFromRow = r
                        BstartFromCol = c
                        firstBlackFound = True
                    elif col == "W" and not firstWhiteFound:
                        WstartFromRow = r
                        WstartFromCol = c
                        firstWhiteFound = True
                posn += 1
                if firstBlackFound and firstWhiteFound:
                    break
            posn = 0
            t += 1
            if firstBlackFound and firstWhiteFound:
                break

        blacksConnected = self.winDFS(BstartFromRow, BstartFromCol, "B", boardConfig)
        whitesConnected = self.winDFS(WstartFromRow, WstartFromCol, "W", boardConfig)
        black_wins = blacksConnected == b
        white_wins = whitesConnected == w
        if black_wins and white_wins:
            return True, DRAWID
        if black_wins:
            return True, BLACKID
        if white_wins:
            return True, WHITEID
        return False, -1

    def winDFS(self, i, j, id, boardConfig):
        if i is None or j is None or not self.withinBoard(i, j) or boardConfig[i][j] != id:
            return 0
        visited = {(i, j)}
        stack = [(i, j)]
        while stack:
            ri, ci = stack.pop()
            for di, dj in DIR:
                dx = ri + di
                dy = ci + dj
                if (
                    self.withinBoard(dx, dy)
                    and (dx, dy) not in visited
                    and boardConfig[dx][dy] == id
                ):
                    visited.add((dx, dy))
                    stack.append((dx, dy))
        return len(visited)

    def __str__(self):
        s = ""
        for r in range(self.dim):
            for c in range(self.dim):
                s += self.simpleBoard[r][c] + " "
            s += "\n"
        return s

    def withinBoard(self, r, c):
        return r >= 0 and r < self.dim and c >= 0 and c < self.dim

    @staticmethod
    def print_board(config):
        dim = len(config)
        s = ""
        for r in range(dim):
            for c in range(dim):
                s += config[r][c] + " "
            s += "\n"
        print(s)
