from engines.stockfish import stockfishpy as stockfish

# ELI5: This is your bot's personal memory for the first few moves.
# Paste the short FEN (board only) as the key, and the move as the value.
# Example: {"rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR": "e2e4"}
PERSONAL_OPENING_BOOK = {

}

def get_move(board, ai_color):
    """Generated Middleman for stockfish"""
    current_fen = board.generate_fen()
    short_fen = current_fen.split()[0]

    # 1. Personal Opening Book Check
    if short_fen in PERSONAL_OPENING_BOOK:
        move_str = PERSONAL_OPENING_BOOK[short_fen]

        # ELI5: Find the piece and make the exact move from the book
        for piece in board.get_all_pieces():
            if piece.color == ai_color and piece.position.to_notation() == move_str[:2]:
                for target_pos, move in piece.legal_moves.items():
                    if target_pos.to_notation() == move_str[2:]:
                        print(f"stockfish played a book move: {move_str}")
                        return move

    # 2. Engine Fallback
    return stockfish.get_stockfish_move(board,elo=9999)
