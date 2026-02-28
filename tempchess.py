import pygame
import sys
import math
import os
from enum import Enum


# ==========================================
# 1. CONFIGURATION & CONSTANTS
# ==========================================
class ChessColor(Enum):
    WHITE = "WHITE"
    BLACK = "BLACK"


class ChessPieceType(Enum):
    PAWN = "P"
    ROOK = "R"
    KNIGHT = "N"
    BISHOP = "B"
    QUEEN = "Q"
    KING = "K"


class MoveType(Enum):
    NORMAL = 1
    EN_PASSANT = 2
    CASTLE = 3
    PROMOTION = 4


OTHER_COLOR = {ChessColor.WHITE: ChessColor.BLACK, ChessColor.BLACK: ChessColor.WHITE}

CONFIG = {
    "BOARD_SIZE": 8,
    "SQUARE_SIZE": 80,
    "MENU_WIDTH": 200,
    "FPS": 60,
    "STARTING_TIME_MS": 5 * 60 * 1000,
    "STARTING_FEN": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
    "COLORS": {
        "LIGHT": (240, 217, 181),
        "DARK": (181, 136, 99),
        "PICKING": (0, 255, 255),
        "LEGAL": (67, 67, 67),
        "HIGHLIGHT": (200, 50, 50)
    }
}

WINDOW_SIZE = CONFIG["BOARD_SIZE"] * CONFIG["SQUARE_SIZE"]
SCREEN_WIDTH = WINDOW_SIZE + CONFIG["MENU_WIDTH"]
SCREEN_HEIGHT = WINDOW_SIZE


# ==========================================
# 2. FOUNDATION (Math & Files)
# ==========================================
def notation_to_row_col(pos: str):
    return 8 - int(pos[1]), ord(pos[0].lower()) - ord('a')


def row_col_to_notation(row: int, col: int):
    return chr(ord('a') + col) + str(8 - row)


def pixel_to_squarepos(mouse_pos):
    col, row = mouse_pos[0] // CONFIG["SQUARE_SIZE"], mouse_pos[1] // CONFIG["SQUARE_SIZE"]
    if 0 <= col < 8 and 0 <= row < 8:
        return SquarePosition(row, col)
    return None


class SquarePosition:
    def __init__(self, row: int, col: int):
        self.row = row
        self.col = col

    def to_notation(self):
        return row_col_to_notation(self.row, self.col)

    def __eq__(self, other):
        return isinstance(other, SquarePosition) and self.row == other.row and self.col == other.col

    def __hash__(self):
        return hash((self.row, self.col))

    def __repr__(self):
        return self.to_notation()


class Move:
    def __init__(self, from_pos, to_pos, move_type=MoveType.NORMAL, victim_pos=None):
        self.from_pos = from_pos
        self.to_pos = to_pos
        self.move_type = move_type
        self.victim_pos = victim_pos if victim_pos else to_pos
        self.promotion_choice = None


class MoveRecord:
    def __init__(self, move, moved_piece, piece_had_moved, victim_piece, clocks, old_ep, old_castling, san):
        self.move = move
        self.moved_piece = moved_piece
        self.piece_had_moved = piece_had_moved
        self.victim_piece = victim_piece
        self.current_times = {ChessColor.WHITE: clocks[ChessColor.WHITE].remaining_ms,
                              ChessColor.BLACK: clocks[ChessColor.BLACK].remaining_ms}
        self.old_en_passant = old_ep
        self.old_castling_rights = old_castling
        self.algebraic_notation = san


class ChessClock:
    def __init__(self, color, starting_time_ms):
        self.color = color
        self.starting_time_ms = starting_time_ms
        self.remaining_ms = starting_time_ms
        self.is_running = False
        self.last_tick = 0

    def start(self):
        self.is_running = True
        self.last_tick = pygame.time.get_ticks()

    def stop(self):
        if self.is_running:
            self.tick()
            self.is_running = False

    def switch(self):
        self.stop()
        self.is_running = not self.is_running
        if self.is_running:
            self.last_tick = pygame.time.get_ticks()

    def tick(self):
        if self.is_running:
            now = pygame.time.get_ticks()
            delta = now - self.last_tick
            self.remaining_ms = max(0, self.remaining_ms - delta)
            self.last_tick = now

    def reset(self):
        self.remaining_ms = self.starting_time_ms
        self.is_running = False

    def standard_notation(self):
        secs = self.remaining_ms // 1000
        return f"{int(secs // 60):02d}:{int(secs % 60):02d}"

    def __bool__(self):
        return self.remaining_ms > 0


