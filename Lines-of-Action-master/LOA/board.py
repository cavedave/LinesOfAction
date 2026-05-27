# import pygame as pg
from pygame import draw
from .constants import *
from .piece import *


class Board:
    def __init__(self, dim):
        # Needed for Piece.calc_pos(); headless/scripts often skip Game init.
        Dims.generateDims(dim)
        self.boardList2d = []
        self.simpleBoard = []
        self.blacks_left = self.whites_left = (dim - 2)*2
        self.dim = dim
        self.addPiecesToBoard()
        
    def draw_checkBoard(self, win):
        s = Dims.SQUARE_SIZE
        posn = 0
        for row in self.simpleBoard:
            if (posn // self.dim) % 2 == 0:
                c1 = CHECK1
                c2 = CHECK2
            else:
                c1 = CHECK2
                c2 = CHECK1
            for col in row:
                r = posn // self.dim
                c = posn % self.dim
                # pygame (x, y) = (col, row) in pixels to match Piece.calc_pos
                x_px, y_px = c * s, r * s
                if c % 2 == 0:
                    draw.rect(win, c1, (x_px, y_px, s, s))
                else:
                    draw.rect(win, c2, (x_px, y_px, s, s))
                posn += 1
            
                    
    def addPiecesToBoard(self):
        for r in range(self.dim):
            self.boardList2d.append([])
            self.simpleBoard.append([])
            for c in range(self.dim):
                if r == 0 or r == self.dim-1:
                    if c!=0 and c!=self.dim-1:
                        p = Piece(r, c, BLACK, BLACKID)
                        simplep = 'B'
                    else:
                        p = -1
                        simplep = '_'        
                else:
                    if c==0 or c==self.dim-1:
                        p = Piece(r, c, WHITE, WHITEID)
                        simplep = 'W'
                    else:
                        p = -1
                        simplep = '_'        
                self.boardList2d[r].append(p)
                self.simpleBoard[r].append(simplep)
    
    def drawUI(self, win):
        self.draw_checkBoard(win)
        for r in range(self.dim):
            for c in range(self.dim):
                p = self.boardList2d[r][c]
                if p != -1:
                    p.draw_piece(win)
                    
    def move(self, piece, r, c):
        self.simpleMove(piece.row, piece.col, r, c)
        self.boardList2d[piece.row][piece.col], self.boardList2d[r][c] = self.boardList2d[r][c], self.boardList2d[piece.row][piece.col]
        piece.update(r, c)

    def apply_move(self, r0, c0, r1, c1):
        """Apply a legal move from (r0,c0) to (r1,c1). Updates simpleBoard and boardList2d."""
        piece = self.boardList2d[r0][c0]
        if piece == -1:
            raise ValueError("apply_move: empty source square")
        if (r1, c1) not in self.getValidMoves(r0, c0):
            raise ValueError("apply_move: illegal destination")
        target = self.boardList2d[r1][c1]
        if target != -1 and target.id != piece.id:
            self.removePiece(r1, c1)
        self.move(piece, r1, c1)
    
    def simpleMove(self, pr, pc, r, c):
        self.simpleBoard[pr][pc], self.simpleBoard[r][c] = self.simpleBoard[r][c], self.simpleBoard[pr][pc]
        
    def getValidMoves(self, r, c):
        validPositions = set()
        for direction in DIRECTIONS:
            dx = DIRX[direction]
            dy = DIRY[direction]
            piecesinBothPaths = self.getPiecesinPath(direction, r, c)
            if self.canJump(piecesinBothPaths, direction, r, c, self.simpleBoard[r][c], dx, dy):
                if self.getOpponentPiecesInPath(piecesinBothPaths, direction, r, c, self.simpleBoard[r][c], dx, dy) == 0:
                    validPositions.add((r + dx*piecesinBothPaths, c + dy*piecesinBothPaths))
            
            dx = DIRX[direction+1]
            dy = DIRY[direction+1]
            if self.canJump(piecesinBothPaths, direction+1, r, c, self.simpleBoard[r][c], dx, dy):
                if self.getOpponentPiecesInPath(piecesinBothPaths, direction+1, r, c, self.simpleBoard[r][c], dx, dy) == 0:
                    validPositions.add((r + dx*piecesinBothPaths, c + dy*piecesinBothPaths))
        return validPositions
    
    def getPiecesinPath(self, direction, r, c):
        return 1 + self.getNumbers(direction, r, c) + self.getNumbers(direction+1, r, c) 
    
    def getNumbers(self, direction, currRow, currCol):
        numbers = 0
        dx = DIRX[direction]
        dy = DIRY[direction]
        currRow = currRow + dx
        currCol = currCol + dy
        while self.withinBoard(currRow, currCol):
            if self.simpleBoard[currRow][currCol] != '_':
                numbers += 1
            currRow = currRow + dx
            currCol = currCol + dy
        return numbers
    
    def canJump(self, jump, direction, currRow, currCol, id, dx, dy):
        r = currRow + dx*jump
        c = currCol + dy*jump
        if self.withinBoard(r, c) and (self.simpleBoard[r][c] == '_' or self.simpleBoard[r][c] != id):
            return True
        else: return False
    
    def getOpponentPiecesInPath(self, jump, direction, currRow, currCol, id, dx, dy):
        opponentPieces = 0
        r = currRow + dx
        c = currCol + dy
        while jump > 1:
            if self.simpleBoard[r][c] != '_' and self.simpleBoard[r][c] != id:
                opponentPieces += 1
            r = r + dx
            c = c + dy
            jump = jump - 1
        return opponentPieces
    
    def getPiece(self, r, c):
        return self.boardList2d[r][c]
    
    def removePiece(self, r, c):
        if self.boardList2d[r][c].id == WHITEID:
            self.whites_left -= 1
        elif self.boardList2d[r][c].id == BLACKID:
            self.blacks_left -= 1
        self.boardList2d[r][c] = -1
        self.simpleBoard[r][c] = '_'
        
    def winner(self):
        if self.whites_left == 1:
            return True, WHITEID
        elif self.blacks_left == 1:
            return True, BLACKID
        BstartFromRow = BstartFromCol = WstartFromRow = WstartFromCol = None
        firstBlackFound = firstWhiteFound = False
        
        posn = 0
        t = 0
        for row in self.simpleBoard:
            for col in row:
                r = t
                c = posn
                if col != '_':
                    if col == 'B' and not firstBlackFound:
                        BstartFromRow = r
                        BstartFromCol = c    
                        firstBlackFound = True
                    elif col == 'W' and not firstWhiteFound:
                        WstartFromRow = r
                        WstartFromCol = c    
                        firstWhiteFound = True
                posn += 1
                if firstBlackFound and firstWhiteFound: break
            posn = 0
            t += 1
            if firstBlackFound and firstWhiteFound: break
            
        blacksConnected = self.winDFS(BstartFromRow, BstartFromCol, 'B')
        whitesConnected = self.winDFS(WstartFromRow, WstartFromCol, 'W')
        black_wins = blacksConnected == self.blacks_left
        white_wins = whitesConnected == self.whites_left
        if black_wins and white_wins:
            return True, DRAWID
        if black_wins:
            return True, BLACKID
        if white_wins:
            return True, WHITEID
        return False, -1

    def side_has_legal_move(self, player_id):
        """Rule 8: whether ``player_id`` (``BLACKID`` / ``WHITEID``) has any legal move."""
        ch = "B" if player_id == BLACKID else "W"
        for r in range(self.dim):
            for c in range(self.dim):
                if self.simpleBoard[r][c] != ch:
                    continue
                if self.getValidMoves(r, c):
                    return True
        return False
    
    def winDFS(self, i, j, id):
        if not self.withinBoard(i, j) or self.simpleBoard[i][j] != id:
            return 0
        visited = {(i, j)}
        stack = [(i, j)]
        while stack:
            ri, ci = stack.pop()
            for k in range(len(DIRX)):
                dx = ri + DIRX[k]
                dy = ci + DIRY[k]
                if (
                    self.withinBoard(dx, dy)
                    and (dx, dy) not in visited
                    and self.simpleBoard[dx][dy] == id
                ):
                    visited.add((dx, dy))
                    stack.append((dx, dy))
        return len(visited)
    
    def __str__(self):
        boardConfig = ""
        for r in range(self.dim):
            for c in range(self.dim):
                if self.boardList2d[r][c] == -1: p = '_ '
                elif self.boardList2d[r][c].id == BLACKID: p = 'B '
                else: p = 'W '
                boardConfig += p
            boardConfig += "\n"
        return boardConfig

    def withinBoard(self, r, c):
        return r >= 0 and r < self.dim and c >= 0 and c < self.dim