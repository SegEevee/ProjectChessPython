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
    def __init__(self, color: ChessColor, position: str, piece_type: ChessPieceType):
        self.color = color
        self.position = position
        self.type = piece_type

    def move_to(self, new_position):
        BOARD.move_piece(self.position, new_position)
        self.position = new_position

    def eat(self, target_piece):
        temp_position = target_piece.position
        target_piece.die()
        self.move_to(temp_position)

    def die(self):
        self.position = None

    def __repr__(self):
        return f"{self.color.value} {self.type.name} @ {self.position}"
    def __eq__(self, other):
        if not isinstance(other, ChessPiece):
            return False
        return (self.color == other.color and
                self.position == other.position and
                self.type == other.type)


class Pawn(ChessPiece):
    def __init__(self, color, position):
        super().__init__(color, position, ChessPieceType.PAWN)

class Rook(ChessPiece):
    def __init__(self, color, position):
        super().__init__(color, position, ChessPieceType.ROOK)

class Knight(ChessPiece):
    def __init__(self, color, position):
        super().__init__(color, position, ChessPieceType.KNIGHT)

class Bishop(ChessPiece):
    def __init__(self, color, position):
        super().__init__(color, position, ChessPieceType.BISHOP)

class Queen(ChessPiece):
    def __init__(self, color, position):
        super().__init__(color, position, ChessPieceType.QUEEN)

class King(ChessPiece):
    def __init__(self, color, position):
        super().__init__(color, position, ChessPieceType.KING)
# </editor-fold>


# <editor-fold desc="HELPERS">
def get_image_path(color: ChessColor, piece_type: ChessPieceType):
    return f"assets/sliced_pieces/{color.value}_{piece_type.name}.png"

def notation_to_row_col(pos: str):
    col = ord(pos[0].lower()) - ord('a')
    row = 8 - int(pos[1])
    return row, col

def row_col_to_notation(row, col):
    return chr(ord('a') + col) + str(8 - row)

def pixel_to_notation(mouse_pos):
    x, y = mouse_pos
    col = x // SQUARE_SIZE
    row = y // SQUARE_SIZE

    if 0 <= col < 8 and 0 <= row < 8:
        return row_col_to_notation(row, col)
    return None

def create_piece_from_fen(char, position):
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
    def __init__(self, fen=None):
        self.grid = [[None for _ in range(8)] for _ in range(8)]
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

        for row_index, row in enumerate(rows):
            col = 0
            for char in row:
                if char.isdigit():
                    col += int(char)
                else:
                    pos = row_col_to_notation(row_index, col)
                    piece = create_piece_from_fen(char, pos)
                    self.grid[row_index][col] = piece
                    col += 1

        self.active_color = ChessColor.WHITE if active == 'w' else ChessColor.BLACK
        self.castling_rights = castling
        self.en_passant = None if en_passant == '-' else en_passant
        self.halfmove_clock = int(halfmove)
        self.fullmove_number = int(fullmove)

    def move_piece(self, from_pos, to_pos):
        from_row, from_col = notation_to_row_col(from_pos)
        to_row, to_col = notation_to_row_col(to_pos)

        piece = self.grid[from_row][from_col]
        if piece is None:
            raise ValueError("No piece at source position")

        target_piece = self.grid[to_row][to_col]
        if target_piece and target_piece.color == piece.color:
            raise ValueError("Cannot move to a square occupied by your own piece")

        if target_piece:
            remove_piece(SCREEN, target_piece)

        self.grid[to_row][to_col] = piece
        self.grid[from_row][from_col] = None

        piece.position = to_pos

        draw_piece(SCREEN, piece , IMAGE_CACHE)

        self.switch_turn()

    def switch_turn(self, last_moved: ChessPiece = None):
        if last_moved is None:
            self.active_color = ChessColor.BLACK if self.active_color == ChessColor.WHITE else ChessColor.WHITE
            return

        self.active_color = ChessColor.BLACK if last_moved and last_moved.color == ChessColor.WHITE else ChessColor.WHITE
        if last_moved and last_moved.type == ChessPieceType.PAWN:
            self.halfmove_clock = 0
        else:
            self.halfmove_clock += 1

        if self.active_color == ChessColor.WHITE:
            self.fullmove_number += 1



    def create_fen(self):
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

    def get_piece_at(self, position):
        row, col = notation_to_row_col(position)
        return self.grid[row][col]

    def get_all_pieces(self):
        return [piece for row in self.grid for piece in row if piece]
# </editor-fold>


# <editor-fold desc="DRAWING">
def draw_board(screen):
    for row in range(8):
        for col in range(8):
            color = LIGHT if (row + col) % 2 == 0 else DARK
            pygame.draw.rect(
                screen,
                color,
                (col * SQUARE_SIZE, row * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE)
            )

def get_piece_image(piece, cache):
    key = (piece.color, piece.type)
    if key not in cache:
        img = pygame.image.load(
            get_image_path(piece.color, piece.type)
        ).convert_alpha()
        img = pygame.transform.smoothscale(
            img,
            (int(SQUARE_SIZE * 0.85), int(SQUARE_SIZE * 0.85))
        )
        cache[key] = img
    return cache[key]

def remove_piece(screen, piece):
    row, col = notation_to_row_col(piece.position)
    pygame.draw.rect(
        screen,
        LIGHT if (row + col) % 2 == 0 else DARK,
        (col * SQUARE_SIZE, row * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE)
    )

def draw_piece(screen, piece : ChessPiece, cache):
    row, col = notation_to_row_col(piece.position)
    img = get_piece_image(piece, cache)
    rect = img.get_rect(center=(
        col * SQUARE_SIZE + SQUARE_SIZE // 2,
        row * SQUARE_SIZE + SQUARE_SIZE // 2
    ))
    screen.blit(img, rect)


def draw_pieces(screen, board, cache):
    for piece in board.get_all_pieces():
        draw_piece(screen, piece, cache)
# </editor-fold>

#<editor-fold desc="global variables">
PYGAME = pygame
SCREEN = pygame.display.set_mode((WINDOW_SIZE, WINDOW_SIZE))
BOARD = Board("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
IMAGE_CACHE = {}
#</editor-fold>


# <editor-fold desc="MAIN">
def main():
    global PYGAME, SCREEN, BOARD,IMAGE_CACHE

    PYGAME.init()
    SCREEN = pygame.display.set_mode((WINDOW_SIZE, WINDOW_SIZE))
    PYGAME.display.set_caption("Chess")
    clock = pygame.time.Clock()

    BOARD = Board("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")


    picking_piece = None

    running = True
    while running:
        for event in PYGAME.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.MOUSEBUTTONDOWN:
                square = pixel_to_notation(event.pos)
                if square:
                    piece = BOARD.get_piece_at(square)
                    if piece:

                        if (piece.color == BOARD.active_color
                                and (picking_piece is None or piece.color == picking_piece.color)):
                            picking_piece = piece
                        elif picking_piece and piece.color != picking_piece.color:
                            BOARD.move_piece(picking_piece.position, piece.position)
                            picking_piece = None

                    else:
                        if picking_piece:
                            BOARD.move_piece(picking_piece.position, square)
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
