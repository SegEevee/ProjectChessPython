# opening_books.py
import random

# The key is the "Short FEN" (just the piece positions)
# The value is the specific move Black should play next
ALPERON_VARIATION = {
    # 1. White plays 1. e4 -> Black plays 1... d5
    "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR": "d7d5",

    # 2. White plays 2. exd5 -> Black plays 2... Qxd5
    "rnbqkbnr/ppp1pppp/8/3P4/8/8/PPPP1PPP/RNBQKBNR": "d8d5",

    # 3. White plays 3. Nc3 -> Black plays 3... Qd8 (The Alperon/Mieses-Kotroc retreat)
    "rnb1kbnr/ppp1pppp/8/3q4/8/2N5/PPPP1PPP/R1BQKBNR": "d5d8",

    # 4. White plays 4. d4 -> Black plays 4... Nf6
    "rnbqkbnr/ppp1pppp/8/8/3P4/2N5/PPP2PPP/R1BQKBNR": "g8f6",

    # 5. White plays 5. Nf3 -> Black plays 5... Bg4 (The Pin)
    "rnbqkb1r/ppp1pppp/5n2/8/3P4/2N2N2/PPP2PPP/R1BQKB1R": "c8g4",

    # 6. White plays 6. Bc4 -> Black plays 6... e6 (Solidifying the center)
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