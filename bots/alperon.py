import random

# The key is the "Short FEN" (just the piece positions)
# The value is the specific move Black should play next
ALPERON_VARIATION = {
    "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR": "d7d5",

    "rnbqkbnr/ppp1pppp/8/3P4/8/8/PPPP1PPP/RNBQKBNR": "d8d5",

    "rnb1kbnr/ppp1pppp/8/3q4/8/2N5/PPPP1PPP/R1BQKBNR": "d5d8",

    "rnbqkbnr/ppp1pppp/8/8/3P4/2N5/PPP2PPP/R1BQKBNR": "g8f6",

    "rnbqkb1r/ppp1pppp/5n2/8/3P4/2N2N2/PPP2PPP/R1BQKB1R": "c8g4",

    "rn1qkb1r/ppp1pppp/5n2/8/2BP2b1/2N2N2/PPP2PPP/R1BQK2R": "e7e6"
}

def get_alperon_variation(fen):
    """
    Checks the book for a move based on the current board layout.
    Works by splitting the FEN and only comparing the board structure.
    """
    if not fen:
        return None
    short_fen = fen.split()[0]
    return ALPERON_VARIATION.get(short_fen, None)

# The Care Package variables
Move = None; MoveType = None; ChessPieceType = None; SquarePosition = None; Board = None; ChessColor = None

def init_bot(passed_Move, passed_MoveType, passed_ChessPieceType, passed_SquarePosition, passed_Board, passed_ChessColor):
    """The Care Package. Main.py hands us the tools we need."""
    global Move, MoveType, ChessPieceType, SquarePosition, Board, ChessColor
    Move = passed_Move; MoveType = passed_MoveType; ChessPieceType = passed_ChessPieceType
    SquarePosition = passed_SquarePosition; Board = passed_Board; ChessColor = passed_ChessColor

def get_move(board, ai_color):
    """The Traffic Cop. Checks the book first, then asks your custom brain."""
    current_fen = board.generate_fen()
    short_fen = current_fen.split()[0]

    # 1. Check the Opening Book first!
    if short_fen in ALPERON_VARIATION:
        move_str = ALPERON_VARIATION[short_fen]

        # Find the piece and make the exact move from the book
        for piece in board.get_all_pieces():
            if piece.color == ai_color and piece.position.to_notation() == move_str[:2]:
                for target_pos, move in piece.legal_moves.items():
                    if target_pos.to_notation() == move_str[2:]:
                        print(f"alperon played a book move: {move_str}")
                        return move

    # 2. If no book move exists, use your custom brain!
    return get_alperon_move(board, ai_color)

def get_alperon_move(board, ai_color: ChessColor):
    """The Toddler Brain: Grabs the shiniest piece on the board and ignores the consequences."""
    best_move = None
    current_fen = board.generate_fen()
    short_fen = current_fen.split()[0]

    # Look for the current board in our book
    if short_fen in ALPERON_VARIATION:
        move_str = get_alperon_variation(current_fen)
        from_not = move_str[:2]  # "e7"
        to_not = move_str[2:]  # "e5"

        # Convert notation to actual board positions
        from_pos = SquarePosition(notation=from_not)
        to_pos = SquarePosition(notation=to_not)

        # Find the piece and the move object
        piece = board.get_piece_at(from_pos)
        if piece and to_pos in piece.legal_moves:
            return piece.legal_moves[to_pos]
    # We start at -1 so that even a "0 point" move (a normal move with no capture)
    # looks good if there is absolutely nothing to eat.
    max_snack_value = -1

    all_possible_moves = []

    # A quick cheat sheet for the toddler to know what tastes best
    piece_values = {
        "P": 100,
        "N": 320,
        "B": 330,
        "R": 500,
        "Q": 900,
        "K": 20000
    }

    # 1. Walk through the whole board and look at our pieces
    for piece in board.get_all_pieces():
        if piece.color == ai_color:

            # 2. Look at every single move this piece can make
            for target_pos, move in piece.legal_moves.items():
                all_possible_moves.append(move)

                # Assume this move gives us 0 points to start
                current_move_value = 0

                # --- THE GREEDY CHECK ---

                # A. Does this move eat somebody?
                if move.victim_pos:
                    victim = board.get_piece_at(move.victim_pos)
                    if victim:
                        # Look up the victim's letter ('Q', 'R', etc.) to get its score
                        current_move_value = piece_values.get(victim.type.value, 0)

                # B. Does this move turn a Pawn into a Queen?
                if move.move_type == MoveType.PROMOTION:
                    current_move_value += 800  # A pawn (100) becomes a Queen (900), gaining 800 points!

                # C. Is this the biggest reward we have seen so far?
                # We use > instead of >= so it naturally picks the *first* best move it finds
                if current_move_value > max_snack_value:
                    max_snack_value = current_move_value
                    best_move = move

    # 3. If everything is equal (like at the very start of the game where no captures exist),
    # the greedy bot gets confused. Let's just have it pick a random move so the game doesn't freeze.
    if max_snack_value == 0 and all_possible_moves:
        best_move = random.choice(all_possible_moves)

    # 4. If it's a promotion, always take the Queen! (Maximum greed)
    if best_move and best_move.move_type == MoveType.PROMOTION:
        best_move.promotion_choice = ChessPieceType.QUEEN

    return best_move