# ==========================================
# 3. THE ARMY (Pieces)
# ==========================================
class ChessPiece:
    def __init__(self, color, position, piece_type):
        self.color = color
        self.position = position
        self.type = piece_type
        self.legal_moves = {}
        self.controlled_squares = set()
        self.has_moved = False

    def die(self):
        self.position = None

    def filter_safe_moves(self, board):
        safe_moves = {}
        for pos, move in self.legal_moves.items():
            if board.is_move_safe(self, move):
                safe_moves[pos] = move
        self.legal_moves = safe_moves


def add_sliding_moves(piece, board, directions):
    for dr, dc in directions:
        r, c = piece.position.row + dr, piece.position.col + dc
        while 0 <= r < 8 and 0 <= c < 8:
            target = board.grid[r][c]
            pos = SquarePosition(r, c)
            piece.controlled_squares.add(pos)
            if not target or (target.type == ChessPieceType.KING and target.color != piece.color):
                piece.legal_moves[pos] = Move(piece.position, pos)
            else:
                if target.color != piece.color:
                    piece.legal_moves[pos] = Move(piece.position, pos)
                break
            r += dr
            c += dc


class Pawn(ChessPiece):
    def __init__(self, color, pos):
        super().__init__(color, pos, ChessPieceType.PAWN)

    def update_all_legal_moves(self, board):
        self.legal_moves.clear();
        self.controlled_squares.clear()
        if not self.position: return
        r, c = self.position.row, self.position.col
        dir_y = -1 if self.color == ChessColor.WHITE else 1
        start_r = 6 if self.color == ChessColor.WHITE else 1
        promo = MoveType.PROMOTION if (r + dir_y) % 7 == 0 else MoveType.NORMAL

        if 0 <= r + dir_y < 8 and not board.grid[r + dir_y][c]:
            pos = SquarePosition(r + dir_y, c)
            self.legal_moves[pos] = Move(self.position, pos, move_type=promo)
            if r == start_r and not board.grid[r + 2 * dir_y][c]:
                pos2 = SquarePosition(r + 2 * dir_y, c)
                self.legal_moves[pos2] = Move(self.position, pos2)

        for dc in (-1, 1):
            if 0 <= r + dir_y < 8 and 0 <= c + dc < 8:
                pos = SquarePosition(r + dir_y, c + dc)
                self.controlled_squares.add(pos)
                target = board.grid[pos.row][pos.col]
                if target and target.color != self.color:
                    self.legal_moves[pos] = Move(self.position, pos, move_type=promo)
                if board.en_passant == pos:
                    self.legal_moves[pos] = Move(self.position, pos, MoveType.EN_PASSANT, SquarePosition(r, c + dc))
        self.filter_safe_moves(board)


class Knight(ChessPiece):
    def __init__(self, color, pos):
        super().__init__(color, pos, ChessPieceType.KNIGHT)

    def update_all_legal_moves(self, board):
        self.legal_moves.clear();
        self.controlled_squares.clear()
        if not self.position: return
        for dr, dc in [(2, 1), (2, -1), (1, 2), (1, -2), (-1, 2), (-1, -2), (-2, 1), (-2, -1)]:
            r, c = self.position.row + dr, self.position.col + dc
            if 0 <= r < 8 and 0 <= c < 8:
                pos = SquarePosition(r, c)
                self.controlled_squares.add(pos)
                if not board.grid[r][c] or board.grid[r][c].color != self.color:
                    self.legal_moves[pos] = Move(self.position, pos)
        self.filter_safe_moves(board)


class Rook(ChessPiece):
    def __init__(self, color, pos): super().__init__(color, pos, ChessPieceType.ROOK)

    def update_all_legal_moves(self, board):
        self.legal_moves.clear();
        self.controlled_squares.clear()
        if not self.position: return
        add_sliding_moves(self, board, [(-1, 0), (1, 0), (0, -1), (0, 1)])
        self.filter_safe_moves(board)


