# chess_engine.py
from chess import Move, MoveType
import random

ChessColor = None
ChessPieceType = None

PIECE_VALUES = {}
KNIGHT_SCORES_1D = [0] * 64
PAWN_SCORES_1D_WHITE = [0] * 64

# Zobrist: keys for (color, piece_type, square)
ZOBRIST_PSQ = {}
ZOBRIST_SIDE_TO_MOVE = 0

# Transposition table: {hash: (depth, flag, score, best_move)}
# flag: 0 EXACT, 1 LOWERBOUND, 2 UPPERBOUND
TRANSPOSITION_TABLE = {}

EXACT = 0
LOWER = 1
UPPER = 2

INF = 100000
MATE_SCORE = 99999


def initialize_engine(color_enum, piece_enum, seed=1337):
    """
    Call once at startup.
    """
    global ChessColor, ChessPieceType, PIECE_VALUES
    global KNIGHT_SCORES_1D, PAWN_SCORES_1D_WHITE
    global ZOBRIST_PSQ, ZOBRIST_SIDE_TO_MOVE, TRANSPOSITION_TABLE

    ChessColor = color_enum
    ChessPieceType = piece_enum

    PIECE_VALUES = {
        ChessPieceType.PAWN: 100,
        ChessPieceType.KNIGHT: 320,
        ChessPieceType.BISHOP: 330,
        ChessPieceType.ROOK: 500,
        ChessPieceType.QUEEN: 900,
        ChessPieceType.KING: 20000
    }

    # Flatten PSTs (your same tables)
    knight_2d = [
        [-50, -40, -30, -30, -30, -30, -40, -50],
        [-40, -20,   0,   5,   5,   0, -20, -40],
        [-30,   5,  10,  15,  15,  10,   5, -30],
        [-30,   0,  15,  20,  20,  15,   0, -30],
        [-30,   5,  15,  20,  20,  15,   5, -30],
        [-30,   0,  10,  15,  15,  10,   0, -30],
        [-40, -20,   0,   0,   0,   0, -20, -40],
        [-50, -40, -30, -30, -30, -30, -40, -50]
    ]
    pawn_2d = [
        [0, 0, 0, 0, 0, 0, 0, 0],
        [50, 50, 50, 50, 50, 50, 50, 50],
        [10, 10, 20, 30, 30, 20, 10, 10],
        [5, 5, 10, 27, 27, 10, 5, 5],
        [0, 0, 0, 25, 25, 0, 0, 0],
        [5, -5, -10, 0, 0, -10, -5, 5],
        [5, 10, 10, -25, -25, 10, 10, 5],
        [0, 0, 0, 0, 0, 0, 0, 0]
    ]

    for r in range(8):
        for c in range(8):
            KNIGHT_SCORES_1D[r * 8 + c] = knight_2d[r][c]
            PAWN_SCORES_1D_WHITE[r * 8 + c] = pawn_2d[r][c]

    # Zobrist init
    rng = random.Random(seed)
    ZOBRIST_PSQ = {}
    for color in (ChessColor.WHITE, ChessColor.BLACK):
        for p_type in (
            ChessPieceType.PAWN, ChessPieceType.KNIGHT, ChessPieceType.BISHOP,
            ChessPieceType.ROOK, ChessPieceType.QUEEN, ChessPieceType.KING
        ):
            for sq in range(64):
                ZOBRIST_PSQ[(color, p_type, sq)] = rng.getrandbits(64)

    ZOBRIST_SIDE_TO_MOVE = rng.getrandbits(64)

    # Reset TT when initializing
    TRANSPOSITION_TABLE = {}


def _pst_bonus(color, p_type, idx):
    """
    Returns PST bonus from White POV.
    So when adding to eval (white-black), you add bonus for white pieces,
    subtract for black pieces.
    """
    if p_type == ChessPieceType.KNIGHT:
        return KNIGHT_SCORES_1D[idx]
    if p_type == ChessPieceType.PAWN:
        if color == ChessColor.WHITE:
            return PAWN_SCORES_1D_WHITE[idx]
        else:
            r, c = divmod(idx, 8)
            return PAWN_SCORES_1D_WHITE[(7 - r) * 8 + c]
    return 0


