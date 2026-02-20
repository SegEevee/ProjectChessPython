import pygame
import sys
from enum import Enum

# <editor-fold desc="CONFIG">
BOARD_SIZE = 8
SQUARE_SIZE = 80
WINDOW_SIZE = BOARD_SIZE * SQUARE_SIZE
FPS = 60

STARTING_POSITION = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

LIGHT = (240, 217, 181)
DARK  = (181, 136, 99)
# </editor-fold>


# <editor-fold desc="HELPERS (notation / coordinates)">
def notation_to_row_col(pos: str):
    pos = pos.strip().lower()
    col = ord(pos[0]) - ord('a')
    row = 8 - int(pos[1])
    return row, col

def row_col_to_notation(row: int, col: int):
    return chr(ord('a') + col) + str(8 - row)

def pixel_to_squarepos(mouse_pos):
    x, y = mouse_pos
    col = x // SQUARE_SIZE
    row = y // SQUARE_SIZE
    if 0 <= col < 8 and 0 <= row < 8:
        return SquarePosition(row=row, col=col)
    return None

def is_iterable_empty(iterable : iter):
    return len(iterable) == 0


# </editor-fold>


# <editor-fold desc="POSITION CLASS">
class SquarePosition:


    def __init__(self, notation: str = None, row: int = None, col: int = None):
        if notation is not None:
            r, c = notation_to_row_col(notation)
            self.row, self.col = r, c
        elif row is not None and col is not None:
            self.row, self.col = row, col
        else:
            self.row = None
            self.col = None

    def to_notation(self) -> str:
        return row_col_to_notation(self.row, self.col)

    def to_translation(self):
        return self.row,self.col
    def add_translation(self,translation : tuple):
        return SquarePosition(row=self.row+translation[0],col=self.col+translation[1])

    def __repr__(self):
        return self.to_notation()

    def __eq__(self, other):
        return isinstance(other, SquarePosition) and self.row == other.row and self.col == other.col

    def __hash__(self):
        return hash((self.row, self.col))
# </editor-fold>


# <editor-fold desc="ENUMS">
class ChessColor(Enum):
    WHITE = "WHITE"
    BLACK = "BLACK"

OTHER_COLOR = {ChessColor.WHITE:ChessColor.BLACK,ChessColor.BLACK:ChessColor.WHITE}



class ChessPieceType(Enum):
    PAWN   = "P"
    ROOK   = "R"
    KNIGHT = "N"
    BISHOP = "B"
    QUEEN  = "Q"
    KING   = "K"
# </editor-fold>

# <editor-fold desc="PIECE_HELPER">
def squares_between(a: SquarePosition, b: SquarePosition) -> set[SquarePosition]:
    """
    Returns the squares strictly between a and b (excluding endpoints),
    but ONLY if a and b are aligned:
      - same row (rank)
      - same col (file)
      - same diagonal (|dr| == |dc|)
    Otherwise returns [].
    """
    dr = b.row - a.row
    dc = b.col - a.col

    # Not aligned => nothing "between" in chess sense
    if not (dr == 0 or dc == 0 or abs(dr) == abs(dc)):
        return set()

    # Step direction: -1, 0, or +1
    step_r = 0 if dr == 0 else (1 if dr > 0 else -1)
    step_c = 0 if dc == 0 else (1 if dc > 0 else -1)

    r = a.row + step_r
    c = a.col + step_c

    between = set()
    while (r, c) != (b.row, b.col):
        between.add(SquarePosition(row=r, col=c))
        r += step_r
        c += step_c

    # This includes b if loop ended incorrectly, but our condition prevents that.
    # Remove endpoints already excluded by starting at a+step and stopping at b.
    return between


def can_castle(board, king, rook):
    # 1. Basic Type and Movement Checks
    if not (king.type == ChessPieceType.KING and rook.type == ChessPieceType.ROOK):
        return False
    if king.has_moved or rook.has_moved or king.color != rook.color:
        return False

    # 2. Path Clearance Check (Are the squares between empty?)
    between_squares = squares_between(king.position, rook.position)
    for pos in between_squares:
        if board.grid[pos.row][pos.col] is not None:
            return False

    # 3. "The Gauntlet" (Safety Checks)
    # Rules: King cannot be in check, pass through check, or land in check.
    player = PLAYERS[king.color]
    enemy_player = PLAYERS[OTHER_COLOR[king.color]]

    if player.is_in_check:
        return False

    # Determine direction to check the two squares the king moves across
    direction = 1 if rook.position.col > king.position.col else -1
    for i in range(1, 3):
        test_pos = SquarePosition(row=king.position.row, col=king.position.col + (i * direction))
        if enemy_player.is_controlling_square(test_pos):
            return False

    return True

