import pygame
import sys
import math
import os
from enum import Enum


#<editor-fold desc="FILES">
GAME_INDEX_FILE = "saved_games/curr_num_of_game.txt"
DIRECTORY_OF_SAVED_GAMES = "saved_games"
#</editor-fold>

# <editor-fold desc="CONFIG">
BOARD_SIZE = 8
SQUARE_SIZE = 80
WINDOW_SIZE = BOARD_SIZE * SQUARE_SIZE

MENU_WIDTH = 200
SCREEN_WIDTH = WINDOW_SIZE + MENU_WIDTH
SCREEN_HEIGHT = WINDOW_SIZE
FPS = 60

#delta time - second divided by FPS
DT = 1/FPS
STARTING_TIME = 5 * 60 #5 mins

#starting pos = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1" (I want to change it to test castling)
STARTING_POSITION = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

LIGHT = (240, 217, 181)
DARK = (181, 136, 99)

PICKING_PIECE_HIGHLIGHT_COLOR = (0, 255, 255)
LEGAL_MOVES_HIGHLIGHT_COLOR = (67, 67, 67)

RIGHT_CLICK_HIGHLIGHT_SQUARE_COLOR = (210, 43, 43)



#<editor-fold desc="SETTINGS MENU CONFIG">
# To add a new button, literally just type its name in this list!
SETTINGS_OPTIONS = [
    ("General Settings", (100, 100, 100), (130, 130, 130)), # Grey
    ("Saved Games", (40, 160, 160), (60, 200, 200)),   # Aqua
    ("Audio Settings", (180, 60, 60), (220, 80, 80)),  # Red
    ("Video Settings", (60, 160, 60), (80, 200, 80))]   #Green
SETTINGS_RECTS = []