class ShadowBoard:
    def __init__(self, py_board=None, side_to_move=None):
        self.grid = [None] * 64

        # Incremental state
        self.eval_score = 0  # white - black
        self.w_king_pos = -1
        self.b_king_pos = -1

        # Zobrist hash
        self.zobrist = 0
        self.side_to_move = side_to_move  # ChessColor

        if py_board:
            self.sync_from_real(py_board)
            if self.side_to_move is None:
                # If you have turn info on your py_board, set it here.
                # Otherwise assume WHITE to move by default.
                self.side_to_move = ChessColor.WHITE

    def sync_from_real(self, py_board):
        """
        Build grid AND incremental eval AND zobrist in one pass.
        """
        self.eval_score = 0
        self.zobrist = 0
        self.w_king_pos = -1
        self.b_king_pos = -1

        for r in range(8):
            for c in range(8):
                p = py_board.grid[r][c]
                idx = r * 8 + c
                if p:
                    color, p_type = p.color, p.type
                    self.grid[idx] = (color, p_type)

                    # eval
                    v = PIECE_VALUES[p_type]
                    b = _pst_bonus(color, p_type, idx)
                    if color == ChessColor.WHITE:
                        self.eval_score += (v + b)
                        if p_type == ChessPieceType.KING:
                            self.w_king_pos = idx
                    else:
                        self.eval_score -= (v + b)
                        if p_type == ChessPieceType.KING:
                            self.b_king_pos = idx

                    # zobrist
                    self.zobrist ^= ZOBRIST_PSQ[(color, p_type, idx)]
                else:
                    self.grid[idx] = None

    def evaluate(self):
        """
        O(1) evaluation.
        """
        if self.w_king_pos == -1:
            return -MATE_SCORE
        if self.b_king_pos == -1:
            return MATE_SCORE
        return self.eval_score

    def execute(self, move_tuple):
        """
        move_tuple: (from_idx, to_idx, is_promotion)
        Returns an undo tuple with everything needed.
        """
        from_idx, to_idx, is_promotion = move_tuple
        moving_piece = self.grid[from_idx]
        captured_piece = self.grid[to_idx]

        m_color, m_type = moving_piece

        # Remove moving piece from from_idx (eval + hash)
        self.zobrist ^= ZOBRIST_PSQ[(m_color, m_type, from_idx)]
        v = PIECE_VALUES[m_type]
        b = _pst_bonus(m_color, m_type, from_idx)
        if m_color == ChessColor.WHITE:
            self.eval_score -= (v + b)
        else:
            self.eval_score += (v + b)

        # If capture, remove captured from to_idx
        if captured_piece:
            c_color, c_type = captured_piece
            self.zobrist ^= ZOBRIST_PSQ[(c_color, c_type, to_idx)]
            cv = PIECE_VALUES[c_type]
            cb = _pst_bonus(c_color, c_type, to_idx)
            if c_color == ChessColor.WHITE:
                self.eval_score -= (cv + cb)
            else:
                self.eval_score += (cv + cb)

        # Move piece (promotion changes type)
        self.grid[from_idx] = None
        if is_promotion:
            new_type = ChessPieceType.QUEEN
        else:
            new_type = m_type

        self.grid[to_idx] = (m_color, new_type)

        # Add moved piece at to_idx
        self.zobrist ^= ZOBRIST_PSQ[(m_color, new_type, to_idx)]
        nv = PIECE_VALUES[new_type]
        nb = _pst_bonus(m_color, new_type, to_idx)
        if m_color == ChessColor.WHITE:
            self.eval_score += (nv + nb)
        else:
            self.eval_score -= (nv + nb)

        # Update king position if needed
        old_wk = self.w_king_pos
        old_bk = self.b_king_pos
        if m_type == ChessPieceType.KING:
            if m_color == ChessColor.WHITE:
                self.w_king_pos = to_idx
            else:
                self.b_king_pos = to_idx

        # Flip side to move (hash)
        self.zobrist ^= ZOBRIST_SIDE_TO_MOVE
        prev_side = self.side_to_move
        self.side_to_move = ChessColor.BLACK if self.side_to_move == ChessColor.WHITE else ChessColor.WHITE

        return (moving_piece, captured_piece, old_wk, old_bk, prev_side)

    def undo(self, move_tuple, undo_info):
        from_idx, to_idx, is_promotion = move_tuple
        moving_piece, captured_piece, old_wk, old_bk, prev_side = undo_info

        # Flip side back
        self.zobrist ^= ZOBRIST_SIDE_TO_MOVE
        self.side_to_move = prev_side

        # Remove piece currently on to_idx (might be promoted queen)
        current_piece = self.grid[to_idx]
        cur_color, cur_type = current_piece

        self.zobrist ^= ZOBRIST_PSQ[(cur_color, cur_type, to_idx)]
        cv = PIECE_VALUES[cur_type]
        cb = _pst_bonus(cur_color, cur_type, to_idx)
        if cur_color == ChessColor.WHITE:
            self.eval_score -= (cv + cb)
        else:
            self.eval_score += (cv + cb)

        # Restore captured piece (if any) at to_idx
        self.grid[to_idx] = captured_piece
        if captured_piece:
            c_color, c_type = captured_piece
            self.zobrist ^= ZOBRIST_PSQ[(c_color, c_type, to_idx)]
            capv = PIECE_VALUES[c_type]
            capb = _pst_bonus(c_color, c_type, to_idx)
            if c_color == ChessColor.WHITE:
                self.eval_score += (capv + capb)
            else:
                self.eval_score -= (capv + capb)

        # Restore moving piece to from_idx (original type, not promoted)
        m_color, m_type = moving_piece
        self.grid[from_idx] = moving_piece
        self.zobrist ^= ZOBRIST_PSQ[(m_color, m_type, from_idx)]
        mv = PIECE_VALUES[m_type]
        mb = _pst_bonus(m_color, m_type, from_idx)
        if m_color == ChessColor.WHITE:
            self.eval_score += (mv + mb)
        else:
            self.eval_score -= (mv + mb)

        # Restore king positions
        self.w_king_pos = old_wk
        self.b_king_pos = old_bk

    def get_pseudo_legal_moves(self, color, only_captures=False):
        """
        Your original generator (kept for now).
        Still sorts each time; we will remove sorting next step.
        Format returned: (score, from_idx, to_idx, is_promotion)
        """
        moves = []
        enemy_color = ChessColor.BLACK if color == ChessColor.WHITE else ChessColor.WHITE

        for i in range(64):
            piece = self.grid[i]
            if piece and piece[0] == color:
                r, c = divmod(i, 8)
                p_type = piece[1]

                # 1. PAWNS
                if p_type == ChessPieceType.PAWN:
                    direction = -1 if color == ChessColor.WHITE else 1
                    prom_row = 0 if color == ChessColor.WHITE else 7

                    # Push
                    if not only_captures:
                        nr = r + direction
                        if 0 <= nr < 8:
                            target_idx = nr * 8 + c
                            if self.grid[target_idx] is None:
                                is_prom = (nr == prom_row)
                                moves.append((8000 if is_prom else 0, i, target_idx, is_prom))
                                # Double push
                                start_row = 6 if color == ChessColor.WHITE else 1
                                if r == start_row:
                                    double_idx = (r + 2 * direction) * 8 + c
                                    if self.grid[double_idx] is None:
                                        moves.append((0, i, double_idx, False))

                    # Captures
                    for dc in (-1, 1):
                        nc = c + dc
                        nr = r + direction
                        if 0 <= nr < 8 and 0 <= nc < 8:
                            target_idx = nr * 8 + nc
                            target = self.grid[target_idx]
                            if target and target[0] == enemy_color:
                                is_prom = (nr == prom_row)
                                score = (PIECE_VALUES[target[1]] * 10) - PIECE_VALUES[ChessPieceType.PAWN]
                                moves.append((score + (8000 if is_prom else 0), i, target_idx, is_prom))

                # 2. KNIGHTS
                elif p_type == ChessPieceType.KNIGHT:
                    for dr, dc in ((2, 1), (1, 2), (-1, 2), (-2, 1), (-2, -1), (-1, -2), (1, -2), (2, -1)):
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < 8 and 0 <= nc < 8:
                            target_idx = nr * 8 + nc
                            target = self.grid[target_idx]
                            if target is None:
                                if not only_captures:
                                    moves.append((0, i, target_idx, False))
                            elif target[0] == enemy_color:
                                score = (PIECE_VALUES[target[1]] * 10) - PIECE_VALUES[ChessPieceType.KNIGHT]
                                moves.append((score, i, target_idx, False))

                # 3. SLIDING
                elif p_type in (ChessPieceType.ROOK, ChessPieceType.BISHOP, ChessPieceType.QUEEN):
                    dirs = []
                    if p_type in (ChessPieceType.ROOK, ChessPieceType.QUEEN):
                        dirs.extend(((0, 1), (1, 0), (0, -1), (-1, 0)))
                    if p_type in (ChessPieceType.BISHOP, ChessPieceType.QUEEN):
                        dirs.extend(((1, 1), (1, -1), (-1, 1), (-1, -1)))

                    for dr, dc in dirs:
                        nr, nc = r + dr, c + dc
                        while 0 <= nr < 8 and 0 <= nc < 8:
                            target_idx = nr * 8 + nc
                            target = self.grid[target_idx]
                            if target is None:
                                if not only_captures:
                                    moves.append((0, i, target_idx, False))
                            else:
                                if target[0] == enemy_color:
                                    score = (PIECE_VALUES[target[1]] * 10) - PIECE_VALUES[p_type]
                                    moves.append((score, i, target_idx, False))
                                break
                            nr += dr
                            nc += dc

                # 4. KING
                elif p_type == ChessPieceType.KING:
                    for dr, dc in ((0, 1), (1, 0), (0, -1), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)):
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < 8 and 0 <= nc < 8:
                            target_idx = nr * 8 + nc
                            target = self.grid[target_idx]
                            if target is None:
                                if not only_captures:
                                    moves.append((0, i, target_idx, False))
                            elif target[0] == enemy_color:
                                score = (PIECE_VALUES[target[1]] * 10) - PIECE_VALUES[ChessPieceType.KING]
                                moves.append((score, i, target_idx, False))

        moves.sort(key=lambda x: x[0], reverse=True)
        return moves


