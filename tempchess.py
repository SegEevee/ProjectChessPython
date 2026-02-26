import pygame
import math
import time
from enum import Enum
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass

# Initialize Pygame
pygame.init()

# Constants
SCREEN_WIDTH = 640
SCREEN_HEIGHT = 840
BOARD_SIZE = 640
SQUARE_SIZE = BOARD_SIZE // 8
SIDE_PANEL_WIDTH = 200
FPS = 60

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
LIGHT_BROWN = (240, 217, 181)
DARK_BROWN = (181, 136, 99)
HIGHLIGHT_YELLOW = (255, 255, 0, 128)
HIGHLIGHT_GREEN = (0, 255, 0, 128)
HIGHLIGHT_RED = (255, 0, 0, 128)
ARROW_ORANGE = (255, 165, 0)
BLUE = (0, 0, 255)
GRAY = (128, 128, 128)

# UI Constants
UNDO_BTN_RECT = pygame.Rect(BOARD_SIZE + 20, 50, 160, 40)
NOTATION_BTN_RECT = pygame.Rect(BOARD_SIZE + 20, 100, 160, 40)


class Color(Enum):
    WHITE = "white"
    BLACK = "black"


class MoveType(Enum):
    NORMAL = "normal"
    CASTLE = "castle"
    EN_PASSANT = "en_passant"
    PROMOTION = "promotion"


class PieceType(Enum):
    PAWN = "pawn"
    ROOK = "rook"
    KNIGHT = "knight"
    BISHOP = "bishop"
    QUEEN = "queen"
    KING = "king"


@dataclass(frozen=True)
class SquarePosition:
    row: int
    col: int

    def __add__(self, other):
        return SquarePosition(self.row + other.row, self.col + other.col)

    def is_valid(self):
        return 0 <= self.row < 8 and 0 <= self.col < 8


@dataclass
class Move:
    from_pos: SquarePosition
    to_pos: SquarePosition
    move_type: MoveType = MoveType.NORMAL
    promotion_piece: Optional[PieceType] = None

    def __hash__(self):
        return hash((self.from_pos, self.to_pos, self.move_type))


@dataclass
class MoveRecord:
    move: Move
    piece_has_moved: bool
    victim_piece: Optional['ChessPiece']
    castling_rights: Dict
    en_passant: Optional[SquarePosition]


class ChessPiece:
    def __init__(self, color: Color, position: SquarePosition):
        self.color = color
        self.position = position
        self.has_moved = False
        self.legal_moves: Dict[SquarePosition, Move] = {}
        self.controlled_squares: Set[SquarePosition] = set()

    def update_all_legal_moves(self, board: 'Board'):
        self.legal_moves.clear()
        self.controlled_squares.clear()
        self.generate_moves(board)
        self.filter_safe_moves(board)

    def generate_moves(self, board: 'Board'):
        pass  # Implemented by subclasses

    def filter_safe_moves(self, board: 'Board'):
        safe_moves = {}
        for to_pos, move in self.legal_moves.items():
            if board.is_move_safe(self, move):
                safe_moves[to_pos] = move
        self.legal_moves = safe_moves

    def add_sliding_moves(self, board: 'Board', directions: List[Tuple[int, int]]):
        for dr, dc in directions:
            current_pos = self.position
            while True:
                current_pos = SquarePosition(current_pos.row + dr, current_pos.col + dc)
                if not current_pos.is_valid():
                    break

                self.controlled_squares.add(current_pos)
                target_piece = board.get_piece(current_pos)

                if target_piece is None:
                    self.legal_moves[current_pos] = Move(self.position, current_pos)
                else:
                    if target_piece.color != self.color:
                        self.legal_moves[current_pos] = Move(self.position, current_pos)
                    break

    def get_symbol(self):
        symbols = {
            PieceType.PAWN: ('♙', '♟'), PieceType.ROOK: ('♖', '♜'),
            PieceType.KNIGHT: ('♘', '♞'), PieceType.BISHOP: ('♗', '♝'),
            PieceType.QUEEN: ('♕', '♛'), PieceType.KING: ('♔', '♚')
        }
        return symbols[self.piece_type][0 if self.color == Color.WHITE else 1]

    def get_fen_char(self):
        chars = {
            PieceType.PAWN: 'P', PieceType.ROOK: 'R', PieceType.KNIGHT: 'N',
            PieceType.BISHOP: 'B', PieceType.QUEEN: 'Q', PieceType.KING: 'K'
        }
        char = chars[self.piece_type]
        return char if self.color == Color.WHITE else char.lower()