#</editor-fold>


# <editor-fold desc="PIECES">
class ChessPiece:
    def __init__(self, color: ChessColor, position: SquarePosition, piece_type: ChessPieceType):
        self.color = color
        self.position: SquarePosition | None = position
        self.type = piece_type
        self.legal_moves: set[SquarePosition] = set()
        self.controlled_squares: set[SquarePosition] = set()
        self.player = PLAYERS[color] if PLAYERS else None
        self.has_moved = False


    def die(self):
        self.position = None

    def update_all_legal_moves(self, board):
        self.legal_moves.clear()

    def is_valid_move(self, new_position: SquarePosition) -> bool:
        return new_position in self.legal_moves

    def is_captureable(self, target) -> bool:
        return target.color != self.color
    def is_controlling_square(self,position : SquarePosition):
        return position in self.controlled_squares

    """def can_defend_check(self):
        enemy_player = PLAYERS.get(OTHER_COLOR.get(self.color))
        if not self.player.is_in_check:
            return True
        if len(enemy_player.checking_pieces) == 2:  # double check
            return self.is_king()
        checking_piece = enemy_player.checking_pieces[0]
        if self.is_controlling_square(checking_piece.position):
            return True
        squares_controlled_by_both = (self.controlled_squares & checking_piece.controlled_squares)

        return squares_controlled_by_both"""


    def update_legal_moves_in_check(self):
        if self.player.is_in_check:
            checking_piece = self.player.checking_pieces[0]
            squares_between_set = squares_between(checking_piece.position,self.player.king.position)

            self.legal_moves = self.legal_moves.union(self.controlled_squares).intersection(squares_between_set.union({checking_piece.position}))

            if self.player.king.position in self.legal_moves:
                self.legal_moves.remove(self.player.king.position)




    def is_king(self):
        return self.type == ChessPieceType.KING



    def __repr__(self):
        return f"{self.color.value} {self.type.name} @ {self.position}"
    def __bool__(self):
        return self.position is not None


#<editor-fold desc = "PIECES HELPER">



def add_sliding_moves(piece: ChessPiece, board, directions):
    """
    directions: iterable of (dr, dc)
    Adds squares until blocked. Can capture enemy on first occupied square, but cannot go beyond it.
    """
    if not piece:
        return

    start_r = piece.position.row
    start_c = piece.position.col

    for dr, dc in directions:
        r = start_r + dr
        c = start_c + dc
        while 0 <= r < 8 and 0 <= c < 8:
            target = board.grid[r][c]

            piece.controlled_squares.add(SquarePosition(row=r, col=c))  # Mark this square as controlled regardless of occupancy

            if not target or target.is_king():
                piece.legal_moves.add(SquarePosition(row=r, col=c))
            else:
                if target.color != piece.color:
                    piece.legal_moves.add(SquarePosition(row=r, col=c))
                break
            r += dr
            c += dc


# Inside Pawn class



#</editor-fold>

class Pawn(ChessPiece):
    def __init__(self, color, position: SquarePosition):
        super().__init__(color, position, ChessPieceType.PAWN)

    def is_captureable(self, target):
        return target is not None and super().is_captureable(target)

    def update_all_legal_moves(self, board):
        self.controlled_squares.clear()
        if self.position is None or board is None:
            return
        if self.player.is_in_check:
            self.update_legal_moves_in_check()
            return
        self.legal_moves.clear()

        row = self.position.row
        col = self.position.col

        direction = -1 if self.color == ChessColor.WHITE else 1
        start_row = 6 if self.color == ChessColor.WHITE else 1

        # 1 step forward
        one_row = row + direction
        if 0 <= one_row < 8:
            if board.grid[one_row][col] is None:
                self.legal_moves.add(SquarePosition(row=one_row, col=col))

                # 2 steps forward from start
                if row == start_row:
                    two_row = row + 2 * direction
                    if 0 <= two_row < 8 and board.grid[two_row][col] is None:
                        self.legal_moves.add(SquarePosition(row=two_row, col=col))

        # diagonal captures
        for dc in (-1, 1):
            cap_row = row + direction
            cap_col = col + dc
            if 0 <= cap_row < 8 and 0 <= cap_col < 8:
                pos = SquarePosition(row=cap_row, col=cap_col)
                self.controlled_squares.add(pos)
                target = board.grid[cap_row][cap_col]
                if self.is_captureable(target):
                    self.legal_moves.add(pos)

