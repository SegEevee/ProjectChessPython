import pygame
from pygame import mixer as dj
import sys
import math
import os
import json
import re
import random
import time
import socket
import importlib.util
from network.network import Network
from enum import Enum
from technical_audio import music_manager
from side_scripts import opening_books as openings
from side_scripts import python_glue as bot
from engines.stockfish import stockfishpy as stockfish
from side_scripts import book_generator
from side_scripts import bot_factory

#<editor-fold desc="FILES AND PREFERENCES">
def get_asset_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # If not running as exe, use the normal folder
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

def get_permanent_path():
    """ Finds the exact permanent folder where the game lives (The Red Box). """
    if getattr(sys, 'frozen', False):
        # I am running as a built PyInstaller .exe
        return os.path.dirname(sys.executable)
    else:
        # I am running as a normal .py script in VS Code
        return os.path.abspath(os.path.dirname(__file__))

def get_audio_path(sound_name):
    """
    The Radio Station: Instead of a fixed list, build the path
    based on whatever 'sound_pack' is in the preferences right now.
    """
    pack = PREFERENCES.get("sound_pack", "Default")

    # Music files are .mp3, everything else (SFX) is .wav
    extension = ".mp3" if "music" in sound_name else ".wav"

    # We build the string: assets/sounds/[PackName]/[SoundName].wav
    relative_path = os.path.join("assets", "sounds", pack, f"{sound_name}{extension}")

    # Finally, anchor it to the permanent root so the EXE can find it
    return get_asset_path(relative_path)

# THE IRON ANCHOR
PERMANENT_ROOT = get_permanent_path()

# FOR WRITING (Where the actual files go when you save, anchored permanently)
DIRECTORY_OF_SAVED_GAMES = os.path.join(PERMANENT_ROOT, "saved_games")
DIRECTORY_OF_GENERAL_SETTINGS = os.path.join(PERMANENT_ROOT, "settings_data")


PREFERENCES_FILE = os.path.join(DIRECTORY_OF_GENERAL_SETTINGS, "preferences.json")
DIRECTORY_OF_BOTS = os.path.join(PERMANENT_ROOT, "bots")

LOADED_BOTS = {}

# The Master Clipboard (Default Values)
PREFERENCES = {
    "game_counter": 1,
    "auto_save": True,
    "starting_time": 5 * 60,
    "game_mode": "Multiplayer",
    "player_color": "White",
    "bot_id": "toddler",
    "bot_thinking_time": 0.3,
    "fps": 60,
    "animation_time": 0.2,
    "master_mute": False,
    "music_mute": False,
    "sfx_mute": False,
    "volume": 0.5,
    "sound_pack": "Default",
    "quick_start_bot": False
}

DEPTH_NAMES = {
    1 : "Loser (1)",
    -1 : "Alperon (??)",
    3 : "Beginner (3)",
    4 : "Average (4)",
    5 : "Above Avg (5)",
    6 : "Best I have (6)",
    9999 : "Good Luck"
}



#</editor-fold>

# <editor-fold desc="CONFIG">

# --- Find your CONFIG section and update the heights ---
BOARD_SIZE = 8
SQUARE_SIZE = 80
WINDOW_SIZE = BOARD_SIZE * SQUARE_SIZE

# The Balanced Layout
SIDE_PANEL_WIDTH = 220
BOTTOM_PANEL_HEIGHT = 120

SCREEN_WIDTH = (SIDE_PANEL_WIDTH * 2) + WINDOW_SIZE
SCREEN_HEIGHT = WINDOW_SIZE + BOTTOM_PANEL_HEIGHT # Expands the window downwards

# The crucial shift for all board math
BOARD_X_OFFSET = SIDE_PANEL_WIDTH

FPS = 60
DT = 1/FPS
STARTING_TIME = 5 * 60 # 5 mins

STARTING_POSITION = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

LIGHT = (240, 217, 181)
DARK = (181, 136, 99)
PICKING_PIECE_HIGHLIGHT_COLOR = (0, 255, 255)
LEGAL_MOVES_HIGHLIGHT_COLOR = (67, 67, 67)
RIGHT_CLICK_HIGHLIGHT_SQUARE_COLOR = (210, 43, 43)

#<editor-fold desc="AI ELEMENTS"
AGREED_GET_BEST_MOVE_THRESHOLD = 0.2
BOT_THINKING_TIME = 0.5
BOT_SEARCH_DEPTH = 6
#</editor-fold>

#<editor-fold desc="UI ELEMENTS">