class Pawn(ChessPiece):
    piece_type = PieceType.PAWN

    def generate_moves(self, board: 'Board'):
        direction = -1 if self.color == Color.WHITE else 1
        start_row = 6 if self.color == Color.WHITE else 1

        # Forward moves
        one_forward = SquarePosition(self.position.row + direction, self.position.col)
        if one_forward.is_valid() and board.get_piece(one_forward) is None:
            if (one_forward.row == 0 and self.color == Color.WHITE) or \
                    (one_forward.row == 7 and self.color == Color.BLACK):
                # Promotion
                for piece_type in [PieceType.QUEEN, PieceType.ROOK, PieceType.BISHOP, PieceType.KNIGHT]:
                    self.legal_moves[one_forward] = Move(
                        self.position, one_forward, MoveType.PROMOTION, piece_type
                    )
            else:
                self.legal_moves[one_forward] = Move(self.position, one_forward)

            # Two squares forward from starting position
            if self.position.row == start_row:
                two_forward = SquarePosition(self.position.row + 2 * direction, self.position.col)
                if two_forward.is_valid() and board.get_piece(two_forward) is None:
                    self.legal_moves[two_forward] = Move(self.position, two_forward)

        # Captures
        for dc in [-1, 1]:
            capture_pos = SquarePosition(self.position.row + direction, self.position.col + dc)
            if capture_pos.is_valid():
                self.controlled_squares.add(capture_pos)
                target_piece = board.get_piece(capture_pos)

                if target_piece and target_piece.color != self.color:
                    if (capture_pos.row == 0 and self.color == Color.WHITE) or \
                            (capture_pos.row == 7 and self.color == Color.BLACK):
                        # Promotion capture
                        for piece_type in [PieceType.QUEEN, PieceType.ROOK, PieceType.BISHOP, PieceType.KNIGHT]:
                            self.legal_moves[capture_pos] = Move(
                                self.position, capture_pos, MoveType.PROMOTION, piece_type
                            )
                    else:
                        self.legal_moves[capture_pos] = Move(self.position, capture_pos)

                # En passant
                if board.en_passant == capture_pos:
                    self.legal_moves[capture_pos] = Move(
                        self.position, capture_pos, MoveType.EN_PASSANT
                    )


class Rook(ChessPiece):
    piece_type = PieceType.ROOK

    def generate_moves(self, board: 'Board'):
        self.add_sliding_moves(board, [(-1, 0), (1, 0), (0, -1), (0, 1)])


class Knight(ChessPiece):
    piece_type = PieceType.KNIGHT

    def generate_moves(self, board: 'Board'):
        knight_moves = [(-2, -1), (-2, 1), (-1, -2), (-1, 2),
                        (1, -2), (1, 2), (2, -1), (2, 1)]

        for dr, dc in knight_moves:
            new_pos = SquarePosition(self.position.row + dr, self.position.col + dc)
            if new_pos.is_valid():
                self.controlled_squares.add(new_pos)
                target_piece = board.get_piece(new_pos)

                if target_piece is None or target_piece.color != self.color:
                    self.legal_moves[new_pos] = Move(self.position, new_pos)


class Bishop(ChessPiece):
    piece_type = PieceType.BISHOP

    def generate_moves(self, board: 'Board'):
        self.add_sliding_moves(board, [(-1, -1), (-1, 1), (1, -1), (1, 1)])


class Queen(ChessPiece):
    piece_type = PieceType.QUEEN

    def generate_moves(self, board: 'Board'):
        self.add_sliding_moves(board, [(-1, -1), (-1, 0), (-1, 1), (0, -1),
                                       (0, 1), (1, -1), (1, 0), (1, 1)])


class King(ChessPiece):
    piece_type = PieceType.KING

    def generate_moves(self, board: 'Board'):
        king_moves = [(-1, -1), (-1, 0), (-1, 1), (0, -1),
                      (0, 1), (1, -1), (1, 0), (1, 1)]

        for dr, dc in king_moves:
            new_pos = SquarePosition(self.position.row + dr, self.position.col + dc)
            if new_pos.is_valid():
                self.controlled_squares.add(new_pos)
                target_piece = board.get_piece(new_pos)

                if target_piece is None or target_piece.color != self.color:
                    self.legal_moves[new_pos] = Move(self.position, new_pos)

        # Castling
        if not self.has_moved and not board.players[self.color].is_in_check:
            # Kingside castling
            if board.castling_rights[self.color]['kingside']:
                if (board.get_piece(SquarePosition(self.position.row, 5)) is None and
                        board.get_piece(SquarePosition(self.position.row, 6)) is None):
                    if not board.is_square_attacked(SquarePosition(self.position.row, 5),
                                                    Color.BLACK if self.color == Color.WHITE else Color.WHITE):
                        self.legal_moves[SquarePosition(self.position.row, 6)] = Move(
                            self.position, SquarePosition(self.position.row, 6), MoveType.CASTLE
                        )

            # Queenside castling
            if board.castling_rights[self.color]['queenside']:
                if (board.get_piece(SquarePosition(self.position.row, 3)) is None and
                        board.get_piece(SquarePosition(self.position.row, 2)) is None and
                        board.get_piece(SquarePosition(self.position.row, 1)) is None):
                    if not board.is_square_attacked(SquarePosition(self.position.row, 3),
                                                    Color.BLACK if self.color == Color.WHITE else Color.WHITE):
                        self.legal_moves[SquarePosition(self.position.row, 2)] = Move(
                            self.position, SquarePosition(self.position.row, 2), MoveType.CASTLE
                        )


class Player:
    def __init__(self, color: Color):
        self.color = color
        self.time_remaining = 600  # 10 minutes in seconds
        self.is_in_check = False
        self.is_in_checkmate = False
        self.lost = False

    def has_legal_moves(self, board: 'Board') -> bool:
        for piece in board.get_player_pieces(self.color):
            if piece.legal_moves:
                return True
        return False