class Knight(ChessPiece):
    def __init__(self, color, position: SquarePosition):
        super().__init__(color, position, ChessPieceType.KNIGHT)
    def update_all_legal_moves(self, board):
        self.legal_moves.clear()
        if self.position is None or board is None:
            return
        if self.player.is_in_check:
            self.update_legal_moves_in_check()
            return
        self.controlled_squares.clear()


        directions = [
           (2,1),(2,-1),
            (1,2),(1,-2),
            (-1,2),(-1,-2),
            (-2,1),(-2,-1)
        ]


        start_r = self.position.row
        start_c = self.position.col

        for dr, dc in directions:
            r = start_r + dr
            c = start_c + dc

            if 0 <= r < 8 and 0 <= c < 8:
                pos = SquarePosition(row=r, col=c)
                target = board.grid[r][c]
                self.controlled_squares.add(pos)
                if not target or target.color != self.color:
                    self.legal_moves.add(pos)



class Rook(ChessPiece):
    def __init__(self, color, position: SquarePosition):
        super().__init__(color, position, ChessPieceType.ROOK)

    def update_all_legal_moves(self, board):
        self.legal_moves.clear()

        if self.player.is_in_check:
            self.update_legal_moves_in_check()
            return
        self.controlled_squares.clear()


        if self.position is None or board is None:
            return

        directions = [
            (-1, 0),  # up
            (1, 0),   # down
            (0, -1),  # left
            (0, 1),   # right
        ]
        add_sliding_moves(self, board, directions)


class Bishop(ChessPiece):
    def __init__(self, color, position: SquarePosition):
        super().__init__(color, position, ChessPieceType.BISHOP)

    def update_all_legal_moves(self, board):
        self.legal_moves.clear()
        self.controlled_squares.clear()

        if self.position is None or board is None:
            return
        if self.player.is_in_check:
            self.update_legal_moves_in_check()
            return
        self.controlled_squares.clear()

        directions = [
            (-1, -1),  # up-left
            (-1, 1),   # up-right
            (1, -1),   # down-left
            (1, 1),    # down-right
        ]
        add_sliding_moves(self, board, directions)


class Queen(ChessPiece):
    def __init__(self, color, position: SquarePosition):
        super().__init__(color, position, ChessPieceType.QUEEN)

    def update_all_legal_moves(self, board):
        self.legal_moves.clear()
        self.controlled_squares.clear()

        if self.position is None or board is None:
            return
        if self.player.is_in_check:
            self.update_legal_moves_in_check()
            return
        self.controlled_squares.clear()

        directions = [
            (-1, 0), (1, 0), (0, -1), (0, 1),      # rook-like
            (-1, -1), (-1, 1), (1, -1), (1, 1),    # bishop-like
        ]
        add_sliding_moves(self, board, directions)

class King(ChessPiece):
    def __init__(self, color, position: SquarePosition):
        super().__init__(color, position, ChessPieceType.KING)

    def update_all_legal_moves(self, board):
        self.legal_moves.clear()
        self.controlled_squares.clear()

        if self.position is None:
            return


        directions = [
            (-1, 0), (1, 0), (0, -1), (0, 1),
            (-1, -1), (-1, 1), (1, -1), (1, 1),
        ]

        enemy_player = PLAYERS.get(OTHER_COLOR.get(self.color))

        for dr, dc in directions:
            r = self.position.row + dr
            c = self.position.col + dc

            if 0 <= r < BOARD_SIZE and 0 <= c < BOARD_SIZE:
                pos = SquarePosition(row=r, col=c)
                self.controlled_squares.add(pos)

                # 1. Check if the square is attacked by ANY enemy piece
                if enemy_player.is_controlling_square(pos):
                    continue

                target = board.grid[r][c]

                # 2. Basic movement / capture logic
                if target is None:
                    self.legal_moves.add(pos)
                else:
                    # Capture only if it's an enemy AND not protected
                    if target.color != self.color:
                        # Crucial: Check if the enemy piece is protected
                        if not self.is_piece_protected(board, pos, enemy_player):
                            self.legal_moves.add(pos)

    def is_piece_protected(self, board, pos, enemy_player):
        """
        Determines if an enemy piece at 'pos' is defended by another enemy piece.
        """
        # In a simple engine, we can check if the enemy player
        # 'controls' the square their own piece is standing on.
        return enemy_player.is_controlling_square(pos)

    def has_valid_moves(self):
        return self.legal_moves






