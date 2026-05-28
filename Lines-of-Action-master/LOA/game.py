# import pygame as pg
from pygame import display, draw, event, font, QUIT, Rect
import sys
from time import sleep
from .ai import AI
from .constants import *
from .board import Board

button6 = button8 = None


class Game:
    def __init__(self, win):
        self.board = None
        self.selectedPiece = None
        self.turn = BLACKID
        self.op = WHITEID
        self.validMoves = set()
        self.win = win
        self.fromPos = None
        self.toPos = None
        self.ai = None
        self.gameStarted = False
        self.dim = None
        self._rep_counts = {}
        self._repetition_draw = False
        self._stalemate_draw = False
        self.ply_count = 0

    def _board_tuple(self):
        return tuple(tuple(row) for row in self.board.simpleBoard)

    def _begin_arrival_at_mover(self):
        if self._repetition_draw or not self.board:
            return
        key = (self._board_tuple(), self.turn)
        self._rep_counts[key] = self._rep_counts.get(key, 0) + 1
        if self._rep_counts[key] >= 3:
            self._repetition_draw = True

    def _advance_ply(self):
        self.ply_count += 1

    def _flip_turn(self):
        if self.turn == BLACKID:
            self.turn = WHITEID
            self.op = BLACKID
        else:
            self.turn = BLACKID
            self.op = WHITEID

    def _resolve_pass_until_moves_or_done(self):
        guard = 0
        while (
            not self._repetition_draw
            and not self._stalemate_draw
            and self.gameStarted
            and self.board
            and guard < 128
        ):
            guard += 1
            hw, _who = self.board.winner()
            if hw:
                return
            if self.board.side_has_legal_move(self.turn):
                return
            op = WHITEID if self.turn == BLACKID else BLACKID
            if not self.board.side_has_legal_move(op):
                self._stalemate_draw = True
                return
            self._flip_turn()
            self._advance_ply()
            self.fromPos = self.toPos = None
            self._begin_arrival_at_mover()

    def _finish_turn_transition(self):
        """After side-to-move changes: rule 9, rule 8 passes, then UI and optional AI."""
        self._begin_arrival_at_mover()
        self._resolve_pass_until_moves_or_done()
        self.update()
        if (
            AImode
            and not self.winner()[0]
            and not self._repetition_draw
            and not self._stalemate_draw
        ):
            if self.turn == WHITEID and self.board.side_has_legal_move(WHITEID):
                self.ai.AImove(self)

    def update(self):
        if self.gameStarted == False:
            self.drawDimSelection()
            return
        self.board.drawUI(self.win)
        if self.selectedPiece is not None:
            self.drawValidMoves(self.validMoves)

        if self.selectedPiece is None:
            self.drawMoveLine(self.fromPos, self.toPos)
            hasWon, who = self.winner()
            if hasWon:
                display.update()
                self.drawWinScreen(who)
        display.update()

    def drawDimSelection(self):
        global button6, button8
        self.win.fill(CHECK2)
        rectWidth = BUTTONHEIGHT * 1.6
        rectHeight = BUTTONHEIGHT
        button6 = Rect(WIDTH / 2 - rectWidth / 2, HEIGHT / 2 - rectHeight / 2 - rectHeight / 1.5, rectWidth, rectHeight)
        button8 = Rect(WIDTH / 2 - rectWidth / 2, HEIGHT / 2 - rectHeight / 2 + rectHeight / 1.5, rectWidth, rectHeight)
        draw.rect(self.win, CHECK1, button6)
        draw.rect(self.win, CHECK1, button8)
        font.init()
        f = font.SysFont("Arial", 60)
        text6 = f.render("6 X 6", False, BLACK)
        text8 = f.render("8 X 8", False, BLACK)
        self.win.blit(text6, (button6.left + text6.get_width() / 2 - 10, button6.top + text6.get_height() / 2 + 5))
        self.win.blit(text8, (button8.left + text8.get_width() / 2 - 10, button8.top + text8.get_height() / 2 + 5))
        display.update()

    def drawWinScreen(self, who):
        print(f"Game over: {who}")
        sleep(2)
        self.win.fill(WINBG)
        sqr = Dims.SQUARE_SIZE
        while True:
            for e in event.get():
                if e.type == QUIT:
                    sys.exit()
            if who == DRAWID:
                draw.circle(self.win, BLACK, (WIDTH // 2, HEIGHT // 2 - 150), sqr * 1.25 + 2)
                draw.circle(self.win, WHITE, (WIDTH // 2, HEIGHT // 2 - 150), sqr * 1.25)
            elif who == BLACKID:
                draw.circle(self.win, WHITE, (WIDTH // 2, HEIGHT // 2 - 150), sqr * 1.25 + 2)
                draw.circle(self.win, BLACK, (WIDTH // 2, HEIGHT // 2 - 150), sqr * 1.25)
            else:
                draw.circle(self.win, BLACK, (WIDTH // 2, HEIGHT // 2 - 150), sqr * 1.25 + 2)
                draw.circle(self.win, WHITE, (WIDTH // 2, HEIGHT // 2 - 150), sqr * 1.25)
            if WINS is not None and who != DRAWID:
                self.win.blit(WINS, (WIDTH // 2 - 200, HEIGHT // 2 + 50))
            else:
                font.init()
                f = font.SysFont("Arial", 56, bold=True)
                if who == DRAWID:
                    label = "Draw!"
                else:
                    label = "Black wins!" if who == BLACKID else "White wins!"
                surf = f.render(label, True, BLACK)
                rect = surf.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 120))
                self.win.blit(surf, rect)
            display.update()

    def drawValidMoves(self, validMoves):
        for move in validMoves:
            r, c = move
            sqr = Dims.SQUARE_SIZE
            draw.circle(
                self.win,
                REDDIRECTION,
                (c * sqr + sqr // 2, r * sqr + sqr // 2),
                sqr / 10,
            )
            draw.line(
                self.win,
                REDDIRECTION,
                (
                    self.selectedPiece.col * sqr + sqr // 2,
                    self.selectedPiece.row * sqr + sqr // 2,
                ),
                (c * sqr + sqr // 2, r * sqr + sqr // 2),
                7,
            )

    def drawMoveLine(self, fromPos, toPos):
        if fromPos is not None and toPos is not None:
            r0, c0 = fromPos
            r1, c1 = toPos
            sqr = Dims.SQUARE_SIZE
            draw.circle(self.win, BLUELINE, (c1 * sqr + sqr // 2, r1 * sqr + sqr // 2), sqr / 10)
            draw.line(
                self.win,
                BLUELINE,
                (c0 * sqr + sqr // 2, r0 * sqr + sqr // 2),
                (c1 * sqr + sqr // 2, r1 * sqr + sqr // 2),
                7,
            )

    def select(self, pos):
        if self.gameStarted == False:
            if button6.collidepoint(pos) or button8.collidepoint(pos):
                if button6.collidepoint(pos):
                    self.dim = 6
                else:
                    self.dim = 8
                self.gameStarted = True
                Dims.generateDims(self.dim)
                self.board = Board(self.dim)
                self.ai = AI(self.dim)
                self._rep_counts = {}
                self._repetition_draw = False
                self._stalemate_draw = False
                self.ply_count = 0
                self._begin_arrival_at_mover()
                self._resolve_pass_until_moves_or_done()
                return
            return
        r, c = mouseOnBoard(pos)
        if self.selectedPiece is None:
            selected = self.selectValidPiece(r, c)
            if selected:
                self.fromPos = (r, c)
        else:
            if (r, c) in self.validMoves:
                self.board.apply_move(self.selectedPiece.row, self.selectedPiece.col, r, c)
                self.toPos = (r, c)
                self.changeTurn()
            elif self.board.boardList2d[r][c] != -1 and self.board.boardList2d[r][c].id == self.selectedPiece.id:
                selected = self.selectValidPiece(r, c)
                if selected:
                    self.fromPos = (r, c)

    def selectValidPiece(self, r, c):
        p = self.board.getPiece(r, c)
        if p != -1 and p.id == self.turn:
            self.selectedPiece = p
            self.validMoves = self.board.getValidMoves(p.row, p.col)
            return True
        return False

    def apply_grid_move(self, r0, c0, r1, c1):
        """Engine / headless path: apply a legal grid move for the side currently on move."""
        if not self.gameStarted or self.board is None:
            return False
        piece = self.board.getPiece(r0, c0)
        if piece == -1 or piece.id != self.turn:
            return False
        if (r1, c1) not in self.board.getValidMoves(r0, c0):
            return False
        self.board.apply_move(r0, c0, r1, c1)
        self.fromPos, self.toPos = (r0, c0), (r1, c1)
        self.changeTurn()
        return True

    def apply_pass(self):
        """Rule 8: pass when the side to move has no legal move."""
        if not self.gameStarted or self.board is None:
            return False
        if self.board.side_has_legal_move(self.turn):
            return False
        self.validMoves.clear()
        self.selectedPiece = None
        self._flip_turn()
        self._advance_ply()
        self.fromPos = self.toPos = None
        self._finish_turn_transition()
        return True

    def changeTurn(self):
        self.validMoves.clear()
        self.selectedPiece = None
        self._flip_turn()
        self._advance_ply()
        self._finish_turn_transition()

    def winner(self):
        if self._repetition_draw or self._stalemate_draw:
            return True, DRAWID
        return self.board.winner()


def mouseOnBoard(pos):
    x, y = pos
    row = y // Dims.SQUARE_SIZE
    col = x // Dims.SQUARE_SIZE
    return row, col