class Bishop(ChessPiece):
    def __init__(self, color, pos): super().__init__(color, pos, ChessPieceType.BISHOP)

    def update_all_legal_moves(self, board):
        self.legal_moves.clear();
        self.controlled_squares.clear()
        if not self.position: return
        add_sliding_moves(self, board, [(-1, -1), (-1, 1), (1, -1), (1, 1)])
        self.filter_safe_moves(board)


class Queen(ChessPiece):
    def __init__(self, color, pos): super().__init__(color, pos, ChessPieceType.QUEEN)

    def update_all_legal_moves(self, board):
        self.legal_moves.clear();
        self.controlled_squares.clear()
        if not self.position: return
        add_sliding_moves(self, board, [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)])
        self.filter_safe_moves(board)


class King(ChessPiece):
    def __init__(self, color, pos):
        super().__init__(color, pos, ChessPieceType.KING)

    def update_all_legal_moves(self, board):
        self.legal_moves.clear();
        self.controlled_squares.clear()
        if not self.position: return
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]:
            r, c = self.position.row + dr, self.position.col + dc
            if 0 <= r < 8 and 0 <= c < 8:
                pos = SquarePosition(r, c)
                self.controlled_squares.add(pos)
                if not board.is_square_attacked(pos, self.color):
                    target = board.grid[r][c]
                    if not target or target.color != self.color:
                        self.legal_moves[pos] = Move(self.position, pos)

        # Castling Logic
        if not self.has_moved and not board.is_square_attacked(self.position, self.color):
            for c_col, r_col, dir_x in [(2, 0, -1), (6, 7, 1)]:
                rook = board.grid[self.position.row][r_col]
                if rook and rook.type == ChessPieceType.ROOK and not rook.has_moved:
                    clear = True
                    for step in range(1, abs(r_col - self.position.col)):
                        test_pos = SquarePosition(self.position.row, self.position.col + (step * dir_x))
                        if board.grid[test_pos.row][test_pos.col] or board.is_square_attacked(test_pos, self.color):
                            clear = False;
                            break
                    if clear:
                        self.legal_moves[rook.position] = Move(self.position, rook.position, MoveType.CASTLE)


def create_piece(char, pos):
    color = ChessColor.WHITE if char.isupper() else ChessColor.BLACK
    c = char.upper()
    if c == 'P': return Pawn(color, pos)
    if c == 'R': return Rook(color, pos)
    if c == 'N': return Knight(color, pos)
    if c == 'B': return Bishop(color, pos)
    if c == 'Q': return Queen(color, pos)
    if c == 'K': return King(color, pos)
    return None


