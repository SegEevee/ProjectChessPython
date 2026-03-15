import json
import os
from engines.stockfish import stockfishpy as stockfish

PERSONAL_OPENING_BOOK = {}
# Factory injected library card:
OPENING_BOOKS_LIST = ['bog']

Move = None; MoveType = None; ChessPieceType = None; SquarePosition = None; Board = None; ChessColor = None

def init_bot(passed_Move, passed_MoveType, passed_ChessPieceType, passed_SquarePosition, passed_Board, passed_ChessColor):
    global Move, MoveType, ChessPieceType, SquarePosition, Board, ChessColor, PERSONAL_OPENING_BOOK
    Move = passed_Move; MoveType = passed_MoveType; ChessPieceType = passed_ChessPieceType
    SquarePosition = passed_SquarePosition; Board = passed_Board; ChessColor = passed_ChessColor

    # Load the library!
    openings_dir = os.path.join(os.path.dirname(__file__), "..", "openings")
    for book_name in OPENING_BOOKS_LIST:
        book_path = os.path.join(openings_dir, f"{book_name}.json")
        if os.path.exists(book_path):
            try:
                with open(book_path, "r", encoding="utf-8") as f:
                    book_data = json.load(f)
                    PERSONAL_OPENING_BOOK.update(book_data)
                print(f"📖 hedo loaded opening book: {book_name}.json")
            except Exception as e:
                print(f"❌ hedo failed to read {book_name}.json: {e}")
        else:
            print(f"⚠️ hedo could not find {book_name}.json")

def get_move(board, ai_color):
    """Generated Middleman for hedo"""
    current_fen = board.generate_fen()
    short_fen = current_fen.split()[0]

    if short_fen in PERSONAL_OPENING_BOOK:
        move_str = PERSONAL_OPENING_BOOK[short_fen]
        for piece in board.get_all_pieces():
            if piece.color == ai_color and piece.position.to_notation() == move_str[:2]:
                for target_pos, move in piece.legal_moves.items():
                    if target_pos.to_notation() == move_str[2:]:
                        print(f"hedo played a book move: {move_str}")
                        return move

    print(f"hedo is thinking with Stockfish (ELO: 1000, Depth: 3)...")
    return stockfish.get_stockfish_move(board, elo=1000, depth=3)