def shadow_quiescence(board: ShadowBoard, alpha, beta, color):
    stand_pat = board.evaluate()

    # Mate checks (your old style)
    if stand_pat >= 90000 and color == ChessColor.BLACK:
        return stand_pat
    if stand_pat <= -90000 and color == ChessColor.WHITE:
        return stand_pat

    enemy_color = ChessColor.BLACK if color == ChessColor.WHITE else ChessColor.WHITE

    if color == ChessColor.WHITE:
        if stand_pat >= beta:
            return beta
        if stand_pat > alpha:
            alpha = stand_pat

        for m in board.get_pseudo_legal_moves(ChessColor.WHITE, only_captures=True):
            move_tuple = (m[1], m[2], m[3])
            undo_info = board.execute(move_tuple)
            score = shadow_quiescence(board, alpha, beta, enemy_color)
            board.undo(move_tuple, undo_info)

            if score >= beta:
                return beta
            if score > alpha:
                alpha = score
        return alpha
    else:
        if stand_pat <= alpha:
            return alpha
        if stand_pat < beta:
            beta = stand_pat

        for m in board.get_pseudo_legal_moves(ChessColor.BLACK, only_captures=True):
            move_tuple = (m[1], m[2], m[3])
            undo_info = board.execute(move_tuple)
            score = shadow_quiescence(board, alpha, beta, enemy_color)
            board.undo(move_tuple, undo_info)

            if score <= alpha:
                return alpha
            if score < beta:
                beta = score
        return beta