class Board:
    def __init__(self):
        self.grid: List[List[Optional[ChessPiece]]] = [[None] * 8 for _ in range(8)]
        self.active_color = Color.WHITE
        self.players = {Color.WHITE: Player(Color.WHITE), Color.BLACK: Player(Color.BLACK)}

        self.castling_rights = {
            Color.WHITE: {'kingside': True, 'queenside': True},
            Color.BLACK: {'kingside': True, 'queenside': True}
        }
        self.en_passant: Optional[SquarePosition] = None
        self.move_log: List[MoveRecord] = []

        self.setup_initial_position()
        self.update_game_state()

    def setup_initial_position(self):
        # Place pawns
        for col in range(8):
            self.grid[1][col] = Pawn(Color.BLACK, SquarePosition(1, col))
            self.grid[6][col] = Pawn(Color.WHITE, SquarePosition(6, col))

        # Place other pieces
        piece_order = [Rook, Knight, Bishop, Queen, King, Bishop, Knight, Rook]
        for col, piece_class in enumerate(piece_order):
            self.grid[0][col] = piece_class(Color.BLACK, SquarePosition(0, col))
            self.grid[7][col] = piece_class(Color.WHITE, SquarePosition(7, col))

    def get_piece(self, position: SquarePosition) -> Optional[ChessPiece]:
        if position.is_valid():
            return self.grid[position.row][position.col]
        return None

    def set_piece(self, position: SquarePosition, piece: Optional[ChessPiece]):
        if position.is_valid():
            self.grid[position.row][position.col] = piece
            if piece:
                piece.position = position

    def get_player_pieces(self, color: Color) -> List[ChessPiece]:
        pieces = []
        for row in self.grid:
            for piece in row:
                if piece and piece.color == color:
                    pieces.append(piece)
        return pieces

    def get_king(self, color: Color) -> Optional[King]:
        for piece in self.get_player_pieces(color):
            if isinstance(piece, King):
                return piece
        return None

    def is_square_attacked(self, position: SquarePosition, by_color: Color) -> bool:
        for piece in self.get_player_pieces(by_color):
            if position in piece.controlled_squares:
                return True
        return False

    def is_move_safe(self, piece: ChessPiece, move: Move) -> bool:
        # Save current state
        original_piece = self.get_piece(move.to_pos)
        original_pos = piece.position

        # Make the move temporarily
        self.set_piece(move.from_pos, None)
        self.set_piece(move.to_pos, piece)

        # Update enemy controlled squares
        enemy_color = Color.BLACK if piece.color == Color.WHITE else Color.WHITE
        for enemy_piece in self.get_player_pieces(enemy_color):
            enemy_piece.controlled_squares.clear()
            enemy_piece.generate_moves(self)

        # Check if king is in check
        king = self.get_king(piece.color)
        king_safe = not self.is_square_attacked(king.position, enemy_color)

        # Restore original state
        self.set_piece(move.to_pos, original_piece)
        self.set_piece(move.from_pos, piece)
        piece.position = original_pos

        return king_safe

    def execute_move(self, move: Move):
        piece = self.get_piece(move.from_pos)
        if not piece:
            return False

        # Create move record
        victim_piece = self.get_piece(move.to_pos)
        move_record = MoveRecord(
            move=move,
            piece_has_moved=piece.has_moved,
            victim_piece=victim_piece,
            castling_rights=dict(self.castling_rights),
            en_passant=self.en_passant
        )
        self.move_log.append(move_record)

        # Handle special moves
        if move.move_type == MoveType.CASTLE:
            self.handle_castling(move)
        elif move.move_type == MoveType.EN_PASSANT:
            self.handle_en_passant(move)
        elif move.move_type == MoveType.PROMOTION:
            self.handle_promotion(move)
        else:
            # Normal move
            self.set_piece(move.from_pos, None)
            self.set_piece(move.to_pos, piece)

        piece.has_moved = True

        # Update castling rights
        if isinstance(piece, King):
            self.castling_rights[piece.color]['kingside'] = False
            self.castling_rights[piece.color]['queenside'] = False
        elif isinstance(piece, Rook):
            if move.from_pos.col == 0:  # Queenside rook
                self.castling_rights[piece.color]['queenside'] = False
            elif move.from_pos.col == 7:  # Kingside rook
                self.castling_rights[piece.color]['kingside'] = False

        # Set en passant square
        self.en_passant = None
        if isinstance(piece, Pawn) and abs(move.to_pos.row - move.from_pos.row) == 2:
            self.en_passant = SquarePosition(
                (move.from_pos.row + move.to_pos.row) // 2, move.from_pos.col
            )

        # Switch active player
        self.active_color = Color.BLACK if self.active_color == Color.WHITE else Color.WHITE
        self.update_game_state()
        return True

    def handle_castling(self, move: Move):
        king = self.get_piece(move.from_pos)
        self.set_piece(move.from_pos, None)
        self.set_piece(move.to_pos, king)

        # Move rook
        if move.to_pos.col == 6:  # Kingside
            rook = self.get_piece(SquarePosition(move.from_pos.row, 7))
            self.set_piece(SquarePosition(move.from_pos.row, 7), None)
            self.set_piece(SquarePosition(move.from_pos.row, 5), rook)
        else:  # Queenside
            rook = self.get_piece(SquarePosition(move.from_pos.row, 0))
            self.set_piece(SquarePosition(move.from_pos.row, 0), None)
            self.set_piece(SquarePosition(move.from_pos.row, 3), rook)

    def handle_en_passant(self, move: Move):
        piece = self.get_piece(move.from_pos)
        self.set_piece(move.from_pos, None)
        self.set_piece(move.to_pos, piece)

        # Remove captured pawn
        captured_pawn_pos = SquarePosition(move.from_pos.row, move.to_pos.col)
        self.set_piece(captured_pawn_pos, None)

    def handle_promotion(self, move: Move):
        pawn = self.get_piece(move.from_pos)
        self.set_piece(move.from_pos, None)

        # Create new piece
        piece_classes = {
            PieceType.QUEEN: Queen, PieceType.ROOK: Rook,
            PieceType.BISHOP: Bishop, PieceType.KNIGHT: Knight
        }
        new_piece = piece_classes[move.promotion_piece](pawn.color, move.to_pos)
        new_piece.has_moved = True
        self.set_piece(move.to_pos, new_piece)

    def undo_move(self):
        if not self.move_log:
            return

        move_record = self.move_log.pop()
        move = move_record.move

        # Get the piece that moved
        piece = self.get_piece(move.to_pos)

        # Handle special undos
        if move.move_type == MoveType.CASTLE:
            self.undo_castling(move)
        elif move.move_type == MoveType.EN_PASSANT:
            self.undo_en_passant(move_record)
        elif move.move_type == MoveType.PROMOTION:
            self.undo_promotion(move_record)
        else:
            # Normal undo
            self.set_piece(move.from_pos, piece)
            self.set_piece(move.to_pos, move_record.victim_piece)

        # Restore piece state
        if piece:
            piece.has_moved = move_record.piece_has_moved

        # Restore board state
        self.castling_rights = move_record.castling_rights
        self.en_passant = move_record.en_passant
        self.active_color = Color.BLACK if self.active_color == Color.WHITE else Color.WHITE

        self.update_game_state()

    def undo_castling(self, move: Move):
        # Move king back
        king = self.get_piece(move.to_pos)
        self.set_piece(move.to_pos, None)
        self.set_piece(move.from_pos, king)

        # Move rook back
        if move.to_pos.col == 6:  # Kingside
            rook = self.get_piece(SquarePosition(move.from_pos.row, 5))
            self.set_piece(SquarePosition(move.from_pos.row, 5), None)
            self.set_piece(SquarePosition(move.from_pos.row, 7), rook)
        else:  # Queenside
            rook = self.get_piece(SquarePosition(move.from_pos.row, 3))
            self.set_piece(SquarePosition(move.from_pos.row, 3), None)
            self.set_piece(SquarePosition(move.from_pos.row, 0), rook)

    def undo_en_passant(self, move_record: MoveRecord):
        move = move_record.move
        pawn = self.get_piece(move.to_pos)

        # Move pawn back
        self.set_piece(move.to_pos, None)
        self.set_piece(move.from_pos, pawn)

        # Restore captured pawn
        captured_pawn_pos = SquarePosition(move.from_pos.row, move.to_pos.col)
        enemy_color = Color.BLACK if pawn.color == Color.WHITE else Color.WHITE
        captured_pawn = Pawn(enemy_color, captured_pawn_pos)
        captured_pawn.has_moved = True
        self.set_piece(captured_pawn_pos, captured_pawn)

    def undo_promotion(self, move_record: MoveRecord):
        move = move_record.move

        # Remove promoted piece
        self.set_piece(move.to_pos, move_record.victim_piece)

        # Restore original pawn
        original_piece = self.get_piece(move.from_pos)
        if not original_piece:  # Need to recreate the pawn
            promoted_piece = self.get_piece(move.to_pos) if not move_record.victim_piece else None
            if promoted_piece:
                pawn_color = promoted_piece.color
                self.set_piece(move.to_pos, move_record.victim_piece)
            else:
                # Determine color from move context
                pawn_color = Color.WHITE if move.from_pos.row == 6 else Color.BLACK

            pawn = Pawn(pawn_color, move.from_pos)
            pawn.has_moved = move_record.piece_has_moved
            self.set_piece(move.from_pos, pawn)

    def update_game_state(self):
        # Reset check states
        for player in self.players.values():
            player.is_in_check = False
            player.is_in_checkmate = False

        # Update all pieces' legal moves
        for piece in self.get_player_pieces(Color.WHITE) + self.get_player_pieces(Color.BLACK):
            piece.update_all_legal_moves(self)

        # Check for check and checkmate
        for color in [Color.WHITE, Color.BLACK]:
            enemy_color = Color.BLACK if color == Color.WHITE else Color.WHITE
            king = self.get_king(color)

            if self.is_square_attacked(king.position, enemy_color):
                self.players[color].is_in_check = True

                # Re-update moves under check
                for piece in self.get_player_pieces(color):
                    piece.update_all_legal_moves(self)

                if not self.players[color].has_legal_moves(self):
                    self.players[color].is_in_checkmate = True

    def generate_fen(self) -> str:
        fen_parts = []

        # Board position
        for row in range(8):
            empty_count = 0
            row_str = ""

            for col in range(8):
                piece = self.grid[row][col]
                if piece:
                    if empty_count > 0:
                        row_str += str(empty_count)
                        empty_count = 0
                    row_str += piece.get_fen_char()
                else:
                    empty_count += 1

            if empty_count > 0:
                row_str += str(empty_count)

            fen_parts.append(row_str)

        fen = "/".join(fen_parts)

        # Active color
        fen += " " + ("w" if self.active_color == Color.WHITE else "b")

        # Castling rights
        castling = ""
        if self.castling_rights[Color.WHITE]['kingside']:
            castling += "K"
        if self.castling_rights[Color.WHITE]['queenside']:
            castling += "Q"
        if self.castling_rights[Color.BLACK]['kingside']:
            castling += "k"
        if self.castling_rights[Color.BLACK]['queenside']:
            castling += "q"
        fen += " " + (castling if castling else "-")

        # En passant
        if self.en_passant:
            fen += f" {chr(ord('a') + self.en_passant.col)}{8 - self.en_passant.row}"
        else:
            fen += " -"

        # Halfmove and fullmove (simplified)
        fen += " 0 1"

        return fen