# </editor-fold>


# <editor-fold desc="FEN helpers">
def create_piece_from_fen(char: str, position: SquarePosition):
    color = ChessColor.WHITE if char.isupper() else ChessColor.BLACK
    c = char.lower()

    if c == 'p': return Pawn(color, position)
    if c == 'r': return Rook(color, position)
    if c == 'n': return Knight(color, position)
    if c == 'b': return Bishop(color, position)
    if c == 'q': return Queen(color, position)
    if c == 'k': return King(color, position)
    return None
# </editor-fold>


# <editor-fold desc="BOARD AND PLAYER">

class Player:
    def __init__(self, board, color):
        self.board = board
        self.color = color
        self.pieces = []
        self.controlled_squares = set()
        self.is_in_check = False
        self.is_in_checkmate = False
        self.checking_pieces = []
        self.king = None
        # Do not calculate here, wait for board to load

    def refresh_pieces(self):
        """Finds my pieces on the current board grid."""
        self.pieces = [p for p in self.board.get_all_pieces() if p.color == self.color]
        self.king = None
        for p in self.pieces:
            if p.is_king():
                self.king = p
        if self.king is None:
            self.is_in_checkmate = True

    def get_legal_moves(self) -> dict[ChessPiece: set[SquarePosition]]:
        legal_moves = {}
        for piece in self.pieces:
            legal_moves[piece] = piece.legal_moves
        return legal_moves




    def update_controlled_squares(self):
        """Calculates all squares my pieces are attacking."""
        self.controlled_squares.clear()
        for piece in self.pieces:
            # Kings need legal moves to move, but their "control" is just their basic move set.
            # To avoid recursion, we can just use the piece's current legal moves
            # (assuming they were updated before calling this).
            for square in piece.controlled_squares:
                self.controlled_squares.add(square)

    def is_controlling_square(self, square_position: SquarePosition) -> bool:
        return square_position in self.controlled_squares


