import random

def get_random_bot_move(board, ai_color):
    moves = []
    for p in board.get_all_pieces():
        if p.color == ai_color:
            for m in p.legal_moves.values():
                moves.append(m)
    return random.choice(moves) if moves else None