#<editor-fold desc="SETTINGS MENU CONFIG">
# To add a new button, literally just type its name in this list!
SETTINGS_OPTIONS = [
    ("General Settings", (100, 100, 100), (130, 130, 130)), # Grey
    ("Saved Games", (40, 160, 160), (60, 200, 200)),   # Aqua
    ("Audio & Music", (180, 60, 60), (220, 80, 80)),  # Red
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
GENERAL_SETTINGS_OPTIONS = ["Auto Save", "Time Control", "Game Mode", "Player Color", "Bot Setup","Forge Bot"]
GENERAL_SETTINGS_RECTS = []

# ELI5: We have 6 blocks. We want them in 2 columns.
for i in range(len(GENERAL_SETTINGS_OPTIONS)):
    col = i % 2
    row = i // 2
    x_position = (SCREEN_WIDTH // 2) - 310 + (col * 320)
    y_position = 250 + (row * 80)
    rect = pygame.Rect(x_position, y_position, 300, 60)
    GENERAL_SETTINGS_RECTS.append(rect)
# </editor-fold>
#</editor-fold>

#<editor-fold desc="VIDEO SETTINGS">


#<editor-fold desc="VIDEO SETTINGS UI">

VIDEO_SETTINGS_OPTIONS = ["FPS", "Animation Time"]
VIDEO_SETTINGS_RECTS = []

for i in range(len(VIDEO_SETTINGS_OPTIONS)):
    col = i % 2
    row = i // 2
    x_position = (SCREEN_WIDTH // 2) - 310 + (col * 320)
    y_position = 250 + (row * 80)
    rect = pygame.Rect(x_position, y_position, 300, 60)
    VIDEO_SETTINGS_RECTS.append(rect)

#</editor-fold>
#</editor-fold>

#<editor-fold desc="AUDIO">

MUSIC_MANAGER : music_manager.MusicManager | None = None

#<editor-fold desc="AUDIO PACKS">

DEFAULT_AUDIO_PACK = {
    # --- MUSIC ---
    "menu_music": get_asset_path("assets/sounds/sfx_packs/default/menu_music.mp3"),
    "board_music": get_asset_path("assets/sounds/board_music_packs/default_pack/Claculated_Calm.mp3"),

    # --- SOUND EFFECTS (SFX) ---
    "move": get_asset_path("assets/sounds/sfx_packs/default/move.wav"),
    "capture": get_asset_path("assets/sounds/sfx_packs/default/capture.wav"),
    "promote": get_asset_path("assets/sounds/sfx_packs/default/promote.wav"),
    "castle": get_asset_path("assets/sounds/sfx_packs/default/castle.wav"),
    "check": get_asset_path("assets/sounds/sfx_packs/default/check.wav"),
    "checkmate": get_asset_path("assets/sounds/sfx_packs/default/checkmate.wav")
}

#</editor-fold>
CURRENT_AUDIO_PATHS = DEFAULT_AUDIO_PACK #I will add it this way

# I will also create a cache to hold the loaded sounds so I don't load them every click
AUDIO_CACHE = {}
CURRENT_MUSIC = None
LAST_REQUESTED_MUSIC = "menu_music"
SFX_VOLUME_ADJUSTMENT = 2.0 #so the sfx will actually be heard in the game

# <editor-fold desc="DJ AUDIO MANAGERS">

def load_sfx(name):
    if name not in AUDIO_CACHE:
        try:
            AUDIO_CACHE[name] = dj.Sound(CURRENT_AUDIO_PATHS[name])
        except Exception as e:
            print(f"Missing technical_audio file: {CURRENT_AUDIO_PATHS[name]}")
            AUDIO_CACHE[name] = None
    return AUDIO_CACHE[name]


def play_sfx(name):
    # The Bouncer: Stop if muted!
    if PREFERENCES["master_mute"] or PREFERENCES["sfx_mute"]:
        return

    sound = load_sfx(name)
    if sound:
        sound.set_volume(PREFERENCES["volume"] * SFX_VOLUME_ADJUSTMENT)
        sound.play()

def play_music(name):
    global CURRENT_MUSIC, LAST_REQUESTED_MUSIC

    # 1. Write the requested song on the sticky note BEFORE checking mutes
    LAST_REQUESTED_MUSIC = name

    # 2. The Bouncer: Stop music if muted
    if PREFERENCES["master_mute"] or PREFERENCES["music_mute"]:
        dj.music.stop()
        CURRENT_MUSIC = None
        return

    # 3. Don't restart the song if it's already playing! Just update the volume.
    if CURRENT_MUSIC == name:
        dj.music.set_volume(PREFERENCES["volume"])
        return

    try:
        dj.music.load(CURRENT_AUDIO_PATHS[name])
        dj.music.set_volume(PREFERENCES["volume"])
        dj.music.play(-1)  # -1 means loop forever
        CURRENT_MUSIC = name
        print(f"done playing music {name}")
    except Exception as e:
        print(f"Could not play music {name}: {e}")
        CURRENT_MUSIC = None

def update_audio_volume():
    """Called instantly when sliding the volume bar so you can hear it change."""
    dj.music.set_volume(PREFERENCES["volume"])

# <editor-fold desc="GLOBAL MEDIA PLAYER LOGIC">
MINI_PLAYER_UI_STATE = {
    "is_dragging": False,
    "drag_percent": 0.0
}

def update_media_player():
    """The Auto-DJ: Put this in ANY game loop to keep the playlist moving."""
    if MUSIC_MANAGER and MUSIC_MANAGER.current_playlist and MUSIC_MANAGER.finished_song():
        MUSIC_MANAGER.next_track()

def handle_media_player_event(event):
    """
    The Universal Music Bouncer: Give it a Pygame event.
    Returns True if the media player ate the event, False if it didn't.
    """
    global MINI_PLAYER_UI_STATE

    # 1. If the radio is off or hidden, we don't care about these clicks.
    if not MUSIC_MANAGER or MUSIC_MANAGER.state == music_manager.MediaPlayerState.OUTSIDE:
        return MenuSignal.FAIL

    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        if MINI_PREV_BTN.collidepoint(event.pos):
            MUSIC_MANAGER.prev_track()
            add_alert("Skipped to Previous")
            return MenuSignal.PASS

        if MINI_NEXT_BTN.collidepoint(event.pos):
            MUSIC_MANAGER.next_track()
            add_alert("Skipped to Next")
            return MenuSignal.PASS

        if MINI_SHUFFLE_BTN.collidepoint(event.pos):
            if not MUSIC_MANAGER.is_playlist_empty():
                MUSIC_MANAGER.shuffle_playlist()
                print("DJ shuffled the playlist!")
                add_alert("Playlist Shuffled!")
            return MenuSignal.PASS

        if MINI_PLAY_BTN.collidepoint(event.pos):
            if MUSIC_MANAGER.state == music_manager.MediaPlayerState.PLAYING:
                MUSIC_MANAGER.pause_music()
                add_alert("Music Paused")
            else:
                MUSIC_MANAGER.unpause_music()
                add_alert("Music Resumed")
            return MenuSignal.PASS
        if ADD_SONGS_BTN.collidepoint(event.pos):
            return MenuSignal.OPEN_PLAYLIST
        if MINI_PROGRESS_BAR.collidepoint(event.pos):
            MINI_PLAYER_UI_STATE["is_dragging"] = True
            relative_x = event.pos[0] - MINI_PROGRESS_BAR.x
            MINI_PLAYER_UI_STATE["drag_percent"] = max(0.0, min(1.0, relative_x / MINI_PROGRESS_BAR.width))
            return MenuSignal.PASS

    elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
        if MINI_PLAYER_UI_STATE["is_dragging"]:
            MINI_PLAYER_UI_STATE["is_dragging"] = False

            current_track = MUSIC_MANAGER.get_current_track()
            if current_track:
                target_time = current_track.length * MINI_PLAYER_UI_STATE["drag_percent"]

                MUSIC_MANAGER.set_timestamp_seconds(target_time)

            return MenuSignal.PASS

    elif event.type == pygame.MOUSEMOTION:
        if MINI_PLAYER_UI_STATE["is_dragging"]:
            relative_x = event.pos[0] - MINI_PROGRESS_BAR.x
            MINI_PLAYER_UI_STATE["drag_percent"] = max(0.0, min(1.0, relative_x / MINI_PROGRESS_BAR.width))
            return MenuSignal.PASS

    return MenuSignal.PASS # The event had nothing to do with the media player
# </editor-fold>



# </editor-fold>

# <editor-fold desc="AUDIO SETTINGS UI">

AUDIO_SETTINGS_OPTIONS = ["Master Playing", "Music Playing", "SFX Playing", "Sound Pack"]
AUDIO_SETTINGS_RECTS = []

# Left column (Mutes)
for i in range(3):
    x_pos = (SCREEN_WIDTH // 2) - 310
    y_pos = 250 + (i * 80)
    AUDIO_SETTINGS_RECTS.append(pygame.Rect(x_pos, y_pos, 300, 60))

# Right column (Sound Pack Button)
pack_rect = pygame.Rect((SCREEN_WIDTH // 2) + 10, 250, 300, 60)
AUDIO_SETTINGS_RECTS.append(pack_rect)

# Right column (Volume Slider Track)
VOLUME_TRACK_RECT = pygame.Rect((SCREEN_WIDTH // 2) + 10, 330, 300, 60)

# </editor-fold>

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
RIGHT_MENU_X = BOARD_X_OFFSET + WINDOW_SIZE

REPLAY_NEXT_BTN = pygame.Rect(RIGHT_MENU_X + 35, 100, 150, 60)
REPLAY_PREV_BTN = pygame.Rect(RIGHT_MENU_X + 35, 180, 150, 60)
REPLAY_RESET_BTN = pygame.Rect(RIGHT_MENU_X + 35, 260, 150, 40)
REPLAY_NOTATION_BTN = pygame.Rect(RIGHT_MENU_X + 35, 320, 150, 40)
REPLAY_MENU_BTN = pygame.Rect(RIGHT_MENU_X + 35, SCREEN_HEIGHT - 100, 150, 60)

#</editor-fold>

# <editor-fold desc="MAIN GAME UI">
RIGHT_MENU_X = BOARD_X_OFFSET + WINDOW_SIZE

PAUSE_BTN_RECT = pygame.Rect(RIGHT_MENU_X + 35, 175, 150, 40)
UNDO_BTN_RECT = pygame.Rect(RIGHT_MENU_X + 35, PAUSE_BTN_RECT.bottom + 10, 150, 40)
RESET_BTN_RECT = pygame.Rect(RIGHT_MENU_X + 35, UNDO_BTN_RECT.bottom + 10, 150, 40)
MENU_BTN_RECT = pygame.Rect(RIGHT_MENU_X + 35, RESET_BTN_RECT.bottom + 10, 150, 40)
NOTATION_BTN_RECT = pygame.Rect(RIGHT_MENU_X + 35, MENU_BTN_RECT.bottom + 10, 150, 40)
FLIP_BTN_RECT = pygame.Rect(RIGHT_MENU_X + 35, NOTATION_BTN_RECT.bottom + 10, 150, 40)
SAVE_BTN_RECT = pygame.Rect(RIGHT_MENU_X + 35, FLIP_BTN_RECT.bottom + 10, 150, 40)

# --- CLOCK RECTS ---
# We anchor to WINDOW_SIZE now! They will not sink when the screen gets taller.
TOP_CLOCK_RECT = pygame.Rect(RIGHT_MENU_X + 25, 20, 110, 60)
BOTTOM_CLOCK_RECT = pygame.Rect(RIGHT_MENU_X + 25, WINDOW_SIZE - 80, 110, 60)

TOP_FLAG_BTN_RECT = pygame.Rect(RIGHT_MENU_X + 145, 30, 40, 40)
BOTTOM_FLAG_BTN_RECT = pygame.Rect(RIGHT_MENU_X + 145, WINDOW_SIZE - 70, 40, 40)

TOP_DRAW_BTN_RECT = pygame.Rect(RIGHT_MENU_X + 145, 80, 40, 40)
BOTTOM_DRAW_BTN_RECT = pygame.Rect(RIGHT_MENU_X + 145, WINDOW_SIZE - 120, 40, 40)


# --- MEDIA MANAGER RECTS (The Basement) ---
BOTTOM_PANEL_BG = pygame.Rect(BOARD_X_OFFSET, WINDOW_SIZE, WINDOW_SIZE, BOTTOM_PANEL_HEIGHT)

# Left Side (The dead button)
ADD_SONGS_BTN = pygame.Rect(BOTTOM_PANEL_BG.x + 20, BOTTOM_PANEL_BG.y + 75, 120, 30)

# Center Math (The controls)
center_x = BOTTOM_PANEL_BG.x + (WINDOW_SIZE // 2)
MINI_PREV_BTN = pygame.Rect(center_x - 70, BOTTOM_PANEL_BG.y + 20, 40, 40)
MINI_PLAY_BTN = pygame.Rect(center_x - 20, BOTTOM_PANEL_BG.y + 20, 40, 40)
MINI_NEXT_BTN = pygame.Rect(center_x + 30, BOTTOM_PANEL_BG.y + 20, 40, 40)
MINI_SHUFFLE_BTN = pygame.Rect(center_x + 80, BOTTOM_PANEL_BG.y + 20, 40, 40)

# Slider anchored under the buttons
MINI_PROGRESS_BAR = pygame.Rect(center_x - 150, BOTTOM_PANEL_BG.y + 80, 300, 15)


# --- FORGE UI ---
FORGE_SAVE_BTN_RECT = pygame.Rect(RIGHT_MENU_X + 35, 100, 150, 60)
FORGE_TOGGLE_BTN_RECT = pygame.Rect(RIGHT_MENU_X + 35, 180, 150, 40)
FORGE_MENU_BTN_RECT = pygame.Rect(RIGHT_MENU_X + 35, SCREEN_HEIGHT - 100, 150, 60)

FORGE_SAVE_MODE = "Both"


# </editor-fold>


#</editor-fold>

# <editor-fold desc="HELPERS (notation / coordinates)">

#<editor-fold desc="ALERTS">

MAX_ALERTS = 4
ALERT_TIME = 3.5

def add_alert(message: str):
    """Drops a new message onto the conveyor belt."""
    global ACTIVE_ALERTS
    ACTIVE_ALERTS.append({"text": message, "time_left": ALERT_TIME})

    # If the box gets too full, instantly kick out the oldest message
    if len(ACTIVE_ALERTS) > MAX_ALERTS:
        ACTIVE_ALERTS.pop(0)

#</editor-fold>




def get_visual_row_col(row, col):
    """The Magic Mirror: Flips the coordinates only for the camera."""
    global BOARD_FLIPPED
    if BOARD_FLIPPED:
        return 7 - row, 7 - col
    return row, col

def notation_to_row_col(pos: str):
    pos = pos.strip().lower()
    col = ord(pos[0]) - ord('a')
    row = 8 - int(pos[1])
    return row, col


def row_col_to_notation(row: int, col: int):
    return chr(ord('a') + col) + str(8 - row)


def pixel_to_squarepos(mouse_pos):
    global BOARD_FLIPPED
    x, y = mouse_pos
    col = (x - BOARD_X_OFFSET) // SQUARE_SIZE
    row = y // SQUARE_SIZE

    if BOARD_FLIPPED:
        col = 7 - col
        row = 7 - row

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
    # --- THE FIX: Don't trust the PREFERENCES counter, find the real hole! ---
    number_of_game = get_next_available_game_number()

    pgn = generate_pgn(board.move_log)
    filename = f"game_{number_of_game}.txt"
    create_file(filename, pgn)

    # Sync the master counter just in case
    PREFERENCES["game_counter"] = get_next_available_game_number()
    save_preferences()


def pgn_to_move_list(pgn_string: str) -> list[str]:
    """Cleans the PGN and strictly filters for things that actually look like moves."""
    # 1. Scrap the headers, comments, and results
    text = re.sub(r'\[.*?\]', '', pgn_string, flags=re.DOTALL)
    text = re.sub(r'\{.*?\}', '', text, flags=re.DOTALL)
    text = re.sub(r'(1-0|0-1|1/2-1/2|\*)', '', text)

    tokens = text.split()
    moves = []

    for t in tokens:
        # Strip move numbers (1. or 24...)
        clean_token = re.sub(r'^\d+\.*', '', t)

        if clean_token and len(clean_token) < 10 and '/' not in clean_token:
            moves.append(clean_token)

        # Exception: Castling
        elif clean_token in ("O-O", "O-O-O"):
            moves.append(clean_token)
    print(moves)
    return moves


def get_move_from_san(board, san_string: str):
    """The Reverse SAN Trick: Finds the move object that produces this exact string."""
    # 1. Strip the Red Pen marks (+ and #)
    clean_san = san_string.replace("+", "").replace("#", "")

    # --- THE MENTOR FIX: Intercept the Promotion! ---
    # If the string has an '=', it means a piece was promoted.
    promotion_type_str = None
    if "=" in clean_san:
        parts = clean_san.split("=")
        clean_san = parts[0]  # This gives us just the base move (e.g., 'e8' or 'exd8')
        promotion_type_str = parts[1]  # This gives us the chosen piece (e.g., 'Q' or 'N')

    # Check every legal move for the current player
    for piece in board.get_all_pieces():
        if piece.color == board.active_color:
            for target_pos, move in piece.legal_moves.items():
                victim = board.get_piece_at(move.victim_pos) if move.victim_pos else None

                # Generate the SAN for this hypothetical move.
                # Because legal moves start with promotion_choice = None, this generates the base SAN ('e8')
                test_san = board.get_algebraic_notation(move, piece, victim)

                # If the base moves match (e.g., 'e8' == 'e8'), we found it!
                if test_san == clean_san:

                    # If we intercepted an '=', we MUST assign that choice to the move object
                    # before we hand it back, otherwise execute_move() will choke.
                    if promotion_type_str and move.move_type == MoveType.PROMOTION:
                        for piece_type in ChessPieceType:
                            if piece_type.value == promotion_type_str:
                                move.promotion_choice = piece_type
                                break

                    return move

    return None

#</editor-fold>

#<editor-fold desc="FILE HANDLING">

def load_all_bots():
    """Reads all JSON bot ID cards and loads their Python brains into memory ONCE."""
    global LOADED_BOTS
    LOADED_BOTS.clear()

    if not os.path.exists(DIRECTORY_OF_BOTS):
        os.makedirs(DIRECTORY_OF_BOTS)

        default_bot = {
            "name": "Toddler (Random)",
            "type": "script",
            "script_file": "toddler.py",
            "function_name": "get_random_bot_move"
        }
        with open(os.path.join(DIRECTORY_OF_BOTS, "toddler.json"), "w") as f:
            json.dump(default_bot, f, indent=4)

        # The toddler gets the Care Package receiver too!
        toddler_code = "import random\nMove=None; MoveType=None; ChessPieceType=None; SquarePosition=None; Board=None; ChessColor=None\n\ndef init_bot(m, mt, cpt, sp, b, cc):\n    global Move, MoveType, ChessPieceType, SquarePosition, Board, ChessColor\n    Move=m; MoveType=mt; ChessPieceType=cpt; SquarePosition=sp; Board=b; ChessColor=cc\n\ndef get_random_bot_move(board, ai_color):\n    moves = []\n    for p in board.get_all_pieces():\n        if p.color == ai_color:\n            moves.extend(p.legal_moves.values())\n    return random.choice(moves) if moves else None\n"
        with open(os.path.join(DIRECTORY_OF_BOTS, "toddler.py"), "w") as f:
            f.write(toddler_code)

    # Now read whatever is in the folder
    for filename in os.listdir(DIRECTORY_OF_BOTS):
        if filename.endswith(".json"):
            filepath = os.path.join(DIRECTORY_OF_BOTS, filename)
            try:
                with open(filepath, "r") as f:
                    bot_data = json.load(f)
                    bot_id = filename.replace(".json", "")

                    # --- THE MAGIC TRICK ---
                    # Load the Python file into RAM immediately so we don't have to do it mid-game!
                    if bot_data.get("type") == "script":
                        script_name = bot_data.get("script_file")
                        script_path = os.path.join(DIRECTORY_OF_BOTS, script_name)

                        if os.path.exists(script_path):
                            spec = importlib.util.spec_from_file_location(f"bot_module_{bot_id}", script_path)
                            module = importlib.util.module_from_spec(spec)
                            spec.loader.exec_module(module)

                            # Give the bot its Care Package of classes!
                            if hasattr(module, "init_bot"):
                                module.init_bot(Move, MoveType, ChessPieceType, SquarePosition, Board, ChessColor)

                            bot_data["live_module"] = module
                        else:
                            print(f"ERROR: Script {script_path} is missing for {bot_id}!")

                    LOADED_BOTS[bot_id] = bot_data
            except Exception as e:
                print(f"ERROR: Could not read bot file {filename}: {e}")

def load_preferences():
    """Opens the JSON backpack from the PERMANENT folder (The Red Box)."""
    global PREFERENCES

    # 1. We ONLY check the permanent file now!
    if os.path.exists(PREFERENCES_FILE):
        try:
            with open(PREFERENCES_FILE, "r") as file:
                loaded_data = json.load(file)
                print(loaded_data)
                PREFERENCES.update(loaded_data)
                print("updated")
        except json.JSONDecodeError:
            print("Preferences file corrupted. Using defaults.")
            save_preferences()
    else:
        # If it doesn't exist yet, make one in the permanent folder!
        save_preferences()

def save_preferences():
    """Takes our current PREFERENCES dictionary and photocopies it into the PERMANENT JSON file."""
    # 1. RUTHLESS MENTOR FIX: I fixed your copy-paste error here.
    # You were checking if DIRECTORY_OF_SAVED_GAMES existed before saving settings!
    if not os.path.exists(DIRECTORY_OF_GENERAL_SETTINGS):
        os.makedirs(DIRECTORY_OF_GENERAL_SETTINGS)

    # 2. Write directly to the RED BOX file, NOT the read-only bundle!
    with open(PREFERENCES_FILE, "w") as file:
        json.dump(PREFERENCES, file, indent=4)

def get_next_available_game_number():
    """Finds the lowest 'hole' in the PERMANENT saved games numbering."""
    # Look in the RED BOX!
    if not os.path.exists(DIRECTORY_OF_SAVED_GAMES):
        return 1

    existing_numbers = set()
    # Look in the RED BOX!
    for filename in os.listdir(DIRECTORY_OF_SAVED_GAMES):
        if filename.startswith("game_") and filename.endswith(".txt"):
            try:
                number_part = filename.replace("game_", "").replace(".txt", "")
                existing_numbers.add(int(number_part))
            except ValueError:
                continue

    counter = 1
    while counter in existing_numbers:
        counter += 1

    return counter

def get_saved_games_data():
    """Reads the PERMANENT folder and returns all games sorted by number."""
    games = []
    # Look in the RED BOX!
    if not os.path.exists(DIRECTORY_OF_SAVED_GAMES):
        return games

    # Look in the RED BOX!
    for filename in os.listdir(DIRECTORY_OF_SAVED_GAMES):
        if filename.endswith(".txt") and filename.startswith("game_"):
            # IMPORTANT: We must join the path with the RED BOX directory!
            filepath = os.path.join(DIRECTORY_OF_SAVED_GAMES, filename)
            pgn = get_file_content(filepath).strip()

            tokens = pgn.split()
            last_move = "None"
            if tokens:
                last_move = tokens[-1]

            games.append({"filename": filename, "pgn": pgn, "last_move": last_move})

    games.sort(key=lambda x: int(x["filename"].split("_")[1].split(".")[0]) if "_" in x["filename"] else 0)
    return games

def create_file(file_path: str, initial_text: str = ""):
    """Creates a new text file and writes the initial text. Overwrites if it exists."""
    if not os.path.exists(DIRECTORY_OF_SAVED_GAMES):
        os.makedirs(DIRECTORY_OF_SAVED_GAMES)

    full_path = os.path.join(DIRECTORY_OF_SAVED_GAMES, file_path)

    # "w" means Write (shred the old one, make a new one)
    with open(full_path, "w") as file:
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
    """Saves a pasted PGN using the Preferences clipboard."""
    number_of_game = PREFERENCES["game_counter"]
    filename = f"game_{number_of_game}.txt"

    # Format the PGN nicely
    san_list = pgn_to_move_list(pgn_string)
    formatted_pgn = []
    for i, san in enumerate(san_list):
        if i % 2 == 0:
            turn_number = (i // 2) + 1
            formatted_pgn.append(f"{turn_number}. {san}")
        else:
            formatted_pgn.append(san)

    final_string = " ".join(formatted_pgn)

    # Save the file and update the master counter
    create_file(filename, final_string)

    PREFERENCES["game_counter"] += 1
    save_preferences()

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
        return f"{int(self.remaining / 60):02d}:{int(self.remaining % 60):02d}"

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

            # --- THE FIX: Protect Castling from the Time Machine ---
            # can_castle() already rigorously checks the real chess rules.
            # If we let the Time Machine simulate it, it moves the King to the Rook's square,
            # which incorrectly bans castling if the Rook is under attack!
            if move.move_type == MoveType.CASTLE:
                safe_moves[pos] = move

            # For all normal moves, use the robotic arm to check for safety
            elif board.is_move_safe(self, move):
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
                    # 1. Create the single mechanical engine move.
                    # We leave 'to_pos' as the Rook so execute_move() can easily find it.
                    castle_move = Move(
                        from_pos=self.position,
                        to_pos=friend.position,
                        move_type=MoveType.CASTLE
                    )

                    # 2. GUI Hitbox A: Allow the player to click/drop on the Rook
                    self.legal_moves[friend.position] = castle_move

                    # 3. GUI Hitbox B: Allow the player to click/drop on the King's final destination
                    direction = 1 if friend.position.col > self.position.col else -1
                    king_new_col = self.position.col + (2 * direction)
                    king_target_pos = SquarePosition(row=self.position.row, col=king_new_col)

                    self.legal_moves[king_target_pos] = castle_move

    def is_piece_protected(self, pos, enemy_player):
        return enemy_player.is_controlling_square(pos)

class MoveRecord:
    """A single page in the Diary, holding a photograph of the past."""

    def __init__(self, move: Move, moved_piece, piece_had_moved: bool, victim_piece, clocks, old_en_passant,
                 old_castling_rights, algebraic_notation, old_halfmove_clock, is_imagining=False):
        self.move = move
        self.moved_piece = moved_piece
        self.piece_had_moved = piece_had_moved
        self.victim_piece = victim_piece
        self.current_times = {ChessColor.WHITE: clocks[ChessColor.WHITE].previous_time,
                              ChessColor.BLACK: clocks[ChessColor.BLACK].previous_time}
        self.old_en_passant = old_en_passant
        self.old_castling_rights = old_castling_rights
        self.algebraic_notation = algebraic_notation

        self.old_halfmove_clock = old_halfmove_clock
        self.is_imagining = is_imagining

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

        self.position_counts = {}
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

        core_fen = self.generate_core_fen()
        self.position_counts[core_fen] = 1

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

    def generate_core_fen(self) -> str:
        """The Deja Vu Camera: Takes a photo of the board without the clocks."""
        fen_rows = []
        for row in range(8):
            empty_count = 0
            row_str = ""
            for col in range(8):
                piece = self.grid[row][col]
                if piece is None:
                    empty_count += 1
                else:
                    if empty_count > 0:
                        row_str += str(empty_count)
                        empty_count = 0
                    char = piece.type.value
                    if piece.color == ChessColor.WHITE:
                        char = char.upper()
                    else:
                        char = char.lower()
                    row_str += char
            if empty_count > 0:
                row_str += str(empty_count)
            fen_rows.append(row_str)

        board_part = "/".join(fen_rows)
        active_part = 'w' if self.active_color == ChessColor.WHITE else 'b'
        castling_part = self.castling_rights if self.castling_rights else "-"
        ep_part = self.en_passant.to_notation() if self.en_passant else "-"

        return f"{board_part} {active_part} {castling_part} {ep_part}"

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

            # 2. Since they are in check, refresh their moves to see if they can escape
            for p in enemy_player.pieces:
                p.update_all_legal_moves(self)

            # 3. If they have NO moves left while in check, it's Game Over
            if not enemy_player.has_legal_moves():
                enemy_player.lost = True
            else:
                enemy_player.lost = False  # They are in check, but not lost yet

        else:
            # 4. THE OFF SWITCH: No enemy piece hits the King's square.
            enemy_player.is_in_check = False
            enemy_player.lost = False

            # Still refresh moves so pieces can move normally
            for p in enemy_player.pieces:
                p.update_all_legal_moves(self)
            if not enemy_player.has_legal_moves():
                self.is_stalemate = True
                self.is_draw = True
            else:
                self.is_stalemate = False

        # 1. The 50-Move Rule (100 half-moves)
        if self.halfmove_clock >= 100:
                self.is_draw = True

        # 2. The 3-Fold Repetition Rule
        # We just look at the photo we just took!
        current_core_fen = self.generate_core_fen()
        if self.position_counts.get(current_core_fen, 0) >= 3:
                self.is_draw = True

    def execute_move(self, move: Move, is_imagining=False):
        """Replaces the old 'move_piece' and natively handles En Passant using the Move manual."""
        piece = self.get_piece_at(move.from_pos)
        if not piece: return

        # 1. THE DIARY: Snapshot BEFORE moving (This part is correct)
        victim = self.get_piece_at(move.victim_pos) if move.victim_pos else None
        san_string = "GHOST_MOVE" if is_imagining else self.get_algebraic_notation(move, piece, victim)

        record = MoveRecord(
            move=move, moved_piece=piece, piece_had_moved=piece.has_moved,
            clocks=CLOCKS, victim_piece=victim, old_en_passant=self.en_passant,
            old_castling_rights=self.castling_rights, algebraic_notation=san_string,
            is_imagining=is_imagining, old_halfmove_clock=self.halfmove_clock
        )
        self.move_log.append(record)

        # 2. UPDATE CLOCKS & ALBUM TRASH CAN
        # If a pawn moves or someone dies, the old photos are useless!
        if piece.type == ChessPieceType.PAWN or move.victim_pos:
            self.halfmove_clock = 0
            if not is_imagining:
                self.position_counts.clear() # THE TRASH CAN: Reset the repeats
        else:
            self.halfmove_clock += 1

        if self.active_color == ChessColor.BLACK:
            self.fullmove_number += 1

        # 3. ACTUALLY MOVE THE PIECES (Physics happens here)
        sound_to_play = "move"

        if move.victim_pos:
            victim_piece = self.get_piece_at(move.victim_pos)
            if victim_piece and victim_piece.color != piece.color:
                victim_piece.die()
                self.grid[move.victim_pos.row][move.victim_pos.col] = None
                sound_to_play = "capture"

        if move.move_type == MoveType.CASTLE:
            rook = self.get_piece_at(move.to_pos)
            if rook:
                self.perform_castle(piece, rook)
                piece.has_moved = True
                sound_to_play = "castle"
        else:
            self.grid[move.to_pos.row][move.to_pos.col] = piece
            self.grid[move.from_pos.row][move.from_pos.col] = None
            piece.position = move.to_pos
            piece.has_moved = True

        if move.move_type == MoveType.PROMOTION:
            piece.die()
            promo_val = move.promotion_choice.value if move.promotion_choice and not is_imagining else "Q"
            self.grid[move.to_pos.row][move.to_pos.col] = create_piece_with_specified_color(
                piece.color, str(promo_val), move.to_pos)
            sound_to_play = "promote"

        self.en_passant = None
        if piece.type == ChessPieceType.PAWN and abs(move.to_pos.row - move.from_pos.row) == 2:
            mid_row = (move.to_pos.row + move.from_pos.row) // 2
            self.en_passant = SquarePosition(row=mid_row, col=move.to_pos.col)

        # --- THE FIX: TAKE THE PHOTO NOW! ---
        # The piece is in the new room, so now we click the camera.
        if not is_imagining:
            core_fen = self.generate_core_fen()
            self.position_counts[core_fen] = self.position_counts.get(core_fen, 0) + 1

        # 4. LET THE REFEREE CHECK THE ALBUM
        self.update_game_state()

        # --- THE RED PEN & FINAL SFX CHECK ---
        enemy_player = PLAYERS[OTHER_COLOR[self.active_color]]

        if enemy_player.lost:
            self.move_log[-1].algebraic_notation += "#"
            sound_to_play = "checkmate"  # Checkmate is the loudest sound!
        elif enemy_player.is_in_check:
            self.move_log[-1].algebraic_notation += "+"
            sound_to_play = "check"  # Check overrides normal captures!

        # --- THE DJ PRESSES PLAY ---
        if not is_imagining:
            play_sfx(sound_to_play)

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

        if self.is_draw:
            self.is_draw = False
            self.is_stalemate = False

        current_core_fen = self.generate_core_fen()
        if current_core_fen in self.position_counts:
            self.position_counts[current_core_fen] -= 1
            if self.position_counts[current_core_fen] <= 0:
                del self.position_counts[current_core_fen] #Undo the move in the clocks

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
            rook.has_moved = False

        else:
            # 4. NORMAL UNDO (Moves, Captures, En Passant, Promotions)

            # Erase whatever is on the destination square
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

        # 6. Restore the clock time (ONLY IF REAL)
        if not record.is_imagining:
            for color in ChessColor:
                CLOCKS[color].remaining = record.current_times[color]

        # 7. Give the turn back
        self.switch_turn()

        # 8. Recalculate the board state
        self.update_game_state()

        # --- THE RUTHLESS MENTOR FIX ---
        # update_game_state only updates the ENEMY king!
        # We MUST force the active king to wake up and dump its ghost moves!
        for p in self.get_all_pieces():
            if p.is_king():
                p.update_all_legal_moves(self)

        return True



# </editor-fold>

# <editor-fold desc="DRAWING">
def get_image_path(color: ChessColor, piece_type: ChessPieceType):
    # 1. Build the relative path string
    relative = f"assets/sliced_pieces/{color.value}_{piece_type.name}.png"

    # 2. Pass it through the 'Pathfinder' to get the real location
    return get_asset_path(relative)



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


def draw_server_browser_page(screen, servers_found: dict, return_rect):
    # 1. Background
    screen.fill((30, 30, 35))
    for row in range(8):
        for col in range(10):
            if (row + col) % 2 == 0:
                pygame.draw.rect(screen, (35, 35, 40), (col * 100, row * 100, 100, 100))

    pygame.font.init()
    font_title = pygame.font.SysFont("Arial", 60, bold=True)
    font_btn = pygame.font.SysFont("Arial", 24, bold=True)

    # 2. Title
    title = font_title.render("LOCAL SERVERS", True, (255, 255, 255))
    screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 80)))

    # 3. Dynamic Server Buttons
    start_y = 180
    mouse_pos = pygame.mouse.get_pos()

    for i, (ip, data) in enumerate(servers_found.items()):
        btn_rect = pygame.Rect((SCREEN_WIDTH // 2) - 250, start_y + (i * 90), 500, 70)

        # ELI5: We update the dictionary with the hitbox right as we paint it!
        data["rect"] = btn_rect

        is_full = data["seats"] == "0"
        if is_full:
            bg_color = (150, 60, 60)
        else:
            bg_color = (80, 150, 200) if btn_rect.collidepoint(mouse_pos) else (60, 120, 160)

        pygame.draw.rect(screen, bg_color, btn_rect, border_radius=10)
        pygame.draw.rect(screen, (255, 255, 255), btn_rect, 2, border_radius=10)

        srv_txt = font_btn.render(f"{data['name']} ({ip})", True, (255, 255, 255))
        seat_txt = font_btn.render(f"Seats: {data['seats']}/2", True,
                                   (200, 255, 200) if not is_full else (255, 150, 150))

        screen.blit(srv_txt, (btn_rect.x + 20, btn_rect.y + 20))
        screen.blit(seat_txt, (btn_rect.right - 140, btn_rect.y + 20))

    # 4. Empty State Text
    if not servers_found:
        search_txt = font_btn.render("Listening for Megaphones...", True, (150, 150, 150))
        screen.blit(search_txt, search_txt.get_rect(center=(SCREEN_WIDTH // 2, 250)))

    # 5. Return Button
    ret_color = (180, 80, 80) if return_rect.collidepoint(mouse_pos) else (150, 60, 60)
    pygame.draw.rect(screen, ret_color, return_rect, border_radius=15)
    pygame.draw.rect(screen, (255, 255, 255), return_rect, 3, border_radius=15)
    ret_txt = font_btn.render("RETURN", True, (255, 255, 255))
    screen.blit(ret_txt, ret_txt.get_rect(center=return_rect.center))

def draw_waiting_room_page(screen, my_color, return_rect):
    screen.fill((30, 30, 35))
    for row in range(8):
        for col in range(10):
            if (row + col) % 2 == 0:
                pygame.draw.rect(screen, (35, 35, 40), (col * 100, row * 100, 100, 100))

    pygame.font.init()
    font_title = pygame.font.SysFont("Arial", 40, bold=True)
    font_sub = pygame.font.SysFont("Arial", 24)
    font_btn = pygame.font.SysFont("Arial", 30, bold=True)

    txt1 = font_title.render(f"You are playing as {my_color}", True, (255, 255, 255))
    txt2 = font_sub.render("Waiting for opponent to join the room...", True, (200, 200, 200))

    screen.blit(txt1, txt1.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 40)))
    screen.blit(txt2, txt2.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 30)))

    # Draw the Return Button
    mouse_pos = pygame.mouse.get_pos()
    ret_color = (180, 80, 80) if return_rect.collidepoint(mouse_pos) else (150, 60, 60)
    pygame.draw.rect(screen, ret_color, return_rect, border_radius=15)
    pygame.draw.rect(screen, (255, 255, 255), return_rect, 3, border_radius=15)
    ret_txt = font_btn.render("RETURN TO MENU", True, (255, 255, 255))
    screen.blit(ret_txt, ret_txt.get_rect(center=return_rect.center))

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

def draw_create_openings_side_menu(screen):
    """Paints a clean side menu specifically for the Sandbox Forge."""
    # 1. Menu Background
    pygame.draw.rect(screen, (30, 30, 30), (RIGHT_MENU_X, 0, SIDE_PANEL_WIDTH, SCREEN_HEIGHT))
    pygame.draw.line(screen, (100, 100, 100), (RIGHT_MENU_X, 0), (RIGHT_MENU_X, SCREEN_HEIGHT), 2)

    mouse_pos = pygame.mouse.get_pos()
    pygame.font.init()
    font_title = pygame.font.SysFont("Arial", 28, bold=True)
    font_btn = pygame.font.SysFont("Arial", 20, bold=True)

    # Title
    title = font_title.render("FORGE MODE", True, (150, 100, 200))
    screen.blit(title, title.get_rect(center=(RIGHT_MENU_X + (SIDE_PANEL_WIDTH // 2), 50)))

    # The Big Purple Save Button
    s_col = (150, 80, 200) if FORGE_SAVE_BTN_RECT.collidepoint(mouse_pos) else (110, 60, 150)
    pygame.draw.rect(screen, s_col, FORGE_SAVE_BTN_RECT, border_radius=10)
    pygame.draw.rect(screen, (255, 215, 0), FORGE_SAVE_BTN_RECT, 2, border_radius=10)
    s_txt = font_btn.render("SAVE TO BOOK", True, (255, 255, 255))
    screen.blit(s_txt, s_txt.get_rect(center=FORGE_SAVE_BTN_RECT.center))

    # --- THE TOGGLE BUTTON ---
    t_col = (100, 150, 200) if FORGE_TOGGLE_BTN_RECT.collidepoint(mouse_pos) else (80, 120, 160)
    pygame.draw.rect(screen, t_col, FORGE_TOGGLE_BTN_RECT, border_radius=5)
    pygame.draw.rect(screen, (255, 255, 255), FORGE_TOGGLE_BTN_RECT, 2, border_radius=5)
    t_txt = font_btn.render(f"Save: {FORGE_SAVE_MODE}", True, (255, 255, 255))
    screen.blit(t_txt, t_txt.get_rect(center=FORGE_TOGGLE_BTN_RECT.center))

    # The Red Back Button
    m_col = (180, 80, 80) if FORGE_MENU_BTN_RECT.collidepoint(mouse_pos) else (150, 60, 60)
    pygame.draw.rect(screen, m_col, FORGE_MENU_BTN_RECT, border_radius=10)
    pygame.draw.rect(screen, (255, 255, 255), FORGE_MENU_BTN_RECT, 2, border_radius=10)
    m_txt = font_btn.render("BACK", True, (255, 255, 255))
    screen.blit(m_txt, m_txt.get_rect(center=FORGE_MENU_BTN_RECT.center))


def draw_bot_wizard_page(screen, step, data, box_rect, text_rect, btn_script, btn_engine, bg_surface):
    pygame.font.init()
    font_title = pygame.font.SysFont("Arial", 30, bold=True)
    font_sub = pygame.font.SysFont("Arial", 20)
    font_input = pygame.font.SysFont("Arial", 24)

    mouse_pos = pygame.mouse.get_pos()

    # 1. Draw the dimmed background photo
    screen.blit(bg_surface, (0, 0))

    # 2. Draw the Main Box
    pygame.draw.rect(screen, (30, 30, 35), box_rect, border_radius=15)
    pygame.draw.rect(screen, (100, 200, 255), box_rect, 3, border_radius=15)

    title = ""
    subtitle = ""
    show_text_box = True
    current_text = ""

    # 3. State Machine UI Rendering
    if step == 0:
        title = "Name Your Bot"
        subtitle = "e.g., 'Toddler Gary' or 'Grandmaster Alpha'"
        current_text = data["name"]
    elif step == 1:
        title = "Create Bot ID"
        subtitle = "No spaces allowed. e.g., 'gary_noob'"
        current_text = data["id"]
    elif step == 2:
        title = "Choose Brain Type"
        subtitle = "How will this bot think?"
        show_text_box = False

        # Draw Buttons for Brain Choice
        c1 = (80, 150, 200) if btn_script.collidepoint(mouse_pos) else (60, 100, 150)
        pygame.draw.rect(screen, c1, btn_script, border_radius=8)
        t1 = font_sub.render("1. Custom Python Script (Write your own)", True, (255, 255, 255))
        screen.blit(t1, t1.get_rect(center=btn_script.center))

        c2 = (150, 80, 80) if btn_engine.collidepoint(mouse_pos) else (120, 60, 60)
        pygame.draw.rect(screen, c2, btn_engine, border_radius=8)
        t2 = font_sub.render("2. Engine Bot (Uses Stockfish)", True, (255, 255, 255))
        screen.blit(t2, t2.get_rect(center=btn_engine.center))

    elif step == 3:
        title = "Assign Opening Books"
        subtitle = "Comma separated (e.g., sicilian, alapin). Or leave blank."
        current_text = data["books"]
    elif step == 4:
        title = "Engine Depth"
        subtitle = "How many moves ahead? (e.g., 4. Max=9999)"
        current_text = data["depth"]
    elif step == 5:
        title = "Engine ELO Limit"
        subtitle = "Limit skill level? (e.g., 1200. Max=9999)"
        current_text = data["elo"]

    # 4. Draw Titles
    t_surf = font_title.render(title, True, (255, 255, 255))
    s_surf = font_sub.render(subtitle, True, (180, 180, 180))
    screen.blit(t_surf, t_surf.get_rect(center=(SCREEN_WIDTH // 2, box_rect.y + 40)))
    screen.blit(s_surf, s_surf.get_rect(center=(SCREEN_WIDTH // 2, box_rect.y + 80)))

    # 5. Draw Text Box (If applicable for this step)
    if show_text_box:
        pygame.draw.rect(screen, (20, 20, 25), text_rect, border_radius=5)
        pygame.draw.rect(screen, (150, 150, 150), text_rect, 2, border_radius=5)

        cursor = "|" if pygame.time.get_ticks() % 1000 < 500 else ""
        txt_surf = font_input.render(current_text + cursor, True, (255, 255, 255))
        screen.blit(txt_surf, (text_rect.x + 10, text_rect.y + 8))

        enter_txt = font_sub.render("Press ENTER to continue, ESC to cancel", True, (100, 100, 100))
        screen.blit(enter_txt, enter_txt.get_rect(center=(SCREEN_WIDTH // 2, box_rect.bottom - 30)))

def draw_bot_selection_page(screen, ui_rects, bot_ids, is_launching, scroll_y, clip_rect, track_rect, thumb_rect, max_scroll):
    # 1. Background
    screen.fill((30, 30, 35))
    for row in range(8):
        for col in range(10):
            if (row + col) % 2 == 0:
                pygame.draw.rect(screen, (35, 35, 40), (col * 100, row * 100, 100, 100))

    mouse_pos = pygame.mouse.get_pos()
    pygame.font.init()
    font_title = pygame.font.SysFont("Arial", 50, bold=True)
    font_sub = pygame.font.SysFont("Arial", 24, bold=True)
    font_btn = pygame.font.SysFont("Arial", 22, bold=True)

    title_surf = font_title.render("BOT SETUP", True, (255, 255, 255))
    screen.blit(title_surf, title_surf.get_rect(center=(SCREEN_WIDTH // 2, 60)))

    # --- 1. Colors ---
    c_txt = font_sub.render("Play As:", True, (200, 200, 200))
    screen.blit(c_txt, c_txt.get_rect(center=(SCREEN_WIDTH // 2, 120)))

    for color_name, rect in ui_rects["colors"].items():
        is_selected = (PREFERENCES["player_color"] == color_name)
        if color_name == "White":
            bg_col = (220, 220, 220) if is_selected else (100, 100, 100)
            text_col = (0, 0, 0) if is_selected else (200, 200, 200)
        else:
            bg_col = (40, 40, 40) if is_selected else (100, 100, 100)
            text_col = (255, 255, 255) if is_selected else (200, 200, 200)

        if rect.collidepoint(mouse_pos) and not is_selected:
            bg_col = (min(bg_col[0] + 30, 255), min(bg_col[1] + 30, 255), min(bg_col[2] + 30, 255))

        pygame.draw.rect(screen, bg_col, rect, border_radius=10)
        pygame.draw.rect(screen, (255, 255, 255) if is_selected else (150, 150, 150), rect, 3, border_radius=10)
        surf = font_btn.render(color_name, True, text_col)
        screen.blit(surf, surf.get_rect(center=rect.center))

    # --- 2. Bots (The Scroller) ---
    b_txt = font_sub.render("Opponent Level:", True, (200, 200, 200))
    screen.blit(b_txt, b_txt.get_rect(center=(SCREEN_WIDTH // 2, 230)))
    pygame.draw.rect(screen, (25, 25, 30), clip_rect, border_radius=5)

    screen.set_clip(clip_rect)
    start_y = 280
    for i, bot_id in enumerate(bot_ids):
        col = i % 2
        row = i // 2
        x = (SCREEN_WIDTH // 2) - 260 + (col * 270)
        y = start_y + (row * 60) - scroll_y
        rect = pygame.Rect(x, y, 250, 45)

        is_selected = (PREFERENCES.get("bot_id") == bot_id)
        base_col = (100, 150, 200) if is_selected else (60, 80, 100)

        if rect.collidepoint(mouse_pos) and not is_selected and clip_rect.collidepoint(mouse_pos):
            base_col = (80, 100, 130)

        pygame.draw.rect(screen, base_col, rect, border_radius=10)
        pygame.draw.rect(screen, (255, 255, 255) if is_selected else (120, 120, 120), rect, 3, border_radius=10)

        bot_name = LOADED_BOTS[bot_id].get("name", "Unknown Bot") if bot_id in LOADED_BOTS else "Unknown"
        surf = font_btn.render(bot_name, True, (255, 255, 255))
        screen.blit(surf, surf.get_rect(center=rect.center))
    screen.set_clip(None)

    if max_scroll > 0:
        pygame.draw.rect(screen, (40, 40, 45), track_rect, border_radius=6)
        thumb_col = (180, 180, 200) if thumb_rect.collidepoint(mouse_pos) else (120, 120, 140)
        pygame.draw.rect(screen, thumb_col, thumb_rect, border_radius=6)

    # --- CREATE OPENINGS BUTTON (Back to full size) ---
    co_rect = ui_rects["create_openings"]
    co_col = (150, 80, 200) if co_rect.collidepoint(mouse_pos) else (110, 60, 150)
    pygame.draw.rect(screen, co_col, co_rect, border_radius=10)
    pygame.draw.rect(screen, (255, 215, 0), co_rect, 2, border_radius=10)
    co_txt = font_btn.render("CREATE OPENING BOOK (Sandbox)", True, (255, 255, 255))
    screen.blit(co_txt, co_txt.get_rect(center=co_rect.center))

    # --- 3. Quick Start Checkbox ---
    qs_rect = ui_rects["quick_start"]
    pygame.draw.rect(screen, (50, 50, 50), qs_rect, border_radius=5)
    if PREFERENCES["quick_start_bot"]:
        pygame.draw.rect(screen, (80, 200, 80), qs_rect.inflate(-8, -8), border_radius=3)
    pygame.draw.rect(screen, (200, 200, 200), qs_rect, 2, border_radius=5)
    qs_txt = font_sub.render("Quick Start (Skip this page next time)", True, (200, 200, 200))
    screen.blit(qs_txt, (qs_rect.right + 15, qs_rect.y + 2))

    # --- 4. Confirm / Cancel ---
    conf_rect = ui_rects["confirm"]
    c_col = (80, 200, 80) if conf_rect.collidepoint(mouse_pos) else (60, 150, 60)
    pygame.draw.rect(screen, c_col, conf_rect, border_radius=15)
    pygame.draw.rect(screen, (255, 255, 255), conf_rect, 3, border_radius=15)
    conf_txt = font_btn.render("START GAME" if is_launching else "SAVE SETTINGS", True, (255, 255, 255))
    screen.blit(conf_txt, conf_txt.get_rect(center=conf_rect.center))

    canc_rect = ui_rects["cancel"]
    can_col = (180, 80, 80) if canc_rect.collidepoint(mouse_pos) else (150, 60, 60)
    pygame.draw.rect(screen, can_col, canc_rect, border_radius=15)
    pygame.draw.rect(screen, (255, 255, 255), canc_rect, 3, border_radius=15)
    can_txt = font_btn.render("CANCEL", True, (255, 255, 255))
    screen.blit(can_txt, can_txt.get_rect(center=canc_rect.center))

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

    txt_str = ""

    # 3. Dynamic Loop
    for i, rect in enumerate(GENERAL_SETTINGS_RECTS):
        btn_name = GENERAL_SETTINGS_OPTIONS[i]
        color = (150, 150, 150)  # Default reset

        if btn_name == "Auto Save":
            if PREFERENCES["auto_save"]:
                color = (180, 180, 180) if rect.collidepoint(mouse_pos) else (150, 150, 150)
                txt_str = "Auto Save: ON"
            else:
                color = (80, 80, 80) if rect.collidepoint(mouse_pos) else (60, 60, 60)
                txt_str = "Auto Save: OFF"

        elif btn_name == "Time Control":
            color = (100, 150, 200) if rect.collidepoint(mouse_pos) else (80, 120, 160)
            txt_str = f"Time: {PREFERENCES['starting_time'] // 60} Min"

        elif btn_name == "Game Mode":
            color = (120, 100, 180) if rect.collidepoint(mouse_pos) else (100, 80, 150)
            txt_str = f"Mode: {PREFERENCES['game_mode']}"

        elif btn_name == "Player Color":
            if PREFERENCES["game_mode"] == "Multiplayer" or PREFERENCES["game_mode"] == "Online":
                color = (60, 60, 60)  # Disabled
                txt_str = "Color: N/A"
            else:
                color = (180, 120, 100) if rect.collidepoint(mouse_pos) else (150, 100, 80)
                txt_str = f"Play as: {PREFERENCES['player_color']}"

        elif btn_name == "Bot Setup":
            if PREFERENCES["game_mode"] == "Singleplayer":
                color = (102, 226, 219) if rect.collidepoint(mouse_pos) else (44, 200, 190)
                txt_str = "Bot Setup"
            else:
                color = (60, 60, 60)  # Disabled
                txt_str = "Bot Setup (N/A)"

        # --- NEW: FORGE BOT ---
        elif btn_name == "Forge Bot":
            color = (100, 180, 255) if rect.collidepoint(mouse_pos) else (80, 140, 200)
            txt_str = "Forge New Bot"

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

def draw_video_settings_page(screen):
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
    title_surf = font_title.render("VIDEO SETTINGS", True, (255, 255, 255))
    screen.blit(title_surf, title_surf.get_rect(center=(SCREEN_WIDTH // 2, 120)))

    # 3. Dynamic Loop for our 2 columns
    for i, rect in enumerate(VIDEO_SETTINGS_RECTS):
        btn_name = VIDEO_SETTINGS_OPTIONS[i]

        if btn_name == "FPS":
            color = (150, 100, 200) if rect.collidepoint(mouse_pos) else (120, 80, 160) # Purple
            txt_str = f"FPS Limit: {PREFERENCES['fps']}"

        elif btn_name == "Animation Time":
            color = (200, 150, 100) if rect.collidepoint(mouse_pos) else (180, 120, 80) # Orange
            if PREFERENCES['animation_time'] == 0.0:
                txt_str = "Animation: Instant (0s)"
            if PREFERENCES['animation_time'] == 60.0:
                txt_str = "Yes"
            else:
                txt_str = f"Animation: {PREFERENCES['animation_time']}s"

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

def draw_playlist_page(screen, ui_rects):
    # 1. Paint the cool checkered background
    screen.fill((30, 30, 35))
    for row in range(8):
        for col in range(10):
            if (row + col) % 2 == 0:
                pygame.draw.rect(screen, (35, 35, 40), (col * 100, row * 100, 100, 100))

    mouse_pos = pygame.mouse.get_pos()
    pygame.font.init()
    font_title = pygame.font.SysFont("Arial", 60, bold=True)
    font_btn = pygame.font.SysFont("Arial", 20, bold=True)
    font_small = pygame.font.SysFont("Arial", 14, bold=True)

    # 2. Draw the big title
    title_surf = font_title.render("THE DJ BOOTH", True, (255, 255, 255))
    screen.blit(title_surf, title_surf.get_rect(center=(SCREEN_WIDTH // 2, 80)))

    # 3. Draw the big red CLEAR button
    clear_rect = ui_rects["clear"]
    c_col = (180, 80, 80) if clear_rect.collidepoint(mouse_pos) else (150, 60, 60)
    pygame.draw.rect(screen, c_col, clear_rect, border_radius=10)
    pygame.draw.rect(screen, (255, 255, 255), clear_rect, 2, border_radius=10)
    c_txt = font_btn.render("CLEAR PLAYLIST", True, (255, 255, 255))
    screen.blit(c_txt, c_txt.get_rect(center=clear_rect.center))

    # 4. Draw all the Music Packs dynamically
    for item in ui_rects["packs"]:
        main_rect = item["main"]
        add_rect = item["add"]
        view_rect = item["view"]

        # The main card background
        pygame.draw.rect(screen, (50, 50, 60), main_rect, border_radius=10)
        pygame.draw.rect(screen, (100, 100, 120), main_rect, 2, border_radius=10)

        # The pack name
        name_txt = font_btn.render(item["pack"].replace("_", " ").title(), True, (220, 220, 220))
        screen.blit(name_txt, (main_rect.x + 20, main_rect.y + 13))

        # The green "Add All" button
        add_col = (80, 200, 80) if add_rect.collidepoint(mouse_pos) else (60, 150, 60)
        pygame.draw.rect(screen, add_col, add_rect, border_radius=5)
        add_txt = font_small.render("+ ADD ALL", True, (255, 255, 255))
        screen.blit(add_txt, add_txt.get_rect(center=add_rect.center))

        # The blue "View Songs" button
        view_col = (80, 150, 200) if view_rect.collidepoint(mouse_pos) else (60, 100, 150)
        pygame.draw.rect(screen, view_col, view_rect, border_radius=5)
        v_txt = font_small.render("VIEW SONGS", True, (255, 255, 255))
        screen.blit(v_txt, v_txt.get_rect(center=view_rect.center))

    # 5. Draw the Return button at the bottom
    ret_rect = ui_rects["return"]
    ret_color = (180, 80, 80) if ret_rect.collidepoint(mouse_pos) else (150, 60, 60)
    pygame.draw.rect(screen, ret_color, ret_rect, border_radius=15)
    pygame.draw.rect(screen, (255, 255, 255), ret_rect, 3, border_radius=15)
    ret_txt = font_btn.render("RETURN", True, (255, 255, 255))
    screen.blit(ret_txt, ret_txt.get_rect(center=ret_rect.center))

def draw_audio_settings_page(screen, ui_rects):
    screen.fill((30, 30, 35))
    for row in range(8):
        for col in range(10):
            if (row + col) % 2 == 0:
                pygame.draw.rect(screen, (35, 35, 40), (col * 100, row * 100, 100, 100))

    mouse_pos = pygame.mouse.get_pos()
    pygame.font.init()
    font_title = pygame.font.SysFont("Arial", 50, bold=True)
    font_sub = pygame.font.SysFont("Arial", 30, bold=True)
    font_btn = pygame.font.SysFont("Arial", 20, bold=True)  # Shrunk!
    font_small = pygame.font.SysFont("Arial", 14, bold=True)  # Shrunk!

    title_surf = font_title.render("AUDIO & MUSIC", True, (255, 255, 255))
    screen.blit(title_surf, title_surf.get_rect(center=(SCREEN_WIDTH // 2, 60)))

    pygame.draw.line(screen, (80, 80, 90), (SCREEN_WIDTH // 2, 140), (SCREEN_WIDTH // 2, SCREEN_HEIGHT - 160), 3)

    # --- LEFT COLUMN: SETTINGS ---
    left_title = font_sub.render("SETTINGS", True, (200, 200, 200))
    screen.blit(left_title, left_title.get_rect(center=(SCREEN_WIDTH // 4, 150)))

    for i in range(4):
        rect = ui_rects["settings"][i]
        btn_name = AUDIO_SETTINGS_OPTIONS[i]

        if "Pack" in btn_name:
            txt_str = f"SFX Pack: {PREFERENCES['sound_pack']}"
            color = (120, 100, 180) if rect.collidepoint(mouse_pos) else (100, 80, 150)
        else:
            is_playing = not PREFERENCES[f"{btn_name.split()[0].lower()}_mute"]
            color = (80, 180, 80) if is_playing else (180, 80, 80)
            if rect.collidepoint(mouse_pos):
                color = (min(color[0] + 30, 255), min(color[1] + 30, 255), min(color[2] + 30, 255))
            txt_str = f"{btn_name}: ON" if is_playing else f"{btn_name}: OFF"

        pygame.draw.rect(screen, color, rect, border_radius=10)
        pygame.draw.rect(screen, (255, 255, 255), rect, 2, border_radius=10)
        txt = font_btn.render(txt_str, True, (255, 255, 255))
        screen.blit(txt, txt.get_rect(center=rect.center))

    vol_rect = ui_rects["volume"]
    pygame.draw.rect(screen, (50, 50, 50), vol_rect, border_radius=15)
    pygame.draw.rect(screen, (255, 255, 255), vol_rect, 3, border_radius=15)
    vol = PREFERENCES["volume"]
    fill_width = int((vol_rect.width - 6) * vol)
    if fill_width > 0:
        fill_rect = pygame.Rect(vol_rect.x + 3, vol_rect.y + 3, fill_width, vol_rect.height - 6)
        pygame.draw.rect(screen, (80, 150, 200), fill_rect, border_radius=12)
    vol_txt = font_btn.render(f"Volume: {int(vol * 100)}%", True, (255, 255, 255))
    screen.blit(vol_txt, vol_txt.get_rect(center=vol_rect.center))

    # --- RIGHT COLUMN: PACKS ---
    right_title = font_sub.render("MUSIC PACKS", True, (200, 200, 200))
    screen.blit(right_title, right_title.get_rect(center=(SCREEN_WIDTH * 3 // 4, 150)))

    clear_rect = ui_rects["clear"]
    c_col = (180, 80, 80) if clear_rect.collidepoint(mouse_pos) else (150, 60, 60)
    pygame.draw.rect(screen, c_col, clear_rect, border_radius=10)
    pygame.draw.rect(screen, (255, 255, 255), clear_rect, 2, border_radius=10)
    c_txt = font_btn.render("CLEAR PLAYLIST", True, (255, 255, 255))
    screen.blit(c_txt, c_txt.get_rect(center=clear_rect.center))

    for item in ui_rects["packs"]:
        main_rect = item["main"]
        add_rect = item["add"]
        view_rect = item["view"]

        pygame.draw.rect(screen, (50, 50, 60), main_rect, border_radius=10)
        pygame.draw.rect(screen, (100, 100, 120), main_rect, 2, border_radius=10)

        name_txt = font_btn.render(item["pack"].replace("_", " ").title(), True, (220, 220, 220))
        screen.blit(name_txt, (main_rect.x + 20, main_rect.y + 13))

        add_col = (80, 200, 80) if add_rect.collidepoint(mouse_pos) else (60, 150, 60)
        pygame.draw.rect(screen, add_col, add_rect, border_radius=5)
        add_txt = font_small.render("+ ADD ALL", True, (255, 255, 255))
        screen.blit(add_txt, add_txt.get_rect(center=add_rect.center))

        view_col = (80, 150, 200) if view_rect.collidepoint(mouse_pos) else (60, 100, 150)
        pygame.draw.rect(screen, view_col, view_rect, border_radius=5)
        v_txt = font_small.render("VIEW SONGS", True, (255, 255, 255))
        screen.blit(v_txt, v_txt.get_rect(center=view_rect.center))

    ret_color = (180, 80, 80) if RETURN_BTN_RECT.collidepoint(mouse_pos) else (150, 60, 60)
    pygame.draw.rect(screen, ret_color, RETURN_BTN_RECT, border_radius=15)
    pygame.draw.rect(screen, (255, 255, 255), RETURN_BTN_RECT, 3, border_radius=15)
    ret_txt = font_btn.render("RETURN", True, (255, 255, 255))
    screen.blit(ret_txt, ret_txt.get_rect(center=RETURN_BTN_RECT.center))

def update_window_size(force_fullscreen=None, in_game=False):
    """Dynamically shrinks or expands the window based on location and mute settings."""
    global SCREEN_HEIGHT, SCREEN, RETURN_BTN_RECT, REPLAY_MENU_BTN

    # 1. Decide the height
    # Only expand if we are ON THE BOARD (in_game) AND the music is allowed to play!
    if in_game and not PREFERENCES["master_mute"] and not PREFERENCES["music_mute"]:
        SCREEN_HEIGHT = WINDOW_SIZE + BOTTOM_PANEL_HEIGHT  # Expand it!
    else:
        SCREEN_HEIGHT = WINDOW_SIZE  # Shrink it!

    # 2. Check if we are fullscreen
    if force_fullscreen is not None:
        is_fullscreen = force_fullscreen
    else:
        is_fullscreen = SCREEN.get_flags() & pygame.FULLSCREEN if SCREEN else False

    # 3. Physically resize the Pygame window (NO SCALED!)
    if is_fullscreen:
        SCREEN = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN)
    else:
        SCREEN = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE)

    # 4. Re-anchor the two global buttons that were glued to the bottom
    RETURN_BTN_RECT.y = SCREEN_HEIGHT - 100
    REPLAY_MENU_BTN.y = SCREEN_HEIGHT - 100


def draw_view_pack_page(screen, pack_name, tracks, scroll_y, track_rects, track_rect, thumb_rect, max_scroll):
    screen.fill((30, 30, 35))
    for row in range(8):
        for col in range(10):
            if (row + col) % 2 == 0:
                pygame.draw.rect(screen, (35, 35, 40), (col * 100, row * 100, 100, 100))

    mouse_pos = pygame.mouse.get_pos()
    pygame.font.init()
    font_title = pygame.font.SysFont("Arial", 50, bold=True)
    font_btn = pygame.font.SysFont("Arial", 20, bold=True)
    font_small = pygame.font.SysFont("Arial", 16, bold=True)

    title_str = pack_name.replace("_", " ").upper() + " SONGS"
    title_surf = font_title.render(title_str, True, (255, 255, 255))
    screen.blit(title_surf, title_surf.get_rect(center=(SCREEN_WIDTH // 2, 60)))

    # The Scissors (Window Pane for scrolling)
    clip_rect = pygame.Rect(0, 120, SCREEN_WIDTH, SCREEN_HEIGHT - 220)
    screen.set_clip(clip_rect)

    track_rects.clear()
    start_y = 140
    for i, track in enumerate(tracks):
        y = start_y + (i * 70) - scroll_y
        main_rect = pygame.Rect((SCREEN_WIDTH // 2) - 300, y, 600, 60)
        next_rect = pygame.Rect(main_rect.right - 240, y + 10, 110, 40)
        end_rect = pygame.Rect(main_rect.right - 120, y + 10, 110, 40)

        track_rects.append({"track": track, "next": next_rect, "end": end_rect})

        pygame.draw.rect(screen, (50, 50, 60), main_rect, border_radius=10)
        pygame.draw.rect(screen, (100, 100, 120), main_rect, 2, border_radius=10)

        # ELI5: Clean up the underscores so the names look nice!
        name_txt = font_btn.render(track.name.replace("_", " "), True, (220, 220, 220))
        screen.blit(name_txt, (main_rect.x + 20, main_rect.y + 18))

        # Play Next Button (Green)
        next_col = (80, 200, 80) if next_rect.collidepoint(mouse_pos) else (60, 150, 60)
        pygame.draw.rect(screen, next_col, next_rect, border_radius=5)
        n_txt = font_small.render("PLAY NEXT", True, (255, 255, 255))
        screen.blit(n_txt, n_txt.get_rect(center=next_rect.center))

        # Add to End Button (Blue)
        end_col = (80, 150, 200) if end_rect.collidepoint(mouse_pos) else (60, 100, 150)
        pygame.draw.rect(screen, end_col, end_rect, border_radius=5)
        e_txt = font_small.render("ADD TO END", True, (255, 255, 255))
        screen.blit(e_txt, e_txt.get_rect(center=end_rect.center))

    screen.set_clip(None)

    # --- THE INTERACTABLE SCROLLBAR ---
    if max_scroll > 0:
        # Draw the Track
        pygame.draw.rect(screen, (40, 40, 45), track_rect, border_radius=6)
        pygame.draw.rect(screen, (60, 60, 65), track_rect, 1, border_radius=6)

        # Draw the Thumb
        thumb_col = (180, 180, 200) if thumb_rect.collidepoint(mouse_pos) else (120, 120, 140)
        pygame.draw.rect(screen, thumb_col, thumb_rect, border_radius=6)

    # Return Button
    ret_color = (180, 80, 80) if RETURN_BTN_RECT.collidepoint(mouse_pos) else (150, 60, 60)
    pygame.draw.rect(screen, ret_color, RETURN_BTN_RECT, border_radius=15)
    pygame.draw.rect(screen, (255, 255, 255), RETURN_BTN_RECT, 3, border_radius=15)
    ret_txt = font_btn.render("RETURN TO PACKS", True, (255, 255, 255))
    screen.blit(ret_txt, ret_txt.get_rect(center=RETURN_BTN_RECT.center))

def draw_saved_games_page(screen, games, scroll_y, return_rect, import_rect, clip_rect, track_rect, thumb_rect,
                          max_scroll):
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

    # --- THE INTERACTABLE SCROLLBAR ---
    if max_scroll > 0:
        # Draw the Track
        pygame.draw.rect(screen, (40, 40, 45), track_rect, border_radius=6)
        pygame.draw.rect(screen, (60, 60, 65), track_rect, 1, border_radius=6)

        # Draw the Thumb
        thumb_col = (180, 180, 200) if thumb_rect.collidepoint(mouse_pos) else (120, 120, 140)
        pygame.draw.rect(screen, thumb_col, thumb_rect, border_radius=6)

    # 6. Return Button (Drawn AFTER the scissors so it sits at the bottom safely)
    ret_color = (180, 80, 80) if return_rect.collidepoint(mouse_pos) else (150, 60, 60)
    pygame.draw.rect(screen, ret_color, return_rect, border_radius=15)
    pygame.draw.rect(screen, (255, 255, 255), return_rect, 3, border_radius=15)
    ret_txt = font_text.render("RETURN", True, (255, 255, 255))
    screen.blit(ret_txt, ret_txt.get_rect(center=return_rect.center))

def draw_paste_pgn_page(screen, status_msg: str, status_color: tuple, is_valid: bool, paste_rect, save_rect, forge_rect, return_rect, input_rect, user_text: str, active: bool):
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
    font_input = pygame.font.SysFont("Arial", 24, bold=False)

    title_surf = font_title.render("IMPORT PGN", True, (255, 255, 255))
    screen.blit(title_surf, title_surf.get_rect(center=(SCREEN_WIDTH // 2, 60)))

    status_surf = font_status.render(status_msg, True, status_color)
    screen.blit(status_surf, status_surf.get_rect(center=(SCREEN_WIDTH // 2, 130)))

    # Text Input Box
    box_color = (100, 150, 200) if active else (50, 50, 60)
    pygame.draw.rect(screen, box_color, input_rect, border_radius=5)
    pygame.draw.rect(screen, (255, 255, 255), input_rect, 2, border_radius=5)

    screen.set_clip(input_rect)
    text_surf = font_input.render(user_text, True, (255, 255, 255))
    text_x = input_rect.x + 10
    if text_surf.get_width() > input_rect.width - 20:
        text_x = input_rect.right - text_surf.get_width() - 10
    screen.blit(text_surf, (text_x, input_rect.y + 10))
    screen.set_clip(None)

    # Paste Button
    p_color = (100, 150, 200) if paste_rect.collidepoint(mouse_pos) else (80, 120, 160)
    pygame.draw.rect(screen, p_color, paste_rect, border_radius=15)
    pygame.draw.rect(screen, (255, 255, 255), paste_rect, 3, border_radius=15)
    p_txt = font_btn.render("PASTE FROM CLIPBOARD", True, (255, 255, 255))
    screen.blit(p_txt, p_txt.get_rect(center=paste_rect.center))

    # Save Button
    s_color = (80, 200, 80) if save_rect.collidepoint(mouse_pos) else (60, 150, 60) if is_valid else (60, 60, 60)
    pygame.draw.rect(screen, s_color, save_rect, border_radius=15)
    pygame.draw.rect(screen, (255, 255, 255), save_rect, 3, border_radius=15)
    s_txt = font_btn.render("SAVE TO GAMES", True, (255, 255, 255) if is_valid else (150, 150, 150))
    screen.blit(s_txt, s_txt.get_rect(center=save_rect.center))

    # Forge Book Button (Purple/Gold Theme)
    f_color = (150, 80, 200) if forge_rect.collidepoint(mouse_pos) else (110, 60, 150) if is_valid else (60, 60, 60)
    pygame.draw.rect(screen, f_color, forge_rect, border_radius=15)
    pygame.draw.rect(screen, (255, 215, 0) if is_valid else (150, 150, 150), forge_rect, 3, border_radius=15)
    f_txt = font_btn.render("FORGE OPENING BOOK (.json)", True, (255, 255, 255) if is_valid else (150, 150, 150))
    screen.blit(f_txt, f_txt.get_rect(center=forge_rect.center))

    # Return Button
    ret_color = (180, 80, 80) if return_rect.collidepoint(mouse_pos) else (150, 60, 60)
    pygame.draw.rect(screen, ret_color, return_rect, border_radius=15)
    pygame.draw.rect(screen, (255, 255, 255), return_rect, 3, border_radius=15)
    ret_txt = font_btn.render("RETURN", True, (255, 255, 255))
    screen.blit(ret_txt, ret_txt.get_rect(center=return_rect.center))


def draw_replay_side_menu(screen, show_notation: bool, current_move_text: str):
    # 1. Background (Shifted to the right room using RIGHT_MENU_X)
    pygame.draw.rect(screen, (30, 30, 30), (RIGHT_MENU_X, 0, SIDE_PANEL_WIDTH, SCREEN_HEIGHT))
    pygame.draw.line(screen, (100, 100, 100), (RIGHT_MENU_X, 0), (RIGHT_MENU_X, SCREEN_HEIGHT), 2)

    mouse_pos = pygame.mouse.get_pos()
    pygame.font.init()
    font_btn = pygame.font.SysFont("Arial", 20, bold=True)
    font_large = pygame.font.SysFont("Arial", 28, bold=True)

    # Move Tracker Label (Centered mathematically in the 220px panel)
    center_x = RIGHT_MENU_X + (SIDE_PANEL_WIDTH // 2)
    lbl = font_large.render("Current Move:", True, (200, 200, 200))
    screen.blit(lbl, lbl.get_rect(center=(center_x, 30)))

    txt = font_large.render(current_move_text, True, (255, 200, 50))
    screen.blit(txt, txt.get_rect(center=(center_x, 65)))

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
            is_light_square = (row + col) % 2 == 0
            color = LIGHT if is_light_square else DARK

            # THE MAGIC MIRROR
            v_row, v_col = get_visual_row_col(row, col)

            x_pos = BOARD_X_OFFSET + (v_col * SQUARE_SIZE)
            y_pos = v_row * SQUARE_SIZE
            pygame.draw.rect(screen, color, (x_pos, y_pos, SQUARE_SIZE, SQUARE_SIZE))

            if show_notation and NOTATION_FONT is not None:
                notation_text = row_col_to_notation(row, col).lower()
                text_color = DARK if is_light_square else LIGHT
                text_surface = NOTATION_FONT.render(notation_text, True, text_color)
                screen.blit(text_surface, (x_pos + 4, y_pos + SQUARE_SIZE - 18))

def draw_side_menu(screen, show_notation: bool,is_paused:bool):
    """Paints the side control panel, clocks, and buttons."""
    # 1. Menu Background
    pygame.draw.rect(screen, (30, 30, 30), (RIGHT_MENU_X, 0, SIDE_PANEL_WIDTH, SCREEN_HEIGHT))
    pygame.draw.line(screen, (100, 100, 100), (RIGHT_MENU_X, 0), (RIGHT_MENU_X, SCREEN_HEIGHT), 2)


    pygame.font.init()
    font_large = pygame.font.SysFont("Arial", 32, bold=True)
    font_small = pygame.font.SysFont("Arial", 20, bold=True)

    mouse_pos = pygame.mouse.get_pos()

    # --- DYNAMIC TOP/BOTTOM LOGIC ---
    top_color = ChessColor.WHITE if BOARD_FLIPPED else ChessColor.BLACK
    bottom_color = ChessColor.BLACK if BOARD_FLIPPED else ChessColor.WHITE
    show_top_buttons = PREFERENCES["game_mode"] == "Multiplayer"

    # --- TOP CLOCK ---
    t_bg = (220, 220, 220) if top_color == ChessColor.WHITE else (20, 20, 20)
    t_fg = (0, 0, 0) if top_color == ChessColor.WHITE else (255, 255, 255)
    pygame.draw.rect(screen, t_bg, TOP_CLOCK_RECT)
    pygame.draw.rect(screen, (100, 100, 100), TOP_CLOCK_RECT, 2)
    t_clock_txt = font_large.render(CLOCKS[top_color].standard_notation(), True, t_fg)
    screen.blit(t_clock_txt, t_clock_txt.get_rect(center=TOP_CLOCK_RECT.center))

    f_txt = font_small.render("F", True, (255, 255, 255))
    d_txt = font_small.render("1/2", True, (255, 255, 255))

    if show_top_buttons:
        # Top Flag
        t_flag_color = (200, 80, 80) if TOP_FLAG_BTN_RECT.collidepoint(mouse_pos) else (150, 40, 40)
        pygame.draw.rect(screen, t_flag_color, TOP_FLAG_BTN_RECT)
        pygame.draw.rect(screen, (200, 200, 200), TOP_FLAG_BTN_RECT, 2)
        screen.blit(f_txt, f_txt.get_rect(center=TOP_FLAG_BTN_RECT.center))

        # Top Draw
        t_draw_color = (100, 100, 150) if TOP_DRAW_BTN_RECT.collidepoint(mouse_pos) else (80, 80, 120)
        pygame.draw.rect(screen, t_draw_color, TOP_DRAW_BTN_RECT)
        pygame.draw.rect(screen, (200, 200, 200), TOP_DRAW_BTN_RECT, 2)
        screen.blit(d_txt, d_txt.get_rect(center=TOP_DRAW_BTN_RECT.center))

    # --- BOTTOM CLOCK ---
    b_bg = (220, 220, 220) if bottom_color == ChessColor.WHITE else (20, 20, 20)
    b_fg = (0, 0, 0) if bottom_color == ChessColor.WHITE else (255, 255, 255)
    pygame.draw.rect(screen, b_bg, BOTTOM_CLOCK_RECT)
    pygame.draw.rect(screen, (100, 100, 100), BOTTOM_CLOCK_RECT, 2)
    b_clock_txt = font_large.render(CLOCKS[bottom_color].standard_notation(), True, b_fg)
    screen.blit(b_clock_txt, b_clock_txt.get_rect(center=BOTTOM_CLOCK_RECT.center))

    # Bottom Flag
    b_flag_color = (200, 80, 80) if BOTTOM_FLAG_BTN_RECT.collidepoint(mouse_pos) else (150, 40, 40)
    pygame.draw.rect(screen, b_flag_color, BOTTOM_FLAG_BTN_RECT)
    pygame.draw.rect(screen, (200, 200, 200), BOTTOM_FLAG_BTN_RECT, 2)
    screen.blit(f_txt, f_txt.get_rect(center=BOTTOM_FLAG_BTN_RECT.center))

    # Bottom Draw
    b_draw_color = (100, 100, 150) if BOTTOM_DRAW_BTN_RECT.collidepoint(mouse_pos) else (80, 80, 120)
    pygame.draw.rect(screen, b_draw_color, BOTTOM_DRAW_BTN_RECT)
    pygame.draw.rect(screen, (200, 200, 200), BOTTOM_DRAW_BTN_RECT, 2)
    screen.blit(d_txt, d_txt.get_rect(center=BOTTOM_DRAW_BTN_RECT.center))

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

    flip_color = (180, 140, 80) if FLIP_BTN_RECT.collidepoint(mouse_pos) else (150, 110, 60)
    pygame.draw.rect(screen, flip_color, FLIP_BTN_RECT)
    pygame.draw.rect(screen, (200, 200, 200), FLIP_BTN_RECT, 2)
    flip_txt = font_small.render("Flip Board", True, (255, 255, 255))
    screen.blit(flip_txt, flip_txt.get_rect(center=FLIP_BTN_RECT.center))

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


def draw_mini_player(screen):
    global MINI_PLAYER_UI_STATE
    if MUSIC_MANAGER is None or MUSIC_MANAGER.state == music_manager.MediaPlayerState.OUTSIDE \
            or not MUSIC_MANAGER.does_user_allow():
        return

    mouse_pos = pygame.mouse.get_pos()
    pygame.font.init()
    font_small = pygame.font.SysFont("Arial", 16, bold=True)
    font_symbols = pygame.font.SysFont("Arial", 20, bold=True)
    font_time = pygame.font.SysFont("Arial", 16, bold=False)

    # 1. Background Box under the Board (Sleeker Darker Slate)
    pygame.draw.rect(screen, (20, 20, 25), BOTTOM_PANEL_BG)
    # The Highlight: A glowing blue line separating the board from the basement
    pygame.draw.line(screen, (100, 150, 200), (BOTTOM_PANEL_BG.x, BOTTOM_PANEL_BG.y),
                     (BOTTOM_PANEL_BG.right, BOTTOM_PANEL_BG.y), 3)

    track = MUSIC_MANAGER.get_current_track()
    if not track: return

    # 2. Left Side: Song Name & Time (Brighter text)
    name = track.name.replace("_", " ")
    # Icy blue text for the song name
    txt = font_small.render(name[:30], True, (150, 200, 255))
    screen.blit(txt, (BOTTOM_PANEL_BG.x + 20, BOTTOM_PANEL_BG.y + 20))

    total_seconds = track.length
    if MINI_PLAYER_UI_STATE["is_dragging"]:
        current_seconds = total_seconds * MINI_PLAYER_UI_STATE["drag_percent"]
    else:
        current_seconds = MUSIC_MANAGER.get_timestamp_seconds()

    current_seconds = min(current_seconds, total_seconds)

    cur_min, cur_sec = int(current_seconds // 60), int(current_seconds % 60)
    tot_min, tot_sec = int(total_seconds // 60), int(total_seconds % 60)

    time_str = f"{cur_min}:{cur_sec:02d} / {tot_min}:{tot_sec:02d}"
    time_surf = font_time.render(time_str, True, (180, 180, 180))
    screen.blit(time_surf, (BOTTOM_PANEL_BG.x + 20, BOTTOM_PANEL_BG.y + 45))

    # 3. Left Side: Add Songs Button (Dead for now, but looks better)
    is_add_hover = ADD_SONGS_BTN.collidepoint(mouse_pos)
    btn_col = (60, 60, 70) if is_add_hover else (40, 40, 50)
    border_col = (255, 255, 255) if is_add_hover else (100, 100, 100)
    pygame.draw.rect(screen, btn_col, ADD_SONGS_BTN, border_radius=5)
    pygame.draw.rect(screen, border_col, ADD_SONGS_BTN, 2, border_radius=5)
    add_txt = font_small.render("+ ADD SONGS", True, (200, 200, 200))
    screen.blit(add_txt, add_txt.get_rect(center=ADD_SONGS_BTN.center))

    # 4. Center Controls (With dynamic border highlights!)
    def draw_btn(rect, base_col, hover_col, symbol):
        is_hover = rect.collidepoint(mouse_pos)
        col = hover_col if is_hover else base_col
        pygame.draw.rect(screen, col, rect, border_radius=10)

        if is_hover:
            # THE HIGHLIGHT: A crisp white border pops up when hovered
            pygame.draw.rect(screen, (255, 255, 255), rect, 2, border_radius=10)

        # Perfect centering magic
        sym_surf = font_symbols.render(symbol, True, (255, 255, 255))
        screen.blit(sym_surf, sym_surf.get_rect(center=rect.center))

    draw_btn(MINI_PREV_BTN, (60, 100, 140), (100, 150, 200), "|<")

    play_sym = "||" if MUSIC_MANAGER.state == music_manager.MediaPlayerState.PLAYING else ">"
    # Play gets a dedicated green theme
    draw_btn(MINI_PLAY_BTN, (60, 140, 60), (100, 200, 100), play_sym)

    draw_btn(MINI_NEXT_BTN, (60, 100, 140), (100, 150, 200), ">|")

    # Shuffle gets a purple theme
    draw_btn(MINI_SHUFFLE_BTN, (100, 60, 140), (150, 100, 200), "S")

    # 5. Center: Interactable Progress Bar with GLOW
    bar_hover = MINI_PROGRESS_BAR.collidepoint(mouse_pos) or MINI_PLAYER_UI_STATE["is_dragging"]
    bg_col = (60, 60, 60) if bar_hover else (40, 40, 40)
    pygame.draw.rect(screen, bg_col, MINI_PROGRESS_BAR, border_radius=5)

    if total_seconds > 0:
        percentage = current_seconds / total_seconds
        fill_width = int(MINI_PROGRESS_BAR.width * percentage)
        fill_width = max(0, min(fill_width, MINI_PROGRESS_BAR.width))

        if fill_width > 0:
            fill_rect = pygame.Rect(MINI_PROGRESS_BAR.x, MINI_PROGRESS_BAR.y, fill_width, MINI_PROGRESS_BAR.height)
            # Brighter cyan fill for the music progress
            pygame.draw.rect(screen, (50, 200, 255), fill_rect, border_radius=5)

        if bar_hover:
            handle_x = MINI_PROGRESS_BAR.x + fill_width

            # The Magic Glow: A transparent larger circle under the main handle
            glow_surface = pygame.Surface((30, 30), pygame.SRCALPHA)
            pygame.draw.circle(glow_surface, (50, 200, 255, 80), (15, 15), 12)
            screen.blit(glow_surface, (handle_x - 15, MINI_PROGRESS_BAR.centery - 15))

            # The solid white handle
            pygame.draw.circle(screen, (255, 255, 255), (handle_x, MINI_PROGRESS_BAR.centery), 7)


def draw_system_alerts(screen):
    """Paints the Chat Box in the bottom left corner, ONLY if the basement is open."""
    global ACTIVE_ALERTS

    # 1. Tick down the clocks on all active messages
    for alert in ACTIVE_ALERTS:
        alert["time_left"] -= DT

    # 2. The Conveyor Belt Edge: Delete any messages that hit 0 seconds
    ACTIVE_ALERTS = [a for a in ACTIVE_ALERTS if a["time_left"] > 0]

    # 3. THE BOUNCER: If the extended screen is off, don't draw anything!
    if SCREEN_HEIGHT <= WINDOW_SIZE:
        return

    # 4. Draw the Chat Box Background (Bottom Left Corner)
    chat_rect = pygame.Rect(0, WINDOW_SIZE, SIDE_PANEL_WIDTH, BOTTOM_PANEL_HEIGHT)
    pygame.draw.rect(screen, (20, 20, 24), chat_rect)  # Dark terminal look

    # Draw some sleek borders to separate it from the diary and the music player
    pygame.draw.line(screen, (60, 60, 70), (0, WINDOW_SIZE), (SIDE_PANEL_WIDTH, WINDOW_SIZE), 2)
    pygame.draw.line(screen, (100, 150, 200), (SIDE_PANEL_WIDTH, WINDOW_SIZE), (SIDE_PANEL_WIDTH, SCREEN_HEIGHT), 2)

    # 5. Paint the actual text inside the box
    font_alert = pygame.font.SysFont("Courier New", 14, bold=True)
    start_y = WINDOW_SIZE + 15

    for i, alert in enumerate(ACTIVE_ALERTS):
        # We use a cool hacker green color for the system alerts
        text_surf = font_alert.render(f"> {alert['text']}", True, (100, 255, 100))
        screen.blit(text_surf, (15, start_y + (i * 22)))



def draw_live_diary(screen, move_log):
    """Paints the move history on the FAR LEFT."""
    pygame.draw.rect(screen, (25, 25, 30), (0, 0, SIDE_PANEL_WIDTH, SCREEN_HEIGHT))
    pygame.draw.line(screen, (80, 80, 80), (SIDE_PANEL_WIDTH, 0), (SIDE_PANEL_WIDTH, SCREEN_HEIGHT), 2)

    pygame.font.init()
    font_header = pygame.font.SysFont("Arial", 24, bold=True)
    font_moves = pygame.font.SysFont("Courier New", 18, bold=True)

    header = font_header.render("MOVE HISTORY", True, (150, 150, 150))
    screen.blit(header, (SIDE_PANEL_WIDTH // 2 - header.get_width() // 2, 15))

    y_start = 60
    line_height = 25
    visible_log = move_log[-40:] if len(move_log) > 40 else move_log

    for i in range(0, len(visible_log), 2):
        turn_num = (i // 2) + 1
        white_move = visible_log[i].algebraic_notation
        black_move = visible_log[i + 1].algebraic_notation if (i + 1) < len(visible_log) else ""

        move_str = f"{turn_num:2}. {white_move:6} {black_move}"
        color = (200, 200, 200) if i >= len(visible_log) - 2 else (120, 120, 120)

        move_surf = font_moves.render(move_str, True, color)
        screen.blit(move_surf, (20, y_start + (i // 2) * line_height))

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

# <editor-fold desc="PROMOTION MENU">
def draw_promotion_menu(screen, color: ChessColor, cache):
    # 1. Dim the background OVER THE BOARD, not over the diary!
    dim_surface = pygame.Surface((WINDOW_SIZE, WINDOW_SIZE))
    dim_surface.set_alpha(150)
    dim_surface.fill((0, 0, 0))
    screen.blit(dim_surface, (BOARD_X_OFFSET, 0))

    # 2. Draw the white menu box in the dead center of the BOARD
    menu_width = 4 * SQUARE_SIZE
    menu_height = SQUARE_SIZE
    # Add the offset!
    start_x = BOARD_X_OFFSET + (WINDOW_SIZE - menu_width) // 2
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

def draw_piece(screen, piece: ChessPiece, cache):
    if piece.position is None: return
    row, col = piece.position.row, piece.position.col

    # THE MAGIC MIRROR
    v_row, v_col = get_visual_row_col(row, col)

    img = get_piece_image(piece, cache)
    center_x = BOARD_X_OFFSET + (v_col * SQUARE_SIZE + SQUARE_SIZE // 2)
    center_y = v_row * SQUARE_SIZE + SQUARE_SIZE // 2
    rect = img.get_rect(center=(center_x, center_y))
    screen.blit(img, rect)

def draw_pieces(screen, board: Board, cache, dragged_piece=None):
    for piece in board.get_all_pieces():
        # Do not draw the piece if it is currently being dragged!
        if piece is not dragged_piece:
            draw_piece(screen, piece, cache)

def highlight_square(screen, square: SquarePosition, color: tuple, alpha: int = 125, thickness: int = 8):
    if square is None: return
    glass_pane = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)
    rgba_color = (color[0], color[1], color[2], alpha)
    pygame.draw.rect(glass_pane, rgba_color, glass_pane.get_rect(), width=thickness)

    # THE MAGIC MIRROR
    v_row, v_col = get_visual_row_col(square.row, square.col)

    x = BOARD_X_OFFSET + (v_col * SQUARE_SIZE)
    y = v_row * SQUARE_SIZE
    screen.blit(glass_pane, (x, y))

def get_square_center(pos: SquarePosition):
    """Returns the exact (x, y) pixel coordinates of the middle of a square."""
    x = pos.col * SQUARE_SIZE + SQUARE_SIZE // 2
    y = pos.row * SQUARE_SIZE + SQUARE_SIZE // 2
    return x, y

def draw_arrow(screen, start_square: SquarePosition, end_square: SquarePosition, color, padding=15, thickness=6):
    # THE MAGIC MIRROR
    v_start_r, v_start_c = get_visual_row_col(start_square.row, start_square.col)
    v_end_r, v_end_c = get_visual_row_col(end_square.row, end_square.col)

    start_x = BOARD_X_OFFSET + (v_start_c * SQUARE_SIZE + SQUARE_SIZE // 2)
    start_y = v_start_r * SQUARE_SIZE + SQUARE_SIZE // 2

    end_x = BOARD_X_OFFSET + (v_end_c * SQUARE_SIZE + SQUARE_SIZE // 2)
    end_y = v_end_r * SQUARE_SIZE + SQUARE_SIZE // 2

    dx_squares = abs(v_end_c - v_start_c)
    dy_squares = abs(v_end_r - v_start_r)

    is_knight_move = (dx_squares == 2 and dy_squares == 1) or (dx_squares == 1 and dy_squares == 2)

    snip_length = 15
    arrow_length = 15

    if is_knight_move:
        if dx_squares == 2:
            corner_x = end_x
            corner_y = start_y
        else:
            corner_x = start_x
            corner_y = end_y

        end_angle = math.atan2(end_y - corner_y, end_x - corner_x)
        start_angle = math.atan2(corner_y - start_y, corner_x - start_x)

        adj_start_x = start_x + padding * math.cos(start_angle)
        adj_start_y = start_y + padding * math.sin(start_angle)

        adj_end_x = end_x - padding * math.cos(end_angle)
        adj_end_y = end_y - padding * math.sin(end_angle)

        stick_end_x = adj_end_x - snip_length * math.cos(end_angle)
        stick_end_y = adj_end_y - snip_length * math.sin(end_angle)

        pygame.draw.line(screen, color, (adj_start_x, adj_start_y), (corner_x, corner_y), thickness)
        pygame.draw.line(screen, color, (corner_x, corner_y), (stick_end_x, stick_end_y), thickness)

        tip = (adj_end_x, adj_end_y)
        left = (adj_end_x - arrow_length * math.cos(end_angle - math.pi / 6), adj_end_y - arrow_length * math.sin(end_angle - math.pi / 6))
        right = (adj_end_x - arrow_length * math.cos(end_angle + math.pi / 6), adj_end_y - arrow_length * math.sin(end_angle + math.pi / 6))
        pygame.draw.polygon(screen, color, [tip, left, right])

    else:
        angle = math.atan2(end_y - start_y, end_x - start_x)

        adj_start_x = start_x + padding * math.cos(angle)
        adj_start_y = start_y + padding * math.sin(angle)

        adj_end_x = end_x - padding * math.cos(angle)
        adj_end_y = end_y - padding * math.sin(angle)

        stick_end_x = adj_end_x - snip_length * math.cos(angle)
        stick_end_y = adj_end_y - snip_length * math.sin(angle)

        pygame.draw.line(screen, color, (adj_start_x, adj_start_y), (stick_end_x, stick_end_y), thickness)

        tip = (adj_end_x, adj_end_y)
        left = (adj_end_x - arrow_length * math.cos(angle - math.pi / 6), adj_end_y - arrow_length * math.sin(angle - math.pi / 6))
        right = (adj_end_x - arrow_length * math.cos(angle + math.pi / 6), adj_end_y - arrow_length * math.sin(angle + math.pi / 6))
        pygame.draw.polygon(screen, color, [tip, left, right])


def draw_game_over_screen(screen, winner_color: ChessColor, is_draw=False):
    # 1. Dim the background
    dim_surface = pygame.Surface((WINDOW_SIZE, WINDOW_SIZE))
    dim_surface.set_alpha(180)
    dim_surface.fill((0, 0, 0))
    screen.blit(dim_surface, (BOARD_X_OFFSET, 0))

    # 2. Draw the menu box
    menu_width = 300
    menu_height = 160
    start_x = BOARD_X_OFFSET + (WINDOW_SIZE - menu_width) // 2
    start_y = (WINDOW_SIZE - menu_height) // 2

    pygame.draw.rect(screen, (40, 40, 40), (start_x, start_y, menu_width, menu_height))
    pygame.draw.rect(screen, (220, 220, 220), (start_x, start_y, menu_width, menu_height), 4)

    # 3. Draw the Winner Text
    pygame.font.init()
    font_large = pygame.font.SysFont("Arial", 40, bold=True)
    font_small = pygame.font.SysFont("Arial", 28, bold=True)

    text = "DRAW!" if is_draw else f"{winner_color.value} WINS!"
    board_center_x = BOARD_X_OFFSET + (WINDOW_SIZE // 2)

    text_surface = font_large.render(text, True, (255, 255, 255))
    text_rect = text_surface.get_rect(center=(board_center_x, start_y + 45))
    screen.blit(text_surface, text_rect)

    # 4. Draw the Buttons based on Game Mode
    is_online = PREFERENCES["game_mode"] == "Online"

    if is_online:
        # --- REMATCH BUTTON ---
        rematch_rect = pygame.Rect(0, 0, 130, 50)
        rematch_rect.center = (board_center_x - 75, start_y + 110)
        pygame.draw.rect(screen, (100, 200, 100), rematch_rect)
        pygame.draw.rect(screen, (255, 255, 255), rematch_rect, 2)
        rm_text = font_small.render("Rematch", True, (0, 0, 0))
        screen.blit(rm_text, rm_text.get_rect(center=rematch_rect.center))

        # --- MENU BUTTON ---
        menu_rect = pygame.Rect(0, 0, 130, 50)
        menu_rect.center = (board_center_x + 75, start_y + 110)
        pygame.draw.rect(screen, (200, 100, 100), menu_rect)
        pygame.draw.rect(screen, (255, 255, 255), menu_rect, 2)
        mn_text = font_small.render("Menu", True, (255, 255, 255))
        screen.blit(mn_text, mn_text.get_rect(center=menu_rect.center))

        return rematch_rect, menu_rect
    else:
        # --- NORMAL AGAIN BUTTON ---
        btn_rect = pygame.Rect(0, 0, 140, 50)
        btn_rect.center = (board_center_x, start_y + 110)
        pygame.draw.rect(screen, (100, 200, 100), btn_rect)
        pygame.draw.rect(screen, (255, 255, 255), btn_rect, 2)
        btn_text = font_small.render("Again?", True, (0, 0, 0))
        screen.blit(btn_text, btn_text.get_rect(center=btn_rect.center))

        return btn_rect, None

# </editor-fold>

# <editor-fold desc="GLOBAL VARIABLES">
PYGAME = pygame
SCREEN = None
PLAYERS = {}
CLOCKS = {}

BOARD_FLIPPED = False
BOARD = Board()

PLAYERS[ChessColor.WHITE] = Player(BOARD, ChessColor.WHITE)
PLAYERS[ChessColor.BLACK] = Player(BOARD, ChessColor.BLACK)

CLOCKS[ChessColor.WHITE] = ChessClock(ChessColor.WHITE, STARTING_TIME)
CLOCKS[ChessColor.BLACK] = ChessClock(ChessColor.BLACK, STARTING_TIME)

IMAGE_CACHE = {}

NOTATION_FONT = None  # We will initialize this inside main()

ONLINE_CONNECTION = None

CHESS_MODEL = None
EVALUATION_CACHE = {}

ACTIVE_ALERTS = []

# </editor-fold>

#<editor-fold desc="BOT">

#
# # <editor-fold desc="NEURAL NETWORK">
#
# import os
# import io
# import json
# import math
# import numpy as np
#
# # We only load these heavy tools if we actually need them!
# from keras.models import load_model, Sequential
# from keras.layers import Dense, Dropout, Input
# from keras.callbacks import EarlyStopping
# import zstandard as zstd
#
# # --- THE LABEL ON THE BOX ---
# # The Iron Anchor ensures we always find the brain inside the Blue Box (.exe bundle)
# CHESS_BRAIN_PATH = get_asset_path(os.path.join("models", "chess_brain.keras"))
#
#
# # ==========================================
# # 1. THE TRANSLATOR (FEN -> 768 Switches)
# # ==========================================
# def fen_to_features(fen: str):
#     """
#     ELI5: The Neural Network doesn't speak 'Chess', it only speaks 'Numbers'.
#     We have an empty tray of 768 light switches.
#     We walk through the board and flip the correct switch for every piece we find.
#     """
#     features = np.zeros(768, dtype=np.float32)
#
#     piece_to_index = {
#         'P': 0, 'N': 1, 'B': 2, 'R': 3, 'Q': 4, 'K': 5,  # White
#         'p': 6, 'n': 7, 'b': 8, 'r': 9, 'q': 10, 'k': 11  # Black
#     }
#
#     board_part = fen.split()[0]
#     rows = board_part.split('/')
#
#     for row_idx, row in enumerate(rows):
#         col_idx = 0
#         for char in row:
#             if char.isdigit():
#                 col_idx += int(char)  # Skip the empty squares
#             else:
#                 # Math magic to find the exact light switch number
#                 piece_idx = piece_to_index[char]
#                 square_idx = row_idx * 8 + col_idx
#                 features[piece_idx * 64 + square_idx] = 1.0
#                 col_idx += 1
#
#     return features
#
#
# # ==========================================
# # 2. THE ORACLE (Evaluating the Board)
# # ==========================================
# def evaluate_position(board):
#     """
#     The Oracle looks at the board, translates it to switches, and asks the Brain.
#     Returns 0.0 (Black is crushing it) to 1.0 (White is crushing it).
#     """
#     global CHESS_MODEL, EVALUATION_CACHE
#
#     current_fen = board.generate_fen()
#
#     # THE SPEED HACK: Did we already calculate this board today?
#     if current_fen in EVALUATION_CACHE:
#         return EVALUATION_CACHE[current_fen]
#
#     # WAKE UP THE BRAIN: If it's asleep, load it from the exact path.
#     if CHESS_MODEL is None:
#         try:
#             CHESS_MODEL = load_model(CHESS_BRAIN_PATH)
#             print("AI Brain Loaded Successfully.")
#         except Exception as e:
#             print(f"Warning: Brain surgery failed. {e}")
#             return 0.5  # If the brain is missing, guess a tie (0.5)
#
#     # Translate and Ask
#     features = fen_to_features(current_fen)
#
#     # We reshape because Keras expects a "list of boards", not just one!
#     prediction = CHESS_MODEL.predict(features.reshape(1, -1), verbose=0)
#     score = float(prediction[0][0])
#
#     EVALUATION_CACHE[current_fen] = score
#     return score
#
#
# def ai_get_evaluation(board):
#     """A simple wrapper for your other AI tools to use."""
#     return evaluate_position(board)
#
#
# # ==========================================
# # 3. THE BEGINNER BOT (Shallow Search)
# # ==========================================
# def get_beginner_bot_move(board, ai_color: ChessColor):
#     """
#     The Beginner Brain: Looks exactly 1 move ahead.
#     It simulates every legal move, asks the Oracle for a score, and picks the best one.
#     """
#     best_move = None
#
#     # White wants the highest score (1.0). Black wants the lowest score (0.0).
#     best_value = -float('inf') if ai_color == ChessColor.WHITE else float('inf')
#
#     moves_to_check = []
#
#     # 1. Gather all legal moves for our color
#     for piece in board.get_all_pieces():
#         if piece.color == ai_color:
#             for move in piece.legal_moves.values():
#                 moves_to_check.append(move)
#
#     # Shuffle them so the bot doesn't play the exact same game every time!
#     random.shuffle(moves_to_check)
#
#     # 2. Test every move in our imagination
#     for move in moves_to_check:
#         board.execute_move(move, is_imagining=True)
#         current_eval = evaluate_position(board)
#         board.undo_move()
#
#         # 3. Did we find a better move?
#         if ai_color == ChessColor.WHITE:
#             if current_eval > best_value:
#                 best_value = current_eval
#                 best_move = move
#         else:
#             if current_eval < best_value:
#                 best_value = current_eval
#                 best_move = move
#
#     # Safety Net: If something goes horribly wrong, pick a random move.
#     if best_move is None and moves_to_check:
#         return random.choice(moves_to_check)
#
#     return best_move
#
#
# # ==========================================
# # 4. THE DATA FACTORY & TRAINING YARD
# # ==========================================
# def squish_score(cp: int) -> float:
#     """Turns Centipawns (-300 to +300) into a Win Probability (0.0 to 1.0)."""
#     return 1 / (1 + math.exp(-0.004 * cp))
#
#
# def build_chess_database(zst_file_path: str, output_name: str, max_rows: int = 10000):
#     """Eats a compressed .zst file line by line without exploding your RAM."""
#     X = []
#     y = []
#
#     print(f"Factory started. Streaming massive file: {zst_file_path}...")
#
#     try:
#         with open(zst_file_path, 'rb') as compressed_file:
#             dctx = zstd.ZstdDecompressor()
#             with dctx.stream_reader(compressed_file) as reader:
#                 text_stream = io.TextIOWrapper(reader, encoding='utf-8')
#
#                 for i, line in enumerate(text_stream):
#                     if i >= max_rows:
#                         break  # THE SAFETY VALVE
#
#                     data = json.loads(line)
#                     fen = data['fen']
#
#                     try:
#                         best_eval = data['evals'][0]['pvs'][0]
#
#                         if 'mate' in best_eval:
#                             mate_in = best_eval['mate']
#                             score = 1.0 if mate_in > 0 else 0.0
#                         else:
#                             cp = best_eval['cp']
#                             score = squish_score(cp)
#
#                         X.append(fen_to_features(fen))
#                         y.append(score)
#
#                     except (KeyError, IndexError):
#                         continue
#
#                     if (i + 1) % 5000 == 0:
#                         print(f"Processed {i + 1} boards...")
#
#         np.savez_compressed(f'data/{output_name}.npz', X=np.array(X), y=np.array(y))
#         print(f"Success! Processed {len(X)} valid boards and saved to data/{output_name}.npz")
#
#     except FileNotFoundError:
#         print(f"ERROR: Could not find the file at {zst_file_path}. Check the path!")
#
#
# def train_chess_brain():
#     """Load the processed data and train the AI."""
#     print("Loading data...")
#     data = np.load('data/chess_training_data.npz')
#     X = data['X']
#     y = data['y']
#     print("Data loaded.")
#
#     model = Sequential([
#         Input(shape=(768,)),
#         Dense(512, activation='relu'),
#         Dropout(0.2),
#         Dense(256, activation='relu'),
#         Dense(128, activation='relu'),
#         Dense(1, activation='sigmoid')
#     ])
#
#     model.compile(
#         optimizer='adam',
#         loss='mean_squared_error',
#         metrics=['mae']
#     )
#
#     stop_early = EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True)
#
#     print("Training Beginning. This might take a few minutes...")
#     model.fit(
#         X, y,
#         epochs=250,
#         batch_size=64,
#         callbacks=[stop_early]
#     )
#
#     # Save to the exact path where the game expects to find it!
#     model.save(CHESS_BRAIN_PATH)
#     print(f"Success! The Chess Brain is saved exactly at {CHESS_BRAIN_PATH}")
#
#
# def test_ai_without_graphics():
#     """Runs a ghost board in memory so you don't have to load Pygame UI."""
#     print("Summoning ghost board...")
#     # Requires the global STARTING_POSITION variable to exist
#     ghost_board = Board(STARTING_POSITION)
#
#     print(f"Ghost Board FEN: {ghost_board.generate_fen()}")
#     features = fen_to_features(ghost_board.generate_fen())
#     print(f"Features Array Shape: {features.shape}")
#
#     score = evaluate_position(ghost_board)
#     print(f"The Oracle scores this position as: {score}")
#
#
# # </editor-fold>

def get_random_bot_move(board, ai_color: ChessColor): #PLACEHOLDER
    """The AI Brain: Gathers every possible move and pulls one out of a hat."""
    all_possible_moves = []

    # 1. Walk through the whole board and look at our pieces
    for piece in board.get_all_pieces():
        if piece.color == ai_color:
            # 2. Dump every legal move this piece has into our giant bucket
            for move in piece.legal_moves.values():
                all_possible_moves.append(move)

    if not all_possible_moves:
        return None  # Checkmate or Stalemate, nothing to do!

    # 3. Close eyes, reach into bucket, pull out a random move
    chosen_move = random.choice(all_possible_moves)

    # 4. If by pure luck the random move is a pawn promotion, default_pack to a Queen!
    if chosen_move.move_type == MoveType.PROMOTION:
        chosen_move.promotion_choice = ChessPieceType.QUEEN

    return chosen_move



def get_bot_move(board, ai_color: ChessColor, bot_id: str):
    """The new Brain Loader. Pulls the pre-loaded module from RAM and fires it."""

    if bot_id not in LOADED_BOTS:
        print(f"CRITICAL ERROR: Bot {bot_id} not found in loaded bots!")
        return None

    bot_data = LOADED_BOTS[bot_id]
    bot_type = bot_data.get("type")

    # --- PATH A: CUSTOM EXTERNAL SCRIPT ---
    if bot_type == "script":
        func_name = bot_data.get("function_name")
        live_module = bot_data.get("live_module")  # We grab the brain out of the jar!

        if live_module and hasattr(live_module, func_name):
            try:
                bot_function = getattr(live_module, func_name)
                # Run the function! Because we ran init_bot earlier, it already knows what a 'Move' is!
                return bot_function(board, ai_color)
            except Exception as e:
                print(f"ERROR: {bot_id}'s script crashed during thinking! Reason: {e}")
                return None
        else:
            print(f"ERROR: Could not find function '{func_name}' inside {bot_id}'s live module.")
            return None

    # --- PATH B: ENGINE FALLBACK (Should rarely trigger now if factory prints scripts) ---
    elif bot_type == "engine":
        depth = bot_data.get("depth", 4)
        elo = bot_data.get("elo", 9999)
        return stockfish.get_stockfish_move(board, elo=elo, depth=depth)

    else:
        print(f"ERROR: Unknown bot type '{bot_type}' in JSON.")
        return None

#</editor-fold>

# <editor-fold desc="RUN MAIN MENU">

#<editor-fold desc="CLASS SIGNAL">
class MenuSignal(Enum):
    CONTINUE = 0
    BACK = 1
    QUIT = 2
    START_GAME = 3
    MAIN_MENU = 5
    OPEN_PLAYLIST = 6
    PASS = True
    FAIL = False
#</editor-fold>

def quit_game():
    if PREFERENCES: save_preferences()
    pygame.quit()
    sys.exit()


def run_waiting_room_screen():
    global SCREEN, FPS, ONLINE_CONNECTION
    pygame_clock = pygame.time.Clock()

    # The new Return Door!
    return_rect = pygame.Rect((SCREEN_WIDTH // 2) - 150, SCREEN_HEIGHT - 100, 300, 60)

    # We stay in this loop drawing the screen until the Referee says "START"
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return MenuSignal.QUIT

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if return_rect.collidepoint(event.pos):
                    return MenuSignal.BACK

        # 1. Check the Mailbox!
        if ONLINE_CONNECTION:
            tag, payload = ONLINE_CONNECTION.peek_mailbox()

            if tag == "SYNC":
                ONLINE_CONNECTION.sync_data = json.loads(payload)
                print("[LOBBY] Downloaded match data from server.")

            elif tag == "START":
                print("[LOBBY] The Starting Gun fired! Let's play.")
                return MenuSignal.START_GAME

            elif tag == "DISCONNECT":
                print("[LOBBY] The Referee vanished. Going back to menu.")
                return MenuSignal.BACK

        # 2. Draw the Waiting Room
        my_color = ONLINE_CONNECTION.color if ONLINE_CONNECTION and ONLINE_CONNECTION.color else "Unknown"
        draw_waiting_room_page(SCREEN, my_color, return_rect)

        pygame.display.flip()
        pygame_clock.tick(FPS)


def run_view_pack_screen(pack_name):
    global SCREEN, FPS
    pygame_clock = pygame.time.Clock()

    # Load the tracks into memory so we can show them
    if pack_name not in music_manager.LOADED_PACKS:
        MUSIC_MANAGER.load_music_pack(pack_name)
    tracks = music_manager.LOADED_PACKS[pack_name].tracks

    scroll_y = 0
    scroll_speed = 30
    clip_rect = pygame.Rect(0, 120, SCREEN_WIDTH, SCREEN_HEIGHT - 220)

    # Elevator controls calculation
    card_height = 70
    total_content_height = len(tracks) * card_height
    max_scroll = max(0, total_content_height - clip_rect.height + 20)

    track_rects = []  # The painter will fill this for us

    # --- SCROLLBAR STATE ---
    scrollbar_dragging = False
    drag_offset_y = 0

    while True:
        # Calculate scrollbar positions every frame
        track_rect = pygame.Rect(SCREEN_WIDTH - 30, clip_rect.y + 5, 12, clip_rect.height - 10)

        if max_scroll > 0:
            thumb_height = max(40, (clip_rect.height / total_content_height) * track_rect.height)
            thumb_y = track_rect.y + (scroll_y / max_scroll) * (track_rect.height - thumb_height)
            thumb_rect = pygame.Rect(track_rect.x, thumb_y, track_rect.width, thumb_height)
        else:
            thumb_rect = None

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return MenuSignal.QUIT

            # --- THE SCROLL WHEEL ---
            if event.type == pygame.MOUSEWHEEL:
                scroll_y -= event.y * scroll_speed
                scroll_y = max(0, min(scroll_y, max_scroll))

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:

                # 1. INTERACTABLE SCROLLBAR: DRAG START
                if thumb_rect and thumb_rect.collidepoint(event.pos):
                    scrollbar_dragging = True
                    drag_offset_y = event.pos[1] - thumb_rect.y
                elif max_scroll > 0 and track_rect.collidepoint(event.pos):
                    # Jump scroll!
                    if event.pos[1] > thumb_rect.bottom:
                        scroll_y = min(max_scroll, scroll_y + clip_rect.height)
                    elif event.pos[1] < thumb_rect.top:
                        scroll_y = max(0, scroll_y - clip_rect.height)

                # 2. Return Button
                elif RETURN_BTN_RECT.collidepoint(event.pos):
                    return MenuSignal.BACK

                # 3. Track Action Buttons
                elif clip_rect.collidepoint(event.pos):
                    for item in track_rects:
                        if item["next"].collidepoint(event.pos):
                            MUSIC_MANAGER.add_track_next(item["track"])
                            print(f"Added {item['track'].name} to play next.")
                        elif item["end"].collidepoint(event.pos):
                            MUSIC_MANAGER.add_track_last(item["track"])
                            print(f"Added {item['track'].name} to end of playlist.")

            # --- INTERACTABLE SCROLLBAR: DRAG RELEASE ---
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                scrollbar_dragging = False

            # --- INTERACTABLE SCROLLBAR: DRAG MOTION ---
            if event.type == pygame.MOUSEMOTION:
                if scrollbar_dragging and max_scroll > 0:
                    new_thumb_y = event.pos[1] - drag_offset_y
                    new_thumb_y = max(track_rect.y, min(new_thumb_y, track_rect.bottom - thumb_height))
                    scroll_percent = (new_thumb_y - track_rect.y) / (track_rect.height - thumb_height)
                    scroll_y = scroll_percent * max_scroll

        # Pass the new scrollbar data to the painter!
        draw_view_pack_page(SCREEN, pack_name, tracks, scroll_y, track_rects, track_rect, thumb_rect, max_scroll)
        pygame.display.flip()
        pygame_clock.tick(FPS)

def run_playlist_screen():
    global SCREEN, FPS
    pygame_clock = pygame.time.Clock()

    # Create the blueprint (hitboxes) for the room
    ui_rects = {
        "clear": pygame.Rect((SCREEN_WIDTH // 2) - 180, 150, 360, 45),
        "packs": [],
        "return": pygame.Rect((SCREEN_WIDTH // 2) - 150, SCREEN_HEIGHT - 100, 300, 60)
    }

    # Mathematically stack the packs right in the middle
    pack_start_y = 220
    for i, pack_name in enumerate(music_manager.MUSIC_PACK_NAMES):
        y = pack_start_y + (i * 60)
        x = (SCREEN_WIDTH // 2) - 180

        main_rect = pygame.Rect(x, y, 360, 50)
        add_rect = pygame.Rect(main_rect.right - 190, y + 8, 85, 34)
        view_rect = pygame.Rect(main_rect.right - 95, y + 8, 85, 34)

        ui_rects["packs"].append({
            "pack": pack_name,
            "main": main_rect,
            "add": add_rect,
            "view": view_rect
        })

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return MenuSignal.QUIT

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Did we click Return?
                if ui_rects["return"].collidepoint(event.pos):
                    return MenuSignal.BACK

                # Did we click Clear?
                if ui_rects["clear"].collidepoint(event.pos):
                    MUSIC_MANAGER.clear_playlist()
                    print("Playlist Cleared.")

                # Did we click inside a Music Pack?
                for item in ui_rects["packs"]:
                    if item["add"].collidepoint(event.pos):
                        MUSIC_MANAGER.add_pack(item["pack"])
                        print(f"Added all tracks from {item['pack']}.")

                    elif item["view"].collidepoint(event.pos):
                        # Dive deeper into the specific pack!
                        result = run_view_pack_screen(item["pack"])
                        if result == MenuSignal.QUIT:
                            return MenuSignal.QUIT

        # Paint the screen
        draw_playlist_page(SCREEN, ui_rects)
        pygame.display.flip()
        pygame_clock.tick(FPS)

def run_audio_settings_screen():
    global SCREEN, FPS
    pygame_clock = pygame.time.Clock()
    is_dragging_slider = False

    ui_rects = {
        "settings": [],
        "volume": None,
        "clear": None,
        "packs": []
    }

    # Left Column (Shrunk down to 320x50, tighter spacing)
    left_center_x = SCREEN_WIDTH // 4
    start_y = 200
    for i in range(4):
        rect = pygame.Rect(0, 0, 320, 50)
        rect.center = (left_center_x, start_y + (i * 65))
        ui_rects["settings"].append(rect)

    # Volume Slider
    vol_rect = pygame.Rect(0, 0, 320, 50)
    vol_rect.center = (left_center_x, start_y + (4 * 65))
    ui_rects["volume"] = vol_rect

    # Right Column (Shrunk down to 360x45, tighter spacing)
    right_center_x = (SCREEN_WIDTH * 3) // 4

    clear_rect = pygame.Rect(0, 0, 360, 45)
    clear_rect.center = (right_center_x, 200)
    ui_rects["clear"] = clear_rect

    pack_start_y = 260
    for i, pack_name in enumerate(music_manager.MUSIC_PACK_NAMES):
        y = pack_start_y + (i * 60)

        x = right_center_x - 180
        main_rect = pygame.Rect(x, y, 360, 50)
        add_rect = pygame.Rect(main_rect.right - 190, y + 8, 85, 34)
        view_rect = pygame.Rect(main_rect.right - 95, y + 8, 85, 34)

        ui_rects["packs"].append({
            "pack": pack_name,
            "main": main_rect,
            "add": add_rect,
            "view": view_rect
        })

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return MenuSignal.QUIT

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if RETURN_BTN_RECT.collidepoint(event.pos):
                    return MenuSignal.BACK

                if ui_rects["volume"].collidepoint(event.pos):
                    is_dragging_slider = True

                for i, rect in enumerate(ui_rects["settings"]):
                    if rect.collidepoint(event.pos):
                        btn_name = AUDIO_SETTINGS_OPTIONS[i]
                        if "Master" in btn_name:
                            PREFERENCES["master_mute"] = not PREFERENCES["master_mute"]
                        elif "Music" in btn_name:
                            PREFERENCES["music_mute"] = not PREFERENCES["music_mute"]
                        elif "SFX" in btn_name:
                            PREFERENCES["sfx_mute"] = not PREFERENCES["sfx_mute"]

                        play_music(LAST_REQUESTED_MUSIC)
                        save_preferences()

                if ui_rects["clear"].collidepoint(event.pos):
                    MUSIC_MANAGER.clear_playlist()
                    print("Playlist Cleared.")

                for item in ui_rects["packs"]:
                    if item["add"].collidepoint(event.pos):
                        MUSIC_MANAGER.add_pack(item["pack"])
                        print(f"Added all tracks from {item['pack']}.")
                    elif item["view"].collidepoint(event.pos):
                        result = run_view_pack_screen(item["pack"])
                        if result == MenuSignal.QUIT:
                            return MenuSignal.QUIT

            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if is_dragging_slider:
                    is_dragging_slider = False
                    save_preferences()

            if event.type == pygame.MOUSEMOTION:
                if is_dragging_slider:
                    vol_rect = ui_rects["volume"]
                    relative_x = event.pos[0] - vol_rect.x
                    new_vol = max(0.0, min(1.0, relative_x / vol_rect.width))
                    PREFERENCES["volume"] = new_vol
                    update_audio_volume()
                    if MUSIC_MANAGER:
                        MUSIC_MANAGER.set_volume(new_vol)

        draw_audio_settings_page(SCREEN, ui_rects)
        pygame.display.flip()
        pygame_clock.tick(FPS)

def run_video_settings_screen():
    global SCREEN, FPS, DT  # We MUST bring these in to change the game's heartbeat!
    pygame_clock = pygame.time.Clock()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return MenuSignal.QUIT

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # 1. Return Button
                if RETURN_BTN_RECT.collidepoint(event.pos):
                    return

                # 2. Dynamic Settings Buttons
                for i, rect in enumerate(VIDEO_SETTINGS_RECTS):
                    if rect.collidepoint(event.pos):
                        btn_name = VIDEO_SETTINGS_OPTIONS[i]

                        if btn_name == "FPS":
                            fps_list = [30, 60, 120, 144]
                            curr = PREFERENCES["fps"]
                            idx = fps_list.index(curr) if curr in fps_list else 1
                            new_fps = fps_list[(idx + 1) % len(fps_list)]

                            PREFERENCES["fps"] = new_fps
                            # Update the actual engine speed!
                            FPS = new_fps
                            DT = 1 / FPS
                            save_preferences()

                        elif btn_name == "Animation Time":
                            times = [0.0, 0.1, 0.2, 0.3, 0.5,60.0]
                            curr = PREFERENCES["animation_time"]
                            idx = times.index(curr) if curr in times else 2
                            PREFERENCES["animation_time"] = times[(idx + 1) % len(times)]
                            save_preferences()

        draw_video_settings_page(SCREEN)
        pygame.display.flip()
        pygame_clock.tick(FPS)


def run_create_openings_screen():
    global SCREEN, BOARD, IMAGE_CACHE, FPS, CURRENT_MUSIC, FORGE_SAVE_MODE
    pygame_clock = pygame.time.Clock()

    if CURRENT_MUSIC == "menu_music":
        dj.music.stop()
        CURRENT_MUSIC = None
    if MUSIC_MANAGER.is_playlist_empty():
        MUSIC_MANAGER.add_pack("default_pack")

    update_window_size(in_game=True)
    MUSIC_MANAGER.continue_playlist()

    BOARD.load_fen(STARTING_POSITION)

    picking_piece = None
    is_dragging = False
    promotion_pending = None
    promotion_rects = []
    drawn_arrows = set()
    highlighted_squares = set()
    right_click_start = None

    while True:
        update_media_player()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return MenuSignal.QUIT

            temp_handle = handle_media_player_event(event)

            if temp_handle == MenuSignal.OPEN_PLAYLIST:
                print("not implomented yet for openings")

            if event.type == pygame.KEYDOWN and event.key == pygame.K_LEFT:
                BOARD.undo_move()
                drawn_arrows.clear()
                highlighted_squares.clear()
                picking_piece = None
                is_dragging = False
                promotion_pending = None

            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:

                    # --- FORGE UI CLICKS ---
                    if FORGE_TOGGLE_BTN_RECT.collidepoint(event.pos):
                        modes = ["Both", "White", "Black"]
                        current_idx = modes.index(FORGE_SAVE_MODE)
                        FORGE_SAVE_MODE = modes[(current_idx + 1) % len(modes)]
                        continue

                    if FORGE_MENU_BTN_RECT.collidepoint(event.pos):
                        MUSIC_MANAGER.exit_music()
                        play_music("menu_music")
                        update_window_size(in_game=False)
                        return MenuSignal.BACK

                    if FORGE_SAVE_BTN_RECT.collidepoint(event.pos):
                        if len(BOARD.move_log) == 0:
                            add_alert("No moves to save!")
                            continue

                        book_name = ask_for_book_name(SCREEN)
                        if book_name:
                            try:
                                # 1. Ask the Generator to build the Toybox!
                                new_moves = book_generator.generate_dictionary_from_log(BOARD.move_log, FORGE_SAVE_MODE)

                                openings_dir = os.path.join(PERMANENT_ROOT, "openings")
                                if not os.path.exists(openings_dir): os.makedirs(openings_dir)

                                file_path = os.path.join(openings_dir, f"{book_name}.json")
                                final_book = {}
                                if os.path.exists(file_path):
                                    with open(file_path, "r", encoding="utf-8") as f:
                                        try:
                                            final_book = json.load(f)
                                        except:
                                            pass

                                moves_before = len(final_book)

                                # 2. MERGE LOGIC: Put the new toys into the old boxes!
                                for fen, move_list in new_moves.items():
                                    if fen not in final_book:
                                        final_book[fen] = []
                                    elif isinstance(final_book[fen], str):
                                        final_book[fen] = [final_book[fen]]  # Fix old strings

                                    for m in move_list:
                                        if m not in final_book[fen]:
                                            final_book[fen].append(m)

                                moves_added = len(final_book) - moves_before

                                with open(file_path, "w", encoding="utf-8") as f:
                                    json.dump(final_book, f, indent=4)

                                if moves_before > 0:
                                    add_alert(f"Added {moves_added} positions to {book_name}.json")
                                else:
                                    add_alert(f"Forged {book_name}.json! ({FORGE_SAVE_MODE})")
                            except Exception as e:
                                add_alert("Forge failed! Check terminal.")
                                print(f"Forge Error: {e}")
                        continue

                    # --- PROMOTION & PIECE PICKUP ---
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
                    if clicked is not None:
                        clicked_piece = BOARD.get_piece_at(clicked)
                        if clicked_piece is not None and clicked_piece.color == BOARD.active_color:
                            picking_piece = clicked_piece
                            is_dragging = True
                            drawn_arrows.clear()
                            highlighted_squares.clear()

                elif event.button == 3:
                    right_click_start = pixel_to_squarepos(event.pos)

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    if is_dragging and picking_piece is not None:
                        is_dragging = False
                        drop_pos = pixel_to_squarepos(event.pos)

                        if drop_pos is not None and drop_pos != picking_piece.position:
                            if picking_piece.is_valid_move(drop_pos):
                                move = picking_piece.legal_moves[drop_pos]
                                if move.move_type == MoveType.PROMOTION:
                                    promotion_pending = move
                                else:
                                    BOARD.execute_move(move)
                                    picking_piece = None
                            else:
                                picking_piece = None

                elif event.button == 3:
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

        SCREEN.fill((0, 0, 0))

        draw_create_openings_side_menu(SCREEN)
        draw_live_diary(SCREEN, BOARD.move_log)
        draw_board(SCREEN, show_notation=False)
        draw_mini_player(SCREEN)
        draw_system_alerts(SCREEN)

        hidden_piece = picking_piece if is_dragging else None
        draw_pieces(SCREEN, BOARD, IMAGE_CACHE, dragged_piece=hidden_piece)

        if is_dragging and picking_piece is not None:
            img = get_piece_image(picking_piece, IMAGE_CACHE)
            mouse_x, mouse_y = pygame.mouse.get_pos()
            rect = img.get_rect(center=(mouse_x, mouse_y))
            SCREEN.blit(img, rect)

        if picking_piece is not None:
            highlight_square(SCREEN, picking_piece.position, PICKING_PIECE_HIGHLIGHT_COLOR)
            for legal_pos in picking_piece.legal_moves.keys():
                highlight_square(SCREEN, legal_pos, LEGAL_MOVES_HIGHLIGHT_COLOR, thickness=5)

        for square in highlighted_squares:
            highlight_square(SCREEN, square, (200, 50, 50), alpha=100, thickness=0)
        for start_pos, end_pos in drawn_arrows:
            draw_arrow(SCREEN, start_pos, end_pos, (255, 170, 0))

        if promotion_pending is not None:
            promotion_rects = draw_promotion_menu(SCREEN, BOARD.active_color, IMAGE_CACHE)

        pygame.display.flip()
        pygame_clock.tick(FPS)


def run_bot_wizard_screen():
    global SCREEN, FPS
    pygame_clock = pygame.time.Clock()

    # --- WIZARD STATES ---
    step = 0
    data = {
        "name": "", "id": "", "brain": "", "books": "", "depth": "4", "elo": "9999"
    }

    # Hitboxes
    box_rect = pygame.Rect((SCREEN_WIDTH // 2) - 250, (SCREEN_HEIGHT // 2) - 150, 500, 300)
    text_rect = pygame.Rect((SCREEN_WIDTH // 2) - 200, (SCREEN_HEIGHT // 2) + 20, 400, 40)
    btn_script = pygame.Rect((SCREEN_WIDTH // 2) - 200, (SCREEN_HEIGHT // 2), 400, 45)
    btn_engine = pygame.Rect((SCREEN_WIDTH // 2) - 200, (SCREEN_HEIGHT // 2) + 60, 400, 45)

    # Take a photo of the current screen to use as a frozen background
    bg_surface = SCREEN.copy()
    dim_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    dim_surface.set_alpha(200)
    dim_surface.fill((0, 0, 0))
    bg_surface.blit(dim_surface, (0, 0))

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False  # Cancel the wizard

                # --- TEXT INPUT HANDLING ---
                if step in [0, 1, 3, 4, 5]:
                    key_map = {0: "name", 1: "id", 3: "books", 4: "depth", 5: "elo"}
                    current_key = key_map[step]

                    if event.key == pygame.K_RETURN:
                        if step == 0 and data["name"].strip():
                            step = 1
                        elif step == 1 and data["id"].strip():
                            step = 2
                        elif step == 3:
                            step = 4 if data["brain"] == "2" else 6
                        elif step == 4:
                            step = 5
                        elif step == 5:
                            step = 6

                    elif event.key == pygame.K_BACKSPACE:
                        data[current_key] = data[current_key][:-1]
                    elif event.unicode.isprintable():
                        if len(data[current_key]) < 30:
                            data[current_key] += event.unicode
                            if step == 1:  # Force bot ID to be snake_case
                                data["id"] = data["id"].replace(" ", "_").lower()

            # --- MOUSE CLICK HANDLING (For Brain Choice) ---
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if step == 2:
                    if btn_script.collidepoint(event.pos):
                        data["brain"] = "1"
                        step = 3
                    elif btn_engine.collidepoint(event.pos):
                        data["brain"] = "2"
                        step = 3

        # --- EXECUTE FORGE ---
        if step == 6:
            book_list = [b.strip() for b in data["books"].split(',')] if data["books"].strip() else []
            depth_val = int(data["depth"]) if data["depth"].isdigit() else 4
            elo_val = int(data["elo"]) if data["elo"].isdigit() else 9999

            success = (bot_factory.
            forge_bot(
                name=data["name"].strip(),
                bot_id=data["id"].strip(),
                brain_choice=data["brain"],
                book_list=book_list,
                depth=depth_val,
                elo=elo_val
            ))
            return success

        # --- CALL THE PAINTER ---
        draw_bot_wizard_page(SCREEN, step, data, box_rect, text_rect, btn_script, btn_engine, bg_surface)

        pygame.display.flip()
        pygame_clock.tick(FPS)

def run_bot_selection_screen(is_launching):
    global SCREEN
    pygame_clock = pygame.time.Clock()

    ui_rects = {
        "colors": {
            "White": pygame.Rect((SCREEN_WIDTH // 2) - 160, 160, 150, 50),
            "Black": pygame.Rect((SCREEN_WIDTH // 2) + 10, 160, 150, 50)
        },
        # Re-centered the openings button since forge left the building
        "create_openings": pygame.Rect((SCREEN_WIDTH // 2) - 200, 475, 400, 45),
        "quick_start": pygame.Rect((SCREEN_WIDTH // 2) - 200, 525, 30, 30),
        "confirm": pygame.Rect((SCREEN_WIDTH // 2) + 20, 565, 200, 60),
        "cancel": pygame.Rect((SCREEN_WIDTH // 2) - 220, 565, 200, 60)
    }

    bot_ids = list(LOADED_BOTS.keys())

    scroll_y = 0
    scroll_speed = 30
    start_y = 290
    clip_rect = pygame.Rect((SCREEN_WIDTH // 2) - 280, 270, 560, 195)

    total_rows = (len(bot_ids) + 1) // 2
    total_content_height = total_rows * 60
    max_scroll = max(0, total_content_height - clip_rect.height + 20)

    scrollbar_dragging = False
    drag_offset_y = 0

    while True:
        track_rect = pygame.Rect(clip_rect.right + 10, clip_rect.y + 5, 12, clip_rect.height - 10)

        if max_scroll > 0:
            thumb_height = max(40, (clip_rect.height / total_content_height) * track_rect.height)
            thumb_y = track_rect.y + (scroll_y / max_scroll) * (track_rect.height - thumb_height)
            thumb_rect = pygame.Rect(track_rect.x, thumb_y, track_rect.width, thumb_height)
        else:
            thumb_rect = None

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return MenuSignal.QUIT

            if event.type == pygame.MOUSEWHEEL:
                scroll_y -= event.y * scroll_speed
                scroll_y = max(0, min(scroll_y, max_scroll))

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if thumb_rect and thumb_rect.collidepoint(event.pos):
                    scrollbar_dragging = True
                    drag_offset_y = event.pos[1] - thumb_rect.y
                elif max_scroll > 0 and track_rect.collidepoint(event.pos):
                    if event.pos[1] > thumb_rect.bottom:
                        scroll_y = min(max_scroll, scroll_y + clip_rect.height)
                    elif event.pos[1] < thumb_rect.top:
                        scroll_y = max(0, scroll_y - clip_rect.height)

                elif ui_rects["cancel"].collidepoint(event.pos):
                    return MenuSignal.BACK

                elif ui_rects["confirm"].collidepoint(event.pos):
                    save_preferences()
                    return MenuSignal.START_GAME if is_launching else MenuSignal.BACK

                elif ui_rects["quick_start"].collidepoint(event.pos):
                    PREFERENCES["quick_start_bot"] = not PREFERENCES["quick_start_bot"]

                elif ui_rects["create_openings"].collidepoint(event.pos):
                    result = run_create_openings_screen()
                    if result == MenuSignal.MAIN_MENU:
                        return MenuSignal.MAIN_MENU
                    elif result == MenuSignal.QUIT:
                        return MenuSignal.QUIT

                for color_name, rect in ui_rects["colors"].items():
                    if rect.collidepoint(event.pos):
                        PREFERENCES["player_color"] = color_name

                if clip_rect.collidepoint(event.pos):
                    for i, bot_id in enumerate(bot_ids):
                        col = i % 2
                        row = i // 2
                        x = (SCREEN_WIDTH // 2) - 260 + (col * 270)
                        y = start_y + (row * 60) - scroll_y
                        bot_rect = pygame.Rect(x, y, 250, 45)

                        if bot_rect.collidepoint(event.pos):
                            PREFERENCES["bot_id"] = bot_id

            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                scrollbar_dragging = False

            if event.type == pygame.MOUSEMOTION:
                if scrollbar_dragging and max_scroll > 0:
                    new_thumb_y = event.pos[1] - drag_offset_y
                    new_thumb_y = max(track_rect.y, min(new_thumb_y, track_rect.bottom - thumb_height))
                    scroll_percent = (new_thumb_y - track_rect.y) / (track_rect.height - thumb_height)
                    scroll_y = scroll_percent * max_scroll

        draw_bot_selection_page(SCREEN, ui_rects, bot_ids, is_launching, scroll_y, clip_rect, track_rect, thumb_rect, max_scroll)
        pygame.display.flip()
        pygame_clock.tick(FPS)

def run_home_screen():
    global SCREEN
    pygame_clock = pygame.time.Clock()
    play_music("menu_music")
    update_window_size(in_game=False)

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return MenuSignal.QUIT

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if START_BTN_RECT.collidepoint(event.pos):

                    # --- THE INTERCEPT ---
                    if PREFERENCES["game_mode"] == "Singleplayer":
                        # If Quick Start is OFF, pull them into the Bot Room
                        if not PREFERENCES.get("quick_start_bot", False):
                            result = run_bot_selection_screen(is_launching=True)
                            if result == MenuSignal.START_GAME:
                                return MenuSignal.START_GAME
                            elif result == MenuSignal.QUIT:
                                return MenuSignal.QUIT
                            # If they hit cancel, we do nothing and stay on the home screen!
                        else:
                            # Quick start is ON, let them through immediately!
                            return MenuSignal.START_GAME
                    else:
                        # Multiplayer or Online, let them right through!
                        return MenuSignal.START_GAME

                elif QUIT_BTN_RECT.collidepoint(event.pos):
                    return MenuSignal.QUIT
                elif SETTINGS_BTN_RECT.collidepoint(event.pos):
                    result = run_settings_screen()
                    if result == MenuSignal.QUIT:
                        return MenuSignal.QUIT

        draw_home_page(SCREEN)
        pygame.display.flip()
        pygame_clock.tick(FPS)




def run_general_settings_screen():
    global SCREEN, AUTO_SAVE, STARTING_TIME
    pygame_clock = pygame.time.Clock()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return MenuSignal.QUIT

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if RETURN_BTN_RECT.collidepoint(event.pos):
                    return MenuSignal.BACK

                for i, rect in enumerate(GENERAL_SETTINGS_RECTS):
                    if rect.collidepoint(event.pos):
                        btn_name = GENERAL_SETTINGS_OPTIONS[i]

                        if btn_name == "Auto Save":
                            PREFERENCES["auto_save"] = not PREFERENCES["auto_save"]
                        elif btn_name == "Time Control":
                            times = [60, 180, 300, 600, 1800]
                            curr = PREFERENCES["starting_time"]
                            idx = times.index(curr) if curr in times else 2
                            PREFERENCES["starting_time"] = times[(idx + 1) % len(times)]
                            for color in [ChessColor.WHITE, ChessColor.BLACK]:
                                CLOCKS[color].change_starting_time(PREFERENCES["starting_time"])
                        elif btn_name == "Game Mode":
                            modes = ["Singleplayer", "Multiplayer", "Online"]
                            curr = PREFERENCES["game_mode"]
                            idx = modes.index(curr) if curr in modes else 0
                            PREFERENCES["game_mode"] = modes[(idx + 1) % len(modes)]

                        elif btn_name == "Player Color" and PREFERENCES["game_mode"] == "Singleplayer":
                            if PREFERENCES["player_color"] == "White":
                                PREFERENCES["player_color"] = "Black"
                            else:
                                PREFERENCES["player_color"] = "White"

                        elif btn_name == "Bot Setup" and PREFERENCES["game_mode"] == "Singleplayer":
                            result = run_bot_selection_screen(is_launching=False)
                            if result == MenuSignal.QUIT:
                                return MenuSignal.QUIT

                        # --- NEW: FORGE BOT LOGIC ---
                        elif btn_name == "Forge Bot":
                            success = run_bot_wizard_screen()
                            if success:
                                # Reload the library quietly in the background!
                                load_all_bots()

                        save_preferences()

        draw_general_settings_page(SCREEN)
        pygame.display.flip()
        pygame_clock.tick(FPS)

def run_server_browser_screen():
    global SCREEN, FPS
    pygame_clock = pygame.time.Clock()

    # --- TURN ON THE MICROPHONE (UDP Listener) ---
    mic = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    mic.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    mic.bind(("", 5556))
    mic.setblocking(False)

    servers_found = {}
    return_rect = pygame.Rect((SCREEN_WIDTH // 2) - 150, SCREEN_HEIGHT - 100, 300, 60)

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if return_rect.collidepoint(event.pos):
                    return "BACK"

                # Check the dictionary to see if they clicked a server hitbox
                for ip, data in servers_found.items():
                    if data.get("rect") and data["rect"].collidepoint(event.pos):
                        if data["seats"] != "0":  # Bouncer: Don't let them click full rooms!
                            return ip

                            # --- LISTEN FOR SHOUTS ---
        try:
            for _ in range(10):
                data, addr = mic.recvfrom(1024)
                msg = data.decode('utf-8')
                if msg.startswith("CHESS_SERVER|"):
                    parts = msg.split("|")

                    # Update the notebook
                    servers_found[addr[0]] = {
                        "time": time.time(),
                        "name": parts[1],
                        "seats": parts[2],
                        "rect": servers_found.get(addr[0], {}).get("rect")  # Keep the old hitbox if it exists
                    }
        except BlockingIOError:
            pass

            # --- CLEAN UP DEAD SERVERS ---
        now = time.time()
        dead_ips = [ip for ip, data in servers_found.items() if now - data["time"] > 3.0]
        for dead in dead_ips:
            del servers_found[dead]

        # Call the Paint Bucket!
        draw_server_browser_page(SCREEN, servers_found, return_rect)

        pygame.display.flip()
        pygame_clock.tick(FPS)

def run_replay_screen(pgn_string: str):
    global SCREEN, IMAGE_CACHE, BOARD,CURRENT_MUSIC
    pygame_clock = pygame.time.Clock()

    # --- THE FIX: Invite the DJ into the room! ---
    if CURRENT_MUSIC == "menu_music":
        dj.music.stop()
        CURRENT_MUSIC = None

    if MUSIC_MANAGER.is_playlist_empty():
        MUSIC_MANAGER.add_pack("default_pack")


    update_window_size(in_game=True)
    MUSIC_MANAGER.continue_playlist()  # This wakes up the UI!

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
        update_media_player()

        # Determine what text to show for the current move
        if current_move_index == 0:
            move_text = "Start"
        else:
            move_text = san_list[current_move_index - 1]

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return MenuSignal.QUIT

            temp_handle = handle_media_player_event(event)

            if temp_handle == MenuSignal.OPEN_PLAYLIST:
                print("not implomented to replay yet")

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
                        # --- THE FIX: Clean up the room before going back to the library! ---
                        MUSIC_MANAGER.exit_music()  # Tell the DJ to pack up
                        play_music("menu_music")  # Turn the lobby elevator music back on
                        update_window_size(in_game=False)  # Shrink the window back

                        return MenuSignal.BACK

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

            draw_live_diary(SCREEN, BOARD.move_log)
            draw_board(SCREEN, show_notation)
            draw_replay_side_menu(SCREEN, show_notation, move_text)
            draw_mini_player(SCREEN)
            draw_system_alerts(SCREEN)


            # Draw pieces using the global BOARD
            draw_pieces(SCREEN, BOARD, IMAGE_CACHE)

            for square in highlighted_squares:
                highlight_square(SCREEN, square, (200, 50, 50), alpha=100, thickness=0)

            for start_pos, end_pos in drawn_arrows:
                draw_arrow(SCREEN, start_pos, end_pos, (255, 170, 0))

            pygame.display.flip()
            pygame_clock.tick(FPS)


def ask_for_book_name(screen):
    """
    ELI5: A mini popup window that freezes the game and asks you to type a name.
    Press ENTER to save, press ESCAPE to cancel.
    """
    pygame_clock = pygame.time.Clock()
    font_title = pygame.font.SysFont("Arial", 30, bold=True)
    font_input = pygame.font.SysFont("Arial", 24)

    input_text = ""
    box_rect = pygame.Rect((SCREEN_WIDTH // 2) - 200, (SCREEN_HEIGHT // 2) - 75, 400, 150)
    text_rect = pygame.Rect((SCREEN_WIDTH // 2) - 180, (SCREEN_HEIGHT // 2) + 10, 360, 40)

    # 1. Take a photo of the current screen
    bg_surface = screen.copy()

    # 2. Dim the lights
    dim_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    dim_surface.set_alpha(180)
    dim_surface.fill((0, 0, 0))
    bg_surface.blit(dim_surface, (0, 0))

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return None  # They cancelled!

                elif event.key == pygame.K_RETURN:
                    # They pressed Enter! Send the text back (replace spaces with underscores)
                    if input_text.strip():
                        return input_text.strip().replace(" ", "_")
                    else:
                        return "custom_book"  # Fallback if they hit enter while empty

                elif event.key == pygame.K_BACKSPACE:
                    input_text = input_text[:-1]  # Delete the last letter

                elif event.unicode.isprintable():
                    if len(input_text) < 25:  # Don't let them type a name that is too long!
                        input_text += event.unicode

        # 3. Draw the dark background
        screen.blit(bg_surface, (0, 0))

        # 4. Draw the purple popup box
        pygame.draw.rect(screen, (40, 40, 45), box_rect, border_radius=15)
        pygame.draw.rect(screen, (150, 80, 200), box_rect, 3, border_radius=15)

        # Draw the title
        title_surf = font_title.render("Name Your Opening Book:", True, (255, 255, 255))
        screen.blit(title_surf, title_surf.get_rect(center=(SCREEN_WIDTH // 2, box_rect.y + 30)))

        # Draw the typing field
        pygame.draw.rect(screen, (20, 20, 25), text_rect, border_radius=5)
        pygame.draw.rect(screen, (150, 150, 150), text_rect, 2, border_radius=5)

        # Draw the text with a blinking cursor effect
        cursor = "|" if pygame.time.get_ticks() % 1000 < 500 else ""
        txt_surf = font_input.render(input_text + cursor, True, (255, 255, 255))
        screen.blit(txt_surf, (text_rect.x + 10, text_rect.y + 8))

        pygame.display.flip()
        pygame_clock.tick(60)


def run_paste_pgn_screen():
    global SCREEN
    pygame_clock = pygame.time.Clock()
    pygame.scrap.init()

    input_rect = pygame.Rect((SCREEN_WIDTH // 2) - 300, 180, 600, 50)
    paste_rect = pygame.Rect((SCREEN_WIDTH // 2) - 200, 250, 400, 50)
    save_rect = pygame.Rect((SCREEN_WIDTH // 2) - 200, 320, 400, 50)
    forge_rect = pygame.Rect((SCREEN_WIDTH // 2) - 200, 390, 400, 50)
    return_rect = pygame.Rect((SCREEN_WIDTH // 2) - 150, SCREEN_HEIGHT - 100, 300, 60)

    user_text = ""
    input_active = False

    status_msg = "Type or Paste to load a PGN"
    status_color = (200, 200, 200)
    is_valid = False

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return MenuSignal.QUIT

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                input_active = input_rect.collidepoint(event.pos)

                if return_rect.collidepoint(event.pos):
                    return

                elif paste_rect.collidepoint(event.pos):
                    raw_bytes = pygame.scrap.get(pygame.SCRAP_TEXT)
                    if raw_bytes:
                        user_text = raw_bytes.replace(b'\x00', b'').decode('utf-8', errors='ignore').strip()
                        if is_pgn_valid(user_text):
                            status_msg = "Valid PGN! Ready to save or forge."
                            status_color = (80, 200, 80)
                            is_valid = True
                        else:
                            status_msg = "Invalid PGN. Check your text."
                            status_color = (200, 80, 80)
                            is_valid = False
                    else:
                        status_msg = "Clipboard is empty!"
                        status_color = (200, 80, 80)

                elif save_rect.collidepoint(event.pos) and is_valid:
                    save_custom_pgn(user_text)
                    return MenuSignal.BACK

                elif forge_rect.collidepoint(event.pos) and is_valid:
                    book_name = ask_for_book_name(SCREEN)

                    if book_name is None:
                        continue

                    try:
                        # 1. Ask the Generator to translate the PGN string!
                        new_moves = book_generator.generate_dictionary_from_pgn(user_text, save_mode="Both")

                        openings_dir = os.path.join(PERMANENT_ROOT, "openings")
                        if not os.path.exists(openings_dir):
                            os.makedirs(openings_dir)

                        file_path = os.path.join(openings_dir, f"{book_name}.json")

                        final_book = {}
                        if os.path.exists(file_path):
                            with open(file_path, "r", encoding="utf-8") as f:
                                try:
                                    final_book = json.load(f)
                                except json.JSONDecodeError:
                                    final_book = {}

                        moves_before = len(final_book)

                        # 2. MERGE LOGIC: The Toybox Method
                        for fen, move_list in new_moves.items():
                            if fen not in final_book:
                                final_book[fen] = []
                            elif isinstance(final_book[fen], str):
                                final_book[fen] = [final_book[fen]]  # Fix old strings

                            for m in move_list:
                                if m not in final_book[fen]:
                                    final_book[fen].append(m)

                        moves_added = len(final_book) - moves_before

                        with open(file_path, "w", encoding="utf-8") as f:
                            json.dump(final_book, f, indent=4)

                        if moves_before > 0:
                            status_msg = f"Merged! Added {moves_added} new positions to {book_name}.json"
                        else:
                            status_msg = f"Forged! Saved {len(final_book)} positions to {book_name}.json"

                        status_color = (150, 80, 200)

                    except Exception as e:
                        status_msg = f"Forge Failed: {e}"
                        status_color = (200, 80, 80)

            elif event.type == pygame.KEYDOWN:
                if input_active:
                    if event.key == pygame.K_BACKSPACE:
                        user_text = user_text[:-1]
                    elif event.unicode.isprintable():
                        user_text += event.unicode

                    if user_text.strip() == "":
                        status_msg = "Type or Paste to load a PGN"
                        status_color = (200, 200, 200)
                        is_valid = False
                    elif is_pgn_valid(user_text):
                        status_msg = "Valid PGN! Ready to save or forge."
                        status_color = (80, 200, 80)
                        is_valid = True
                    else:
                        status_msg = "Typing... (Invalid PGN)"
                        status_color = (200, 150, 50)
                        is_valid = False

        draw_paste_pgn_page(SCREEN, status_msg, status_color, is_valid, paste_rect, save_rect, forge_rect, return_rect,
                            input_rect, user_text, input_active)
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

    # --- SCROLLBAR STATE ---
    scrollbar_dragging = False
    drag_offset_y = 0

    while True:
        # Calculate scrollbar positions every frame
        # Anchored to the far right side of the screen, just past the cards
        track_rect = pygame.Rect(SCREEN_WIDTH - 30, clip_rect.y + 5, 12, clip_rect.height - 10)

        if max_scroll > 0:
            thumb_height = max(40, (clip_rect.height / total_content_height) * track_rect.height)
            thumb_y = track_rect.y + (scroll_y / max_scroll) * (track_rect.height - thumb_height)
            thumb_rect = pygame.Rect(track_rect.x, thumb_y, track_rect.width, thumb_height)
        else:
            thumb_rect = None

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return MenuSignal.QUIT

            # --- THE SCROLL WHEEL ---
            if event.type == pygame.MOUSEWHEEL:
                scroll_y -= event.y * scroll_speed
                scroll_y = max(0, min(scroll_y, max_scroll))

            # --- MOUSE CLICKS ---
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:

                # 1. INTERACTABLE SCROLLBAR: DRAG START
                if thumb_rect and thumb_rect.collidepoint(event.pos):
                    scrollbar_dragging = True
                    drag_offset_y = event.pos[1] - thumb_rect.y
                elif max_scroll > 0 and track_rect.collidepoint(event.pos):
                    # Jump scroll!
                    if event.pos[1] > thumb_rect.bottom:
                        scroll_y = min(max_scroll, scroll_y + clip_rect.height)
                    elif event.pos[1] < thumb_rect.top:
                        scroll_y = max(0, scroll_y - clip_rect.height)

                # 2. Return Button
                elif return_rect.collidepoint(event.pos):
                    return MenuSignal.BACK

                # 3. Import Button
                elif import_rect.collidepoint(event.pos):
                    result = run_paste_pgn_screen()
                    # We must refresh the Librarian when we get back so the new game shows up!
                    games = get_saved_games_data()
                    total_content_height = len(games) * card_height
                    max_scroll = max(0, total_content_height - window_pane_height + 20)

                    if result == MenuSignal.QUIT:
                        return MenuSignal.QUIT

                # 4. Check game buttons IF click is inside the window pane
                elif clip_rect.collidepoint(event.pos):
                    for i, game in enumerate(games):
                        # Calculate exact hitbox based on current scroll
                        y = start_y + (i * card_height) - scroll_y
                        main_rect = pygame.Rect(50, y, SCREEN_WIDTH - 100, 75)

                        show_rect = pygame.Rect(main_rect.right - 260, y + 17, 70, 40)
                        copy_rect = pygame.Rect(main_rect.right - 170, y + 17, 70, 40)
                        delete_rect = pygame.Rect(main_rect.right - 80, y + 17, 70, 40)

                        if show_rect.collidepoint(event.pos):
                            result = run_replay_screen(game['pgn'])
                            if result == MenuSignal.QUIT:
                                return MenuSignal.QUIT

                        elif copy_rect.collidepoint(event.pos):
                            pygame.scrap.init()
                            pygame.scrap.put(pygame.SCRAP_TEXT, game['pgn'].encode('utf-8'))
                            print(f"Copied {game['filename']} to clipboard!")

                        elif delete_rect.collidepoint(event.pos):
                            # 1. Safely delete the file
                            filepath = os.path.join(DIRECTORY_OF_SAVED_GAMES, game['filename'])
                            if os.path.exists(filepath):
                                save_preferences()
                                os.remove(filepath)
                                game_number = get_next_available_game_number()
                                PREFERENCES['game_counter'] = game_number
                                print(f"Deleted {game['filename']}")

                            # 2. Tell the Librarian to refresh the list!
                            games = get_saved_games_data()

                            # 3. Recalculate the floor
                            total_content_height = len(games) * card_height
                            max_scroll = max(0, total_content_height - window_pane_height + 20)

                            # 4. Snap the elevator back up if we were at the very bottom
                            scroll_y = min(scroll_y, max_scroll)

            # --- INTERACTABLE SCROLLBAR: DRAG RELEASE ---
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                scrollbar_dragging = False

            # --- INTERACTABLE SCROLLBAR: DRAG MOTION ---
            if event.type == pygame.MOUSEMOTION:
                if scrollbar_dragging and max_scroll > 0:
                    new_thumb_y = event.pos[1] - drag_offset_y
                    new_thumb_y = max(track_rect.y, min(new_thumb_y, track_rect.bottom - thumb_height))
                    scroll_percent = (new_thumb_y - track_rect.y) / (track_rect.height - thumb_height)
                    scroll_y = scroll_percent * max_scroll

        # Pass the new scrollbar data to the painter!
        draw_saved_games_page(SCREEN, games, scroll_y, return_rect, import_rect, clip_rect, track_rect, thumb_rect,
                              max_scroll)
        pygame.display.flip()
        pygame_clock.tick(FPS)

def run_settings_screen():
    global SCREEN
    """The Settings Room. You stay here until you click Return to Menu."""
    pygame_clock = pygame.time.Clock()
    result = None

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return MenuSignal.QUIT

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Check all the dynamic buttons in one simple loop!
                for i, rect in enumerate(SETTINGS_RECTS):
                    if rect.collidepoint(event.pos):
                        btn_name = SETTINGS_OPTIONS[i][0]
                        if btn_name == "Saved Games":
                            result = run_saved_games_screen()
                        elif btn_name == "General Settings":
                            result = run_general_settings_screen()
                        elif btn_name == "Video Settings":
                            result = run_video_settings_screen()
                        elif btn_name == "Audio & Music":
                            result = run_audio_settings_screen()
                        else:
                            print(f"TODO: Open menu for {btn_name}")
                        if result == MenuSignal.QUIT:
                            return MenuSignal.QUIT

                # Check the Return button
                if RETURN_BTN_RECT.collidepoint(event.pos):
                    return MenuSignal.BACK


        draw_settings_page(SCREEN)
        pygame.display.flip()
        pygame_clock.tick(FPS)

#</editor-fold>

# <editor-fold desc="MAIN">

def main():
    global SCREEN, BOARD, IMAGE_CACHE, PLAYERS, NOTATION_FONT, FPS,DT,BOARD_FLIPPED,ONLINE_CONNECTION,MUSIC_MANAGER

    load_preferences()
    load_all_bots()
    pygame.init()
    dj.init()

    MUSIC_MANAGER = music_manager.MusicManager(PREFERENCES)

    bot.innit(chessColor=ChessColor, chessPieceType=ChessPieceType,
              move=Move, moveType=MoveType, squarePosition=SquarePosition)

    stockfish.innit(
        passed_move=Move,
        passed_chess_piece_type=ChessPieceType,
        passed_move_type=MoveType,
        passed_square_position=SquarePosition,
        passed_board_class=Board
    )

    book_generator.init(Board, Move, MoveType, SquarePosition, ChessPieceType)

    NOTATION_FONT = pygame.font.SysFont("Arial", 14, bold=True)

    update_window_size()
    pygame.display.set_caption("Chess")
    FPS = PREFERENCES['fps']
    DT = 1/FPS

    pygame_clock = pygame.time.Clock()
    BOARD.load_fen(STARTING_POSITION)
    IMAGE_CACHE = {}

    # ==========================================
    # 1. THE ANIMATION STATE
    # ==========================================
    animation_state = {
        "piece": None,  # Which piece is flying?
        "start_pos": None,  # (x, y) pixels
        "end_pos": None,  # (x, y) pixels
        "progress": 0.0  # 0.0 to 1.0
    }

    def animate_move(piece, from_sq, to_sq):
        nonlocal animation_state
        if PREFERENCES["animation_time"] <= 0:
            return

        if animation_state["piece"] is not None:
            animation_state["progress"] = 1.0

        v_start_r, v_start_c = get_visual_row_col(from_sq.row, from_sq.col)
        v_end_r, v_end_c = get_visual_row_col(to_sq.row, to_sq.col)

        start_x = BOARD_X_OFFSET + (v_start_c * SQUARE_SIZE + SQUARE_SIZE // 2)
        start_y = v_start_r * SQUARE_SIZE + SQUARE_SIZE // 2
        end_x = BOARD_X_OFFSET + (v_end_c * SQUARE_SIZE + SQUARE_SIZE // 2)
        end_y = v_end_r * SQUARE_SIZE + SQUARE_SIZE // 2

        animation_state.update({
            "piece": piece,
            "start_pos": (start_x, start_y),
            "end_pos": (end_x, end_y),
            "progress": 0.0
        })

    # ==========================================
    # 2. STATE VARIABLES
    # ==========================================
    picking_piece: ChessPiece | None = None
    is_dragging = False
    promotion_pending: Move | None = None
    promotion_rects = []
    drawn_arrows = set()
    highlighted_squares = set()
    right_click_start = None
    game_over_btn_rect = None
    show_notation = False
    is_fullscreen = False
    has_auto_saved = False
    ai_thinking_timer = 0  # Defined up here so nonlocal can see it!

    # Mini Player timeline
    is_dragging_timeline = False
    dragged_percentage = 0.0


    # ==========================================
    # 3. THE CLEANUP CREW
    # ==========================================
    def reset_match(keep_connection=False):
        nonlocal picking_piece, is_dragging, promotion_pending, game_over_btn_rect, is_paused, has_auto_saved, ai_thinking_timer, animation_state,ai_color
        global BOARD_FLIPPED,ONLINE_CONNECTION,CURRENT_MUSIC
        PLAYERS[ChessColor.WHITE].lost = False
        PLAYERS[ChessColor.BLACK].lost = False
        BOARD.is_draw = False
        BOARD.draw_offered_by = None
        BOARD.is_stalemate = False
        BOARD.load_fen(STARTING_POSITION)

        drawn_arrows.clear()
        highlighted_squares.clear()

        picking_piece = None
        is_dragging = False
        promotion_pending = None
        game_over_btn_rect = None
        is_paused = False
        has_auto_saved = False
        ai_thinking_timer = 0

        # Kill the ghost piece if we reset mid-flight!
        animation_state["piece"] = None

        for clock in CLOCKS.values():
            clock.reset()

        CLOCKS[BOARD.active_color].start()
        CLOCKS[OTHER_COLOR[BOARD.active_color]].stop()

        #BOOKMARK
        if PREFERENCES["game_mode"] == "Online":

            # 1. If we don't have a connection, open the Server Browser!
            if not keep_connection:
                chosen_ip = run_server_browser_screen()

                if chosen_ip is None:  # They clicked the red X on the window
                    quit_game()
                elif chosen_ip == "BACK":  # They clicked Return
                    ONLINE_CONNECTION = None
                    action = run_home_screen()
                    if action == MenuSignal.QUIT:
                        quit_game()
                    elif action == MenuSignal.START_GAME:
                        reset_match()
                    return  # Stop resetting, we left!
                else:
                    # They clicked a valid server button! Dial the phone!
                    print(f"Dialing {chosen_ip}...")
                    try:
                        ONLINE_CONNECTION = Network(chosen_ip)
                        PREFERENCES["player_color"] = ONLINE_CONNECTION.color
                    except Exception as e:
                        print(f"Failed to dial {chosen_ip}: {e}")
                        ONLINE_CONNECTION = None
                        PREFERENCES["game_mode"] = "Multiplayer"

            # 2. Whether we kept the connection or just made a new one, go wait in the Lobby!
            if ONLINE_CONNECTION:
                lobby_result = run_waiting_room_screen()
                if lobby_result == MenuSignal.QUIT:
                    quit_game()
                elif lobby_result == MenuSignal.BACK:
                    ONLINE_CONNECTION.send_message("LEAVE")
                    ONLINE_CONNECTION = None
                    action = run_home_screen()
                    if action == MenuSignal.QUIT:
                        quit_game()
                    elif action == MenuSignal.START_GAME:
                        reset_match()
                    return
                else:
                    # 3. ONLY sync history if it's a fresh connection. Rematches start fresh!
                    if not keep_connection:
                        sync = ONLINE_CONNECTION.sync_data
                        if sync:
                            print("[LOBBY] Syncing clocks and board state...")
                            CLOCKS[ChessColor.WHITE].restore_time(sync["time_w"])
                            CLOCKS[ChessColor.BLACK].restore_time(sync["time_b"])

                            old_sfx = PREFERENCES["sfx_mute"]
                            PREFERENCES["sfx_mute"] = True

                            for san in sync["history"]:
                                move = get_move_from_san(BOARD, san)
                                if move: BOARD.execute_move(move)

                            PREFERENCES["sfx_mute"] = old_sfx

                            if BOARD.active_color == ChessColor.WHITE:
                                CLOCKS[ChessColor.BLACK].stop()
                                CLOCKS[ChessColor.WHITE].start()
                            else:
                                CLOCKS[ChessColor.WHITE].stop()
                                CLOCKS[ChessColor.BLACK].start()
        else:
            ONLINE_CONNECTION = None

        if PREFERENCES["game_mode"] == "Singleplayer":
            ai_color = ChessColor.BLACK if PREFERENCES["player_color"] == "White" else ChessColor.WHITE
        else: ai_color = None

        if PREFERENCES["game_mode"] in ["Singleplayer", "Online"] and PREFERENCES["player_color"] == "Black":
            BOARD_FLIPPED = True
        else:
            BOARD_FLIPPED = False

        if CURRENT_MUSIC == "menu_music":
            dj.music.stop()
            CURRENT_MUSIC = None

        # Start the radio. This changes the state to PLAYING so the Mini Player draws!
        if MUSIC_MANAGER.is_playlist_empty():
            MUSIC_MANAGER.add_pack("default_pack")

        update_window_size(in_game=True)




    def undo_move():
        nonlocal drawn_arrows, highlighted_squares, picking_piece, is_dragging, promotion_pending, ai_thinking_timer

        # ANIMATION HOOK: We look at the diary before tearing out the page!
        if len(BOARD.move_log) > 0:
            last_record = BOARD.move_log[-1]
            move = last_record.move
            piece = last_record.moved_piece
            # Fly from the destination backwards to the start!
            animate_move(piece, move.to_pos, move.from_pos)

        # Now actually reverse the math
        BOARD.undo_move()

        drawn_arrows.clear()
        highlighted_squares.clear()
        picking_piece = None
        is_dragging = False
        promotion_pending = None
        ai_thinking_timer = 0

    # ==========================================
    # 4. THE CRITICAL SYNC
    # ==========================================
    for color in [ChessColor.WHITE, ChessColor.BLACK]:
        CLOCKS[color].change_starting_time(PREFERENCES["starting_time"])

    CLOCKS[BOARD.active_color].start()

    ai_color = None


    is_paused = False
    running = True

    home_screen_action = run_home_screen()
    if home_screen_action == MenuSignal.QUIT:
        running = False
    elif home_screen_action == MenuSignal.START_GAME:
        reset_match()


    MUSIC_MANAGER.continue_playlist()

    while running:
        update_media_player()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT:
                    undo_move()

                # --- FULLSCREEN TOGGLE ---
                elif event.key == pygame.K_F11:
                    is_fullscreen = not is_fullscreen
                    update_window_size(force_fullscreen=is_fullscreen)


            #finished the song and moving on to the next.
            temp_handle = handle_media_player_event(event)
            if temp_handle == MenuSignal.OPEN_PLAYLIST:
                was_paused = is_paused
                # THE BOUNCER: Only pause time if we are offline!
                if PREFERENCES["game_mode"] != "Online":
                    is_paused = True
                    CLOCKS[BOARD.active_color].stop()

                # Send the chef to the Audio Room
                result = run_playlist_screen()

                # Check if they hit the red X while in the menu
                if result == MenuSignal.QUIT:
                    running = False
                    continue

                # When the chef gets back, unpause (if it wasn't already manually paused before)
                if PREFERENCES["game_mode"] != "Online":
                    is_paused = was_paused
                    if not is_paused:
                        CLOCKS[BOARD.active_color].start()
                continue

            # ==========================================
            # THE PICK UP (Mouse Down)
            # ==========================================
            if event.type == pygame.MOUSEBUTTONDOWN:

                # --- LEFT CLICK (Normal Play) ---
                if event.button == 1:
                    # 1. UI BUTTON INTERCEPTS (Menu area)
                    if UNDO_BTN_RECT.collidepoint(event.pos):
                        undo_move()
                        continue

                    if NOTATION_BTN_RECT.collidepoint(event.pos):
                        show_notation = not show_notation
                        continue

                    if FLIP_BTN_RECT.collidepoint(event.pos):
                        BOARD_FLIPPED = not BOARD_FLIPPED
                        continue

                    if SAVE_BTN_RECT.collidepoint(event.pos):
                        create_new_chess_file(BOARD)
                        add_alert("Game Saved!")
                        continue

                    # --- DYNAMIC BUTTON LOGIC ---
                    top_color = ChessColor.WHITE if BOARD_FLIPPED else ChessColor.BLACK
                    bottom_color = ChessColor.BLACK if BOARD_FLIPPED else ChessColor.WHITE
                    show_top_buttons = PREFERENCES["game_mode"] == "Multiplayer"

                    # --- TOP BUTTONS (Only click if visible!) ---
                    if show_top_buttons:
                        if TOP_FLAG_BTN_RECT.collidepoint(event.pos):
                            PLAYERS[top_color].lost = True
                            if ONLINE_CONNECTION: ONLINE_CONNECTION.send_message("RESIGN")
                            continue

                        if TOP_DRAW_BTN_RECT.collidepoint(event.pos):
                            if BOARD.draw_offered_by == bottom_color:
                                BOARD.is_draw = True
                                if ONLINE_CONNECTION: ONLINE_CONNECTION.send_message("DRAW_ACCEPT")
                            else:
                                BOARD.draw_offered_by = top_color
                                if ONLINE_CONNECTION: ONLINE_CONNECTION.send_message("DRAW_OFFER", top_color.value)
                            continue

                    # --- BOTTOM BUTTONS ---
                    if BOTTOM_FLAG_BTN_RECT.collidepoint(event.pos):
                        # Online Anti-Cheat
                        if PREFERENCES[
                            "game_mode"] == "Online" and ONLINE_CONNECTION and ONLINE_CONNECTION.color != bottom_color.value.capitalize():
                            continue
                        PLAYERS[bottom_color].lost = True
                        if ONLINE_CONNECTION: ONLINE_CONNECTION.send_message("RESIGN")
                        continue

                    if BOTTOM_DRAW_BTN_RECT.collidepoint(event.pos):
                        # Online Anti-Cheat
                        if PREFERENCES[
                            "game_mode"] == "Online" and ONLINE_CONNECTION and ONLINE_CONNECTION.color != bottom_color.value.capitalize():
                            continue

                        if BOARD.draw_offered_by == top_color:
                            BOARD.is_draw = True
                            if ONLINE_CONNECTION: ONLINE_CONNECTION.send_message("DRAW_ACCEPT")
                        else:
                            BOARD.draw_offered_by = bottom_color
                            if ONLINE_CONNECTION: ONLINE_CONNECTION.send_message("DRAW_OFFER", bottom_color.value)
                        continue

                    if PAUSE_BTN_RECT.collidepoint(event.pos):
                        is_paused = not is_paused
                        if is_paused:
                            CLOCKS[BOARD.active_color].stop()
                        else:
                            CLOCKS[BOARD.active_color].start()
                        continue


                    if RESET_BTN_RECT.collidepoint(event.pos):
                        reset_match()
                        continue

                    if MENU_BTN_RECT.collidepoint(event.pos):
                        # Stop the clocks and hang up the phone!
                        CLOCKS[BOARD.active_color].stop()
                        ONLINE_CONNECTION.send_message("LEAVE") if ONLINE_CONNECTION else None
                        ONLINE_CONNECTION = None

                        MUSIC_MANAGER.exit_music()
                        action = run_home_screen()
                        if action == MenuSignal.QUIT:
                            running = False
                        elif action == MenuSignal.START_GAME:
                            reset_match()
                            MUSIC_MANAGER.continue_playlist()
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
                        rect1, rect2 = game_over_btn_rect

                        # Rematch / Again Button
                        if rect1 and rect1.collidepoint(event.pos):
                            if PREFERENCES["game_mode"] == "Online" and ONLINE_CONNECTION:
                                ONLINE_CONNECTION.send_message("REMATCH")
                                reset_match(keep_connection=True)
                            else:
                                reset_match()
                            continue

                        # Menu Button (Only exists in Online mode right now)
                        if rect2 and rect2.collidepoint(event.pos):
                            if ONLINE_CONNECTION:
                                ONLINE_CONNECTION.send_message("LEAVE")
                            ONLINE_CONNECTION = None
                            CLOCKS[BOARD.active_color].stop()

                            action = run_home_screen()
                            if action == MenuSignal.QUIT:
                                running = False
                            elif action == MenuSignal.START_GAME:
                                reset_match()
                            continue

                        continue  # DO NOT LET THEM CLICK THE BOARD!

                    # 3. IS THERE AI??? FRFR
                    if ai_color is not None and BOARD.active_color == ai_color:
                        continue


                    #4 - PROMOTION - DID IT PROMOTE??
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

                    # --- NEW: ONLINE ANTI-CHEAT ---
                    if PREFERENCES["game_mode"] == "Online" and ONLINE_CONNECTION:
                        # If the piece you clicked does NOT match the color the Referee gave you...
                        if clicked_piece is not None and clicked_piece.color.value.upper() != ONLINE_CONNECTION.color.upper():
                            continue  # Ignore the click completely!

                    # 1. Grab a piece to drag
                    if clicked_piece is not None and clicked_piece.color == BOARD.active_color:
                        picking_piece = clicked_piece
                        is_dragging = True

                    # 2. Hybrid Click-to-Move (if they clicked an empty square or enemy without dragging)
                    elif picking_piece is not None:

                        if picking_piece.is_valid_move(clicked):
                            move = picking_piece.legal_moves[clicked]
                            # THE HOOK: Fly the ghost!
                            animate_move(picking_piece, move.from_pos, move.to_pos)
                            if move.move_type == MoveType.PROMOTION:
                                promotion_pending = move
                            else:
                                BOARD.execute_move(move)
                                picking_piece = None

                                if ONLINE_CONNECTION is not None:
                                    san_string = BOARD.move_log[-1].algebraic_notation
                                    clean_san = san_string.replace("+", "").replace("#", "")
                                    ONLINE_CONNECTION.send_message("MOVE", clean_san)

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
                                    if ONLINE_CONNECTION is not None:
                                        san_string = BOARD.move_log[-1].algebraic_notation
                                        clean_san = san_string.replace("+", "").replace("#", "")
                                        ONLINE_CONNECTION.send_message("MOVE", clean_san)
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


        # ==========================================
        # UPDATE ANIMATION PROGRESS
        # ==========================================
        if animation_state["piece"]:
            # Progress goes from 0.0 to 1.0 based on Delta Time and your settings
            animation_state["progress"] += DT / PREFERENCES["animation_time"]
            if animation_state["progress"] >= 1.0:
                animation_state["piece"] = None  # Trip finished! Ghost disappears.

        # --- DRAWING PHASE ---
        SCREEN.fill((0, 0, 0))

        # Draw the Rooms
        draw_side_menu(SCREEN, show_notation, is_paused)
        draw_live_diary(SCREEN, BOARD.move_log)
        draw_board(SCREEN, show_notation)

        draw_mini_player(SCREEN)
        draw_system_alerts(SCREEN)

        # THE MAGIC TRICK: Hide the piece if we are dragging it OR animating it!
        hidden_piece = picking_piece if is_dragging else animation_state["piece"]
        draw_pieces(SCREEN, BOARD, IMAGE_CACHE, dragged_piece=hidden_piece)

        # --- DRAW THE GHOSTS (The Special Effects!) ---
        # 1. Are we dragging? (Draw it on the mouse)
        if is_dragging and picking_piece is not None:
            img = get_piece_image(picking_piece, IMAGE_CACHE)
            mouse_x, mouse_y = pygame.mouse.get_pos()
            rect = img.get_rect(center=(mouse_x, mouse_y))
            SCREEN.blit(img, rect)

        # 2. Are we animating? (Draw it sliding across the board)
        elif animation_state["piece"]:
            p = animation_state["piece"]
            prog = animation_state["progress"]
            s = animation_state["start_pos"]
            e = animation_state["end_pos"]

            # LERP MATH: Start + (Distance * Percentage)
            curr_x = s[0] + (e[0] - s[0]) * prog
            curr_y = s[1] + (e[1] - s[1]) * prog

            img = get_piece_image(p, IMAGE_CACHE)
            rect = img.get_rect(center=(curr_x, curr_y))
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
            if PREFERENCES["auto_save"] and not has_auto_saved:
                create_new_chess_file(BOARD)
                has_auto_saved = True
                add_alert("Audo Saved!")

            for clock in CLOCKS.values():
                clock.stop()
        else:
            game_over_btn_rect = None

        # ==========================================
        # THE AI OR THE NETWORK'S TURN
        # ==========================================
        if not is_paused and game_over_btn_rect is None:
            if ai_color is not None and BOARD.active_color == ai_color:
                # Tell Pygame to draw the board quickly before the AI thinks
                pygame.display.flip()

                ai_thinking_timer += DT

                # 2. Has the AI thought for long enough?
                if ai_thinking_timer >= PREFERENCES['bot_thinking_time']:
                    ai_move = get_bot_move(BOARD, ai_color, PREFERENCES['bot_id'])
                    if ai_move:
                        # THE HOOK: Grab the piece and tell it to fly!
                        moving_piece = BOARD.get_piece_at(ai_move.from_pos)
                        animate_move(moving_piece, ai_move.from_pos, ai_move.to_pos)

                        BOARD.execute_move(ai_move)

                    # 3. Reset the stopwatch for the next turn
                    ai_thinking_timer = 0

            #network

            elif ONLINE_CONNECTION is not None and not is_paused and game_over_btn_rect is None:
                # We ALWAYS check the mailbox now, because the server might tell us our flag fell!
                tag, payload = ONLINE_CONNECTION.peek_mailbox()

                if tag:
                    if tag == "MOVE":
                        # Only apply the move if it's NOT our turn (sanity check)
                        if BOARD.active_color.value.upper() != ONLINE_CONNECTION.color.upper():
                            enemy_move = get_move_from_san(BOARD, payload)
                            if enemy_move:
                                moving_piece = BOARD.get_piece_at(enemy_move.from_pos)
                                animate_move(moving_piece, enemy_move.from_pos, enemy_move.to_pos)
                                BOARD.execute_move(enemy_move)

                    elif tag == "FLAG" or tag == "RESIGN":
                        # Payload is the color ("White" or "Black"). The server decides who lost!
                        loser_color = ChessColor.WHITE if payload == "White" else ChessColor.BLACK
                        PLAYERS[loser_color].lost = True

                    elif tag == "DRAW_OFFER":
                        # The enemy handed us a note. Mark it on the board!
                        BOARD.draw_offered_by = ChessColor.WHITE if payload == "White" else ChessColor.BLACK
                        print(f"[NETWORK] {payload} offered a draw.")

                    elif tag == "DRAW":
                        # The server declared the game a draw!
                        BOARD.is_draw = True
                        print("[NETWORK] Match ended in a draw.")

                    elif tag == "OPPONENT_DISCONNECTED":
                        print("[NETWORK] Opponent disconnected! Do not close the window, they can reconnect.")



        pygame.display.flip()
        pygame_clock.tick(FPS)

    MUSIC_MANAGER.cleanup()
    quit_game()


if __name__ == "__main__":
    main()
# </editor-fold>
