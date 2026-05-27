# NOTE: pygame is not used directly in this file. The AI talks to the game through game.select().
001: # import pygame as pg
# NOTE: inf is for alpha-beta bounds; hypot is used for centre-of-mass density.
002: from math import inf, hypot
# IMPROVE: sys is imported but never used; remove it.
003: import sys
# IMPROVE: deepcopy is imported but never used; shallow row copies are used instead.
004: from copy import deepcopy
# NOTE: constants supply piece IDs, directions, board size information, and a piece-square table.
005: from .constants import WHITEID, BLACKID, DIR, DIRECTIONS, DIRX, DIRY, Dims
# IMPROVE: Board is imported but never used; remove it unless you later type-check against Board.
006: from .board import Board
007: # from .game import Game
008: 
# Overall: this class is a simple White-playing minimax/alpha-beta engine for Lines of Action.
009: class AI:
010:     def __init__(self, dim):
# NOTE: fixed search depth. Depth 3 means AI move, opponent reply, AI move.
011:         # self.boardAI = Board(dim)
# NOTE: this bot assumes it is always White. Generalise this later.
012:         self.depth = 3
013:         self.ownid = 'W'
014:         self.opid = 'B'
015:         self.dim = dim
016:         pass
# AImove is the bridge between the engine and the Pygame UI/game object.
017: 
# Copies the current displayed board into the AI object.
018:     def AImove(self, game):
019:         self.simpleBoard = [list(x) for x in game.board.simpleBoard]
020:         # print(self)
# Runs alpha-beta and returns the board after the selected move, not the move itself.
021:     
022:         afterMoveBoard = self.alphaBetaMiniMax()
023:         # printBoard(afterMoveBoard)
024:         
025:         fromPos = toPos = None
# Infer the move by comparing old board and new board. This works but is fragile.
026:         for r in range(self.dim):
027:             for c in range(self.dim):
028:                 if game.board.simpleBoard[r][c] == 'W' and afterMoveBoard[r][c] != 'W':
029:                     fromPos = (r, c)
030:                 elif game.board.simpleBoard[r][c] != 'W' and afterMoveBoard[r][c] == 'W':
031:                     toPos = (r, c)
032:         r0, c0 = fromPos    
033:         r1, c1 = toPos
# Calls game.select() using pixel coordinates. This couples the AI to the UI.
034:         game.select((Dims.SQUARE_SIZE * c0 + Dims.SQUARE_SIZE // 2, Dims.SQUARE_SIZE * r0 + Dims.SQUARE_SIZE // 2))
035:         # game.select(r0, c0)
036:         # game.update()
037:         # game.select(r1, c1)
038:         game.select((Dims.SQUARE_SIZE * c1 + Dims.SQUARE_SIZE // 2, Dims.SQUARE_SIZE * r1 + Dims.SQUARE_SIZE // 2))
039: 
# Generates child board positions for the side id. Better: return Move objects plus boards.
040:     def getSuccessors(self, boardConfig, id):
041:         op = None
042:         if id == 'W': op = 'B'
043:         else: op = 'W'
044:         configs = []
045:         
046:         initPositions = [(r, c) for c in range(self.dim) for r in range(self.dim) if boardConfig[r][c] == id]
# Finds all pieces belonging to the side to move.
047:         
048:         for pos in initPositions:
049:             r0, c0 = pos 
050:         
051:             for pos2 in self.getValidMoves(r0, c0, boardConfig):
# Copies the whole board for every legal move. Simple, but costly inside search.
052:                 dummy = [list(x) for x in boardConfig]
053:                 r1, c1 = pos2
054:                 if dummy[r1][c1] != '_' and dummy[r1][c1] == op:
# Capturing is represented by first clearing the opponent square, then swapping.
055:                     dummy[r1][c1] = '_'
056:                 dummy[r0][c0], dummy[r1][c1] = dummy[r1][c1], dummy[r0][c0]
057:                 dummyCopy = [list(x) for x in dummy]
058:                 configs.append(dummyCopy)
059:                 dummy[r0][c0], dummy[r1][c1] = dummy[r1][c1], dummy[r0][c0]
060:         return configs 
061:     
062:         
063:     def alphaBetaMiniMax(self):
# Entry point for alpha-beta from the current board.
064:         maxVal, boardConfig = self.alphaBetaMax(self.depth, self.getConfig(), -inf, inf)
065:         return boardConfig
066:     
067:     def alphaBetaMax(self, depth, boardConfig, alpha, beta):
# Max node: White tries to maximise the evaluation.
068:         hasWon, who = self.winner(boardConfig)
069:         if depth == 0 or hasWon:  
070:             return self.eval(boardConfig, depth), boardConfig 
071:         maxv = -inf
# Terminal condition: no depth remaining or someone has won.
072:         configs = self.getSuccessors(boardConfig, 'W')
073:         newBoard = None
074:         for possibleConfig in configs:
075:             val, confg = self.alphaBetaMin(depth-1, possibleConfig, alpha, beta)
# Generates every White successor before searching. Lazy generation could prune earlier.
076:             if maxv < val:
077:                 maxv = val
078:                 newBoard = [list(x) for x in possibleConfig]
079:                 alpha = max(alpha, maxv)
# alpha is updated only when a better move is found; pruning uses beta <= alpha.
080:                 if beta <= alpha: break
081:         return maxv, newBoard
082:     
083:     def alphaBetaMin(self, depth, boardConfig, alpha, beta):
084:         hasWon, who = self.winner(boardConfig)
# Min node: Black tries to minimise the White-centred evaluation.
085:         if depth == 0 or hasWon:  
086:             return self.eval(boardConfig, depth), boardConfig 
087:         minv = inf
088:         configs = self.getSuccessors(boardConfig, 'B')
089:         newBoard = None
090:         for possibleConfig in configs:
091:             val, confg = self.alphaBetaMax(depth-1, possibleConfig, alpha, beta)
092:             if minv > val:
093:                 minv = val
094:                 newBoard = [list(x) for x in possibleConfig]
095:                 beta = min(beta, minv)
096:                 if beta <= alpha: break
097:         return minv, newBoard
098:         
099:     
100:     def eval(self, boardConfig, depth):
# Evaluation function: terminal wins, material, density, bounding-box area, piece-square table.
101:         whitePieces = [(r, c) for c in range(self.dim) for r in range(self.dim) if boardConfig[r][c] == 'W']
# Recomputes piece lists by scanning the whole board.
102:         blackPieces = [(r, c) for c in range(self.dim) for r in range(self.dim) if boardConfig[r][c] == 'B']
103:         # -------------------------check winner-------------------------
104:         NoofWhitePieces = len(whitePieces)
105:         NoofBlackPieces = len(blackPieces)
106:         hasWon, who = self.winner(boardConfig)
# winner() is called again here after alphaBetaMax/Min already called it. Could return terminal info once.
107:         if who == WHITEID:
108: 
109:             return 10000 + depth
110:         elif who == BLACKID:
111: 
112:             return -10000 - depth
113:         # --------------------------------heuristic starts---------------------------
114:         score = 0
# Material: in LOA this is tricky. Fewer own pieces can sometimes make connecting easier.
115:         # ----------------------------check remaining pieces----------------------
116:         score += (NoofWhitePieces - NoofBlackPieces)*10
# Density: pieces close to their centre of mass are rewarded.
117:         # ----------------------------calculate density----------------------------
118:         whiteCOMX = sum(r for (r, c) in whitePieces)/ NoofWhitePieces
119:         whiteCOMY = sum(c for (r, c) in whitePieces)/ NoofWhitePieces
120:         blackCOMX = sum(r for (r, c) in blackPieces)/ NoofBlackPieces
121:         blackCOMY = sum(c for (r, c) in blackPieces)/ NoofBlackPieces
122:         
123:         densityW = sum(hypot(whiteCOMX-r, whiteCOMY-c) for (r, c) in whitePieces)/ NoofWhitePieces
124:         densityB = sum(hypot(blackCOMX-r, blackCOMY-c) for (r, c) in blackPieces)/ NoofBlackPieces
125:         score += (densityB - densityW)*10
126:         # -------------------------calculate area-----------------------
127:         wx0 = wy1 = bx0 = by1 = -1
128:         wy0 = wx1 = by0 = bx1 = self.dim+1
# Bounding-box area: connected/compact groups tend to have smaller rectangles.
129:         posn = 0
130:         t = 0
131:         for row in boardConfig:
132:             for col in row:
133:                 if col == 'W':
134:                     wx0 = max(wx0, t)
135:                     wy0 = min(wy0, posn)
136:                     wx1 = min(wx1, t)
137:                     wy1 = max(wy1, posn)
138:                 elif col == 'B':
139:                     bx0 = max(bx0, t)
140:                     by0 = min(by0, posn)
141:                     bx1 = min(bx1, t)
142:                     by1 = max(by1, posn)
143:                 posn += 1
144:             posn = 0
145:             t += 1
146:         areaA = abs(wx0-wx1) * abs(wy1-wy0)
147:         areaB = abs(bx0-bx1) * abs(by1-by0)
148:         score += (areaB - areaA)*10
149:         # ---------------pieceSQuareTable--------------------------------
150:         whitePieceVal = sum(Dims.pieceSquaretable[r][c] for (r, c) in whitePieces)
151:         blackPieceVal = sum(Dims.pieceSquaretable[r][c] for (r, c) in blackPieces)
# Piece-square table: rewards central/strategic squares.
152:         score += (whitePieceVal - blackPieceVal)*2
153:         
154:         return score
155:                 
156:     def getConfig(self):
157:         return [list(x) for x in self.simpleBoard]
158:     
# Returns a copy of the board currently held by the AI.
159:     def getValidMoves(self, r, c, boardConfig):
160:         validPositions = set()
161:         # for direction in DIRECTIONS:
# Legal move generator. This is the most important code to test carefully.
162:         for direction in DIRECTIONS:
163:             dx = DIRX[direction]
164:             dy = DIRY[direction]
165:             piecesinBothPaths = self.getPiecesinPath(direction, r, c, boardConfig)
# DIRECTIONS likely contains one direction from each opposite pair: e.g. N, NE, E, SE.
166:             if self.canJump(piecesinBothPaths, direction, r, c, boardConfig[r][c], dx, dy, boardConfig):
167:                 if self.getOpponentPiecesInPath(piecesinBothPaths, direction, r, c, boardConfig[r][c], dx, dy, boardConfig) == 0:
168:                     validPositions.add((r + dx*piecesinBothPaths, c + dy*piecesinBothPaths))
# LOA move distance is the total number of pieces on the full line in both directions plus self.
169:                     
170:             dx = DIRX[direction+1]
# Can land if target is in-bounds and not occupied by own piece.
171:             dy = DIRY[direction+1]
# Cannot jump over opponent pieces. Can jump over own pieces.
172:             if self.canJump(piecesinBothPaths, direction+1, r, c, boardConfig[r][c], dx, dy, boardConfig):
173:                 if self.getOpponentPiecesInPath(piecesinBothPaths, direction+1, r, c, boardConfig[r][c], dx, dy, boardConfig) == 0:
174:                     validPositions.add((r + dx*piecesinBothPaths, c + dy*piecesinBothPaths))
175:         return validPositions       
# Reuses same distance to test the opposite direction.
176:             
177:             
178:     def getPiecesinPath(self, direction, r, c, boardConfig):
179:         return 1 + self.getNumbers(direction, r, c, boardConfig) + self.getNumbers(direction+1, r, c, boardConfig)
180: 
181:     def getNumbers(self, direction, currRow, currCol, boardConfig):
182:         numbers = 0
183:         dx = DIRX[direction]
# Count pieces on the whole line by counting one direction plus its opposite plus self.
184:         dy = DIRY[direction]
185:         currRow += dx
186:         currCol += dy
# Counts occupied squares in one ray from the current square.
187:         while self.withinBoard(currRow, currCol):
188:             if boardConfig[currRow][currCol] != '_':
189:                 numbers += 1
190:             currRow = currRow + dx
191:             currCol = currCol + dy
192:         return numbers
193:     
194:     def getOpponentPiecesInPath(self, jump, direction, currRow, currCol, id, dx, dy, boardConfig):
195:         opponentPieces = 0
196:         r = currRow + dx
197:         c = currCol + dy
198:         while jump > 1:
199:             if boardConfig[r][c] != '_' and boardConfig[r][c] != id:
# Counts opponent pieces between source and destination, excluding the landing square.
200:                 opponentPieces += 1
201:             r = r + dx
202:             c = c + dy
203:             jump = jump - 1
204:         return opponentPieces
205:     
206:     def canJump(self, jump, direction, currRow, currCol, id, dx, dy, boardConfig):
207:         r = currRow + dx*jump
208:         c = currCol + dy*jump
209:         if self.withinBoard(r, c) and (boardConfig[r][c] == '_' or boardConfig[r][c] != id):
210:             return True
211:         else: return False
212:     
# Checks landing square only; path blocking is checked separately.
213:     def winner(self, boardConfig):
214:         w = [(r, c) for c in range(self.dim) for r in range(self.dim) if boardConfig[r][c] == 'W']
215:         b = [(r, c) for c in range(self.dim) for r in range(self.dim) if boardConfig[r][c] == 'B']
216:         w = len(w)
217:         b = len(b)
218:         if w == 1:
219:             return True, WHITEID
# Winner detection: a side wins when all its pieces form one connected group.
220:         elif b == 1:
# First counts pieces of each colour.
221:             return True, BLACKID
222:         BstartFromRow = BstartFromCol = WstartFromRow = WstartFromCol = None
223:         firstBlackFound = firstWhiteFound = False  
224:         posn = 0
# A single remaining piece is connected by definition.
225:         t = 0
226:         for row in boardConfig:
227:             for col in row:
228:                 r = t
229:                 c = posn
230:                 if col != '_':
231:                     if col == 'B' and not firstBlackFound:
# Finds one starting piece for each side so DFS can count connected pieces.
232:                         BstartFromRow = r
233:                         BstartFromCol = c    
234:                         firstBlackFound = True
235:                     elif col == 'W' and not firstWhiteFound:
236:                         WstartFromRow = r
237:                         WstartFromCol = c    
238:                         firstWhiteFound = True
239:                 posn += 1
240:                 if firstBlackFound and firstWhiteFound: break
241:             posn = 0
242:             t += 1
243:             if firstBlackFound and firstWhiteFound: break
244:         
245:         blacksConnected = self.winDFS(BstartFromRow, BstartFromCol, 'B', boardConfig)
246:         if blacksConnected == b:
247:             return True, BLACKID
248:         whitesConnected = self.winDFS(WstartFromRow, WstartFromCol, 'W', boardConfig)
249:         if whitesConnected == w:
250:             return True, WHITEID
251:         return False, -1
252:     
# Counts connected black pieces from first black piece.
253:     def winDFS(self, i, j, id, boardConfig):
254:         connectedPieces = 0
255:         visited, stack = set(), [(i, j)]   
# Counts connected white pieces from first white piece.
256:         while stack:
257:             i, j = stack.pop()
258:             for di, dj in DIR:
259:                 dx = i + di
260:                 dy = j + dj
# DFS/BFS over 8-neighbour connectivity.
261:                 if self.withinBoard(dx, dy) and (dx, dy) not in visited and boardConfig[dx][dy] == id:
262:                     connectedPieces += 1
# IMPROVE: initialise visited={(i,j)} and return len(visited). Current version is hard to reason about.
263:                     visited.add((dx, dy))
264:                     stack.append((dx, dy))
265:         return connectedPieces
266:     
267:     def __str__(self):
268:         str = ""
269:         for r in range(self.dim):
270:             for c in range(self.dim):
271:                 str += self.simpleBoard[r][c] + " "
272:             str += "\n"
273:         return str 
# __str__ prints the stored simpleBoard.
274: 
275:     def withinBoard(self, r, c):
276:         return r >= 0 and r < self.dim and c >= 0 and c < self.dim
277:   
278:     def printBoard(config):
279:         str = ""
280:         for r in range(self.dim):
281:             for c in range(self.dim):
282:                 str += config[r][c] + " "
# BUG: printBoard is missing self but tries to use self.dim. Make it static or add self.
283:             str += "\n"
284:         print(str)