class ChessUI:
    def __init__(self, screen):
        self.screen = screen
        self.font = pygame.font.Font(None, 48)
        self.small_font = pygame.font.Font(None, 24)
        self.selected_square = None
        self.highlighted_squares = set()
        self.right_click_squares = set()
        self.arrows = []
        self.show_notation = False
        self.promotion_pending = None
        self.dragging_piece = None
        self.drag_offset = (0, 0)

    def pixel_to_square_pos(self, pixel_pos) -> Optional[SquarePosition]:
        x, y = pixel_pos
        if 0 <= x < BOARD_SIZE and 0 <= y < BOARD_SIZE:
            return SquarePosition(y // SQUARE_SIZE, x // SQUARE_SIZE)
        return None

    def square_pos_to_pixel(self, square_pos: SquarePosition) -> Tuple[int, int]:
        return (square_pos.col * SQUARE_SIZE, square_pos.row * SQUARE_SIZE)

    def draw_board(self):
        for row in range(8):
            for col in range(8):
                color = LIGHT_BROWN if (row + col) % 2 == 0 else DARK_BROWN
                rect = pygame.Rect(col * SQUARE_SIZE, row * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE)
                pygame.draw.rect(self.screen, color, rect)

                # Draw coordinates if notation is enabled
                if self.show_notation:
                    square_pos = SquarePosition(row, col)
                    text_color = DARK_BROWN if (row + col) % 2 == 0 else LIGHT_BROWN

                    # File letters (A-H)
                    if row == 7:
                        file_text = self.small_font.render(chr(ord('a') + col), True, text_color)
                        self.screen.blit(file_text, (col * SQUARE_SIZE + SQUARE_SIZE - 15,
                                                     row * SQUARE_SIZE + SQUARE_SIZE - 15))

                    # Rank numbers (1-8)
                    if col == 0:
                        rank_text = self.small_font.render(str(8 - row), True, text_color)
                        self.screen.blit(rank_text, (col * SQUARE_SIZE + 5, row * SQUARE_SIZE + 5))

    def draw_highlights(self, board: Board):
        # Highlight selected square
        if self.selected_square:
            x, y = self.square_pos_to_pixel(self.selected_square)
            highlight_surface = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)
            highlight_surface.fill(HIGHLIGHT_YELLOW)
            self.screen.blit(highlight_surface, (x, y))

        # Highlight legal moves
        if self.selected_square:
            piece = board.get_piece(self.selected_square)
            if piece and piece.color == board.active_color:
                for move_pos in piece.legal_moves.keys():
                    x, y = self.square_pos_to_pixel(move_pos)
                    highlight_surface = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)
                    highlight_surface.fill(HIGHLIGHT_GREEN)
                    self.screen.blit(highlight_surface, (x, y))

        # Highlight right-clicked squares
        for square_pos in self.right_click_squares:
            x, y = self.square_pos_to_pixel(square_pos)
            highlight_surface = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)
            highlight_surface.fill(HIGHLIGHT_RED)
            self.screen.blit(highlight_surface, (x, y))

        # Highlight king in check
        for color in [Color.WHITE, Color.BLACK]:
            if board.players[color].is_in_check:
                king = board.get_king(color)
                if king:
                    x, y = self.square_pos_to_pixel(king.position)
                    highlight_surface = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)
                    highlight_surface.fill((255, 0, 0, 100))  # Semi-transparent red
                    self.screen.blit(highlight_surface, (x, y))

    def draw_pieces(self, board: Board):
        for row in range(8):
            for col in range(8):
                piece = board.grid[row][col]
                if piece and piece != self.dragging_piece:
                    x, y = self.square_pos_to_pixel(SquarePosition(row, col))
                    symbol = piece.get_symbol()
                    text_surface = self.font.render(symbol, True, BLACK)
                    text_rect = text_surface.get_rect(center=(x + SQUARE_SIZE // 2, y + SQUARE_SIZE // 2))
                    self.screen.blit(text_surface, text_rect)

        # Draw dragging piece
        if self.dragging_piece:
            mouse_pos = pygame.mouse.get_pos()
            symbol = self.dragging_piece.get_symbol()
            text_surface = self.font.render(symbol, True, BLACK)
            text_rect = text_surface.get_rect(center=(mouse_pos[0] + self.drag_offset[0],
                                                      mouse_pos[1] + self.drag_offset[1]))
            self.screen.blit(text_surface, text_rect)

    def draw_arrows(self):
        for start_pos, end_pos in self.arrows:
            start_pixel = self.square_pos_to_pixel(start_pos)
            end_pixel = self.square_pos_to_pixel(end_pos)

            start_center = (start_pixel[0] + SQUARE_SIZE // 2, start_pixel[1] + SQUARE_SIZE // 2)
            end_center = (end_pixel[0] + SQUARE_SIZE // 2, end_pixel[1] + SQUARE_SIZE // 2)

            # Check if it's a knight move for special L-shaped arrow
            dr = abs(end_pos.row - start_pos.row)
            dc = abs(end_pos.col - start_pos.col)

            if (dr == 2 and dc == 1) or (dr == 1 and dc == 2):
                # Draw L-shaped arrow for knight moves
                self.draw_knight_arrow(start_center, end_center, start_pos, end_pos)
            else:
                # Draw straight arrow
                self.draw_straight_arrow(start_center, end_center)

    def draw_straight_arrow(self, start, end):
        if start == end:
            return

        # Calculate arrow properties
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        length = math.sqrt(dx * dx + dy * dy)

        if length == 0:
            return

        # Normalize direction
        unit_x = dx / length
        unit_y = dy / length

        # Arrow dimensions
        arrow_length = min(length * 0.8, length - 20)
        arrow_head_size = 15

        # Calculate end point (shortened)
        arrow_end_x = start[0] + unit_x * arrow_length
        arrow_end_y = start[1] + unit_y * arrow_length

        # Draw arrow body
        pygame.draw.line(self.screen, ARROW_ORANGE, start, (arrow_end_x, arrow_end_y), 5)

        # Draw arrow head
        perp_x = -unit_y
        perp_y = unit_x

        head_point1 = (arrow_end_x - unit_x * arrow_head_size + perp_x * arrow_head_size / 2,
                       arrow_end_y - unit_y * arrow_head_size + perp_y * arrow_head_size / 2)
        head_point2 = (arrow_end_x - unit_x * arrow_head_size - perp_x * arrow_head_size / 2,
                       arrow_end_y - unit_y * arrow_head_size - perp_y * arrow_head_size / 2)

        pygame.draw.polygon(self.screen, ARROW_ORANGE,
                            [(arrow_end_x, arrow_end_y), head_point1, head_point2])

    def draw_knight_arrow(self, start, end, start_pos, end_pos):
        # Calculate L-shaped path for knight moves
        dr = end_pos.row - start_pos.row
        dc = end_pos.col - start_pos.col

        # Determine the corner point for L-shape
        if abs(dr) == 2:  # Vertical then horizontal
            corner_row = start_pos.row + dr
            corner_col = start_pos.col
        else:  # Horizontal then vertical
            corner_row = start_pos.row
            corner_col = start_pos.col + dc

        corner_pixel = self.square_pos_to_pixel(SquarePosition(corner_row, corner_col))
        corner_center = (corner_pixel[0] + SQUARE_SIZE // 2, corner_pixel[1] + SQUARE_SIZE // 2)

        # Draw two segments
        pygame.draw.line(self.screen, ARROW_ORANGE, start, corner_center, 4)
        pygame.draw.line(self.screen, ARROW_ORANGE, corner_center, end, 4)

        # Draw arrow head at the end
        dx = end[0] - corner_center[0]
        dy = end[1] - corner_center[1]
        length = math.sqrt(dx * dx + dy * dy)

        if length > 0:
            unit_x = dx / length
            unit_y = dy / length
            arrow_head_size = 12

            perp_x = -unit_y
            perp_y = unit_x

            head_point1 = (end[0] - unit_x * arrow_head_size + perp_x * arrow_head_size / 2,
                           end[1] - unit_y * arrow_head_size + perp_y * arrow_head_size / 2)
            head_point2 = (end[0] - unit_x * arrow_head_size - perp_x * arrow_head_size / 2,
                           end[1] - unit_y * arrow_head_size - perp_y * arrow_head_size / 2)

            pygame.draw.polygon(self.screen, ARROW_ORANGE, [end, head_point1, head_point2])

    def draw_side_panel(self, board: Board):
        # Fill side panel background
        panel_rect = pygame.Rect(BOARD_SIZE, 0, SCREEN_WIDTH - BOARD_SIZE, SCREEN_HEIGHT)
        pygame.draw.rect(self.screen, GRAY, panel_rect)

        # Draw title
        title_text = self.font.render("Chess Engine", True, BLACK)
        self.screen.blit(title_text, (BOARD_SIZE + 10, 10))

        # Draw buttons
        pygame.draw.rect(self.screen, WHITE, UNDO_BTN_RECT)
        pygame.draw.rect(self.screen, BLACK, UNDO_BTN_RECT, 2)
        undo_text = self.small_font.render("UNDO (<-)", True, BLACK)
        undo_text_rect = undo_text.get_rect(center=UNDO_BTN_RECT.center)
        self.screen.blit(undo_text, undo_text_rect)

        pygame.draw.rect(self.screen, WHITE, NOTATION_BTN_RECT)
        pygame.draw.rect(self.screen, BLACK, NOTATION_BTN_RECT, 2)
        notation_text = self.small_font.render("Toggle A-H/1-8", True, BLACK)
        notation_text_rect = notation_text.get_rect(center=NOTATION_BTN_RECT.center)
        self.screen.blit(notation_text, notation_text_rect)

        # Draw game status
        y_offset = 160
        status_text = f"Turn: {'White' if board.active_color == Color.WHITE else 'Black'}"
        status_surface = self.small_font.render(status_text, True, BLACK)
        self.screen.blit(status_surface, (BOARD_SIZE + 10, y_offset))

        # Draw check/checkmate status
        y_offset += 30
        for color in [Color.WHITE, Color.BLACK]:
            player = board.players[color]
            color_name = "White" if color == Color.WHITE else "Black"

            if player.is_in_checkmate:
                check_text = f"{color_name}: CHECKMATE!"
                color_surface = self.small_font.render(check_text, True, (255, 0, 0))
            elif player.is_in_check:
                check_text = f"{color_name}: In Check"
                color_surface = self.small_font.render(check_text, True, (255, 100, 0))
            else:
                check_text = f"{color_name}: OK"
                color_surface = self.small_font.render(check_text, True, (0, 100, 0))

            self.screen.blit(color_surface, (BOARD_SIZE + 10, y_offset))
            y_offset += 25

        # Draw clocks
        y_offset += 20
        for color in [Color.WHITE, Color.BLACK]:
            player = board.players[color]
            color_name = "White" if color == Color.WHITE else "Black"

            minutes = int(player.time_remaining // 60)
            seconds = int(player.time_remaining % 60)
            time_text = f"{color_name}: {minutes:02d}:{seconds:02d}"

            time_color = BLACK
            if player.time_remaining < 60:  # Less than 1 minute
                time_color = (255, 0, 0)
            elif player.time_remaining < 300:  # Less than 5 minutes
                time_color = (255, 165, 0)

            time_surface = self.small_font.render(time_text, True, time_color)
            self.screen.blit(time_surface, (BOARD_SIZE + 10, y_offset))
            y_offset += 25

        # Draw move count
        y_offset += 20
        move_count_text = f"Moves: {len(board.move_log)}"
        move_surface = self.small_font.render(move_count_text, True, BLACK)
        self.screen.blit(move_surface, (BOARD_SIZE + 10, y_offset))

    def draw_promotion_menu(self, color: Color):
        # Draw semi-transparent overlay
        overlay = pygame.Surface((BOARD_SIZE, BOARD_SIZE), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 128))
        self.screen.blit(overlay, (0, 0))

        # Draw promotion options
        menu_width = 4 * SQUARE_SIZE
        menu_height = SQUARE_SIZE
        menu_x = (BOARD_SIZE - menu_width) // 2
        menu_y = (BOARD_SIZE - menu_height) // 2

        menu_rect = pygame.Rect(menu_x, menu_y, menu_width, menu_height)
        pygame.draw.rect(self.screen, WHITE, menu_rect)
        pygame.draw.rect(self.screen, BLACK, menu_rect, 3)

        # Draw piece options
        pieces = [PieceType.QUEEN, PieceType.ROOK, PieceType.BISHOP, PieceType.KNIGHT]
        symbols = {
            PieceType.QUEEN: ('♕', '♛'), PieceType.ROOK: ('♖', '♜'),
            PieceType.BISHOP: ('♗', '♝'), PieceType.KNIGHT: ('♘', '♞')
        }

        for i, piece_type in enumerate(pieces):
            piece_rect = pygame.Rect(menu_x + i * SQUARE_SIZE, menu_y, SQUARE_SIZE, SQUARE_SIZE)

            # Highlight on hover
            mouse_pos = pygame.mouse.get_pos()
            if piece_rect.collidepoint(mouse_pos):
                pygame.draw.rect(self.screen, HIGHLIGHT_YELLOW, piece_rect)

            # Draw piece symbol
            symbol = symbols[piece_type][0 if color == Color.WHITE else 1]
            text_surface = self.font.render(symbol, True, BLACK)
            text_rect = text_surface.get_rect(center=piece_rect.center)
            self.screen.blit(text_surface, text_rect)

        return [(menu_x + i * SQUARE_SIZE, menu_y, SQUARE_SIZE, SQUARE_SIZE)
                for i in range(4)]

    def draw_game_over_screen(self, board: Board):
        # Determine winner
        winner = None
        if board.players[Color.WHITE].is_in_checkmate:
            winner = "Black"
        elif board.players[Color.BLACK].is_in_checkmate:
            winner = "White"
        elif board.players[Color.WHITE].lost:
            winner = "Black (Time)"
        elif board.players[Color.BLACK].lost:
            winner = "White (Time)"

        if winner:
            # Draw semi-transparent overlay
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            self.screen.blit(overlay, (0, 0))

            # Draw game over message
            game_over_text = self.font.render("GAME OVER", True, WHITE)
            winner_text = self.font.render(f"{winner} Wins!", True, WHITE)

            game_over_rect = game_over_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 50))
            winner_rect = winner_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))

            self.screen.blit(game_over_text, game_over_rect)
            self.screen.blit(winner_text, winner_rect)

            # Draw restart instruction
            restart_text = self.small_font.render("Press R to restart", True, WHITE)
            restart_rect = restart_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 50))
            self.screen.blit(restart_text, restart_rect)

            return True
        return False


