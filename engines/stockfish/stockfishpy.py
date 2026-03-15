import os
from stockfish import Stockfish


Move = None
ChessPieceType = None
MoveType = None
SquarePosition = None
Board = None


def innit(passed_move, passed_chess_piece_type, passed_move_type, passed_square_position, passed_board_class):
    global Move, ChessPieceType, MoveType, SquarePosition, Board

    Move = passed_move
    ChessPieceType = passed_chess_piece_type
    MoveType = passed_move_type
    SquarePosition = passed_square_position
    Board = passed_board_class

# 1. This finds the exact folder where this python script is currently sitting
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

# 2. This glues the folder path and your specific 'stockfish.exe' together
# We are grabbing the bot by the collar. No basement searching allowed.
STOCKFISH_PATH = os.path.join(CURRENT_DIR, "stockfish.exe")

try:
    # 3. We force the library to use YOUR path
    bot = Stockfish(path=STOCKFISH_PATH)
except Exception as e:
    print(f"Error: I could not find your specific Stockfish at {STOCKFISH_PATH}.")
    print(f"Details: {e}")
    exit()

bot.set_depth(15)


def uci_to_move(board, uci_string: str):
    """
    Translates a Stockfish UCI string (e.g., 'e2e4', 'e1g1', 'e7e8q')
    into your custom Move class.
    """
    global Move,ChessPieceType,MoveType,SquarePosition,Board

    if not uci_string or len(uci_string) < 4:
        return None

    # 1. Parse standard coordinates
    from_not = uci_string[0:2]
    to_not = uci_string[2:4]

    from_pos = SquarePosition(notation=from_not)
    to_pos = SquarePosition(notation=to_not)

    # Grab the moving piece from the live board to check its type
    moving_piece = board.get_piece_at(from_pos)
    if not moving_piece:
        return None  # The board and Stockfish are out of sync!

    # 2. Defaults
    move_type = MoveType.NORMAL
    victim_pos = to_pos
    promotion_choice = None

    # 3. Detect Special Moves

    # A. PROMOTION (Stockfish adds a 5th letter, e.g., 'e7e8q')
    if len(uci_string) == 5:
        move_type = MoveType.PROMOTION
        promo_char = uci_string[4].lower()

        if promo_char == 'q':
            promotion_choice = ChessPieceType.QUEEN
        elif promo_char == 'r':
            promotion_choice = ChessPieceType.ROOK
        elif promo_char == 'b':
            promotion_choice = ChessPieceType.BISHOP
        elif promo_char == 'n':
            promotion_choice = ChessPieceType.KNIGHT

    # B. CASTLING
    # King moves 2 columns left or right
    elif moving_piece.type == ChessPieceType.KING and abs(from_pos.col - to_pos.col) == 2:
        move_type = MoveType.CASTLE

        # FIX: Force to_pos to be the Rook's square so execute_move() doesn't crash
        if to_not in ("g1", "g8"):  # Kingside
            rook_col = 7
        elif to_not in ("c1", "c8"):  # Queenside
            rook_col = 0

        to_pos = SquarePosition(row=from_pos.row, col=rook_col)
        victim_pos = to_pos

    # C. EN PASSANT
    # Pawn moves diagonally, but the landing square is completely empty
    elif moving_piece.type == ChessPieceType.PAWN and from_pos.col != to_pos.col:
        target_piece = board.get_piece_at(to_pos)
        if target_piece is None:
            move_type = MoveType.EN_PASSANT
            # The victim is on the same row the pawn started on, but in the new column
            victim_pos = SquarePosition(row=from_pos.row, col=to_pos.col)

    # 4. Construct your Move object
    final_move = Move(from_pos=from_pos, to_pos=to_pos, move_type=move_type, victim_pos=victim_pos)

    # Inject the promotion choice if needed
    if move_type == MoveType.PROMOTION:
        final_move.promotion_choice = promotion_choice

    return final_move

def get_uci_stockfish_move(fen_string: str) -> str:
    """
    Takes a board position (FEN), passes it to YOUR Stockfish, and returns the best move.
    """
    if not bot.is_fen_valid(fen_string):
        return "Error: You gave Stockfish an illegal or broken FEN string."

    bot.set_fen_position(fen_string)
    return bot.get_best_move()

def apply_skill_settings(elo, depth=15):
    """
    The Bouncer. Forces Stockfish to limit its brainpower.
    """
    # THE FIX: Modern Stockfish crashes if ELO is set below 1320!
    # If the factory asks for 900, we silently bump it to 1320 to keep the engine alive.
    safe_elo = max(1320, elo)

    # 9999 is our code for "God Mode"
    if elo >= 9999:
        bot.update_engine_parameters({"UCI_LimitStrength": False})
        bot.set_depth(depth)
    else:
        # THE FIX: The exact dictionary key Stockfish demands is "UCI_Elo"
        bot.update_engine_parameters({
            "UCI_LimitStrength": True,
            "UCI_Elo": safe_elo
        })

        # Even with low ELO, if Stockfish searches 15 moves deep, it will
        # accidentally find brilliant tactics. We have to blindfold it a bit.
        if safe_elo < 1500:
            bot.set_depth(5)
        elif safe_elo < 2000:
            bot.set_depth(8)
        else:
            bot.set_depth(12)

def get_stockfish_move(board, elo=9999, depth=15):
    """
    Gets a move from Stockfish, strictly obeying the ELO limit.
    """
    # 1. Wire up the brain settings before we ask for a move
    apply_skill_settings(elo, depth)

    # 2. Get the full FEN, not the core FEN!
    fen_string = board.generate_fen()
    best_uci_move = get_uci_stockfish_move(fen_string)

    # Catch the error if Stockfish hates the FEN
    if "Error" in best_uci_move:
        print(best_uci_move)
        return None

    return uci_to_move(board, best_uci_move)


# --- Test ---
if __name__ == "__main__":
    # Let's test if the Noob brain works
    start_fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

    # God Mode
    bot.update_engine_parameters({"UCI_LimitStrength": "false"})
    bot.set_depth(15)
    print(f"God Mode says: {get_uci_stockfish_move(start_fen)}")

    # 1300 ELO Mode
    bot.update_engine_parameters({"UCI_LimitStrength": "true", "Elo": 1300})
    bot.set_depth(5)
    print(f"1300 ELO says: {get_uci_stockfish_move(start_fen)}")