import re
import sys

# ELI5: These are empty boxes. They don't know what a 'Board' is yet.
# chess.py will drop off the real classes into these boxes when the game boots.
Board = None
Move = None
MoveType = None
SquarePosition = None
ChessPieceType = None

STARTING_POSITION = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"


def init(passed_board, passed_move, passed_move_type, passed_square_pos, passed_piece_type):
    """The Loading Dock. chess.py drops off the chess rules here."""
    global Board, Move, MoveType, SquarePosition, ChessPieceType
    Board = passed_board
    Move = passed_move
    MoveType = passed_move_type
    SquarePosition = passed_square_pos
    ChessPieceType = passed_piece_type


def _clean_pgn(pgn_string: str) -> list[str]:
    """ELI5: Scraps all the extra junk (headers, comments, 1-0) out of the raw text."""
    text = re.sub(r'\[.*?\]', '', pgn_string, flags=re.DOTALL)
    text = re.sub(r'\{.*?\}', '', text, flags=re.DOTALL)
    text = re.sub(r'(1-0|0-1|1/2-1/2|\*)', '', text)

    tokens = text.split()
    moves = []

    for t in tokens:
        clean_token = re.sub(r'^\d+\.*', '', t)
        if clean_token and len(clean_token) < 10 and '/' not in clean_token:
            moves.append(clean_token)
        elif clean_token in ("O-O", "O-O-O"):
            moves.append(clean_token)
    return moves


def _find_move(board, san_string: str):
    """The Reverse SAN Trick. Finds the exact physical move object."""
    clean_san = san_string.replace("+", "").replace("#", "")
    promotion_type_str = None

    if "=" in clean_san:
        parts = clean_san.split("=")
        clean_san = parts[0]
        promotion_type_str = parts[1]

    for piece in board.get_all_pieces():
        if piece.color == board.active_color:
            for target_pos, move in piece.legal_moves.items():
                victim = board.get_piece_at(move.victim_pos) if move.victim_pos else None
                test_san = board.get_algebraic_notation(move, piece, victim)

                if test_san == clean_san:
                    if promotion_type_str and move.move_type == MoveType.PROMOTION:
                        for piece_type in ChessPieceType:
                            if piece_type.value == promotion_type_str:
                                move.promotion_choice = piece_type
                                break
                    return move
    return None


def _get_uci_string(move):
    """Translates a physical move into pure UCI language for the bots."""
    uci_move = move.from_pos.to_notation() + move.to_pos.to_notation()
    if move.move_type == MoveType.PROMOTION and move.promotion_choice:
        uci_move += move.promotion_choice.value.lower()
    return uci_move


def _run_in_isolation(func, *args):
    """
    THE QUARANTINE ZONE
    This forces the Ghost Board to use dummy players and clocks so it doesn't
    accidentally abduct pieces from the live game running in chess.py!
    """
    if Board is None:
        print("CRITICAL ERROR: You forgot to call init() from chess.py!")
        return {}

    # 1. Sneak into chess.py and grab the global dictionaries
    chess_mod = sys.modules[Board.__module__]
    original_players = chess_mod.PLAYERS
    original_clocks = chess_mod.CLOCKS

    # 2. Create a BLANK board first so it doesn't load pieces yet
    ghost_board = Board()

    # 3. Build fake isolated players and clocks for the ghost board
    sandboxed_players = {
        chess_mod.ChessColor.WHITE: chess_mod.Player(ghost_board, chess_mod.ChessColor.WHITE),
        chess_mod.ChessColor.BLACK: chess_mod.Player(ghost_board, chess_mod.ChessColor.BLACK)
    }
    sandboxed_clocks = {
        chess_mod.ChessColor.WHITE: chess_mod.ChessClock(chess_mod.ChessColor.WHITE, 300),
        chess_mod.ChessColor.BLACK: chess_mod.ChessClock(chess_mod.ChessColor.BLACK, 300)
    }

    try:
        # 4. Swap the global wires! chess.py is now hooked up to our sandbox
        chess_mod.PLAYERS = sandboxed_players
        chess_mod.CLOCKS = sandboxed_clocks

        # 5. NOW it is safe to load the FEN and generate moves
        ghost_board.load_fen(STARTING_POSITION)
        return func(ghost_board, *args)

    finally:
        # 6. CRITICAL: Put the live game back together even if the generator crashes!
        chess_mod.PLAYERS = original_players
        chess_mod.CLOCKS = original_clocks


def generate_dictionary_from_log(move_log: list, save_mode: str) -> dict:
    """The Live Forge: Translates the Diary into a Toybox of lists."""

    def _process_log(ghost_board, move_log, save_mode):
        toybox = {}
        for record in move_log:
            current_fen = ghost_board.generate_fen()
            core_fen = current_fen.split()[0] + " " + current_fen.split()[1]
            turn_color = "White" if ghost_board.active_color.value == "WHITE" else "Black"

            clean_san = record.algebraic_notation.replace("+", "").replace("#", "")
            move = _find_move(ghost_board, clean_san)

            if not move:
                break

            if save_mode == "Both" or save_mode == turn_color:
                uci_move = _get_uci_string(move)
                if core_fen not in toybox:
                    toybox[core_fen] = []
                if uci_move not in toybox[core_fen]:
                    toybox[core_fen].append(uci_move)

            ghost_board.execute_move(move, is_imagining=True)

        return toybox

    return _run_in_isolation(_process_log, move_log, save_mode)


def generate_dictionary_from_pgn(pgn_string: str, save_mode: str) -> dict:
    """The Text Importer: Translates raw text into a Toybox of lists."""

    def _process_pgn(ghost_board, pgn_string, save_mode):
        toybox = {}
        san_moves = _clean_pgn(pgn_string)

        for san in san_moves:
            current_fen = ghost_board.generate_fen()
            core_fen = current_fen.split()[0] + " " + current_fen.split()[1]
            turn_color = "White" if ghost_board.active_color.value == "WHITE" else "Black"

            move = _find_move(ghost_board, san)

            if not move:
                print(f"ERROR: The reverse-SAN engine choked on '{san}'. Stopping translation here.")
                break

            if save_mode == "Both" or save_mode == turn_color:
                uci_move = _get_uci_string(move)
                if core_fen not in toybox:
                    toybox[core_fen] = []
                if uci_move not in toybox[core_fen]:
                    toybox[core_fen].append(uci_move)

            ghost_board.execute_move(move, is_imagining=True)

        return toybox

    return _run_in_isolation(_process_pgn, pgn_string, save_mode)