# ==========================================
# 4. THE MASTERMIND (Board & Rules)
# ==========================================
class Board:
    def __init__(self, clocks):
        self.clocks = clocks
        self.grid = [[None for _ in range(8)] for _ in range(8)]
        self.active_color = ChessColor.WHITE
        self.castling_rights = ""
        self.en_passant = None
        self.move_log = []
        self.winner = None

    def load_fen(self, fen):
        self.grid = [[None for _ in range(8)] for _ in range(8)]
        self.move_log.clear()
        self.winner = None
        for clock in self.clocks.values(): clock.reset()

        parts = fen.strip().split()
        rows = parts[0].split('/')
        for r, row in enumerate(rows):
            c = 0
            for ch in row:
                if ch.isdigit():
                    c += int(ch)
                else:
                    self.grid[r][c] = create_piece(ch, SquarePosition(r, c))
                    c += 1
        self.active_color = ChessColor.WHITE if parts[1] == 'w' else ChessColor.BLACK
        self.castling_rights = parts[2]
        self.en_passant = None if parts[3] == '-' else SquarePosition(*notation_to_row_col(parts[3]))
        self.update_all()
        self.clocks[self.active_color].start()

    def get_all_pieces(self):
        return [p for row in self.grid for p in row if p]

    def is_square_attacked(self, pos, my_color):
        enemy_color = OTHER_COLOR[my_color]
        for p in self.get_all_pieces():
            if p.color == enemy_color and pos in p.controlled_squares:
                return True
        return False

    def is_move_safe(self, piece, move):
        og_pos, target_pos, vic_pos = piece.position, move.to_pos, move.victim_pos
        target_bkp = self.grid[target_pos.row][target_pos.col]
        vic_bkp = self.grid[vic_pos.row][vic_pos.col] if vic_pos else None

        self.grid[og_pos.row][og_pos.col] = None
        if vic_pos: self.grid[vic_pos.row][vic_pos.col] = None
        self.grid[target_pos.row][target_pos.col] = piece
        piece.position = target_pos

        king = next((p for p in self.get_all_pieces() if p.type == ChessPieceType.KING and p.color == piece.color),
                    None)
        is_safe = True if not king else not self.is_square_attacked(king.position, piece.color)

        piece.position = og_pos
        self.grid[og_pos.row][og_pos.col] = piece
        if vic_pos: self.grid[vic_pos.row][vic_pos.col] = vic_bkp
        if target_pos != vic_pos: self.grid[target_pos.row][target_pos.col] = target_bkp
        return is_safe

    def execute_move(self, move):
        piece = self.grid[move.from_pos.row][move.from_pos.col]
        victim = self.grid[move.victim_pos.row][move.victim_pos.col] if move.victim_pos else None

        # Diary
        self.move_log.append(
            MoveRecord(move, piece, piece.has_moved, victim, self.clocks, self.en_passant, self.castling_rights, "SAN"))

        if victim and victim.color != piece.color:
            victim.die()
            self.grid[move.victim_pos.row][move.victim_pos.col] = None

        if move.move_type == MoveType.CASTLE:
            rook = self.grid[move.to_pos.row][move.to_pos.col]
            dir_x = 1 if move.to_pos.col > move.from_pos.col else -1
            k_new = move.from_pos.col + (2 * dir_x)
            r_new = k_new - dir_x

            self.grid[move.from_pos.row][move.from_pos.col] = None
            self.grid[move.to_pos.row][move.to_pos.col] = None
            self.grid[move.from_pos.row][k_new] = piece
            self.grid[move.from_pos.row][r_new] = rook
            piece.position = SquarePosition(move.from_pos.row, k_new)
            rook.position = SquarePosition(move.from_pos.row, r_new)
            rook.has_moved = True
        else:
            self.grid[move.to_pos.row][move.to_pos.col] = piece
            self.grid[move.from_pos.row][move.from_pos.col] = None
            piece.position = move.to_pos

        if move.move_type == MoveType.PROMOTION:
            piece.die()
            char = move.promotion_choice.value if piece.color == ChessColor.BLACK else move.promotion_choice.value.upper()
            self.grid[move.to_pos.row][move.to_pos.col] = create_piece(char, move.to_pos)

        piece.has_moved = True
        self.en_passant = SquarePosition((move.to_pos.row + move.from_pos.row) // 2,
                                         move.to_pos.col) if piece.type == ChessPieceType.PAWN and abs(
            move.to_pos.row - move.from_pos.row) == 2 else None

        self.switch_turn()
        self.update_all()

    def undo_move(self):
        if not self.move_log: return
        rec = self.move_log.pop()
        move, piece, victim = rec.move, rec.moved_piece, rec.victim_piece

        if move.move_type == MoveType.CASTLE:
            dir_x = 1 if move.to_pos.col > move.from_pos.col else -1
            k_new, r_new = move.from_pos.col + (2 * dir_x), move.from_pos.col + dir_x
            rook = self.grid[move.from_pos.row][r_new]

            self.grid[move.from_pos.row][k_new] = None
            self.grid[move.from_pos.row][r_new] = None
            self.grid[move.from_pos.row][move.from_pos.col] = piece
            self.grid[move.to_pos.row][move.to_pos.col] = rook
            piece.position, rook.position = move.from_pos, move.to_pos
            rook.has_moved = False
        else:
            self.grid[move.to_pos.row][move.to_pos.col] = None
            self.grid[move.from_pos.row][move.from_pos.col] = piece
            piece.position = move.from_pos
            if victim:
                self.grid[move.victim_pos.row][move.victim_pos.col] = victim
                victim.position = move.victim_pos

        piece.has_moved = rec.piece_had_moved
        self.en_passant = rec.old_en_passant
        self.castling_rights = rec.old_castling_rights
        for color, time in rec.current_times.items():
            self.clocks[color].remaining_ms = time

        self.switch_turn()
        self.update_all()

    def switch_turn(self):
        self.clocks[self.active_color].switch()
        self.active_color = OTHER_COLOR[self.active_color]
        self.clocks[self.active_color].switch()

    def update_all(self):
        pieces = self.get_all_pieces()
        # Update controlled squares (raw vision)
        for p in pieces:
            p.controlled_squares.clear()
            p.update_all_legal_moves(self)

        # Check for Checkmate/Stalemate
        has_moves = False
        for p in pieces:
            if p.color == self.active_color and p.legal_moves:
                has_moves = True;
                break

        if not has_moves:
            king = next((p for p in pieces if p.type == ChessPieceType.KING and p.color == self.active_color), None)
            if king and self.is_square_attacked(king.position, self.active_color):
                self.winner = OTHER_COLOR[self.active_color]
            else:
                self.winner = "STALEMATE"


