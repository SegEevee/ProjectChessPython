import random
import json
import os

PERSONAL_OPENING_BOOK = {}
# Factory injected library card:
OPENING_BOOKS_LIST = [] 

Move = None; MoveType = None; ChessPieceType = None; SquarePosition = None; Board = None; ChessColor = None

def init_bot(passed_Move, passed_MoveType, passed_ChessPieceType, passed_SquarePosition, passed_Board, passed_ChessColor):
    """The Care Package. Main.py hands us the tools, and we read our books."""
    global Move, MoveType, ChessPieceType, SquarePosition, Board, ChessColor, PERSONAL_OPENING_BOOK
    Move = passed_Move; MoveType = passed_MoveType; ChessPieceType = passed_ChessPieceType
    SquarePosition = passed_SquarePosition; Board = passed_Board; ChessColor = passed_ChessColor

    openings_dir = os.path.join(os.path.dirname(__file__), "..", "openings")
    for book_name in OPENING_BOOKS_LIST:
        book_path = os.path.join(openings_dir, f"{book_name}.json")
        if os.path.exists(book_path):
            try:
                with open(book_path, "r", encoding="utf-8") as f:
                    book_data = json.load(f)
                    PERSONAL_OPENING_BOOK.update(book_data)
                print(f"📖 bog_ai loaded opening book: {book_name}.json")
            except Exception as e:
                print(f"❌ bog_ai failed to read {book_name}.json: {e}")
        else:
            print(f"⚠️ bog_ai could not find {book_name}.json")

def get_move(board, ai_color):
    """The Traffic Cop. Checks the book first, then asks your custom brain."""
    current_fen = board.generate_fen()

    # THE UPGRADE: We MUST include the turn color (w or b) so White doesn't play Black's moves!
    core_fen = current_fen.split()[0] + " " + current_fen.split()[1]

    if core_fen in PERSONAL_OPENING_BOOK:
        toybox = PERSONAL_OPENING_BOOK[core_fen]

        if isinstance(toybox, str): 
            toybox = [toybox]

        move_str = random.choice(toybox)

        for piece in board.get_all_pieces():
            if piece.color == ai_color and piece.position.to_notation() == move_str[:2]:
                for target_pos, move in piece.legal_moves.items():
                    if target_pos.to_notation() == move_str[2:]:
                        print(f"bog_ai played a random book move: {move_str}")
                        return move

    return get_custom_move(board, ai_color)

def get_custom_move(board, ai_color):
    all_possible_moves = []
    for piece in board.get_all_pieces():
        if piece.color == ai_color:
            for move in piece.legal_moves.values():
                all_possible_moves.append(move)

    if not all_possible_moves: return None
    return random.choice(all_possible_moves)