# Automatically generate a perfectly stacked hitbox for every word in the list
for i in range(len(SETTINGS_OPTIONS)):
    # Start at Y=220, and space them out by 80 pixels each
    y_position = 220 + (i * 80)
    rect = pygame.Rect((SCREEN_WIDTH // 2) - 150, y_position, 300, 60)
    SETTINGS_RECTS.append(rect)

# The Return Button stays anchored to the bottom of the screen
RETURN_BTN_RECT = pygame.Rect((SCREEN_WIDTH // 2) - 150, SCREEN_HEIGHT - 100, 300, 60)

#<editor-fold desc="GENERAL SETTINGS">

#<editor-fold desc="GENERAL SETTINGS UI">
GENERAL_SETTINGS_OPTIONS = ["Auto Save"]
GENERAL_SETTINGS_RECTS = []

for i in range(len(GENERAL_SETTINGS_OPTIONS)):
    y_position = 250 + (i * 80)
    rect = pygame.Rect((SCREEN_WIDTH // 2) - 150, y_position, 300, 60)
    GENERAL_SETTINGS_RECTS.append(rect)
#</editor-fold>

#<editor-fold desc="SETTINGS VARIABLES">
AUTO_SAVE = True

#</editor-fold>
#</editor-fold>

#</editor-fold>

#<editor-fold desc="MAIN MENU CONFIG">

# --- HOME PAGE RECTS ---
# Centered mathematically based on SCREEN_WIDTH and SCREEN_HEIGHT
START_BTN_RECT = pygame.Rect((SCREEN_WIDTH // 2) - 125, (SCREEN_HEIGHT // 2) - 40, 250, 80)
QUIT_BTN_RECT = pygame.Rect((SCREEN_WIDTH // 2) - 125, (SCREEN_HEIGHT // 2) + 60, 250, 80)
SETTINGS_BTN_RECT = pygame.Rect(SCREEN_WIDTH - 60, 20, 40, 40)



#</editor-fold>

#<editor-fold desc="REPLAY GAME UI">
# --- REPLAY SCREEN HITBOXES ---
REPLAY_NEXT_BTN = pygame.Rect(WINDOW_SIZE + 25, 100, 150, 60)
REPLAY_PREV_BTN = pygame.Rect(WINDOW_SIZE + 25, 180, 150, 60)
REPLAY_RESET_BTN = pygame.Rect(WINDOW_SIZE + 25, 260, 150, 40)
REPLAY_NOTATION_BTN = pygame.Rect(WINDOW_SIZE + 25, 320, 150, 40)
REPLAY_MENU_BTN = pygame.Rect(WINDOW_SIZE + 25, SCREEN_HEIGHT - 100, 150, 60)

#</editor-fold>

#<editor-fold desc="MAIN GAME UI">
# --- PRE-CALCULATED UI HITBOXES ---
# 6 buttons, 40px height, 10px gaps. Start Y is exactly centered.
PAUSE_BTN_RECT = pygame.Rect(WINDOW_SIZE + 25, 175, 150, 40)
UNDO_BTN_RECT = pygame.Rect(WINDOW_SIZE + 25, PAUSE_BTN_RECT.bottom + 10, 150, 40)
RESET_BTN_RECT = pygame.Rect(WINDOW_SIZE + 25, UNDO_BTN_RECT.bottom + 10, 150, 40)
MENU_BTN_RECT = pygame.Rect(WINDOW_SIZE + 25, RESET_BTN_RECT.bottom + 10, 150, 40)
NOTATION_BTN_RECT = pygame.Rect(WINDOW_SIZE + 25, MENU_BTN_RECT.bottom + 10, 150, 40)
SAVE_BTN_RECT = pygame.Rect(WINDOW_SIZE + 25, NOTATION_BTN_RECT.bottom + 10, 150, 40)

# Clocks are now 110px wide. These 40x40 buttons sit perfectly to the right of them.
B_FLAG_BTN_RECT = pygame.Rect(WINDOW_SIZE + 140, 30, 40, 40)
W_FLAG_BTN_RECT = pygame.Rect(WINDOW_SIZE + 140, SCREEN_HEIGHT - 70, 40, 40)

# Anchored directly to the clocks/flags
B_DRAW_BTN_RECT = pygame.Rect(WINDOW_SIZE + 140, 80, 40, 40)
W_DRAW_BTN_RECT = pygame.Rect(WINDOW_SIZE + 140, SCREEN_HEIGHT - 120, 40, 40)

# --- CLOCK RECTS ---
B_CLOCK_RECT = pygame.Rect(WINDOW_SIZE + 20, 20, 110, 60)
W_CLOCK_RECT = pygame.Rect(WINDOW_SIZE + 20, SCREEN_HEIGHT - 80, 110, 60)
#</editor-fold>


#</editor-fold>

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




def generate_pgn(diary: list) -> str:
    """Translates a list of MoveRecords into a basic PGN string by reading the Diary."""
    pgn_moves = []

    for i, record in enumerate(diary):
        # 1. Just read the label we already perfectly calculated!
        san = record.algebraic_notation

        # 2. Format the move numbers
        if i % 2 == 0:
            turn_number = (i // 2) + 1
            pgn_moves.append(f"{turn_number}. {san}")
        else:
            pgn_moves.append(san)

    return " ".join(pgn_moves)

def create_new_chess_file(board):
    number_of_game = int(get_file_content(GAME_INDEX_FILE))
    pgn = generate_pgn(board.move_log)
    create_file(f"{DIRECTORY_OF_SAVED_GAMES}/game_{number_of_game}.txt", pgn)
    change_file(GAME_INDEX_FILE, str(number_of_game + 1))


def pgn_to_move_list(pgn_string: str) -> list[str]:
    """Strips the numbers (1. 2.) and returns a pure list of SAN strings."""
    tokens = pgn_string.split()
    moves = []
    for token in tokens:
        # If it doesn't have a dot in it, it's a move, not a turn number!
        if "." not in token:
            moves.append(token)
    return moves


def get_move_from_san(board, san_string: str):
    """The Reverse SAN Trick: Finds the move object that produces this exact string."""
    # Strip the Red Pen marks (+ and #) because the move generator doesn't use them
    clean_san = san_string.replace("+", "").replace("#", "")

    # Check every legal move for the current player
    for piece in board.get_all_pieces():
        if piece.color == board.active_color:
            for target_pos, move in piece.legal_moves.items():
                victim = board.get_piece_at(move.victim_pos) if move.victim_pos else None
                # Generate the SAN for this hypothetical move
                test_san = board.get_algebraic_notation(move, piece, victim)

                # If it matches our diary, this is the one!
                if test_san == clean_san:
                    return move
    return None
#</editor-fold>

#<editor-fold desc="FILE HANDLING">

def create_file(file_path: str, initial_text: str = ""):
    """Creates a new text file and writes the initial text. Overwrites if it exists."""
    # "w" means Write (shred the old one, make a new one)
    with open(file_path, "w") as file:
        file.write(initial_text)

def change_file(file_path: str, new_text: str):
    """Opens a text file and adds new text to the bottom."""
    # "a" means Append (add to the bottom)
    with open(file_path, "w") as file:
        # We add \n at the end so the next thing we write goes on a new line
        file.write(new_text + "\n")
def get_file_content(file_path: str) -> str:
    """Reads the entire content of a file and returns it as a string."""
    try:
        # "r" means Read only (safe mode)
        with open(file_path, "r") as file:
            content = file.read()
            return content
    except FileNotFoundError:
        print(f"ERROR: The file at {file_path} was not found.")
        return ""


def get_saved_games_data():
    """Reads the saved_games folder and returns all games sorted by number."""
    games = []
    if not os.path.exists(DIRECTORY_OF_SAVED_GAMES):
        return games

    for filename in os.listdir(DIRECTORY_OF_SAVED_GAMES):
        if filename.endswith(".txt") and filename.startswith("game_"):
            filepath = os.path.join(DIRECTORY_OF_SAVED_GAMES, filename)
            pgn = get_file_content(filepath).strip()

            # Find the last move (the last word in the file)
            tokens = pgn.split()
            last_move = "None"
            if tokens:
                last_move = tokens[-1]

            games.append({"filename": filename, "pgn": pgn, "last_move": last_move})

    # Sort them by game number
    games.sort(key=lambda x: int(x["filename"].split("_")[1].split(".")[0]) if "_" in x["filename"] else 0)
    return games


def is_pgn_valid(pgn_string: str) -> bool:
    """Uses the global BOARD to test if the text is a real game of chess."""
    global BOARD
    if not pgn_string.strip():
        return False

    # 1. Reset the main board to the start
    BOARD.load_fen(STARTING_POSITION)

    # 2. Translate the text into raw moves
    san_list = pgn_to_move_list(pgn_string)
    if len(san_list) == 0:
        return False

    # 3. Force the board to play the game
    for san in san_list:
        move = get_move_from_san(BOARD, san)
        if move is None:
            # The Reverse SAN engine couldn't find a legal move for this string!
            print(f"Validation failed on move: {san}")
            BOARD.load_fen(STARTING_POSITION)  # Clean up the mess before failing!
            return False
        BOARD.execute_move(move)

    # If we made it through, it's valid! Clean up and return True.
    BOARD.load_fen(STARTING_POSITION)
    return True

def save_custom_pgn(pgn_string: str):
    """Formats the raw string perfectly and saves it as a new file."""
    number_of_game = int(get_file_content(GAME_INDEX_FILE))
    filepath = f"{DIRECTORY_OF_SAVED_GAMES}/game_{number_of_game}.txt"

    # Clean it up so it formats perfectly like our normal auto-saves
    san_list = pgn_to_move_list(pgn_string)
    formatted_pgn = []

    for i, san in enumerate(san_list):
        if i % 2 == 0:
            turn_number = (i // 2) + 1
            formatted_pgn.append(f"{turn_number}. {san}")
        else:
            formatted_pgn.append(san)

    final_string = " ".join(formatted_pgn)

    # Save it and tick the counter up!
    create_file(filepath, final_string)
    change_file(GAME_INDEX_FILE, str(number_of_game + 1))

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
        return self.row, self.col

    def add_translation(self, translation: tuple):
        return SquarePosition(row=self.row + translation[0], col=self.col + translation[1])

    def __repr__(self):
        return self.to_notation()

    def __eq__(self, other):
        return isinstance(other, SquarePosition) and self.row == other.row and self.col == other.col

    def __hash__(self):
        return hash((self.row, self.col))


# </editor-fold>

# <editor-fold desc="ENUMS & MOVE TYPES">
class ChessColor(Enum):
    WHITE = "WHITE"
    BLACK = "BLACK"




OTHER_COLOR = {ChessColor.WHITE: ChessColor.BLACK, ChessColor.BLACK: ChessColor.WHITE}


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


class Move:
    """The Instruction Manual for the Board"""

    def __init__(self, from_pos: SquarePosition, to_pos: SquarePosition, move_type=MoveType.NORMAL, victim_pos=None):
        self.from_pos = from_pos
        self.to_pos = to_pos
        self.move_type = move_type
        # If it's a normal capture, the victim is where we land. If En Passant, it's defined separately.
        self.victim_pos = victim_pos if victim_pos else to_pos
        self.promotion_choice = None

    def get_as_tuple(self):
        return self.move_type, self.from_pos, self.to_pos

    def __repr__(self):
        return f"{self.move_type.name} {self.from_pos}->{self.to_pos}"



# </editor-fold>

# <editor-fold desc="ChessClock">
class ChessClock:
    def __init__(self,color,starting_time):
        self.color = color
        self.starting_time = starting_time
        self.remaining = starting_time
        self.ms = 0 #will be from 0-1
        self.is_running = False
        self.previous_time = starting_time

    def tick(self):
        if not self.is_running: return
        self.ms += DT
        if self.ms >= 1:
            self.remaining -= 1
            self.ms = 0
    def start(self):
        self.is_running = True
    def stop(self):
        self.is_running = False
    def switch(self):
        self.is_running = not self.is_running
        self.previous_time = self.remaining

    def change_starting_time(self,new_starting_time):
        self.starting_time = new_starting_time
        self.remaining = new_starting_time
    def reset(self):
        self.remaining = self.starting_time
        self.is_running = False
    def restore_time(self, seconds):
        self.remaining = seconds
        self.ms = 0
    def standard_notation(self) -> str:
        return f"{int(self.remaining/60):02d}:{self.remaining%60:02d}"

    def __bool__(self):
        return self.remaining != 0
    def __str__(self) -> str:
        return str(self.remaining)
#</editor-fold>

# <editor-fold desc="PIECE_HELPER">
def squares_between(a: SquarePosition, b: SquarePosition) -> set[SquarePosition]:
    dr = b.row - a.row
    dc = b.col - a.col

    if not (dr == 0 or dc == 0 or abs(dr) == abs(dc)):
        return set()

    step_r = 0 if dr == 0 else (1 if dr > 0 else -1)
    step_c = 0 if dc == 0 else (1 if dc > 0 else -1)

    r = a.row + step_r
    c = a.col + step_c

    between = set()
    while (r, c) != (b.row, b.col):
        between.add(SquarePosition(row=r, col=c))
        r += step_r
        c += step_c
    return between


def can_castle(board, king, rook):

    if not king or not rook:
        return False
    if not (king.type == ChessPieceType.KING and rook.type == ChessPieceType.ROOK):
        return False
    if king.has_moved or rook.has_moved or king.color != rook.color:
        return False

    between_squares = squares_between(king.position, rook.position)
    for pos in between_squares:
        if board.grid[pos.row][pos.col] is not None:
            return False

    player = PLAYERS[king.color]
    enemy_player = PLAYERS[OTHER_COLOR[king.color]]

    if player.is_in_check:
        return False

    direction = 1 if rook.position.col > king.position.col else -1
    for i in range(1, 3):
        test_pos = SquarePosition(row=king.position.row, col=king.position.col + (i * direction))
        if enemy_player.is_controlling_square(test_pos):
            return False

    return True


def add_sliding_moves(piece, board, directions):
    if not piece:
        return

    start_r = piece.position.row
    start_c = piece.position.col

    for dr, dc in directions:
        r = start_r + dr
        c = start_c + dc
        while 0 <= r < 8 and 0 <= c < 8:
            target = board.grid[r][c]
            pos = SquarePosition(row=r, col=c)
            piece.controlled_squares.add(pos)

            if not target or (target.is_king() and target.color != piece.color):
                piece.legal_moves[pos] = Move(piece.position, pos)
            else:
                if target.color != piece.color:
                    piece.legal_moves[pos] = Move(piece.position, pos)
                break
            r += dr
            c += dc


# </editor-fold>

# <editor-fold desc="PIECES">
class ChessPiece:
    def __init__(self, color: ChessColor, position: SquarePosition, piece_type: ChessPieceType):
        self.color = color
        self.position: SquarePosition | None = position
        self.type = piece_type
        # Changed to Dictionary for instant lookup of Move objects
        self.legal_moves: dict[SquarePosition, Move] = {}
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

    def is_controlling_square(self, position: SquarePosition):
        return position in self.controlled_squares

    def filter_safe_moves(self, board):
        """The Bouncer. Throws out any move that gets the King killed."""
        safe_moves = {}
        for pos, move in self.legal_moves.items():
            # We ask the Board (the table) to use its robotic arm on this specific move
            if board.is_move_safe(self, move):
                safe_moves[pos] = move

        # Replace the old list with the strictly safe list
        self.legal_moves = safe_moves

    def is_king(self):
        return self.type == ChessPieceType.KING

    def __repr__(self):
        return f"{self.color.value} {self.type.name} @ {self.position}"

    def __bool__(self):
        return self.position is not None


class Pawn(ChessPiece):
    def __init__(self, color, position: SquarePosition):
        super().__init__(color, position, ChessPieceType.PAWN)

    def is_captureable(self, target):
        return target is not None and super().is_captureable(target)

    def update_all_legal_moves(self, board):
        self.legal_moves.clear()
        self.controlled_squares.clear()

        if self.position is None or board is None:
            return

        row = self.position.row
        col = self.position.col
        direction = -1 if self.color == ChessColor.WHITE else 1
        start_row = 6 if self.color == ChessColor.WHITE else 1

        move_type = MoveType.NORMAL
        # PROMOTION CHECK
        if (row + direction) % 7 == 0:  # if its 0 or 7 (first or last row)
            move_type = MoveType.PROMOTION

        # 1 step forward
        one_row = row + direction
        if 0 <= one_row < 8:
            if board.grid[one_row][col] is None:
                pos = SquarePosition(row=one_row, col=col)
                self.legal_moves[pos] = Move(self.position, pos, move_type=move_type)

                # 2 steps forward from start
                if row == start_row:
                    two_row = row + 2 * direction
                    if 0 <= two_row < 8 and board.grid[two_row][col] is None:
                        pos2 = SquarePosition(row=two_row, col=col)
                        self.legal_moves[pos2] = Move(self.position, pos2)

        # diagonal captures & En Passant
        for dc in (-1, 1):
            cap_row = row + direction
            cap_col = col + dc
            if 0 <= cap_row < 8 and 0 <= cap_col < 8:
                pos = SquarePosition(row=cap_row, col=cap_col)
                self.controlled_squares.add(pos)

                target = board.grid[cap_row][cap_col]
                if self.is_captureable(target):
                    self.legal_moves[pos] = Move(self.position, pos, move_type=move_type)

                # EN PASSANT CHECK
                if board.en_passant is not None and board.en_passant == pos:
                    victim_pos = SquarePosition(row=row, col=cap_col)  # The victim is next to us!
                    self.legal_moves[pos] = Move(
                        self.position,
                        pos,
                        MoveType.EN_PASSANT,
                        victim_pos=victim_pos
                    )

        self.filter_safe_moves(board)


class Knight(ChessPiece):
    def __init__(self, color, position: SquarePosition):
        super().__init__(color, position, ChessPieceType.KNIGHT)

    def update_all_legal_moves(self, board):
        self.legal_moves.clear()
        self.controlled_squares.clear()
        if self.position is None or board is None: return

        directions = [(2, 1), (2, -1), (1, 2), (1, -2), (-1, 2), (-1, -2), (-2, 1), (-2, -1)]
        start_r, start_c = self.position.row, self.position.col

        for dr, dc in directions:
            r, c = start_r + dr, start_c + dc
            if 0 <= r < 8 and 0 <= c < 8:
                pos = SquarePosition(row=r, col=c)
                target = board.grid[r][c]
                self.controlled_squares.add(pos)
                if not target or target.color != self.color:
                    self.legal_moves[pos] = Move(self.position, pos)

        self.filter_safe_moves(board)


class Rook(ChessPiece):
    def __init__(self, color, position: SquarePosition):
        super().__init__(color, position, ChessPieceType.ROOK)

    def update_all_legal_moves(self, board):
        self.legal_moves.clear()
        self.controlled_squares.clear()
        if self.position is None or board is None: return
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        add_sliding_moves(self, board, directions)
        self.filter_safe_moves(board)


class Bishop(ChessPiece):
    def __init__(self, color, position: SquarePosition):
        super().__init__(color, position, ChessPieceType.BISHOP)

    def update_all_legal_moves(self, board):
        self.legal_moves.clear()
        self.controlled_squares.clear()
        if self.position is None or board is None: return
        directions = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
        add_sliding_moves(self, board, directions)
        self.filter_safe_moves(board)


class Queen(ChessPiece):
    def __init__(self, color, position: SquarePosition):
        super().__init__(color, position, ChessPieceType.QUEEN)

    def update_all_legal_moves(self, board):
        self.legal_moves.clear()
        self.controlled_squares.clear()
        if self.position is None or board is None: return
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]
        add_sliding_moves(self, board, directions)
        self.filter_safe_moves(board)


class King(ChessPiece):
    def __init__(self, color, position: SquarePosition):
        super().__init__(color, position, ChessPieceType.KING)

    def update_all_legal_moves(self, board):
        self.legal_moves.clear()
        self.controlled_squares.clear()
        if self.position is None: return

        directions = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]
        enemy_player = PLAYERS.get(OTHER_COLOR.get(self.color))

        for dr, dc in directions:
            r = self.position.row + dr
            c = self.position.col + dc
            if 0 <= r < BOARD_SIZE and 0 <= c < BOARD_SIZE:
                pos = SquarePosition(row=r, col=c)
                self.controlled_squares.add(pos)

                if enemy_player.is_controlling_square(pos):
                    continue

                target = board.grid[r][c]
                if target is None:
                    self.legal_moves[pos] = Move(self.position, pos)
                elif target.color != self.color:
                    if not self.is_piece_protected(pos, enemy_player):
                        self.legal_moves[pos] = Move(self.position, pos)

        # --- CASTLING MOVES ---
        # Look at all our own pieces. If it's a Rook, see if we can castle with it.
        for friend in self.player.pieces:
            if friend.type == ChessPieceType.ROOK:
                if can_castle(board, self, friend):
                    # The target square is the Rook's square, so the UI knows we clicked it!
                    self.legal_moves[friend.position] = Move(
                        from_pos=self.position,
                        to_pos=friend.position,
                        move_type=MoveType.CASTLE
                    )

    def is_piece_protected(self, pos, enemy_player):
        return enemy_player.is_controlling_square(pos)

class MoveRecord:
    """A single page in the Diary, holding a photograph of the past."""
    def __init__(self, move: Move, moved_piece, piece_had_moved: bool, victim_piece,clocks, old_en_passant, old_castling_rights,algebraic_notation):
        self.move = move

        self.moved_piece = moved_piece
        self.piece_had_moved = piece_had_moved
        self.victim_piece = victim_piece

        self.current_times = {ChessColor.WHITE: clocks[ChessColor.WHITE].previous_time, ChessColor.BLACK: clocks[ChessColor.BLACK].previous_time}

        self.old_en_passant = old_en_passant
        self.old_castling_rights = old_castling_rights

        self.algebraic_notation = algebraic_notation

# </editor-fold>

# <editor-fold desc="FEN helpers">
def create_piece_with_specified_color(color: ChessColor, char: str, position: SquarePosition):
    c = char.upper()  # to match the enums
    if c == 'P': return Pawn(color, position)
    if c == 'R': return Rook(color, position)
    if c == 'N': return Knight(color, position)
    if c == 'B': return Bishop(color, position)
    if c == 'Q': return Queen(color, position)
    if c == 'K': return King(color, position)
    return None


def create_piece_from_fen(char: str, position: SquarePosition):
    color = ChessColor.WHITE if char.isupper() else ChessColor.BLACK
    c = char.upper()  # to match the enums
    if c == 'P': return Pawn(color, position)
    if c == 'R': return Rook(color, position)
    if c == 'N': return Knight(color, position)
    if c == 'B': return Bishop(color, position)
    if c == 'Q': return Queen(color, position)
    if c == 'K': return King(color, position)
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
        self.lost = False
        self.checking_pieces = []
        self.king = None

    def refresh_pieces(self):
        self.pieces = [p for p in self.board.get_all_pieces() if p.color == self.color]
        self.king = next((p for p in self.pieces if p.is_king()), None)
        if self.king is None:
            self.lost = True

    def get_legal_moves(self) -> dict:
        legal_moves = {}
        for piece in self.pieces:
            legal_moves[piece] = piece.legal_moves
        return legal_moves

    def has_legal_moves(self):
        has_moves = False
        for piece in self.pieces:
            has_moves = has_moves or piece.legal_moves
        return has_moves

    def update_controlled_squares(self):
        self.controlled_squares.clear()
        for piece in self.pieces:
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
        self.is_draw = False
        self.draw_offered_by = None  # Remembers who extended their hand
        self.is_stalemate = False

        # --- THE DIARY ---
        self.move_log: list[MoveRecord] = []

        if fen: self.load_fen(fen)

    def clear(self):
        self.grid = [[None for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
        self.move_log.clear()

    def load_fen(self, fen: str):
        self.clear()

        parts = fen.strip().split()
        if len(parts) != 6: raise ValueError("Invalid FEN")

        piece_data, active, castling, en_passant_str, halfmove, fullmove = parts
        rows = piece_data.split('/')
        for row_index, row in enumerate(rows):
            col = 0
            for ch in row:
                if ch.isdigit():
                    col += int(ch)
                else:
                    pos = SquarePosition(row=row_index, col=col)
                    self.grid[row_index][col] = create_piece_from_fen(ch, pos)
                    col += 1

        self.active_color = ChessColor.WHITE if active == 'w' else ChessColor.BLACK
        self.castling_rights = castling
        self.en_passant = None if en_passant_str == '-' else SquarePosition(notation=en_passant_str)
        self.halfmove_clock = int(halfmove)
        self.fullmove_number = int(fullmove)

        self.update_game_state()

    def generate_fen(self) -> str:
        """Scans the board and generates a perfect FEN string on demand."""
        fen_rows = []

        # 1. Scan the grid row by row
        for row in range(8):
            empty_count = 0
            row_str = ""
            for col in range(8):
                piece = self.grid[row][col]
                if piece is None:
                    empty_count += 1
                else:
                    # If we have empty spaces saved up, write the number first
                    if empty_count > 0:
                        row_str += str(empty_count)
                        empty_count = 0

                    # Get the piece letter
                    char = piece.type.value
                    if piece.color == ChessColor.WHITE:
                        char = char.upper()
                    else:
                        char = char.lower()

                    row_str += char

            # If the row ends with empty spaces, write the final number
            if empty_count > 0:
                row_str += str(empty_count)

            fen_rows.append(row_str)

        # Join the rows with slashes
        board_part = "/".join(fen_rows)

        # 2. Who's turn is it?
        active_part = 'w' if self.active_color == ChessColor.WHITE else 'b'

        # 3. Castling Rights (If empty, it must be "-")
        castling_part = self.castling_rights if self.castling_rights else "-"

        # 4. En Passant Target
        ep_part = self.en_passant.to_notation() if self.en_passant else "-"

        # 5. Clocks
        halfmove = str(self.halfmove_clock)
        fullmove = str(self.fullmove_number)

        # Smash it all together
        return f"{board_part} {active_part} {castling_part} {ep_part} {halfmove} {fullmove}"

    def get_algebraic_notation(self, move, piece, victim):
        """Calculates the exact SAN string for a move before it happens."""
        # 1. Castling
        if move.move_type == MoveType.CASTLE:
            if move.to_pos.col > move.from_pos.col:
                return "O-O"
            else:
                return "O-O-O"

        san = ""
        is_pawn = piece.type == ChessPieceType.PAWN

        # 2. Piece Letter & DISAMBIGUATION
        if not is_pawn:
            san += piece.type.value

            # THE DISAMBIGUATION TEST: Scan the whole board for clones
            clones = []
            for r in range(BOARD_SIZE):
                for c in range(BOARD_SIZE):
                    other = self.grid[r][c]
                    # Is it the exact same type, same color, but NOT the piece we are moving?
                    if other is not None and other != piece and other.type == piece.type and other.color == piece.color:
                        # Can this clone also hit the exact same destination square?
                        if move.to_pos in other.legal_moves:
                            clones.append(other)

            if clones:
                # We have a conflict! We must disambiguate.
                # Do any of the clones share the exact same column (File) as our piece?
                same_col = any(c.position.col == piece.position.col for c in clones)

                if not same_col:
                    # They are in different columns. Use the letter (e.g., Nbd7)
                    san += move.from_pos.to_notation()[0]
                else:
                    # They are in the SAME column. Use the number (e.g., R1a3)
                    san += move.from_pos.to_notation()[1]

                    # 3. Captures
        if victim is not None or move.move_type == MoveType.EN_PASSANT:
            if is_pawn:
                san += move.from_pos.to_notation()[0]  # Pawns always show their starting file on a capture
            san += "x"

        # 4. Destination
        san += move.to_pos.to_notation()

        # 5. Promotion
        if move.move_type == MoveType.PROMOTION and move.promotion_choice is not None:
            san += f"={move.promotion_choice.value}"
        return san

    def get_piece_at(self, position: SquarePosition) -> ChessPiece | None:
        return self.grid[position.row][position.col]

    def get_all_pieces(self):
        return [p for row in self.grid for p in row if p is not None]

    def is_move_safe(self, piece, move: Move) -> bool:
        """The Time Machine. Makes a fake move, checks the King, and hits Undo."""
        original_pos = piece.position
        target_pos = move.to_pos
        victim_pos = move.victim_pos

        # 1. TAKE THE POLAROID
        target_piece_backup = self.grid[target_pos.row][target_pos.col]
        victim_piece_backup = self.grid[victim_pos.row][victim_pos.col] if victim_pos else None

        # 2. FAST FORWARD (Simulate)
        self.grid[original_pos.row][original_pos.col] = None
        if victim_pos:
            self.grid[victim_pos.row][victim_pos.col] = None

        self.grid[target_pos.row][target_pos.col] = piece
        piece.position = target_pos

        # 3. LOOK AT THE KING
        king = piece.player.king
        # Use the King's current position (if the King is the one moving, this reflects the new square)
        king_current_square = king.position

        is_safe = not self.is_square_attacked(king_current_square, piece.color)

        # 4. REWIND TIME (Undo)
        piece.position = original_pos
        self.grid[original_pos.row][original_pos.col] = piece

        # Crucial: Restore victims and targets correctly without overwriting
        if victim_pos:
            self.grid[victim_pos.row][victim_pos.col] = victim_piece_backup
        if target_pos != victim_pos:
            self.grid[target_pos.row][target_pos.col] = target_piece_backup

        return is_safe

    def update_game_state(self):
        if not PLAYERS: return

        for p in PLAYERS.values(): p.refresh_pieces()

        all_pieces = self.get_all_pieces()
        for p in all_pieces:
            if not p.is_king(): p.update_all_legal_moves(self)

        for p in PLAYERS.values(): p.update_controlled_squares()

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

            # Reprocess enemy moves to filter them against the check
            for p in enemy_player.pieces:
                p.update_all_legal_moves(self)

            if not enemy_player.has_legal_moves():
                enemy_player.lost = True
            else:
                enemy_player.is_in_check = False

        else:

            # They are NOT in check.
            enemy_player.is_in_check = False
            enemy_player.lost = False
            enemy_player.king.update_all_legal_moves(self)
            # Reprocess all their moves to be completely sure
            for p in enemy_player.pieces:
                p.update_all_legal_moves(self)
            # --- THE STALEMATE TEST ---
            # If they have absolutely zero legal moves anywhere on the board...
            if not enemy_player.has_legal_moves():
                self.is_stalemate = True
                self.is_draw = True
            else:
                self.is_stalemate = False

    def execute_move(self, move: Move):
        """Replaces the old 'move_piece' and natively handles En Passant using the Move manual."""
        piece = self.get_piece_at(move.from_pos)
        if not piece: return

        # ==========================================
        # THE DIARY: TAKE THE SNAPSHOT BEFORE MOVING
        # ==========================================
        # Find out if anyone is about to die
        victim = self.get_piece_at(move.victim_pos) if move.victim_pos else None

        san_string = self.get_algebraic_notation(move, piece, victim)

        # Take the photograph
        record = MoveRecord(
            move=move,
            moved_piece=piece,
            piece_had_moved=piece.has_moved,
            clocks=CLOCKS,
            victim_piece=victim,
            old_en_passant=self.en_passant,
            old_castling_rights=self.castling_rights,
            algebraic_notation=san_string
        )

        # Save it in the book
        self.move_log.append(record)

        # 1. Capture Logic (Handles normal captures AND En Passant inherently)
        if move.victim_pos:
            victim = self.get_piece_at(move.victim_pos)
            if victim and victim.color != piece.color:
                victim.die()
                self.grid[move.victim_pos.row][move.victim_pos.col] = None

        # check castle
        if move.move_type == MoveType.CASTLE:
            rook = self.get_piece_at(move.to_pos)
            if not rook: return
            if can_castle(self,piece,rook):
                self.perform_castle(piece, rook)
                piece.has_moved = True


        else:
            # 2. Move Logic
            self.grid[move.to_pos.row][move.to_pos.col] = piece
            self.grid[move.from_pos.row][move.from_pos.col] = None
            piece.position = move.to_pos
            piece.has_moved = True



        #check promotion
        if move.move_type == MoveType.PROMOTION:
            piece.die()
            self.grid[move.to_pos.row][move.to_pos.col] = create_piece_with_specified_color(piece.color,
                                                                                            str(move.promotion_choice.value),
                                                                                            move.to_pos)

        # 3. En Passant Memory Update
        self.en_passant = None  # Always clear old memory
        if piece.type == ChessPieceType.PAWN and abs(move.to_pos.row - move.from_pos.row) == 2:
            mid_row = (move.to_pos.row + move.from_pos.row) // 2
            self.en_passant = SquarePosition(row=mid_row, col=move.to_pos.col)

        self.update_game_state()

        # --- THE RED PEN: Add + or # to the Diary ---
        # The turn hasn't switched yet, so active_color is still the guy who just moved.
        enemy_player = PLAYERS[OTHER_COLOR[self.active_color]]

        if enemy_player.lost:
            # They have no legal moves and are in check. Checkmate!
            self.move_log[-1].algebraic_notation += "#"
        elif enemy_player.is_in_check:
            # They are in check, but survive to fight another day.
            self.move_log[-1].algebraic_notation += "+"

        self.switch_turn()

    def perform_castle(self, king, rook):

        if not king or not rook: return
        king_old_pos = king.position
        rook_old_pos = rook.position

        direction = 1 if rook_old_pos.col > king_old_pos.col else -1
        king_new_col = king_old_pos.col + (2 * direction)
        rook_new_col = king_new_col - direction

        king_new_pos = SquarePosition(row=king_old_pos.row, col=king_new_col)
        rook_new_pos = SquarePosition(row=king_old_pos.row, col=rook_new_col)

        self.grid[king_old_pos.row][king_old_pos.col] = None
        self.grid[rook_old_pos.row][rook_old_pos.col] = None
        self.grid[king_new_pos.row][king_new_pos.col] = king
        self.grid[rook_new_pos.row][rook_new_pos.col] = rook

        king.position = king_new_pos
        rook.position = rook_new_pos
        king.has_moved = True
        rook.has_moved = True


    def switch_turn(self):
        CLOCKS[self.active_color].switch()
        self.active_color = ChessColor.BLACK if self.active_color == ChessColor.WHITE else ChessColor.WHITE
        CLOCKS[self.active_color].switch()

    # <editor-fold desc = "BOARD_HELPER">
    def is_square_attacked(self, square: SquarePosition, my_color: ChessColor) -> bool:
        """The Laser Eyes. Shoots rays outward to find enemy threats."""
        enemy_color = OTHER_COLOR[my_color]

        # 1. Straight Lasers (Looking for Rooks and Queens)
        directions_straight = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        for dr, dc in directions_straight:
            r, c = square.row + dr, square.col + dc
            while 0 <= r < 8 and 0 <= c < 8:
                target = self.grid[r][c]
                if target is not None:
                    if target.color == enemy_color and target.type in (ChessPieceType.ROOK, ChessPieceType.QUEEN):
                        return True
                    break  # Blocked by a piece (friendly, or non-threatening enemy)
                r += dr
                c += dc

        # 2. Diagonal Lasers (Looking for Bishops and Queens)
        directions_diag = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
        for dr, dc in directions_diag:
            r, c = square.row + dr, square.col + dc
            while 0 <= r < 8 and 0 <= c < 8:
                target = self.grid[r][c]
                if target is not None:
                    if target.color == enemy_color and target.type in (ChessPieceType.BISHOP, ChessPieceType.QUEEN):
                        return True
                    break
                r += dr
                c += dc

        # 3. L-Shape Lasers (Looking for Knights)
        knight_moves = [(2, 1), (2, -1), (1, 2), (1, -2), (-1, 2), (-1, -2), (-2, 1), (-2, -1)]
        for dr, dc in knight_moves:
            r, c = square.row + dr, square.col + dc
            if 0 <= r < 8 and 0 <= c < 8:
                target = self.grid[r][c]
                if target is not None and target.color == enemy_color and target.type == ChessPieceType.KNIGHT:
                    return True

        # 4. Pawn Check (Looking for Pawns)
        # WARNING: If I am White, enemy pawns attack DOWN (+1 row).
        # So I must look UP (-1 row) to find them!
        pawn_direction = -1 if my_color == ChessColor.WHITE else 1
        for dc in (-1, 1):
            r, c = square.row + pawn_direction, square.col + dc
            if 0 <= r < 8 and 0 <= c < 8:
                target = self.grid[r][c]
                if target is not None and target.color == enemy_color and target.type == ChessPieceType.PAWN:
                    return True

        # 5. King Check (Are we too close to the enemy king?)
        king_moves = directions_straight + directions_diag
        for dr, dc in king_moves:
            r, c = square.row + dr, square.col + dc
            if 0 <= r < 8 and 0 <= c < 8:
                target = self.grid[r][c]
                if target is not None and target.color == enemy_color and target.type == ChessPieceType.KING:
                    return True

        return False

    def undo_move(self):
        """Reads the last page of the diary and reverses time."""
        if len(self.move_log) == 0:
            return False

        # 1. Open the Diary and rip out the last page
        record = self.move_log.pop()
        move = record.move

        # 2. Grab the actors from the photograph
        piece = record.moved_piece
        victim = record.victim_piece

        # 3. SPECIAL CASE: Undo Castling
        if move.move_type == MoveType.CASTLE:
            # Recreate your exact math to find where the King and Rook landed
            direction = 1 if move.to_pos.col > move.from_pos.col else -1
            king_new_col = move.from_pos.col + (2 * direction)
            rook_new_col = king_new_col - direction

            # Grab the Rook from its new spot
            rook = self.grid[move.from_pos.row][rook_new_col]

            # Erase them from their new spots
            self.grid[move.from_pos.row][king_new_col] = None
            self.grid[move.from_pos.row][rook_new_col] = None

            # Put them back where they started
            self.grid[move.from_pos.row][move.from_pos.col] = piece
            self.grid[move.to_pos.row][move.to_pos.col] = rook

            piece.position = move.from_pos
            rook.position = move.to_pos

            # Restore their 'has_moved' status
            piece.has_moved = record.piece_had_moved
            rook.has_moved = False  # It hadn't moved if we were allowed to castle!

        else:
            # 4. NORMAL UNDO (Moves, Captures, En Passant, Promotions)

            # Erase whatever is on the destination square (the piece, or the new Promotion Queen)
            self.grid[move.to_pos.row][move.to_pos.col] = None

            # Put the original piece back where it started
            self.grid[move.from_pos.row][move.from_pos.col] = piece
            piece.position = move.from_pos
            piece.has_moved = record.piece_had_moved

            # Bring the dead back to life!
            if victim is not None:
                self.grid[move.victim_pos.row][move.victim_pos.col] = victim
                victim.position = move.victim_pos

        # 5. Restore the Board's memories
        self.en_passant = record.old_en_passant
        self.castling_rights = record.old_castling_rights

        #6. Restore the clock time
        for color in ChessColor:
            CLOCKS[color].remaining = record.current_times[color]

        # 7. Give the turn back and recalculate check
        self.switch_turn()
        self.update_game_state()

        return True




    # </editor-fold>


# </editor-fold>

# <editor-fold desc="DRAWING">
def get_image_path(color: ChessColor, piece_type: ChessPieceType):
    return f"assets/sliced_pieces/{color.value}_{piece_type.name}.png"

def draw_home_page(screen):
    # 1. Background - Deep Slate with a faint, massive checkerboard pattern
    screen.fill((30, 30, 35))
    for row in range(8):
        for col in range(10): # Wider to cover the menu area too
            if (row + col) % 2 == 0:
                pygame.draw.rect(screen, (35, 35, 40), (col * 100, row * 100, 100, 100))

    mouse_pos = pygame.mouse.get_pos()
    pygame.font.init()
    font_title = pygame.font.SysFont("Arial", 80, bold=True)
    font_btn = pygame.font.SysFont("Arial", 30, bold=True)

    # 2. The Title (With Drop Shadow)
    shadow_surf = font_title.render("CHESS", True, (0, 0, 0))
    screen.blit(shadow_surf, shadow_surf.get_rect(center=(SCREEN_WIDTH // 2 + 5, 205))) # Offset by 5px
    title_surf = font_title.render("CHESS", True, (255, 255, 255))
    screen.blit(title_surf, title_surf.get_rect(center=(SCREEN_WIDTH // 2, 200)))

    # 3. Start Game Button
    start_color = (80, 180, 80) if START_BTN_RECT.collidepoint(mouse_pos) else (60, 150, 60)
    pygame.draw.rect(screen, start_color, START_BTN_RECT, border_radius=15)
    pygame.draw.rect(screen, (255, 255, 255), START_BTN_RECT, 3, border_radius=15)
    start_txt = font_btn.render("START GAME", True, (255, 255, 255))
    screen.blit(start_txt, start_txt.get_rect(center=START_BTN_RECT.center))

    # 4. Quit Game Button
    quit_color = (180, 80, 80) if QUIT_BTN_RECT.collidepoint(mouse_pos) else (150, 60, 60)
    pygame.draw.rect(screen, quit_color, QUIT_BTN_RECT, border_radius=15)
    pygame.draw.rect(screen, (255, 255, 255), QUIT_BTN_RECT, 3, border_radius=15)
    quit_txt = font_btn.render("QUIT", True, (255, 255, 255))
    screen.blit(quit_txt, quit_txt.get_rect(center=QUIT_BTN_RECT.center))

    # 5. Settings Icon (Trigonometry Gear)
    set_color = (255, 255, 255) if SETTINGS_BTN_RECT.collidepoint(mouse_pos) else (150, 150, 150)
    cx, cy = SETTINGS_BTN_RECT.center
    pygame.draw.circle(screen, set_color, (cx, cy), 12, 3) # Inner ring
    for i in range(8):
        angle = i * (math.pi / 4)
        out_x = cx + 18 * math.cos(angle)
        out_y = cy + 18 * math.sin(angle)
        in_x = cx + 12 * math.cos(angle)
        in_y = cy + 12 * math.sin(angle)
        pygame.draw.line(screen, set_color, (in_x, in_y), (out_x, out_y), 4) # Teeth


def draw_settings_page(screen):
    # 1. Same cool background as the Home Page
    screen.fill((30, 30, 35))
    for row in range(8):
        for col in range(10):
            if (row + col) % 2 == 0:
                pygame.draw.rect(screen, (35, 35, 40), (col * 100, row * 100, 100, 100))

    mouse_pos = pygame.mouse.get_pos()
    pygame.font.init()
    font_title = pygame.font.SysFont("Arial", 80, bold=True)
    font_btn = pygame.font.SysFont("Arial", 30, bold=True)

    # 2. Title
    shadow_surf = font_title.render("SETTINGS", True, (0, 0, 0))
    screen.blit(shadow_surf, shadow_surf.get_rect(center=(SCREEN_WIDTH // 2 + 5, 125)))
    title_surf = font_title.render("SETTINGS", True, (255, 255, 255))
    screen.blit(title_surf, title_surf.get_rect(center=(SCREEN_WIDTH // 2, 120)))

    # 3. Dynamic Buttons Loop
    # 3. Dynamic Buttons Loop
    for i, settings_rect in enumerate(SETTINGS_RECTS):
        # Open the package! Grab the 3 things inside.
        btn_text, normal_color, hover_color = SETTINGS_OPTIONS[i]

        # Use the colors from the package!
        color = hover_color if settings_rect.collidepoint(mouse_pos) else normal_color

        pygame.draw.rect(screen, color, settings_rect, border_radius=15)
        pygame.draw.rect(screen, (255, 255, 255), settings_rect, 3, border_radius=15)

        # Use the text from the package!
        txt = font_btn.render(btn_text, True, (255, 255, 255))
        screen.blit(txt, txt.get_rect(center=settings_rect.center))

    # 4. Return to Menu Button
    ret_color = (180, 80, 80) if RETURN_BTN_RECT.collidepoint(mouse_pos) else (150, 60, 60)
    pygame.draw.rect(screen, ret_color, RETURN_BTN_RECT, border_radius=15)
    pygame.draw.rect(screen, (255, 255, 255), RETURN_BTN_RECT, 3, border_radius=15)
    ret_txt = font_btn.render("RETURN TO MENU", True, (255, 255, 255))
    screen.blit(ret_txt, ret_txt.get_rect(center=RETURN_BTN_RECT.center))

def draw_general_settings_page(screen):
    # 1. Background
    screen.fill((30, 30, 35))
    for row in range(8):
        for col in range(10):
            if (row + col) % 2 == 0:
                pygame.draw.rect(screen, (35, 35, 40), (col * 100, row * 100, 100, 100))

    mouse_pos = pygame.mouse.get_pos()
    pygame.font.init()
    font_title = pygame.font.SysFont("Arial", 60, bold=True)
    font_btn = pygame.font.SysFont("Arial", 30, bold=True)

    # 2. Title
    title_surf = font_title.render("GENERAL SETTINGS", True, (255, 255, 255))
    screen.blit(title_surf, title_surf.get_rect(center=(SCREEN_WIDTH // 2, 120)))

    # 3. Dynamic Loop
    for i, rect in enumerate(GENERAL_SETTINGS_RECTS):
        btn_name = GENERAL_SETTINGS_OPTIONS[i]

        if btn_name == "Auto Save":
            if AUTO_SAVE:
                # Light Grey when ON
                color = (180, 180, 180) if rect.collidepoint(mouse_pos) else (150, 150, 150)
                txt_str = "Auto Save: ON"
            else:
                # Dark Fading Grey when OFF
                color = (80, 80, 80) if rect.collidepoint(mouse_pos) else (60, 60, 60)
                txt_str = "Auto Save: OFF"

        pygame.draw.rect(screen, color, rect, border_radius=15)
        pygame.draw.rect(screen, (255, 255, 255), rect, 3, border_radius=15)

        txt = font_btn.render(txt_str, True, (255, 255, 255))
        screen.blit(txt, txt.get_rect(center=rect.center))

    # 4. Return Button
    ret_color = (180, 80, 80) if RETURN_BTN_RECT.collidepoint(mouse_pos) else (150, 60, 60)
    pygame.draw.rect(screen, ret_color, RETURN_BTN_RECT, border_radius=15)
    pygame.draw.rect(screen, (255, 255, 255), RETURN_BTN_RECT, 3, border_radius=15)
    ret_txt = font_btn.render("RETURN", True, (255, 255, 255))
    screen.blit(ret_txt, ret_txt.get_rect(center=RETURN_BTN_RECT.center))

def draw_saved_games_page(screen, games, scroll_y, return_rect,import_rect):
    # 1. Background
    screen.fill((30, 30, 35))
    for row in range(8):
        for col in range(10):
            if (row + col) % 2 == 0:
                pygame.draw.rect(screen, (35, 35, 40), (col * 100, row * 100, 100, 100))

    mouse_pos = pygame.mouse.get_pos()
    pygame.font.init()
    font_title = pygame.font.SysFont("Arial", 60, bold=True)
    font_text = pygame.font.SysFont("Arial", 22, bold=True)
    font_btn = pygame.font.SysFont("Arial", 16, bold=True)

    # 2. Title (Drawn BEFORE the scissors so it is always visible)
    title_surf = font_title.render("SAVED GAMES", True, (255, 255, 255))
    screen.blit(title_surf, title_surf.get_rect(center=(SCREEN_WIDTH // 2, 80)))

    # --- IMPORT BUTTON (Drawn BEFORE the scissors!) ---
    imp_col = (100, 150, 200) if import_rect.collidepoint(mouse_pos) else (80, 120, 160)
    pygame.draw.rect(screen, imp_col, import_rect, border_radius=10)
    pygame.draw.rect(screen, (255, 255, 255), import_rect, 2, border_radius=10)
    imp_txt = font_text.render("IMPORT PGN", True, (255, 255, 255))
    screen.blit(imp_txt, imp_txt.get_rect(center=import_rect.center))

    # 3. SET THE SCISSORS (The Window Pane)
    clip_rect = pygame.Rect(0, 130, SCREEN_WIDTH, SCREEN_HEIGHT - 250)
    screen.set_clip(clip_rect)

    # 4. Draw the Game Slots dynamically inside the elevator
    start_y = 150
    for i, game in enumerate(games):
        # Subtract scroll_y to move them up!
        y = start_y + (i * 90) - scroll_y

        main_rect = pygame.Rect(50, y, SCREEN_WIDTH - 100, 75)
        show_rect = pygame.Rect(main_rect.right - 260, y + 17, 70, 40)
        copy_rect = pygame.Rect(main_rect.right - 170, y + 17, 70, 40)
        delete_rect = pygame.Rect(main_rect.right - 80, y + 17, 70, 40)

        # Draw Card
        pygame.draw.rect(screen, (50, 50, 60), main_rect, border_radius=10)
        pygame.draw.rect(screen, (100, 100, 120), main_rect, 2, border_radius=10)

        # Draw Text
        game_title = f"{game['filename']}  |  Last Move: {game['last_move']}"
        txt_surf = font_text.render(game_title, True, (220, 220, 220))
        screen.blit(txt_surf, (main_rect.x + 20, main_rect.y + 25))

        # Show Button
        show_color = (80, 200, 80) if show_rect.collidepoint(mouse_pos) else (60, 150, 60)
        pygame.draw.rect(screen, show_color, show_rect, border_radius=5)
        show_txt = font_btn.render("SHOW", True, (255, 255, 255))
        screen.blit(show_txt, show_txt.get_rect(center=show_rect.center))

        # Copy Button
        copy_color = (80, 150, 200) if copy_rect.collidepoint(mouse_pos) else (60, 100, 150)
        pygame.draw.rect(screen, copy_color, copy_rect, border_radius=5)
        copy_txt = font_btn.render("COPY", True, (255, 255, 255))
        screen.blit(copy_txt, copy_txt.get_rect(center=copy_rect.center))

        # Delete Button
        del_color = (200, 80, 80) if delete_rect.collidepoint(mouse_pos) else (150, 60, 60)
        pygame.draw.rect(screen, del_color, delete_rect, border_radius=5)
        del_txt = font_btn.render("DEL", True, (255, 255, 255))
        screen.blit(del_txt, del_txt.get_rect(center=delete_rect.center))

    # 5. REMOVE THE SCISSORS
    screen.set_clip(None)

    # 6. Return Button (Drawn AFTER the scissors so it sits at the bottom safely)
    ret_color = (180, 80, 80) if return_rect.collidepoint(mouse_pos) else (150, 60, 60)
    pygame.draw.rect(screen, ret_color, return_rect, border_radius=15)
    pygame.draw.rect(screen, (255, 255, 255), return_rect, 3, border_radius=15)
    ret_txt = font_text.render("RETURN", True, (255, 255, 255))
    screen.blit(ret_txt, ret_txt.get_rect(center=return_rect.center))


def draw_paste_pgn_page(screen, status_msg: str, status_color: tuple, is_valid: bool, paste_rect, save_rect,
                        return_rect):
    # 1. Background
    screen.fill((30, 30, 35))
    for row in range(8):
        for col in range(10):
            if (row + col) % 2 == 0:
                pygame.draw.rect(screen, (35, 35, 40), (col * 100, row * 100, 100, 100))

    mouse_pos = pygame.mouse.get_pos()
    pygame.font.init()
    font_title = pygame.font.SysFont("Arial", 60, bold=True)
    font_btn = pygame.font.SysFont("Arial", 30, bold=True)
    font_status = pygame.font.SysFont("Arial", 24, bold=True)

    # 2. Title & Status Message
    title_surf = font_title.render("IMPORT PGN", True, (255, 255, 255))
    screen.blit(title_surf, title_surf.get_rect(center=(SCREEN_WIDTH // 2, 80)))

    status_surf = font_status.render(status_msg, True, status_color)
    screen.blit(status_surf, status_surf.get_rect(center=(SCREEN_WIDTH // 2, 160)))

    # 3. Paste Button (Blue)
    p_color = (100, 150, 200) if paste_rect.collidepoint(mouse_pos) else (80, 120, 160)
    pygame.draw.rect(screen, p_color, paste_rect, border_radius=15)
    pygame.draw.rect(screen, (255, 255, 255), paste_rect, 3, border_radius=15)
    p_txt = font_btn.render("PASTE FROM CLIPBOARD", True, (255, 255, 255))
    screen.blit(p_txt, p_txt.get_rect(center=paste_rect.center))

    # 4. Save Button (Only Green if valid, otherwise dark grey)
    if is_valid:
        s_color = (80, 200, 80) if save_rect.collidepoint(mouse_pos) else (60, 150, 60)
    else:
        s_color = (60, 60, 60)  # Disabled
    pygame.draw.rect(screen, s_color, save_rect, border_radius=15)
    pygame.draw.rect(screen, (255, 255, 255), save_rect, 3, border_radius=15)
    s_txt = font_btn.render("SAVE GAME", True, (255, 255, 255) if is_valid else (150, 150, 150))
    screen.blit(s_txt, s_txt.get_rect(center=save_rect.center))

    # 5. Return Button
    ret_color = (180, 80, 80) if return_rect.collidepoint(mouse_pos) else (150, 60, 60)
    pygame.draw.rect(screen, ret_color, return_rect, border_radius=15)
    pygame.draw.rect(screen, (255, 255, 255), return_rect, 3, border_radius=15)
    ret_txt = font_btn.render("RETURN", True, (255, 255, 255))
    screen.blit(ret_txt, ret_txt.get_rect(center=return_rect.center))

def draw_replay_side_menu(screen, show_notation: bool, current_move_text: str):
    pygame.draw.rect(screen, (30, 30, 30), (WINDOW_SIZE, 0, MENU_WIDTH, SCREEN_HEIGHT))
    pygame.draw.line(screen, (100, 100, 100), (WINDOW_SIZE, 0), (WINDOW_SIZE, SCREEN_HEIGHT), 2)

    mouse_pos = pygame.mouse.get_pos()
    pygame.font.init()
    font_btn = pygame.font.SysFont("Arial", 20, bold=True)
    font_large = pygame.font.SysFont("Arial", 28, bold=True)

    # Move Tracker Label
    lbl = font_large.render("Current Move:", True, (200, 200, 200))
    screen.blit(lbl, lbl.get_rect(center=(WINDOW_SIZE + 100, 30)))

    txt = font_large.render(current_move_text, True, (255, 200, 50))
    screen.blit(txt, txt.get_rect(center=(WINDOW_SIZE + 100, 65)))

    # Next Button (Green)
    n_col = (80, 200, 80) if REPLAY_NEXT_BTN.collidepoint(mouse_pos) else (60, 150, 60)
    pygame.draw.rect(screen, n_col, REPLAY_NEXT_BTN, border_radius=10)
    n_txt = font_btn.render("NEXT MOVE", True, (255, 255, 255))
    screen.blit(n_txt, n_txt.get_rect(center=REPLAY_NEXT_BTN.center))

    # Prev Button (Yellow)
    p_col = (200, 200, 80) if REPLAY_PREV_BTN.collidepoint(mouse_pos) else (150, 150, 60)
    pygame.draw.rect(screen, p_col, REPLAY_PREV_BTN, border_radius=10)
    p_txt = font_btn.render("PREV MOVE", True, (0, 0, 0))
    screen.blit(p_txt, p_txt.get_rect(center=REPLAY_PREV_BTN.center))

    # Reset Button (Red)
    r_col = (200, 80, 80) if REPLAY_RESET_BTN.collidepoint(mouse_pos) else (150, 60, 60)
    pygame.draw.rect(screen, r_col, REPLAY_RESET_BTN, border_radius=5)
    r_txt = font_btn.render("Restart Match", True, (255, 255, 255))
    screen.blit(r_txt, r_txt.get_rect(center=REPLAY_RESET_BTN.center))

    # Notation Toggle
    not_col = (100, 180, 100) if show_notation else (150, 100, 100)
    pygame.draw.rect(screen, not_col, REPLAY_NOTATION_BTN, border_radius=5)
    t_txt = font_btn.render("Notation: ON" if show_notation else "Notation: OFF", True, (255, 255, 255))
    screen.blit(t_txt, t_txt.get_rect(center=REPLAY_NOTATION_BTN.center))

    # Menu Button (Blue)
    m_col = (80, 150, 200) if REPLAY_MENU_BTN.collidepoint(mouse_pos) else (60, 100, 150)
    pygame.draw.rect(screen, m_col, REPLAY_MENU_BTN, border_radius=10)
    m_txt = font_btn.render("Return to Menu", True, (255, 255, 255))
    screen.blit(m_txt, m_txt.get_rect(center=REPLAY_MENU_BTN.center))


def draw_board(screen, show_notation: bool = False):
    for row in range(8):
        for col in range(8):
            # 1. Paint the wood
            is_light_square = (row + col) % 2 == 0
            color = LIGHT if is_light_square else DARK
            pygame.draw.rect(screen, color, (col * SQUARE_SIZE, row * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE))

            # 2. Paint the notation if the toggle is ON
            if show_notation and NOTATION_FONT is not None:
                # Get the text (e.g., 'a8') and capitalize it ('A8')
                notation_text = row_col_to_notation(row, col).lower()

                # Make the text color the opposite of the wood color
                text_color = DARK if is_light_square else LIGHT

                # Carve the stamp and press it into the bottom left corner
                text_surface = NOTATION_FONT.render(notation_text, True, text_color)

                # Math: x is just past the left edge, y is just above the bottom edge
                x_pos = col * SQUARE_SIZE + 4
                y_pos = (row + 1) * SQUARE_SIZE - 18
                screen.blit(text_surface, (x_pos, y_pos))


def draw_side_menu(screen, show_notation: bool,is_paused:bool):
    """Paints the side control panel, clocks, and buttons."""
    # 1. Menu Background
    pygame.draw.rect(screen, (30, 30, 30), (WINDOW_SIZE, 0, MENU_WIDTH, SCREEN_HEIGHT))
    pygame.draw.line(screen, (100, 100, 100), (WINDOW_SIZE, 0), (WINDOW_SIZE, SCREEN_HEIGHT), 2)

    pygame.font.init()
    font_large = pygame.font.SysFont("Arial", 32, bold=True)
    font_small = pygame.font.SysFont("Arial", 20, bold=True)

    mouse_pos = pygame.mouse.get_pos()

    # 2. Black's Clock (Top)
    # Width shrunk to 110, X-position moved slightly left to 20
    pygame.draw.rect(screen, (20, 20, 20), (WINDOW_SIZE + 20, 20, 110, 60))
    pygame.draw.rect(screen, (100, 100, 100), (WINDOW_SIZE + 20, 20, 110, 60), 2)

    b_clock_txt = font_large.render(CLOCKS[ChessColor.BLACK].standard_notation(), True, (255, 255, 255))
    b_txt_rect = b_clock_txt.get_rect(center=(WINDOW_SIZE + 75, 50))  # Centered mathematically
    screen.blit(b_clock_txt, b_txt_rect)

    # --- Black's Flag Button ---
    b_flag_color = (200, 80, 80) if B_FLAG_BTN_RECT.collidepoint(mouse_pos) else (150, 40, 40)
    pygame.draw.rect(screen, b_flag_color, B_FLAG_BTN_RECT)
    pygame.draw.rect(screen, (200, 200, 200), B_FLAG_BTN_RECT, 2)
    f_txt = font_small.render("F", True, (255, 255, 255))
    screen.blit(f_txt, f_txt.get_rect(center=B_FLAG_BTN_RECT.center))

    # 3. White's Clock (Bottom)
    pygame.draw.rect(screen, (220, 220, 220), (WINDOW_SIZE + 20, SCREEN_HEIGHT - 80, 110, 60))
    pygame.draw.rect(screen, (100, 100, 100), (WINDOW_SIZE + 20, SCREEN_HEIGHT - 80, 110, 60), 2)

    w_clock_txt = font_large.render(CLOCKS[ChessColor.WHITE].standard_notation(), True, (0, 0, 0))
    w_txt_rect = w_clock_txt.get_rect(center=(WINDOW_SIZE + 75, SCREEN_HEIGHT - 50))
    screen.blit(w_clock_txt, w_txt_rect)

    # --- White's Flag Button ---
    w_flag_color = (200, 80, 80) if W_FLAG_BTN_RECT.collidepoint(mouse_pos) else (150, 40, 40)
    pygame.draw.rect(screen, w_flag_color, W_FLAG_BTN_RECT)
    pygame.draw.rect(screen, (200, 200, 200), W_FLAG_BTN_RECT, 2)
    screen.blit(f_txt, f_txt.get_rect(center=W_FLAG_BTN_RECT.center))



    # --- Black's Draw Button ---
    b_draw_color = (100, 100, 150) if B_DRAW_BTN_RECT.collidepoint(mouse_pos) else (80, 80, 120)
    pygame.draw.rect(screen, b_draw_color, B_DRAW_BTN_RECT)
    pygame.draw.rect(screen, (200, 200, 200), B_DRAW_BTN_RECT, 2)
    b_draw_txt = font_small.render("1/2", True, (255, 255, 255))
    screen.blit(b_draw_txt, b_draw_txt.get_rect(center=B_DRAW_BTN_RECT.center))

    # ... [Right below where you draw W_FLAG_BTN_RECT] ...
    # --- White's Draw Button ---
    w_draw_color = (100, 100, 150) if W_DRAW_BTN_RECT.collidepoint(mouse_pos) else (80, 80, 120)
    pygame.draw.rect(screen, w_draw_color, W_DRAW_BTN_RECT)
    pygame.draw.rect(screen, (200, 200, 200), W_DRAW_BTN_RECT, 2)
    w_draw_txt = font_small.render("1/2", True, (255, 255, 255))
    screen.blit(w_draw_txt, w_draw_txt.get_rect(center=W_DRAW_BTN_RECT.center))


    # 4. The Undo Button
    btn_color = (120, 120, 150) if UNDO_BTN_RECT.collidepoint(mouse_pos) else (80, 80, 100)
    pygame.draw.rect(screen, btn_color, UNDO_BTN_RECT)
    pygame.draw.rect(screen, (200, 200, 200), UNDO_BTN_RECT, 2)
    undo_txt = font_small.render("Undo Move", True, (255, 255, 255))
    screen.blit(undo_txt, undo_txt.get_rect(center=UNDO_BTN_RECT.center))

    # 5. The Notation Toggle Button
    if show_notation:
        not_color = (100, 180, 100) if NOTATION_BTN_RECT.collidepoint(mouse_pos) else (80, 150, 80)
    else:
        not_color = (150, 100, 100) if NOTATION_BTN_RECT.collidepoint(mouse_pos) else (120, 80, 80)

    pygame.draw.rect(screen, not_color, NOTATION_BTN_RECT)
    pygame.draw.rect(screen, (200, 200, 200), NOTATION_BTN_RECT, 2)
    toggle_txt = font_small.render("Notation: ON" if show_notation else "Notation: OFF", True, (255, 255, 255))
    screen.blit(toggle_txt, toggle_txt.get_rect(center=NOTATION_BTN_RECT.center))

    # 6. The Save Game Button
    if SAVE_BTN_RECT.collidepoint(mouse_pos):
        save_btn_color = (100, 150, 200)  # Lighter blue on hover
    else:
        save_btn_color = (80, 120, 160)  # Darker blue

    # --- The Pause/Resume Button ---
    pause_color = (200, 150, 80) if PAUSE_BTN_RECT.collidepoint(mouse_pos) else (180, 120, 60)
    pygame.draw.rect(screen, pause_color, PAUSE_BTN_RECT)
    pygame.draw.rect(screen, (255, 255, 255), PAUSE_BTN_RECT, 2)
    pause_text_str = "RESUME" if is_paused else "PAUSE"
    pause_txt = font_small.render(pause_text_str, True, (255, 255, 255))
    screen.blit(pause_txt, pause_txt.get_rect(center=PAUSE_BTN_RECT.center))

    #the save game
    pygame.draw.rect(screen, save_btn_color, SAVE_BTN_RECT)
    pygame.draw.rect(screen, (200, 200, 200), SAVE_BTN_RECT, 2)
    save_txt = font_small.render("Save Game", True, (255, 255, 255))
    screen.blit(save_txt, save_txt.get_rect(center=SAVE_BTN_RECT.center))

    # --- Reset Button ---
    reset_color = (180, 100, 100) if RESET_BTN_RECT.collidepoint(mouse_pos) else (150, 80, 80)
    pygame.draw.rect(screen, reset_color, RESET_BTN_RECT)
    pygame.draw.rect(screen, (255, 255, 255), RESET_BTN_RECT, 2)
    reset_txt = font_small.render("Reset Game", True, (255, 255, 255))
    screen.blit(reset_txt, reset_txt.get_rect(center=RESET_BTN_RECT.center))

    # --- Menu Button ---
    menu_color = (100, 150, 150) if MENU_BTN_RECT.collidepoint(mouse_pos) else (80, 120, 120)
    pygame.draw.rect(screen, menu_color, MENU_BTN_RECT)
    pygame.draw.rect(screen, (255, 255, 255), MENU_BTN_RECT, 2)
    menu_txt = font_small.render("Main Menu", True, (255, 255, 255))
    screen.blit(menu_txt, menu_txt.get_rect(center=MENU_BTN_RECT.center))

def get_piece_image(piece: ChessPiece, cache):
    return get_piece_image_with_color_and_type(piece.color, piece.type, cache)


def get_piece_image_with_color_and_type(color, piece_type, cache):
    key = (color, piece_type)
    if key not in cache:
        try:
            img = pygame.image.load(get_image_path(color, piece_type)).convert_alpha()
            img = pygame.transform.smoothscale(img, (int(SQUARE_SIZE * 0.85), int(SQUARE_SIZE * 0.85)))
            cache[key] = img
        except FileNotFoundError:
            # Fallback for debugging if assets are missing
            img = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE))
            img.fill((255, 0, 0) if color == ChessColor.WHITE else (0, 0, 255))
            cache[key] = img
    return cache[key]


def draw_piece(screen, piece: ChessPiece, cache):
    if piece.position is None: return
    row, col = piece.position.row, piece.position.col
    img = get_piece_image(piece, cache)
    rect = img.get_rect(center=(col * SQUARE_SIZE + SQUARE_SIZE // 2, row * SQUARE_SIZE + SQUARE_SIZE // 2))
    screen.blit(img, rect)


def draw_pieces(screen, board: Board, cache, dragged_piece=None):
    for piece in board.get_all_pieces():
        # Do not draw the piece if it is currently being dragged!
        if piece is not dragged_piece:
            draw_piece(screen, piece, cache)


def highlight_square(screen, square: SquarePosition, color: tuple, alpha: int = 125, thickness: int = 8):
    """Lays a see-through highlight over a square.
       If thickness > 0, it draws a hollow picture frame instead."""
    if square is None:
        return

    # 1. Create a special piece of glass that is 100% invisible by default_pack
    glass_pane = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)

    # 2. Mix the RGB paint with the Alpha (transparency)
    rgba_color = (color[0], color[1], color[2], alpha)

    # 3. Paint the rectangle on the glass.
    # If thickness is 0, it fills the whole glass.
    # If thickness is 5, it just paints a 5-pixel border.
    pygame.draw.rect(glass_pane, rgba_color, glass_pane.get_rect(), width=thickness)

    # 4. Calculate exactly where to put it on the floor
    x = square.col * SQUARE_SIZE
    y = square.row * SQUARE_SIZE

    # 5. Lay it down
    screen.blit(glass_pane, (x, y))

def get_square_center(pos: SquarePosition):
    """Returns the exact (x, y) pixel coordinates of the middle of a square."""
    x = pos.col * SQUARE_SIZE + SQUARE_SIZE // 2
    y = pos.row * SQUARE_SIZE + SQUARE_SIZE // 2
    return x, y


def draw_arrow(screen, start_square: SquarePosition, end_square: SquarePosition, color, padding=15, thickness=5):
    start_x = start_square.col * SQUARE_SIZE + SQUARE_SIZE // 2
    start_y = start_square.row * SQUARE_SIZE + SQUARE_SIZE // 2

    end_x = end_square.col * SQUARE_SIZE + SQUARE_SIZE // 2
    end_y = end_square.row * SQUARE_SIZE + SQUARE_SIZE // 2

    dx_squares = abs(end_square.col - start_square.col)
    dy_squares = abs(end_square.row - start_square.row)

    is_knight_move = (dx_squares == 2 and dy_squares == 1) or (dx_squares == 1 and dy_squares == 2)

    snip_length = 15
    arrow_length = 15

    if is_knight_move:
        # --- THE KNIGHT LOGIC ---
        # Determine the elbow/corner of the L-shape: Always move the 2-squares FIRST
        if dx_squares == 2:
            # Move 2 squares horizontally first, then 1 vertically
            corner_x = end_x
            corner_y = start_y
        else:
            # Move 2 squares vertically first, then 1 horizontally
            corner_x = start_x
            corner_y = end_y

        # 1. The angle from the corner to the end square (for the arrowhead)
        end_angle = math.atan2(end_y - corner_y, end_x - corner_x)

        # 2. The angle from the start square to the corner (for start padding)
        start_angle = math.atan2(corner_y - start_y, corner_x - start_x)

        # 3. Apply padding so lines don't start exactly in the center of the piece
        adj_start_x = start_x + padding * math.cos(start_angle)
        adj_start_y = start_y + padding * math.sin(start_angle)

        adj_end_x = end_x - padding * math.cos(end_angle)
        adj_end_y = end_y - padding * math.sin(end_angle)

        # 4. Snip the stick so it doesn't pierce the arrowhead
        stick_end_x = adj_end_x - snip_length * math.cos(end_angle)
        stick_end_y = adj_end_y - snip_length * math.sin(end_angle)

        # Draw the L-Shape Lines
        pygame.draw.line(screen, color, (adj_start_x, adj_start_y), (corner_x, corner_y), thickness)
        pygame.draw.line(screen, color, (corner_x, corner_y), (stick_end_x, stick_end_y), thickness)

        # Draw the Arrowhead pointing from the corner
        tip = (adj_end_x, adj_end_y)
        left = (
            adj_end_x - arrow_length * math.cos(end_angle - math.pi / 6),
            adj_end_y - arrow_length * math.sin(end_angle - math.pi / 6)
        )
        right = (
            adj_end_x - arrow_length * math.cos(end_angle + math.pi / 6),
            adj_end_y - arrow_length * math.sin(end_angle + math.pi / 6)
        )
        pygame.draw.polygon(screen, color, [tip, left, right])

    else:
        # --- NORMAL STRAIGHT ARROW LOGIC ---
        angle = math.atan2(end_y - start_y, end_x - start_x)

        adj_start_x = start_x + padding * math.cos(angle)
        adj_start_y = start_y + padding * math.sin(angle)

        adj_end_x = end_x - padding * math.cos(angle)
        adj_end_y = end_y - padding * math.sin(angle)

        stick_end_x = adj_end_x - snip_length * math.cos(angle)
        stick_end_y = adj_end_y - snip_length * math.sin(angle)

        pygame.draw.line(screen, color, (adj_start_x, adj_start_y), (stick_end_x, stick_end_y), thickness)

        tip = (adj_end_x, adj_end_y)
        left = (
            adj_end_x - arrow_length * math.cos(angle - math.pi / 6),
            adj_end_y - arrow_length * math.sin(angle - math.pi / 6)
        )
        right = (
            adj_end_x - arrow_length * math.cos(angle + math.pi / 6),
            adj_end_y - arrow_length * math.sin(angle + math.pi / 6)
        )
        pygame.draw.polygon(screen, color, [tip, left, right])
def draw_game_over_screen(screen, winner_color: ChessColor,is_draw = False):
    # 1. Dim the background so the board looks "finished"
    dim_surface = pygame.Surface((WINDOW_SIZE, WINDOW_SIZE))
    dim_surface.set_alpha(180)  # 0 is clear, 255 is solid black
    dim_surface.fill((0, 0, 0))
    screen.blit(dim_surface, (0, 0))

    # 2. Draw the menu box in the dead center
    menu_width = 300
    menu_height = 160
    start_x = (WINDOW_SIZE - menu_width) // 2
    start_y = (WINDOW_SIZE - menu_height) // 2

    pygame.draw.rect(screen, (40, 40, 40), (start_x, start_y, menu_width, menu_height))
    pygame.draw.rect(screen, (220, 220, 220), (start_x, start_y, menu_width, menu_height), 4)

    # 3. Draw the Winner Text
    pygame.font.init()  # Ensure fonts are ready
    font_large = pygame.font.SysFont("Arial", 40, bold=True)
    font_small = pygame.font.SysFont("Arial", 28, bold=True)

    if is_draw:
        text = "DRAW!"
    else:
        text = f"{winner_color.value} WINS!"

    text_surface = font_large.render(text, True, (255, 255, 255))
    text_rect = text_surface.get_rect(center=(WINDOW_SIZE // 2, start_y + 45))
    screen.blit(text_surface, text_rect)

    # 4. Draw the "Again?" Button
    btn_width = 140
    btn_height = 50
    btn_rect = pygame.Rect(0, 0, btn_width, btn_height)
    btn_rect.center = (WINDOW_SIZE // 2, start_y + 110)

    pygame.draw.rect(screen, (100, 200, 100), btn_rect)
    pygame.draw.rect(screen, (255, 255, 255), btn_rect, 2)

    btn_text = font_small.render("Again?", True, (0, 0, 0))
    btn_text_rect = btn_text.get_rect(center=btn_rect.center)
    screen.blit(btn_text, btn_text_rect)

    # Return the invisible button box so the mouse clicker knows where it is
    return btn_rect

# </editor-fold>

# <editor-fold desc="GLOBAL VARIABLES">
PYGAME = pygame
SCREEN = None
PLAYERS = {}
CLOCKS = {}


BOARD = Board()

PLAYERS[ChessColor.WHITE] = Player(BOARD, ChessColor.WHITE)
PLAYERS[ChessColor.BLACK] = Player(BOARD, ChessColor.BLACK)

CLOCKS[ChessColor.WHITE] = ChessClock(ChessColor.WHITE, STARTING_TIME)
CLOCKS[ChessColor.BLACK] = ChessClock(ChessColor.BLACK, STARTING_TIME)

IMAGE_CACHE = {}

NOTATION_FONT = None  # We will initialize this inside main()


# </editor-fold>

# <editor-fold desc="PROMOTION MENU">
def draw_promotion_menu(screen, color: ChessColor, cache):
    # 1. Dim the background so the board looks "paused"
    dim_surface = pygame.Surface((WINDOW_SIZE, WINDOW_SIZE))
    dim_surface.set_alpha(150)  # 0 is clear, 255 is solid black
    dim_surface.fill((0, 0, 0))
    screen.blit(dim_surface, (0, 0))

    # 2. Draw the white menu box in the dead center
    menu_width = 4 * SQUARE_SIZE
    menu_height = SQUARE_SIZE
    start_x = (WINDOW_SIZE - menu_width) // 2
    start_y = (WINDOW_SIZE - menu_height) // 2

    pygame.draw.rect(screen, (220, 220, 220), (start_x, start_y, menu_width, menu_height))
    pygame.draw.rect(screen, (50, 50, 50), (start_x, start_y, menu_width, menu_height), 3)

    # 3. Draw the 4 pieces and save their invisible clickable boxes
    pieces = [ChessPieceType.QUEEN, ChessPieceType.ROOK, ChessPieceType.BISHOP, ChessPieceType.KNIGHT]
    clickable_areas = []

    for i, ptype in enumerate(pieces):
        img = get_piece_image_with_color_and_type(color, ptype, cache)

        # Calculate exact center for this piece's slot
        center_x = start_x + (i * SQUARE_SIZE) + (SQUARE_SIZE // 2)
        center_y = start_y + (SQUARE_SIZE // 2)

        rect = img.get_rect(center=(center_x, center_y))
        screen.blit(img, rect)

        # Save the box and the piece type it represents
        clickable_areas.append((rect, ptype))

    return clickable_areas


# </editor-fold>

# <editor-fold desc="MAIN MENU">

def run_general_settings_screen():
    global SCREEN, AUTO_SAVE
    pygame_clock = pygame.time.Clock()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # 1. Return Button
                if RETURN_BTN_RECT.collidepoint(event.pos):
                    return

                # 2. Dynamic Settings Buttons
                for i, rect in enumerate(GENERAL_SETTINGS_RECTS):
                    if rect.collidepoint(event.pos):
                        btn_name = GENERAL_SETTINGS_OPTIONS[i]

                        if btn_name == "Auto Save":
                            AUTO_SAVE = not AUTO_SAVE  # Flip the switch!

        draw_general_settings_page(SCREEN)
        pygame.display.flip()
        pygame_clock.tick(FPS)

def run_replay_screen(pgn_string: str):
    global SCREEN, IMAGE_CACHE, BOARD
    pygame_clock = pygame.time.Clock()

    # 1. Use the global BOARD instead of creating a fake one!
    BOARD.load_fen(STARTING_POSITION)

    # 2. Parse the Diary
    san_list = pgn_to_move_list(pgn_string)
    current_move_index = 0

    show_notation = False
    drawn_arrows = set()
    highlighted_squares = set()
    right_click_start = None

    while True:
        # Determine what text to show for the current move
        if current_move_index == 0:
            move_text = "Start"
        else:
            move_text = san_list[current_move_index - 1]

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            # --- KEYBOARD SHORTCUTS ---
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RIGHT and current_move_index < len(san_list):
                    drawn_arrows.clear()
                    target_san = san_list[current_move_index]
                    move = get_move_from_san(BOARD, target_san)
                    if move:
                        BOARD.execute_move(move)
                        current_move_index += 1
                elif event.key == pygame.K_LEFT and current_move_index > 0:
                    drawn_arrows.clear()
                    BOARD.undo_move()
                    current_move_index -= 1

            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left Click
                    # 1. Wipe whiteboard on any left click
                    drawn_arrows.clear()
                    highlighted_squares.clear()

                    # 2. Button Intercepts
                    if REPLAY_MENU_BTN.collidepoint(event.pos):
                        return  # Exit the room!

                    elif REPLAY_NOTATION_BTN.collidepoint(event.pos):
                        show_notation = not show_notation

                    elif REPLAY_RESET_BTN.collidepoint(event.pos):
                        BOARD.load_fen(STARTING_POSITION)
                        current_move_index = 0

                    elif REPLAY_NEXT_BTN.collidepoint(event.pos) and current_move_index < len(san_list):
                        target_san = san_list[current_move_index]
                        move = get_move_from_san(BOARD, target_san)
                        if move:
                            BOARD.execute_move(move)
                            current_move_index += 1

                    elif REPLAY_PREV_BTN.collidepoint(event.pos) and current_move_index > 0:
                        BOARD.undo_move()
                        current_move_index -= 1

                elif event.button == 3:  # Right Click
                    right_click_start = pixel_to_squarepos(event.pos)

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 3:
                    if right_click_start is not None:
                        right_click_end = pixel_to_squarepos(event.pos)
                        if right_click_end is not None:
                            if right_click_start != right_click_end:
                                arrow_tuple = (right_click_start, right_click_end)
                                if arrow_tuple in drawn_arrows:
                                    drawn_arrows.remove(arrow_tuple)
                                else:
                                    drawn_arrows.add(arrow_tuple)
                            else:
                                if right_click_start in highlighted_squares:
                                    highlighted_squares.remove(right_click_start)
                                else:
                                    highlighted_squares.add(right_click_start)
                        right_click_start = None

        # --- DRAWING PHASE ---
        SCREEN.fill((0, 0, 0))
        draw_board(SCREEN, show_notation)
        draw_replay_side_menu(SCREEN, show_notation, move_text)

        # Draw pieces using the global BOARD
        draw_pieces(SCREEN, BOARD, IMAGE_CACHE)

        for square in highlighted_squares:
            highlight_square(SCREEN, square, (200, 50, 50), alpha=100, thickness=0)

        for start_pos, end_pos in drawn_arrows:
            draw_arrow(SCREEN, start_pos, end_pos, (255, 170, 0))

        pygame.display.flip()
        pygame_clock.tick(FPS)


def run_paste_pgn_screen():
    global SCREEN
    pygame_clock = pygame.time.Clock()
    pygame.scrap.init()

    paste_rect = pygame.Rect((SCREEN_WIDTH // 2) - 200, 220, 400, 60)
    save_rect = pygame.Rect((SCREEN_WIDTH // 2) - 200, 320, 400, 60)
    return_rect = pygame.Rect((SCREEN_WIDTH // 2) - 150, SCREEN_HEIGHT - 100, 300, 60)

    pasted_text = ""
    status_msg = "Click Paste to load from clipboard"
    status_color = (200, 200, 200)
    is_valid = False

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # 1. Return
                if return_rect.collidepoint(event.pos):
                    return

                # 2. Paste Button
                elif paste_rect.collidepoint(event.pos):
                    raw_bytes = pygame.scrap.get(pygame.SCRAP_TEXT)
                    if raw_bytes:
                        # Clean invisible Windows clipboard junk and decode it
                        pasted_text = raw_bytes.replace(b'\x00', b'').decode('utf-8')

                        # Send it to the Shadow Board!
                        if is_pgn_valid(pasted_text):
                            status_msg = "Valid PGN! Ready to save."
                            status_color = (80, 200, 80)
                            is_valid = True
                        else:
                            status_msg = "Invalid PGN. Check your text."
                            status_color = (200, 80, 80)
                            is_valid = False
                    else:
                        status_msg = "Clipboard is empty!"
                        status_color = (200, 80, 80)

                # 3. Save Button
                elif save_rect.collidepoint(event.pos) and is_valid:
                    save_custom_pgn(pasted_text)
                    return  # Exit the room instantly so the Saved Games list refreshes!

        draw_paste_pgn_page(SCREEN, status_msg, status_color, is_valid, paste_rect, save_rect, return_rect)
        pygame.display.flip()
        pygame_clock.tick(FPS)

def run_saved_games_screen():
    global SCREEN
    pygame_clock = pygame.time.Clock()

    games = get_saved_games_data()

    # Elevator controls
    scroll_y = 0
    scroll_speed = 30
    start_y = 150
    card_height = 90

    # Calculate the floor: How far down can we scroll?
    total_content_height = len(games) * card_height
    window_pane_height = SCREEN_HEIGHT - 250
    max_scroll = max(0, total_content_height - window_pane_height + 20)

    import_rect = pygame.Rect(SCREEN_WIDTH - 220, 20, 200, 50)  # Top right corner
    return_rect = pygame.Rect((SCREEN_WIDTH // 2) - 150, SCREEN_HEIGHT - 80, 300, 60)
    clip_rect = pygame.Rect(0, 130, SCREEN_WIDTH, SCREEN_HEIGHT - 250)

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            # --- THE SCROLL WHEEL ---
            if event.type == pygame.MOUSEWHEEL:
                scroll_y -= event.y * scroll_speed
                # Clamp the elevator so it doesn't break the roof or floor
                scroll_y = max(0, min(scroll_y, max_scroll))

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # 1. Return Button
                if return_rect.collidepoint(event.pos):
                    return
                # NEW IMPORT DOOR
                if import_rect.collidepoint(event.pos):
                    run_paste_pgn_screen()
                    # We must refresh the Librarian when we get back so the new game shows up!
                    games = get_saved_games_data()
                    total_content_height = len(games) * card_height
                    max_scroll = max(0, total_content_height - window_pane_height + 20)

                # 2. Check game buttons IF click is inside the window pane
                if clip_rect.collidepoint(event.pos):
                    for i, game in enumerate(games):
                        # Calculate exact hitbox based on current scroll
                        y = start_y + (i * card_height) - scroll_y
                        main_rect = pygame.Rect(50, y, SCREEN_WIDTH - 100, 75)

                        show_rect = pygame.Rect(main_rect.right - 260, y + 17, 70, 40)
                        copy_rect = pygame.Rect(main_rect.right - 170, y + 17, 70, 40)
                        delete_rect = pygame.Rect(main_rect.right - 80, y + 17, 70, 40)

                        if show_rect.collidepoint(event.pos):
                            run_replay_screen(game['pgn'])
                        elif copy_rect.collidepoint(event.pos):
                            pygame.scrap.init()
                            pygame.scrap.put(pygame.SCRAP_TEXT, game['pgn'].encode('utf-8'))
                            print(f"Copied {game['filename']} to clipboard!")

                        elif delete_rect.collidepoint(event.pos):

                            # 1. Safely delete the file
                            filepath = os.path.join(DIRECTORY_OF_SAVED_GAMES, game['filename'])
                            if os.path.exists(filepath):
                                os.remove(filepath)
                                print(f"Deleted {game['filename']}")

                            # 2. Tell the Librarian to refresh the list!
                            games = get_saved_games_data()

                            # 3. Recalculate the floor (in case deleting a game made the list shorter)
                            total_content_height = len(games) * card_height
                            max_scroll = max(0, total_content_height - window_pane_height + 20)

                            # 4. Snap the elevator back up if we were at the very bottom
                            scroll_y = min(scroll_y, max_scroll)

        draw_saved_games_page(SCREEN, games, scroll_y, return_rect,import_rect)
        pygame.display.flip()
        pygame_clock.tick(FPS)

def run_settings_screen():
    global SCREEN
    """The Settings Room. You stay here until you click Return to Menu."""
    pygame_clock = pygame.time.Clock()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:

                # Check all the dynamic buttons in one simple loop!
                for i, rect in enumerate(SETTINGS_RECTS):
                    if rect.collidepoint(event.pos):
                        btn_name = SETTINGS_OPTIONS[i][0]
                        if btn_name == "Saved Games":
                            run_saved_games_screen()
                        elif btn_name == "General Settings":
                            run_general_settings_screen()
                        else:
                            print(f"TODO: Open menu for {btn_name}")

                # Check the Return button
                if RETURN_BTN_RECT.collidepoint(event.pos):
                    return  # Break the loop! This teleports us back to the Home Screen.

        draw_settings_page(SCREEN)
        pygame.display.flip()
        pygame_clock.tick(FPS)

def run_home_screen():
    global SCREEN
    """The Waiting Room. You stay here until you click Start or Quit."""
    pygame_clock = pygame.time.Clock()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "QUIT"

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if START_BTN_RECT.collidepoint(event.pos):
                    return "START"  # Break the loop and return to main!
                elif QUIT_BTN_RECT.collidepoint(event.pos):
                    return "QUIT"
                elif SETTINGS_BTN_RECT.collidepoint(event.pos):
                    run_settings_screen()

        draw_home_page(SCREEN)
        pygame.display.flip()
        pygame_clock.tick(FPS)
# </editor-fold>

# <editor-fold desc="MAIN">

def main():
    global SCREEN, BOARD, IMAGE_CACHE, PLAYERS,NOTATION_FONT

    pygame.init()

    NOTATION_FONT = pygame.font.SysFont("Arial", 14, bold=True)

    SCREEN = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SCALED|pygame.RESIZABLE)
    pygame.display.set_caption("Chess")

    home_screen_action = run_home_screen()
    if home_screen_action == "QUIT":
        pygame.quit()
        sys.exit()

    # clocks

    pygame_clock = pygame.time.Clock()
    BOARD.load_fen(STARTING_POSITION)
    IMAGE_CACHE = {}



    picking_piece: ChessPiece | None = None
    is_dragging = False

    # THE STATE MACHINE TRIGGER
    promotion_pending: Move | None = None
    promotion_rects = []

    # ARROW MEMORY
    drawn_arrows = set()
    highlighted_squares = set()
    right_click_start = None

    game_over_btn_rect = None
    show_notation = False
    is_fullscreen = False
    has_auto_saved = False

    # ==========================================
    # THE CLEANUP CREW
    # ==========================================
    def reset_match():
        nonlocal picking_piece, is_dragging, promotion_pending, game_over_btn_rect, is_paused,has_auto_saved

        # 1. Cure the players and the board
        PLAYERS[ChessColor.WHITE].lost = False
        PLAYERS[ChessColor.BLACK].lost = False
        BOARD.is_draw = False
        BOARD.draw_offered_by = None
        BOARD.is_stalemate = False
        BOARD.load_fen(STARTING_POSITION)

        # 2. Wipe the whiteboards
        drawn_arrows.clear()
        highlighted_squares.clear()

        # 3. Drop any pieces we were holding
        picking_piece = None
        is_dragging = False
        promotion_pending = None
        game_over_btn_rect = None
        is_paused = False

        #only relevent if autosave is true
        has_auto_saved = False

        # 4. Reset the clocks
        for clock in CLOCKS.values():
            clock.reset()
        CLOCKS[BOARD.active_color].start()
        CLOCKS[OTHER_COLOR[BOARD.active_color]].stop()

    CLOCKS[BOARD.active_color].start()

    is_paused = False
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT:
                    BOARD.undo_move()
                    # Cancel any active UI states so the board doesn't glitch
                    picking_piece = None
                    is_dragging = False
                    promotion_pending = None
                    drawn_arrows.clear()
                    highlighted_squares.clear()

                # --- FULLSCREEN TOGGLE ---
                elif event.key == pygame.K_F11:
                    is_fullscreen = not is_fullscreen
                    if is_fullscreen:
                        # Turn on Fullscreen AND the Projector
                        SCREEN = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT),
                                                         pygame.FULLSCREEN | pygame.SCALED)
                    else:
                        # Go back to Windowed Mode with the Projector
                        SCREEN = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SCALED)

            # ==========================================
            # THE PICK UP (Mouse Down)
            # ==========================================
            if event.type == pygame.MOUSEBUTTONDOWN:

                # --- LEFT CLICK (Normal Play) ---
                if event.button == 1:

                    # 1. UI BUTTON INTERCEPTS (Menu area)
                    if UNDO_BTN_RECT.collidepoint(event.pos):
                        BOARD.undo_move()
                        drawn_arrows.clear()
                        highlighted_squares.clear()
                        picking_piece = None
                        is_dragging = False
                        promotion_pending = None
                        continue

                    if NOTATION_BTN_RECT.collidepoint(event.pos):
                        show_notation = not show_notation
                        continue

                        # --- NEW: SIDEBAR SAVE BUTTON ---
                    if SAVE_BTN_RECT.collidepoint(event.pos):
                        create_new_chess_file(BOARD)
                        continue

                        # --- FLAG (RESIGN) BUTTONS ---
                    if W_FLAG_BTN_RECT.collidepoint(event.pos):
                        PLAYERS[ChessColor.WHITE].lost = True
                        continue

                    if B_FLAG_BTN_RECT.collidepoint(event.pos):
                        PLAYERS[ChessColor.BLACK].lost = True
                        continue

                    if PAUSE_BTN_RECT.collidepoint(event.pos):
                        is_paused = not is_paused
                        if is_paused:
                            CLOCKS[BOARD.active_color].stop()
                        else:
                            CLOCKS[BOARD.active_color].start()
                        continue

                    if B_DRAW_BTN_RECT.collidepoint(event.pos):
                        if BOARD.draw_offered_by == ChessColor.WHITE:
                            BOARD.is_draw = True  # White already offered. Black accepts!
                        else:
                            BOARD.draw_offered_by = ChessColor.BLACK  # Black offers
                            print("black offered")
                        continue

                    if W_DRAW_BTN_RECT.collidepoint(event.pos):
                        if BOARD.draw_offered_by == ChessColor.BLACK:
                            BOARD.is_draw = True  # Black already offered. White accepts!
                        else:
                            BOARD.draw_offered_by = ChessColor.WHITE  # White offers
                        continue

                    if RESET_BTN_RECT.collidepoint(event.pos):
                        reset_match()
                        continue

                    if MENU_BTN_RECT.collidepoint(event.pos):
                        # 1. Stop the clocks!
                        CLOCKS[BOARD.active_color].stop()

                        # 2. Open the Main Menu room
                        action = run_home_screen()

                        # 3. Did they quit, or hit Start?
                        if action == "QUIT":
                            running = False
                        elif action == "START":
                            reset_match()  # Clean the board for the new game!
                        continue

                    # If the click made it here, they are interacting with the board.
                    drawn_arrows.clear()
                    highlighted_squares.clear()

                    # THE PAUSE BOUNCER
                    # If the game is paused, trash the click right here.
                    if is_paused:
                        continue

                    # 2. IS THE GAME OVER? THE GLASS CASE BOUNCER
                    if game_over_btn_rect is not None:
                        if game_over_btn_rect.collidepoint(event.pos):
                            reset_match()
                            continue  # DO NOT LET THEM CLICK THE BOARD



                    #3 - PROMOTION - DID IT PROMOTE??
                    if promotion_pending is not None:
                        for rect, piece_type in promotion_rects:
                            if rect.collidepoint(event.pos):
                                promotion_pending.promotion_choice = piece_type
                                BOARD.execute_move(promotion_pending)
                                promotion_pending = None
                                picking_piece = None
                                is_dragging = False
                                break
                        continue


                    clicked = pixel_to_squarepos(event.pos)
                    if clicked is None: continue

                    clicked_piece = BOARD.get_piece_at(clicked)

                    # 1. Grab a piece to drag
                    if clicked_piece is not None and clicked_piece.color == BOARD.active_color:
                        picking_piece = clicked_piece
                        is_dragging = True

                    # 2. Hybrid Click-to-Move (if they clicked an empty square or enemy without dragging)
                    elif picking_piece is not None:
                        if picking_piece.is_valid_move(clicked):
                            move = picking_piece.legal_moves[clicked]
                            if move.move_type == MoveType.PROMOTION:
                                promotion_pending = move
                            else:
                                BOARD.execute_move(move)
                                picking_piece = None


                # --- RIGHT CLICK (Start Arrow) ---
                elif event.button == 3:
                    right_click_start = pixel_to_squarepos(event.pos)

            # ==========================================
            # THE DROP (Mouse Up)
            # ==========================================
            elif event.type == pygame.MOUSEBUTTONUP:

                # --- LEFT CLICK (Drop Piece) ---
                if event.button == 1:
                    if is_dragging and picking_piece is not None:
                        is_dragging = False
                        drop_pos = pixel_to_squarepos(event.pos)

                        # If they dropped it on a new square
                        if drop_pos is not None and drop_pos != picking_piece.position:
                            dropped_on_piece = BOARD.get_piece_at(drop_pos)

                            # Normal Drag Move Check
                            if picking_piece.is_valid_move(drop_pos):
                                move = picking_piece.legal_moves[drop_pos]
                                if move.move_type == MoveType.PROMOTION:
                                    promotion_pending = move
                                else:
                                    BOARD.execute_move(move)
                                    picking_piece = None
                            else:
                                picking_piece = None  # that's how I want it to be

                # --- RIGHT CLICK (Finish Arrow) ---
                elif event.button == 3:
                    if right_click_start is not None:
                        right_click_end = pixel_to_squarepos(event.pos)

                        if right_click_end is not None:
                            # DID THEY DRAG?
                            if right_click_start != right_click_end:
                                arrow_tuple = (right_click_start, right_click_end)
                                if arrow_tuple in drawn_arrows:
                                    drawn_arrows.remove(arrow_tuple)
                                else:
                                    drawn_arrows.add(arrow_tuple)
                            # NO DRAG, JUST A CLICK!
                            else:
                                if right_click_start in highlighted_squares:
                                    highlighted_squares.remove(right_click_start)  # Turn off
                                else:
                                    highlighted_squares.add(right_click_start)  # Turn on

                        right_click_start = None

        if not is_paused:
            CLOCKS[BOARD.active_color].tick()
            if not CLOCKS[BOARD.active_color]:
                PLAYERS[BOARD.active_color].lost = True

        # --- DRAWING PHASE ---
        SCREEN.fill((0, 0, 0))
        draw_board(SCREEN,show_notation)

        draw_side_menu(SCREEN, show_notation,is_paused)

        # Draw all pieces EXCEPT the one being dragged
        dragged_piece = picking_piece if is_dragging else None
        draw_pieces(SCREEN, BOARD, IMAGE_CACHE, dragged_piece)

        # Draw the "Ghost Piece" directly on the mouse cursor
        if is_dragging and picking_piece is not None:
            img = get_piece_image(picking_piece, IMAGE_CACHE)
            mouse_x, mouse_y = pygame.mouse.get_pos()
            rect = img.get_rect(center=(mouse_x, mouse_y))
            SCREEN.blit(img, rect)

        # Draw the highlights that a piece needs.
        if picking_piece is not None:
            highlight_square(SCREEN, picking_piece.position, PICKING_PIECE_HIGHLIGHT_COLOR)
            for legal_pos in picking_piece.legal_moves.keys():
                highlight_square(SCREEN, legal_pos, LEGAL_MOVES_HIGHLIGHT_COLOR, thickness=5)

        for square in highlighted_squares:
            # Color: Red, Alpha: 100 (transparent), Thickness: 0 (filled square)
            highlight_square(SCREEN, square, (200, 50, 50), alpha=100, thickness=0)

        # Draw the Arrows
        for start_pos, end_pos in drawn_arrows:
            draw_arrow(SCREEN, start_pos, end_pos, (255, 170, 0))  # Orange arrows

        # Draw the Menu OVER everything if we are frozen
        if promotion_pending is not None:
            color = BOARD.active_color
            promotion_rects = draw_promotion_menu(SCREEN, color, IMAGE_CACHE)

        # --- THE CHECKMATE SCREEN ---


        winner = None
        if PLAYERS[ChessColor.WHITE].lost:
            winner = ChessColor.BLACK
        elif PLAYERS[ChessColor.BLACK].lost:
            winner = ChessColor.WHITE

        if winner is not None or BOARD.is_draw:
            game_over_btn_rect = draw_game_over_screen(SCREEN, winner,BOARD.is_draw)
            if AUTO_SAVE and not has_auto_saved:
                create_new_chess_file(BOARD)
                has_auto_saved = True
                print("Auto-saved game successfully.")

            for clock in CLOCKS.values():
                clock.stop()
        else:
            game_over_btn_rect = None

        pygame.display.flip()
        pygame_clock.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
# </editor-fold>