def main():
    # Initialize display
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT),
                                     pygame.SCALED | pygame.RESIZABLE)
    pygame.display.set_caption("Custom Chess Engine")
    clock = pygame.time.Clock()

    # Initialize game objects
    board = Board()
    ui = ChessUI(screen)

    # Game state variables
    running = True
    fullscreen = False
    right_click_start = None
    last_time = time.time()

    while running:
        # Calculate delta time
        current_time = time.time()
        dt = current_time - last_time
        last_time = current_time

        # Update clocks
        if not (board.players[Color.WHITE].is_in_checkmate or
                board.players[Color.BLACK].is_in_checkmate or
                board.players[Color.WHITE].lost or
                board.players[Color.BLACK].lost):
            board.players[board.active_color].time_remaining -= dt
            if board.players[board.active_color].time_remaining <= 0:
                board.players[board.active_color].lost = True

        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                # Toggle fullscreen
                if event.key == pygame.K_F11:
                    fullscreen = not fullscreen
                    if fullscreen:
                        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN | pygame.SCALED)
                    else:
                        screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT),
                                                         pygame.SCALED | pygame.RESIZABLE)
                    ui.screen = screen

                # Undo move
                elif event.key == pygame.K_LEFT:
                    board.undo_move()
                    ui.selected_square = None
                    ui.arrows.clear()

                # Generate FEN
                elif event.key == pygame.K_s:
                    print(f"FEN: {board.generate_fen()}")

                # Restart game
                elif event.key == pygame.K_r:
                    if (board.players[Color.WHITE].is_in_checkmate or
                            board.players[Color.BLACK].is_in_checkmate or
                            board.players[Color.WHITE].lost or
                            board.players[Color.BLACK].lost):
                        board = Board()
                        ui.selected_square = None
                        ui.right_click_squares.clear()
                        ui.arrows.clear()
                        ui.promotion_pending = None

            elif event.type == pygame.MOUSEBUTTONDOWN:
                # Check if game is over
                if (board.players[Color.WHITE].is_in_checkmate or
                        board.players[Color.BLACK].is_in_checkmate or
                        board.players[Color.WHITE].lost or
                        board.players[Color.BLACK].lost):
                    continue

                # Handle promotion menu
                if ui.promotion_pending:
                    promotion_rects = ui.draw_promotion_menu(ui.promotion_pending['color'])
                    pieces = [PieceType.QUEEN, PieceType.ROOK, PieceType.BISHOP, PieceType.KNIGHT]

                    for i, rect in enumerate(promotion_rects):
                        if pygame.Rect(rect).collidepoint(event.pos):
                            move = ui.promotion_pending['move']
                            move.promotion_piece = pieces[i]
                            board.execute_move(move)
                            ui.promotion_pending = None
                            ui.selected_square = None
                            break
                    continue

                # Handle UI buttons
                if UNDO_BTN_RECT.collidepoint(event.pos):
                    board.undo_move()
                    ui.selected_square = None
                    ui.arrows.clear()
                    continue

                if NOTATION_BTN_RECT.collidepoint(event.pos):
                    ui.show_notation = not ui.show_notation
                    continue

                # Handle board clicks
                square_pos = ui.pixel_to_square_pos(event.pos)
                if not square_pos:
                    continue

                if event.button == 1:  # Left click
                    piece = board.get_piece(square_pos)

                    # If clicking on own piece, select it
                    if piece and piece.color == board.active_color:
                        ui.selected_square = square_pos
                        ui.dragging_piece = piece
                        mouse_x, mouse_y = pygame.mouse.get_pos()
                        piece_x, piece_y = ui.square_pos_to_pixel(square_pos)
                        ui.drag_offset = (piece_x + SQUARE_SIZE // 2 - mouse_x,
                                          piece_y + SQUARE_SIZE // 2 - mouse_y)

                    # If clicking on highlighted square, try to move
                    elif ui.selected_square:
                        selected_piece = board.get_piece(ui.selected_square)
                        if selected_piece and square_pos in selected_piece.legal_moves:
                            move = selected_piece.legal_moves[square_pos]

                            # Handle promotion
                            if move.move_type == MoveType.PROMOTION:
                                ui.promotion_pending = {
                                    'move': move,
                                    'color': selected_piece.color
                                }
                            else:
                                board.execute_move(move)
                                ui.selected_square = None
                        else:
                            ui.selected_square = None

                elif event.button == 3:  # Right click
                    # Toggle square highlight
                    if square_pos in ui.right_click_squares:
                        ui.right_click_squares.remove(square_pos)
                    else:
                        ui.right_click_squares.add(square_pos)

                    right_click_start = square_pos

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:  # Left click release
                    if ui.dragging_piece:
                        drop_square = ui.pixel_to_square_pos(event.pos)
                        if drop_square and ui.selected_square:
                            selected_piece = board.get_piece(ui.selected_square)
                            if selected_piece and drop_square in selected_piece.legal_moves:
                                move = selected_piece.legal_moves[drop_square]

                                # Handle promotion
                                if move.move_type == MoveType.PROMOTION:
                                    ui.promotion_pending = {
                                        'move': move,
                                        'color': selected_piece.color
                                    }
                                else:
                                    board.execute_move(move)
                                    ui.selected_square = None
                            else:
                                ui.selected_square = None

                        ui.dragging_piece = None

                elif event.button == 3:  # Right click release
                    if right_click_start:
                        end_square = ui.pixel_to_square_pos(event.pos)
                        if end_square and end_square != right_click_start:
                            # Add or remove arrow
                            arrow = (right_click_start, end_square)
                            if arrow in ui.arrows:
                                ui.arrows.remove(arrow)
                            else:
                                ui.arrows.append(arrow)
                        right_click_start = None

        # Clear screen
        screen.fill(WHITE)

        # Draw game
        ui.draw_board()
        ui.draw_highlights(board)
        ui.draw_pieces(board)
        ui.draw_arrows()
        ui.draw_side_panel(board)

        # Draw promotion menu if needed
        if ui.promotion_pending:
            ui.draw_promotion_menu(ui.promotion_pending['color'])

        # Draw game over screen
        ui.draw_game_over_screen(board)

        # Update display
        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()


if __name__ == "__main__":
    main()

