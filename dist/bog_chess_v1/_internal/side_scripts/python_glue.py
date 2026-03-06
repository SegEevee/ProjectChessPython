# fast_engine/python_glue.py
from __future__ import annotations

from array import array
from typing import Optional

from fast_engine import _core as core

# Adjust these imports to your project:

# -------- Board encoding to C++ --------
# We encode each square as int8:
#   0 = empty
#   +1..+6 = white pawn..king
#   -1..-6 = black pawn..king

_PIECE_TO_ABS = None

ChessColor = None
ChessPieceType = None
Move = None
MoveType = None
SquarePosition = None

def innit(chessColor, chessPieceType, move, moveType, squarePosition):
    global _PIECE_TO_ABS, ChessColor, ChessPieceType, Move, MoveType, SquarePosition
    ChessColor = chessColor
    ChessPieceType = chessPieceType
    Move = move
    MoveType = moveType
    SquarePosition = squarePosition
    
        
    _PIECE_TO_ABS = {
    ChessPieceType.PAWN: 1,
    ChessPieceType.KNIGHT: 2,
    ChessPieceType.BISHOP: 3,
    ChessPieceType.ROOK: 4,
    ChessPieceType.QUEEN: 5,
    ChessPieceType.KING: 6,
}

def _encode_board_to_bytes(board) -> bytes:
    vals = [0] * 64
    for r in range(8):
        for c in range(8):
            p = board.grid[r][c]
            idx = r * 8 + c
            if p is None:
                vals[idx] = 0
            else:
                abs_code = _PIECE_TO_ABS[p.type]
                sign = +1 if p.color == ChessColor.WHITE else -1
                vals[idx] = sign * abs_code
    return array("b", vals).tobytes()


def _castle_rights_mask(board) -> int:
    """
    Bits: 1 = WK, 2 = WQ, 4 = BK, 8 = BQ
    You MUST map this to your board's actual fields.
    """
    # If you already store a mask:
    if hasattr(board, "castle_rights_mask"):
        return int(board.castle_rights_mask) & 15

    mask = 0
    # Change these attribute names to your actual board fields if needed:
    if getattr(board, "white_can_castle_kingside", False):  mask |= 1
    if getattr(board, "white_can_castle_queenside", False): mask |= 2
    if getattr(board, "black_can_castle_kingside", False):  mask |= 4
    if getattr(board, "black_can_castle_queenside", False): mask |= 8
    return mask


def _ep_square_idx(board) -> int:
    """
    Return en-passant square index 0..63, or -1 if none.
    You MUST map to your board's EP representation.
    """
    ep = getattr(board, "en_passant_pos", None)
    if ep is None:
        return -1
    return ep.row * 8 + ep.col


def _idx_to_squarepos(idx: int) -> SquarePosition:
    r, c = divmod(idx, 8)
    # Your SquarePosition class might be (notation) or (row,col).
    # If it's notation-based, change this accordingly.
    return SquarePosition(row=r, col=c)


# -------- Main function you call from chess.py --------

def ai_get_best_move_cpp(board, ai_color: ChessColor, depth: int = 4) -> Optional[Move]:
    """
    Calls C++ core.search(...) and returns your Move object.
    """

    board_bytes = _encode_board_to_bytes(board)

    side_to_move = 0 if ai_color == ChessColor.WHITE else 1
    castle_mask = _castle_rights_mask(board)
    ep_idx = _ep_square_idx(board)

    from_idx, to_idx, promo = core.search(board_bytes, side_to_move, castle_mask, ep_idx, int(depth))

    if from_idx < 0:
        return None

    from_pos = _idx_to_squarepos(from_idx)
    to_pos = _idx_to_squarepos(to_idx)

    if promo != 0:
        m = Move(from_pos, to_pos, move_type=MoveType.PROMOTION)
        m.promotion_choice = ChessPieceType.QUEEN  # match your python engine choice
        return m

    return Move(from_pos, to_pos, move_type=MoveType.NORMAL)


def reset_tt_cpp():
    """Optional: expose TT reset from C++ to python."""
    core.reset_tt()