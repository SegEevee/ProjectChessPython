import pygame
import sys
from enum import Enum

# <editor-fold desc="CONFIG">
BOARD_SIZE = 8
SQUARE_SIZE = 80
WINDOW_SIZE = BOARD_SIZE * SQUARE_SIZE
FPS = 60

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
            raise ValueError("SquarePosition requires notation or row+col")

    def to_notation(self) -> str:
        return row_col_to_notation(self.row, self.col)

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

class ChessPieceType(Enum):
    PAWN   = "P"
    ROOK   = "R"
    KNIGHT = "N"
    BISHOP = "B"
    QUEEN  = "Q"
    KING   = "K"
# </editor-fold>


# <editor-fold desc="PIECES">
class ChessPiece:
    def __init__(self, color: ChessColor, position: SquarePosition, piece_type: ChessPieceType):
        self.color = color
        self.position: SquarePosition | None = position
        self.type = piece_type
        self.legal_moves: set[SquarePosition] = set()

    def die(self):
        self.position = None

    def update_all_legal_moves(self, board):
        self.legal_moves.clear()

    def is_valid_move(self, new_position: SquarePosition) -> bool:
        return new_position in self.legal_moves

    def __repr__(self):
        return f"{self.color.value} {self.type.name} @ {self.position}"


class Pawn(ChessPiece):
    def __init__(self, color, position: SquarePosition):
        super().__init__(color, position, ChessPieceType.PAWN)


    def update_all_legal_moves(self, board):
        self.legal_moves.clear()
        if self.position is None or board is None:
            return

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
                target = board.grid[cap_row][cap_col]
                if target is not None and target.color != self.color:
                    self.legal_moves.add(SquarePosition(row=cap_row, col=cap_col))


class Rook(ChessPiece):
    def __init__(self, color, position: SquarePosition):
        super().__init__(color, position, ChessPieceType.ROOK)

class Knight(ChessPiece):
    def __init__(self, color, position: SquarePosition):
        super().__init__(color, position, ChessPieceType.KNIGHT)

class Bishop(ChessPiece):
    def __init__(self, color, position: SquarePosition):
        super().__init__(color, position, ChessPieceType.BISHOP)

class Queen(ChessPiece):
    def __init__(self, color, position: SquarePosition):
        super().__init__(color, position, ChessPieceType.QUEEN)

class King(ChessPiece):
    def __init__(self, color, position: SquarePosition):
        super().__init__(color, position, ChessPieceType.KING)
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


# <editor-fold desc="BOARD">
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
        self.grid = [[None for _ in range(8)] for _ in range(8)]

    def load_fen(self, fen: str):
        self.clear()
        parts = fen.strip().split()
        if len(parts) != 6:
            raise ValueError("Invalid FEN")

        piece_data, active, castling, en_passant, halfmove, fullmove = parts
        rows = piece_data.split('/')
        if len(rows) != 8:
            raise ValueError("Invalid FEN rows")

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

        for piece in self.get_all_pieces():
            piece.update_all_legal_moves(self)

    def get_piece_at(self, position: SquarePosition) -> ChessPiece | None:
        return self.grid[position.row][position.col]

    def get_all_pieces(self):
        return [p for row in self.grid for p in row if p is not None]



    def move_piece(self, from_pos: SquarePosition, to_pos: SquarePosition):
        piece = self.grid[from_pos.row][from_pos.col]
        if piece is None:
            raise ValueError("No piece at source position")

        target = self.grid[to_pos.row][to_pos.col]
        if target is not None and target.color == piece.color:
            raise ValueError("Cannot move onto your own piece")

        # capture
        if target is not None:
            target.die()

        # move
        self.grid[to_pos.row][to_pos.col] = piece
        self.grid[from_pos.row][from_pos.col] = None
        piece.position = SquarePosition(row=to_pos.row, col=to_pos.col)
        piece.update_all_legal_moves(self)

        self.switch_turn()




    def switch_turn(self):
        self.active_color = ChessColor.BLACK if self.active_color == ChessColor.WHITE else ChessColor.WHITE

    def create_fen(self) -> str:
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
BOARD = None
IMAGE_CACHE = {}
# </editor-fold>


# <editor-fold desc="MAIN">
def main():
    global SCREEN, BOARD, IMAGE_CACHE

    pygame.init()
    SCREEN = pygame.display.set_mode((WINDOW_SIZE, WINDOW_SIZE))
    pygame.display.set_caption("Chess")
    clock = pygame.time.Clock()
    print("got here")
    BOARD = Board("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
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
                    if clicked_piece.color == BOARD.active_color and (
                        picking_piece is None or clicked_piece.color == picking_piece.color
                    ):
                        picking_piece = clicked_piece
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