def _tt_probe(board_hash, depth, alpha, beta):
    entry = TRANSPOSITION_TABLE.get(board_hash)
    if not entry:
        return None
    e_depth, e_flag, e_score, e_best = entry
    if e_depth < depth:
        return None

    if e_flag == EXACT:
        return e_score
    if e_flag == LOWER and e_score >= beta:
        return e_score
    if e_flag == UPPER and e_score <= alpha:
        return e_score
    return None


def _tt_store(board_hash, depth, flag, score, best_move):
    # Simple replacement: prefer deeper
    prev = TRANSPOSITION_TABLE.get(board_hash)
    if prev is None or depth >= prev[0]:
        TRANSPOSITION_TABLE[board_hash] = (depth, flag, score, best_move)


def shadow_search_pvs(board: ShadowBoard, depth, alpha, beta, color):
    """
    Alpha-beta with TT + PVS.
    """
    if depth == 0:
        return shadow_quiescence(board, alpha, beta, color)

    eval_score = board.evaluate()
    if eval_score >= 90000 or eval_score <= -90000:
        return eval_score

    # TT probe
    hit = _tt_probe(board.zobrist, depth, alpha, beta)
    if hit is not None:
        return hit

    enemy_color = ChessColor.BLACK if color == ChessColor.WHITE else ChessColor.WHITE
    best_move = None
    alpha_orig = alpha
    beta_orig = beta

    # Move ordering: TT best move first (if exists)
    tt_entry = TRANSPOSITION_TABLE.get(board.zobrist)
    tt_best = tt_entry[3] if tt_entry else None

    moves = board.get_pseudo_legal_moves(color)
    if tt_best is not None:
        # bring tt_best to front if present
        # tt_best is stored as (from,to,is_prom)
        for j in range(len(moves)):
            if moves[j][1] == tt_best[0] and moves[j][2] == tt_best[1] and moves[j][3] == tt_best[2]:
                moves[0], moves[j] = moves[j], moves[0]
                break

    if not moves:
        # No moves: treat as static eval for now (later: checkmate/stalemate)
        return eval_score

    if color == ChessColor.WHITE:
        value = -INF
        first = True
        for m in moves:
            mv = (m[1], m[2], m[3])
            undo_info = board.execute(mv)

            if first:
                score = shadow_search_pvs(board, depth - 1, alpha, beta, enemy_color)
                first = False
            else:
                # PVS null window
                score = shadow_search_pvs(board, depth - 1, alpha, alpha + 1, enemy_color)
                if score > alpha and score < beta:
                    score = shadow_search_pvs(board, depth - 1, alpha, beta, enemy_color)

            board.undo(mv, undo_info)

            if score > value:
                value = score
                best_move = mv
            if score > alpha:
                alpha = score
            if alpha >= beta:
                break

        # Store TT
        if value <= alpha_orig:
            flag = UPPER
        elif value >= beta_orig:
            flag = LOWER
        else:
            flag = EXACT
        _tt_store(board.zobrist, depth, flag, value, best_move)
        return value

    else:
        value = INF
        first = True
        for m in moves:
            mv = (m[1], m[2], m[3])
            undo_info = board.execute(mv)

            if first:
                score = shadow_search_pvs(board, depth - 1, alpha, beta, enemy_color)
                first = False
            else:
                score = shadow_search_pvs(board, depth - 1, beta - 1, beta, enemy_color)
                if score < beta and score > alpha:
                    score = shadow_search_pvs(board, depth - 1, alpha, beta, enemy_color)

            board.undo(mv, undo_info)

            if score < value:
                value = score
                best_move = mv
            if score < beta:
                beta = score
            if alpha >= beta:
                break

        if value <= alpha_orig:
            flag = UPPER
        elif value >= beta_orig:
            flag = LOWER
        else:
            flag = EXACT
        _tt_store(board.zobrist, depth, flag, value, best_move)
        return value