# ==========================================
# 5. UI MANAGER & FILE IO
# ==========================================
class UIManager:
    def __init__(self):
        self.buttons = {
            "Undo": pygame.Rect(WINDOW_SIZE + 25, (SCREEN_HEIGHT // 2) - 85, 150, 50),
            "Notation": pygame.Rect(WINDOW_SIZE + 25, (SCREEN_HEIGHT // 2) - 15, 150, 40),
            "Save": pygame.Rect(WINDOW_SIZE + 25, (SCREEN_HEIGHT // 2) + 45, 150, 40),
            "B_Flag": pygame.Rect(WINDOW_SIZE + 140, 30, 40, 40),
            "W_Flag": pygame.Rect(WINDOW_SIZE + 140, SCREEN_HEIGHT - 70, 40, 40)
        }
        self.show_notation = False

    def save_game(self, move_log):
        os.makedirs("saved_games", exist_ok=True)
        idx_file = "saved_games/curr_num_of_game.txt"
        num = 1
        if os.path.exists(idx_file):
            with open(idx_file, "r") as f:
                content = f.read().strip()
                if content.isdigit(): num = int(content)

        with open(f"saved_games/game_{num}.txt", "w") as f:
            f.write(" ".join([rec.algebraic_notation for rec in move_log]))  # Simple PGN
        with open(idx_file, "w") as f:
            f.write(str(num + 1))
        print(f"Game saved as game_{num}.txt")


# ==========================================
# 6. RENDERER (The Decor)
# ==========================================
class Renderer:
    def __init__(self, screen):
        self.screen = screen
        self.font_large = pygame.font.SysFont("Arial", 32, bold=True)
        self.font_small = pygame.font.SysFont("Arial", 20, bold=True)
        self.cache = {}

    def draw_board(self, show_notation):
        for r in range(8):
            for c in range(8):
                color = CONFIG["COLORS"]["LIGHT"] if (r + c) % 2 == 0 else CONFIG["COLORS"]["DARK"]
                rect = (
                c * CONFIG["SQUARE_SIZE"], r * CONFIG["SQUARE_SIZE"], CONFIG["SQUARE_SIZE"], CONFIG["SQUARE_SIZE"])
                pygame.draw.rect(self.screen, color, rect)
                if show_notation:
                    txt = self.font_small.render(row_col_to_notation(r, c), True, (100, 100, 100))
                    self.screen.blit(txt, (c * CONFIG["SQUARE_SIZE"] + 4, (r + 1) * CONFIG["SQUARE_SIZE"] - 22))

    def draw_ui(self, ui, clocks):
        pygame.draw.rect(self.screen, (30, 30, 30), (WINDOW_SIZE, 0, CONFIG["MENU_WIDTH"], SCREEN_HEIGHT))
        pygame.draw.line(self.screen, (100, 100, 100), (WINDOW_SIZE, 0), (WINDOW_SIZE, SCREEN_HEIGHT), 2)
        m_pos = pygame.mouse.get_pos()

        # Clocks
        pygame.draw.rect(self.screen, (20, 20, 20), (WINDOW_SIZE + 20, 20, 110, 60))
        b_txt = self.font_large.render(clocks[ChessColor.BLACK].standard_notation(), True, (255, 255, 255))
        self.screen.blit(b_txt, b_txt.get_rect(center=(WINDOW_SIZE + 75, 50)))

        pygame.draw.rect(self.screen, (220, 220, 220), (WINDOW_SIZE + 20, SCREEN_HEIGHT - 80, 110, 60))
        w_txt = self.font_large.render(clocks[ChessColor.WHITE].standard_notation(), True, (0, 0, 0))
        self.screen.blit(w_txt, w_txt.get_rect(center=(WINDOW_SIZE + 75, SCREEN_HEIGHT - 50)))

        # Buttons
        for name, rect in ui.buttons.items():
            color = (150, 150, 150) if rect.collidepoint(m_pos) else (100, 100, 100)
            if "Flag" in name: color = (200, 80, 80) if rect.collidepoint(m_pos) else (150, 40, 40)
            pygame.draw.rect(self.screen, color, rect)
            pygame.draw.rect(self.screen, (200, 200, 200), rect, 2)

            lbl = "F" if "Flag" in name else ("Notate: ON" if name == "Notation" and ui.show_notation else name)
            txt = self.font_small.render(lbl, True, (255, 255, 255))
            self.screen.blit(txt, txt.get_rect(center=rect.center))

    def get_piece_img(self, piece):
        key = (piece.color, piece.type)
        if key not in self.cache:
            try:
                img = pygame.image.load(
                    f"assets/sliced_pieces/{piece.color.value}_{piece.type.name}.png").convert_alpha()
                self.cache[key] = pygame.transform.smoothscale(img, (
                int(CONFIG["SQUARE_SIZE"] * .85), int(CONFIG["SQUARE_SIZE"] * .85)))
            except:
                img = pygame.Surface((CONFIG["SQUARE_SIZE"], CONFIG["SQUARE_SIZE"]))
                img.fill((255, 0, 0) if piece.color == ChessColor.WHITE else (0, 0, 255))
                self.cache[key] = img
        return self.cache[key]

    def draw_pieces(self, board, dragged_piece=None):
        for p in board.get_all_pieces():
            if p != dragged_piece:
                img = self.get_piece_img(p)
                rect = img.get_rect(center=(p.position.col * CONFIG["SQUARE_SIZE"] + CONFIG["SQUARE_SIZE"] // 2,
                                            p.position.row * CONFIG["SQUARE_SIZE"] + CONFIG["SQUARE_SIZE"] // 2))
                self.screen.blit(img, rect)

    def draw_highlight(self, pos, color, alpha=125, thick=0):
        s = pygame.Surface((CONFIG["SQUARE_SIZE"], CONFIG["SQUARE_SIZE"]), pygame.SRCALPHA)
        pygame.draw.rect(s, (*color, alpha), s.get_rect(), width=thick)
        self.screen.blit(s, (pos.col * CONFIG["SQUARE_SIZE"], pos.row * CONFIG["SQUARE_SIZE"]))

    def draw_game_over(self, winner):
        s = pygame.Surface((WINDOW_SIZE, WINDOW_SIZE));
        s.set_alpha(180);
        s.fill((0, 0, 0))
        self.screen.blit(s, (0, 0))
        rect = pygame.Rect(0, 0, 300, 160);
        rect.center = (WINDOW_SIZE // 2, WINDOW_SIZE // 2)
        pygame.draw.rect(self.screen, (40, 40, 40), rect)
        pygame.draw.rect(self.screen, (220, 220, 220), rect, 4)
        txt = self.font_large.render(f"{winner.value} WINS!" if type(winner) != str else "STALEMATE", True,
                                     (255, 255, 255))
        self.screen.blit(txt, txt.get_rect(center=(WINDOW_SIZE // 2, WINDOW_SIZE // 2 - 20)))
        btn = pygame.Rect(0, 0, 140, 50);
        btn.center = (WINDOW_SIZE // 2, WINDOW_SIZE // 2 + 45)
        pygame.draw.rect(self.screen, (100, 200, 100), btn)
        btn_txt = self.font_small.render("Again?", True, (0, 0, 0))
        self.screen.blit(btn_txt, btn_txt.get_rect(center=btn.center))
        return btn


# ==========================================
# 7. THE MANAGER (Game Loop)
# ==========================================
def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Professional Chess Engine")
    pygame_clock = pygame.time.Clock()

    clocks = {ChessColor.WHITE: ChessClock(ChessColor.WHITE, CONFIG["STARTING_TIME_MS"]),
              ChessColor.BLACK: ChessClock(ChessColor.BLACK, CONFIG["STARTING_TIME_MS"])}

    board = Board(clocks)
    board.load_fen(CONFIG["STARTING_FEN"])
    ui = UIManager()
    renderer = Renderer(screen)

    picking_piece = None
    promo_pending = None
    right_click_start = None
    drawn_arrows = set()
    highlighted = set()
    game_over_btn = None

    running = True
    while running:
        # Check Time Out
        if not clocks[board.active_color] and not board.winner:
            board.winner = OTHER_COLOR[board.active_color]

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left Click
                    if board.winner:
                        if game_over_btn and game_over_btn.collidepoint(event.pos):
                            board.load_fen(CONFIG["STARTING_FEN"])
                            drawn_arrows.clear();
                            highlighted.clear()
                        continue

                    # UI Handling
                    for name, rect in ui.buttons.items():
                        if rect.collidepoint(event.pos):
                            if name == "Undo":
                                board.undo_move(); picking_piece = None; drawn_arrows.clear()
                            elif name == "Notation":
                                ui.show_notation = not ui.show_notation
                            elif name == "Save":
                                ui.save_game(board.move_log)
                            elif name == "W_Flag":
                                board.winner = ChessColor.BLACK
                            elif name == "B_Flag":
                                board.winner = ChessColor.WHITE
                            continue

                    # Board Handling
                    clicked = pixel_to_squarepos(event.pos)
                    if not clicked: continue
                    piece = board.grid[clicked.row][clicked.col]

                    drawn_arrows.clear();
                    highlighted.clear()

                    if piece and piece.color == board.active_color:
                        picking_piece = piece
                    elif picking_piece and clicked in picking_piece.legal_moves:
                        move = picking_piece.legal_moves[clicked]
                        if move.move_type == MoveType.PROMOTION:
                            move.promotion_choice = ChessPieceType.QUEEN  # Auto Queen for speed
                            board.execute_move(move)
                        else:
                            board.execute_move(move)
                        picking_piece = None

                elif event.button == 3:  # Right click
                    right_click_start = pixel_to_squarepos(event.pos)

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1 and picking_piece:
                    drop_pos = pixel_to_squarepos(event.pos)
                    if drop_pos and drop_pos != picking_piece.position and drop_pos in picking_piece.legal_moves:
                        move = picking_piece.legal_moves[drop_pos]
                        if move.move_type == MoveType.PROMOTION:
                            move.promotion_choice = ChessPieceType.QUEEN
                        board.execute_move(move)
                    picking_piece = None

                elif event.button == 3 and right_click_start:
                    end = pixel_to_squarepos(event.pos)
                    if end:
                        if right_click_start != end:
                            arr = (right_click_start, end)
                            if arr in drawn_arrows:
                                drawn_arrows.remove(arr)
                            else:
                                drawn_arrows.add(arr)
                        else:
                            if right_click_start in highlighted:
                                highlighted.remove(right_click_start)
                            else:
                                highlighted.add(right_click_start)
                    right_click_start = None

        # Logic Update
        clocks[board.active_color].tick()

        # Draw Update
        screen.fill((0, 0, 0))
        renderer.draw_board(ui.show_notation)
        renderer.draw_ui(ui, clocks)
        renderer.draw_pieces(board, picking_piece if pygame.mouse.get_pressed()[0] else None)

        if picking_piece:
            renderer.draw_highlight(picking_piece.position, CONFIG["COLORS"]["PICKING"])
            for move in picking_piece.legal_moves:
                renderer.draw_highlight(move, CONFIG["COLORS"]["LEGAL"], thick=5)

        for sq in highlighted: renderer.draw_highlight(sq, CONFIG["COLORS"]["HIGHLIGHT"], 100)
        for s, e in drawn_arrows: pygame.draw.line(screen, (255, 170, 0), get_center(s), get_center(e), 5)  # Arrow Stub

        if picking_piece and pygame.mouse.get_pressed()[0]:
            img = renderer.get_piece_img(picking_piece)
            screen.blit(img, img.get_rect(center=pygame.mouse.get_pos()))

        if board.winner:
            game_over_btn = renderer.draw_game_over(board.winner)

        pygame.display.flip()
        pygame_clock.tick(CONFIG["FPS"])


def get_center(pos):
    return pos.col * CONFIG["SQUARE_SIZE"] + CONFIG["SQUARE_SIZE"] // 2, pos.row * CONFIG["SQUARE_SIZE"] + CONFIG[
        "SQUARE_SIZE"] // 2


if __name__ == "__main__":
    main()