class Board:
    def __init__(self, fen: str = None):
        self.grid: list[list[ChessPiece | None]] = [[None for _ in range(8)] for _ in range(8)]
        self.active_color = ChessColor.WHITE
        self.castling_rights = ""
        self.en_passant = None
        self.halfmove_clock = 0
        self.fullmove_number = 1

        if fen:
            self.load_fen(fen)

    def clear(self):
        self.grid = [[None for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]

    def load_fen(self, fen: str):
        self.clear()
        parts = fen.strip().split()
        if len(parts) != 6:
            raise ValueError("Invalid FEN")

        piece_data, active, castling, en_passant, halfmove, fullmove = parts
        rows = piece_data.split('/')
        for row_index, row in enumerate(rows):
            col = 0
            for ch in row:
                if ch.isdigit():
                    col += int(ch)
                else:
                    pos = SquarePosition(row=row_index, col=col)
                    piece = create_piece_from_fen(ch, pos)
                    self.grid[row_index][col] = piece
                    col += 1

        self.active_color = ChessColor.WHITE if active == 'w' else ChessColor.BLACK
        self.castling_rights = castling
        self.en_passant = None if en_passant == '-' else en_passant
        self.halfmove_clock = int(halfmove)
        self.fullmove_number = int(fullmove)

        self.update_game_state()

    def perform_castle(self, king, rook):
        king_old_pos = king.position
        rook_old_pos = rook.position

        # Calculate the new columns
        direction = 1 if rook_old_pos.col > king_old_pos.col else -1
        king_new_col = king_old_pos.col + (2 * direction)
        rook_new_col = king_new_col - direction

        king_new_pos = SquarePosition(row=king_old_pos.row, col=king_new_col)
        rook_new_pos = SquarePosition(row=king_old_pos.row, col=rook_new_col)

        # 1. Update the grid (Clear old, set new)
        self.grid[king_old_pos.row][king_old_pos.col] = None
        self.grid[rook_old_pos.row][rook_old_pos.col] = None
        self.grid[king_new_pos.row][king_new_pos.col] = king
        self.grid[rook_new_pos.row][rook_new_pos.col] = rook

        # 2. Update the piece objects
        king.position = king_new_pos
        rook.position = rook_new_pos
        king.has_moved = True
        rook.has_moved = True

        # 3. Finalize the turn
        self.update_game_state()
        self.switch_turn()

    def get_piece_at(self, position: SquarePosition) -> ChessPiece | None:
        return self.grid[position.row][position.col]

    def get_all_pieces(self):
        return [p for row in self.grid for p in row if p is not None]

    def update_game_state(self):

        # 1. Refresh piece ownership
        if PLAYERS:
            for p in PLAYERS.values():
                p.refresh_pieces()
        else: return

        # 2. Update moves for Non-Kings (Sliding, Knights, Pawns)
        all_pieces = self.get_all_pieces()
        for p in all_pieces:
            if not p.is_king():
                p.update_all_legal_moves(self)


        # 3. Update Controlled Squares
        if PLAYERS:
            for p in PLAYERS.values():
                p.update_controlled_squares()


        enemy_player = PLAYERS.get(OTHER_COLOR.get(self.active_color))
        playing_player = PLAYERS.get(self.active_color)
        if playing_player.is_controlling_square(enemy_player.king.position):
            enemy_player.is_in_check = True
            enemy_player.king.update_all_legal_moves(self)


            enemy_player.checking_pieces.clear()
            king_pos = enemy_player.king.position
            for piece in playing_player.pieces:
                if piece.is_controlling_square(king_pos):
                    enemy_player.checking_pieces.append(piece)
            playing_player.refresh_pieces()

            # 2. Checkmate detection
            if enemy_player.is_in_check:
                # Check if ANY piece has ANY legal move.
                # Note: True chess logic requires ensuring the move actually resolves the check.
                has_any_escape = False
                escape_pieces = []
                for piece in enemy_player.pieces:
                    piece.update_all_legal_moves(self)
                    if piece.legal_moves:  # If at least one piece can move somewhere
                        has_any_escape = True

                        escape_pieces.append(piece)
                        break

                enemy_player.is_in_checkmate = not has_any_escape
                print("escaped = ", escape_pieces)
            else:
                enemy_player.is_in_checkmate = False

            if enemy_player.is_in_checkmate:
                print(f"CHECKMATE! {OTHER_COLOR.get(enemy_player.color).value} wins!")
            else:
                print(f"{enemy_player.color.value} is in check!")
                print(enemy_player.get_legal_moves())
        elif enemy_player.is_controlling_square(playing_player.king):
            print("nah bro")

        # 4. Update moves for Kings (Now they can see attacked squares)





    def update_all_pieces_legal_moves(self):
        # Redirect to the safe update method
        self.update_game_state()

    def move_piece(self, from_pos: SquarePosition, to_pos: SquarePosition):
        piece = self.grid[from_pos.row][from_pos.col]
        if piece is None:
            raise ValueError("No piece at source position")

        target = self.grid[to_pos.row][to_pos.col]

        # capture
        if target is not None:
            target.die()

        # move
        self.grid[to_pos.row][to_pos.col] = piece
        self.grid[from_pos.row][from_pos.col] = None
        piece.position = SquarePosition(row=to_pos.row, col=to_pos.col)
        piece.has_moved = True

        # Update everything
        self.update_game_state()
        self.switch_turn()

    def switch_turn(self):
        self.active_color = ChessColor.BLACK if self.active_color == ChessColor.WHITE else ChessColor.WHITE

    # ... (Keep create_fen as it was)
    def create_fen(self) -> str:
        # ... [Your existing create_fen code] ...
        fen_rows = []
        for row in range(8):
            empty = 0
            fen_row = ""
            for col in range(8):
                piece = self.grid[row][col]
                if piece is None:
                    empty += 1
                else:
                    if empty:
                        fen_row += str(empty)
                        empty = 0
                    char = piece.type.value
                    if piece.color == ChessColor.BLACK:
                        char = char.lower()
                    fen_row += char
            if empty:
                fen_row += str(empty)
            fen_rows.append(fen_row)

        placement = "/".join(fen_rows)
        active = "w" if self.active_color == ChessColor.WHITE else "b"
        castling = self.castling_rights or "-"
        en_passant = self.en_passant or "-"
        return f"{placement} {active} {castling} {en_passant} {self.halfmove_clock} {self.fullmove_number}"


# </editor-fold>


# <editor-fold desc="DRAWING">
def get_image_path(color: ChessColor, piece_type: ChessPieceType):
    return f"assets/sliced_pieces/{color.value}_{piece_type.name}.png"

def draw_board(screen):
    for row in range(8):
        for col in range(8):
            color = LIGHT if (row + col) % 2 == 0 else DARK
            pygame.draw.rect(
                screen,
                color,
                (col * SQUARE_SIZE, row * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE)
            )

def get_piece_image(piece: ChessPiece, cache):
    key = (piece.color, piece.type)
    if key not in cache:
        img = pygame.image.load(get_image_path(piece.color, piece.type)).convert_alpha()
        img = pygame.transform.smoothscale(img, (int(SQUARE_SIZE * 0.85), int(SQUARE_SIZE * 0.85)))
        cache[key] = img
    return cache[key]

def draw_piece(screen, piece: ChessPiece, cache):
    if piece.position is None:
        return
    row = piece.position.row
    col = piece.position.col
    img = get_piece_image(piece, cache)
    rect = img.get_rect(center=(
        col * SQUARE_SIZE + SQUARE_SIZE // 2,
        row * SQUARE_SIZE + SQUARE_SIZE // 2
    ))
    screen.blit(img, rect)

def draw_pieces(screen, board: Board, cache):
    for piece in board.get_all_pieces():
        draw_piece(screen, piece, cache)
# </editor-fold>


# <editor-fold desc="GLOBAL VARIABLES">
PYGAME = pygame
SCREEN = None

# Initialize dict first to avoid NameError if Board tries to access it
PLAYERS = {}

BOARD = Board()

# Now populate Players
PLAYERS[ChessColor.WHITE] = Player(BOARD, ChessColor.WHITE)
PLAYERS[ChessColor.BLACK] = Player(BOARD, ChessColor.BLACK)

IMAGE_CACHE = {}



# </editor-fold>


# <editor-fold desc="MAIN">
def main():
    global SCREEN, BOARD, IMAGE_CACHE,WHITE_PLAYER,BLACK_PLAYER,PLAYERS

    pygame.init()
    SCREEN = pygame.display.set_mode((WINDOW_SIZE, WINDOW_SIZE))
    pygame.display.set_caption("Chess")
    clock = pygame.time.Clock()
    BOARD.load_fen(STARTING_POSITION)
    IMAGE_CACHE = {}



    picking_piece: ChessPiece | None = None

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.MOUSEBUTTONDOWN:
                clicked = pixel_to_squarepos(event.pos)
                if clicked is None:
                    continue

                clicked_piece = BOARD.get_piece_at(clicked)

                if clicked_piece is not None:
                    # selecting your own piece

                    if clicked_piece.color == BOARD.active_color and picking_piece is None:
                        picking_piece = clicked_piece

                    elif picking_piece is not None and clicked_piece.color == BOARD.active_color and (
                         clicked_piece.color == picking_piece.color
                    ):
                        if can_castle(BOARD,picking_piece,clicked_piece):
                            perform_castle()
                            picking_piece = None

                        else: picking_piece = clicked_piece
                    # capturing opponent
                    elif (picking_piece is not None and clicked_piece.color != picking_piece.color
                          and picking_piece.is_valid_move(clicked)):
                        BOARD.move_piece(picking_piece.position, clicked_piece.position)
                        picking_piece = None
                else:
                    # moving to empty square
                    if picking_piece is not None and picking_piece.is_valid_move(clicked):
                        BOARD.move_piece(picking_piece.position, clicked)
                        picking_piece = None

        SCREEN.fill((0, 0, 0))
        draw_board(SCREEN)
        draw_pieces(SCREEN, BOARD, IMAGE_CACHE)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
# </editor-fold>