def ai_get_best_move(board, ai_color, search_depth=4):
    """
    Root: still uses your real board for move generation,
    but evaluates each move using ONE ShadowBoard that we update via sync once per move.
    Next patch will convert root to pure shadow moves (no resync per root).
    """
    moves = []
    for piece in board.get_all_pieces():
        if piece.color == ai_color:
            for move in piece.legal_moves.values():
                moves.append(move)
    if not moves:
        return None

    enemy_color = ChessColor.BLACK if ai_color == ChessColor.WHITE else ChessColor.WHITE

    best_move = None
    best_score = -INF if ai_color == ChessColor.WHITE else INF

    # Iterative deepening
    shadow = ShadowBoard()
    for current_depth in range(1, search_depth + 1):
        # Aspiration window around last best score (simple)
        if current_depth == 1:
            window_alpha, window_beta = -INF, INF
        else:
            margin = 50
            window_alpha = best_score - margin
            window_beta = best_score + margin

        # If aspiration fails, we widen
        def search_with_window(a, b):
            nonlocal best_move, best_score
            local_best = None
            local_best_score = -INF if ai_color == ChessColor.WHITE else INF

            for move in moves:
                if move.move_type == MoveType.PROMOTION:
                    move.promotion_choice = ChessPieceType.QUEEN

                board.execute_move(move, is_imagining=True)
                shadow.sync_from_real(board)
                shadow.side_to_move = enemy_color
                shadow.zobrist ^= ZOBRIST_SIDE_TO_MOVE  # because side_to_move differs after move

                score = shadow_search_pvs(shadow, current_depth - 1, a, b, enemy_color)

                board.undo_move()

                if ai_color == ChessColor.WHITE:
                    if score > local_best_score:
                        local_best_score = score
                        local_best = move
                else:
                    if score < local_best_score:
                        local_best_score = score
                        local_best = move

            best_move = local_best
            best_score = local_best_score

        search_with_window(window_alpha, window_beta)

        # Aspiration fail: widen
        if ai_color == ChessColor.WHITE:
            if best_score <= window_alpha or best_score >= window_beta:
                search_with_window(-INF, INF)
        else:
            if best_score <= window_alpha or best_score >= window_beta:
                search_with_window(-INF, INF)

    return best_move