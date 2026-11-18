CHESS_PIECES = {
    0 : "Pawn",
    1 : "Knight",
    2 : "Bishop",
    3 : "Rook",
    4 : "Queen",
    5 : "King"
}

WHITE, BLACK = 0, 1
PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING = range(6)

CASTLE_WK = 1
CASTLE_WQ = 2
CASTLE_BK = 4
CASTLE_BQ = 8

FILES = "abcdefgh"
SQUARE_NAMES = [f"{FILES[s % 8]}{s // 8 + 1}" for s in range(64)]


def sq(file, rank):
    return rank * 8 + file


def file_of(square):
    return square % 8


def rank_of(square):
    return square // 8


def bit(square):
    return 1 << square


KNIGHT_ATTACKS = [0] * 64
KING_ATTACKS = [0] * 64
WHITE_PAWN_ATTACKS = [0] * 64
BLACK_PAWN_ATTACKS = [0] * 64

KNIGHT_DELTAS = ((1, 2), (2, 1), (2, -1), (1, -2), (-1, -2), (-2, -1), (-2, 1), (-1, 2))
KING_DELTAS = ((1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1))
BISHOP_DIRS = ((1, 1), (1, -1), (-1, 1), (-1, -1))
ROOK_DIRS = ((1, 0), (-1, 0), (0, 1), (0, -1))

for _s in range(64):
    _f, _r = file_of(_s), rank_of(_s)

    for _df, _dr in KNIGHT_DELTAS:
        _nf, _nr = _f + _df, _r + _dr
        if 0 <= _nf < 8 and 0 <= _nr < 8:
            KNIGHT_ATTACKS[_s] |= bit(sq(_nf, _nr))

    for _df, _dr in KING_DELTAS:
        _nf, _nr = _f + _df, _r + _dr
        if 0 <= _nf < 8 and 0 <= _nr < 8:
            KING_ATTACKS[_s] |= bit(sq(_nf, _nr))

    for _df in (-1, 1):
        _nf, _nr = _f + _df, _r + 1
        if 0 <= _nf < 8 and _nr < 8:
            WHITE_PAWN_ATTACKS[_s] |= bit(sq(_nf, _nr))
        _nf, _nr = _f + _df, _r - 1
        if 0 <= _nf < 8 and _nr >= 0:
            BLACK_PAWN_ATTACKS[_s] |= bit(sq(_nf, _nr))


def sliding_attacks(square, occupied, directions):
    attacks = 0
    f0, r0 = file_of(square), rank_of(square)
    for df, dr in directions:
        f, r = f0 + df, r0 + dr
        while 0 <= f < 8 and 0 <= r < 8:
            target = sq(f, r)
            attacks |= bit(target)
            if occupied & bit(target):
                break
            f += df
            r += dr
    return attacks


def bishop_attacks(square, occupied):
    return sliding_attacks(square, occupied, BISHOP_DIRS)


def rook_attacks(square, occupied):
    return sliding_attacks(square, occupied, ROOK_DIRS)


def queen_attacks(square, occupied):
    return bishop_attacks(square, occupied) | rook_attacks(square, occupied)


def get_default_chess_board():
    return AiBoard()


class Move:
    def __init__(self, from_sq, to_sq, piece, color, captured_piece=None, captured_color=None,
                 promotion=None, is_en_passant=False, is_castle=False, is_double_push=False,
                 captured_sq=None):
        self.from_sq = from_sq
        self.to_sq = to_sq
        self.piece = piece
        self.color = color
        self.captured_piece = captured_piece
        self.captured_color = captured_color
        self.promotion = promotion
        self.is_en_passant = is_en_passant
        self.is_castle = is_castle
        self.is_double_push = is_double_push
        self.captured_sq = captured_sq if captured_sq is not None else to_sq

    def __eq__(self, other):
        return (isinstance(other, Move) and self.from_sq == other.from_sq
                and self.to_sq == other.to_sq and self.promotion == other.promotion
                and self.is_castle == other.is_castle)

    def __repr__(self):
        promo = f"={CHESS_PIECES[self.promotion]}" if self.promotion is not None else ""
        return f"{CHESS_PIECES[self.piece]} {SQUARE_NAMES[self.from_sq]}->{SQUARE_NAMES[self.to_sq]}{promo}"


class AiBoard:
    def __init__(self):
        self.piece_bb = [[0] * 6 for _ in range(2)]
        self.color_bb = [0, 0]
        self.occupied = 0
        self.side_to_move = WHITE
        self.castling_rights = CASTLE_WK | CASTLE_WQ | CASTLE_BK | CASTLE_BQ
        self.en_passant_square = None
        self.halfmove_clock = 0
        self.fullmove_number = 1
        self.history = []
        self.set_start_position()

    def set_start_position(self):
        self.piece_bb = [[0] * 6 for _ in range(2)]
        back_rank = (ROOK, KNIGHT, BISHOP, QUEEN, KING, BISHOP, KNIGHT, ROOK)
        for file_idx, p_type in enumerate(back_rank):
            self.piece_bb[WHITE][p_type] |= bit(sq(file_idx, 0))
            self.piece_bb[BLACK][p_type] |= bit(sq(file_idx, 7))
        for file_idx in range(8):
            self.piece_bb[WHITE][PAWN] |= bit(sq(file_idx, 1))
            self.piece_bb[BLACK][PAWN] |= bit(sq(file_idx, 6))

        self.side_to_move = WHITE
        self.castling_rights = CASTLE_WK | CASTLE_WQ | CASTLE_BK | CASTLE_BQ
        self.en_passant_square = None
        self.halfmove_clock = 0
        self.fullmove_number = 1
        self.history = []
        self._update_occupancy()

    def _update_occupancy(self):
        self.color_bb[WHITE] = 0
        self.color_bb[BLACK] = 0
        for p_type in range(6):
            self.color_bb[WHITE] |= self.piece_bb[WHITE][p_type]
            self.color_bb[BLACK] |= self.piece_bb[BLACK][p_type]
        self.occupied = self.color_bb[WHITE] | self.color_bb[BLACK]

    def piece_at(self, square):
        square_bit = bit(square)
        for color in (WHITE, BLACK):
            for p_type in range(6):
                if self.piece_bb[color][p_type] & square_bit:
                    return color, p_type
        return None

    def king_square(self, color):
        king_bb = self.piece_bb[color][KING]
        return (king_bb & -king_bb).bit_length() - 1 if king_bb else None

    def attacks_from(self, square, color, piece_type):
        if piece_type == PAWN:
            return WHITE_PAWN_ATTACKS[square] if color == WHITE else BLACK_PAWN_ATTACKS[square]
        if piece_type == KNIGHT:
            return KNIGHT_ATTACKS[square]
        if piece_type == KING:
            return KING_ATTACKS[square]
        if piece_type == BISHOP:
            return bishop_attacks(square, self.occupied)
        if piece_type == ROOK:
            return rook_attacks(square, self.occupied)
        return queen_attacks(square, self.occupied)

    def is_square_attacked(self, square, by_color):
        target_bit = bit(square)
        for p_type in range(6):
            bb = self.piece_bb[by_color][p_type]
            while bb:
                lsb = bb & -bb
                from_sq = lsb.bit_length() - 1
                bb ^= lsb
                if self.attacks_from(from_sq, by_color, p_type) & target_bit:
                    return True
        return False

    def is_in_check(self, color):
        king_sq = self.king_square(color)
        if king_sq is None:
            return False
        enemy = BLACK if color == WHITE else WHITE
        return self.is_square_attacked(king_sq, enemy)

    def generate_pseudo_legal_moves(self, color=None):
        if color is None:
            color = self.side_to_move

        moves = []
        enemy = BLACK if color == WHITE else WHITE
        own_occ = self.color_bb[color]
        enemy_occ = self.color_bb[enemy]

        moves.extend(self._generate_pawn_moves(color, enemy_occ))

        for p_type in (KNIGHT, BISHOP, ROOK, QUEEN, KING):
            bb = self.piece_bb[color][p_type]
            while bb:
                lsb = bb & -bb
                from_sq = lsb.bit_length() - 1
                bb ^= lsb

                targets = self.attacks_from(from_sq, color, p_type) & ~own_occ
                while targets:
                    tlsb = targets & -targets
                    to_sq = tlsb.bit_length() - 1
                    targets ^= tlsb

                    if enemy_occ & bit(to_sq):
                        cap_color, cap_piece = self.piece_at(to_sq)
                        moves.append(Move(from_sq, to_sq, p_type, color, cap_piece, cap_color))
                    else:
                        moves.append(Move(from_sq, to_sq, p_type, color))

        moves.extend(self._generate_castle_moves(color))
        return moves

    def _generate_pawn_moves(self, color, enemy_occ):
        moves = []
        direction = 1 if color == WHITE else -1
        start_rank = 1 if color == WHITE else 6
        promo_rank = 7 if color == WHITE else 0
        pawn_attacks = WHITE_PAWN_ATTACKS if color == WHITE else BLACK_PAWN_ATTACKS
        enemy = BLACK if color == WHITE else WHITE

        bb = self.piece_bb[color][PAWN]
        while bb:
            lsb = bb & -bb
            from_sq = lsb.bit_length() - 1
            bb ^= lsb
            f, r = file_of(from_sq), rank_of(from_sq)

            one_sq = sq(f, r + direction)
            if not (self.occupied & bit(one_sq)):
                if r + direction == promo_rank:
                    for promo in (QUEEN, ROOK, BISHOP, KNIGHT):
                        moves.append(Move(from_sq, one_sq, PAWN, color, promotion=promo))
                else:
                    moves.append(Move(from_sq, one_sq, PAWN, color))
                    if r == start_rank:
                        two_sq = sq(f, r + 2 * direction)
                        if not (self.occupied & bit(two_sq)):
                            moves.append(Move(from_sq, two_sq, PAWN, color, is_double_push=True))

            targets = pawn_attacks[from_sq] & enemy_occ
            while targets:
                tlsb = targets & -targets
                to_sq = tlsb.bit_length() - 1
                targets ^= tlsb
                cap_color, cap_piece = self.piece_at(to_sq)
                if rank_of(to_sq) == promo_rank:
                    for promo in (QUEEN, ROOK, BISHOP, KNIGHT):
                        moves.append(Move(from_sq, to_sq, PAWN, color, cap_piece, cap_color, promotion=promo))
                else:
                    moves.append(Move(from_sq, to_sq, PAWN, color, cap_piece, cap_color))

            if self.en_passant_square is not None and (pawn_attacks[from_sq] & bit(self.en_passant_square)):
                captured_sq = sq(file_of(self.en_passant_square), rank_of(self.en_passant_square) - direction)
                moves.append(Move(from_sq, self.en_passant_square, PAWN, color, PAWN, enemy,
                                   is_en_passant=True, captured_sq=captured_sq))

        return moves

    def _generate_castle_moves(self, color):
        moves = []
        enemy = BLACK if color == WHITE else WHITE
        if self.is_in_check(color):
            return moves

        if color == WHITE:
            king_from = sq(4, 0)
            kingside_flag, kingside_empty, kingside_path, kingside_to = (
                CASTLE_WK, (sq(5, 0), sq(6, 0)), (sq(4, 0), sq(5, 0), sq(6, 0)), sq(6, 0))
            queenside_flag, queenside_empty, queenside_path, queenside_to = (
                CASTLE_WQ, (sq(1, 0), sq(2, 0), sq(3, 0)), (sq(4, 0), sq(3, 0), sq(2, 0)), sq(2, 0))
        else:
            king_from = sq(4, 7)
            kingside_flag, kingside_empty, kingside_path, kingside_to = (
                CASTLE_BK, (sq(5, 7), sq(6, 7)), (sq(4, 7), sq(5, 7), sq(6, 7)), sq(6, 7))
            queenside_flag, queenside_empty, queenside_path, queenside_to = (
                CASTLE_BQ, (sq(1, 7), sq(2, 7), sq(3, 7)), (sq(4, 7), sq(3, 7), sq(2, 7)), sq(2, 7))

        if self.castling_rights & kingside_flag:
            if not any(self.occupied & bit(s) for s in kingside_empty):
                if not any(self.is_square_attacked(s, enemy) for s in kingside_path):
                    moves.append(Move(king_from, kingside_to, KING, color, is_castle=True))

        if self.castling_rights & queenside_flag:
            if not any(self.occupied & bit(s) for s in queenside_empty):
                if not any(self.is_square_attacked(s, enemy) for s in queenside_path):
                    moves.append(Move(king_from, queenside_to, KING, color, is_castle=True))

        return moves

    def generate_legal_moves(self, color=None):
        if color is None:
            color = self.side_to_move

        legal_moves = []
        for move in self.generate_pseudo_legal_moves(color):
            self.make_move(move)
            if not self.is_in_check(color):
                legal_moves.append(move)
            self.unmake_move()
        return legal_moves

    def make_move(self, move):
        color = move.color
        enemy = BLACK if color == WHITE else WHITE
        from_bb = bit(move.from_sq)
        to_bb = bit(move.to_sq)

        undo = {
            "move": move,
            "castling_rights": self.castling_rights,
            "en_passant_square": self.en_passant_square,
            "halfmove_clock": self.halfmove_clock,
        }

        self.piece_bb[color][move.piece] &= ~from_bb

        if move.captured_piece is not None:
            self.piece_bb[move.captured_color][move.captured_piece] &= ~bit(move.captured_sq)

        final_piece = move.promotion if move.promotion is not None else move.piece
        self.piece_bb[color][final_piece] |= to_bb

        if move.is_castle:
            if move.to_sq > move.from_sq:
                rook_from, rook_to = move.from_sq + 3, move.from_sq + 1
            else:
                rook_from, rook_to = move.from_sq - 4, move.from_sq - 1
            self.piece_bb[color][ROOK] &= ~bit(rook_from)
            self.piece_bb[color][ROOK] |= bit(rook_to)
            undo["rook_from"] = rook_from
            undo["rook_to"] = rook_to

        if move.piece == KING:
            self.castling_rights &= ~(CASTLE_WK | CASTLE_WQ) if color == WHITE else ~(CASTLE_BK | CASTLE_BQ)
        if move.from_sq == sq(0, 0) or move.to_sq == sq(0, 0):
            self.castling_rights &= ~CASTLE_WQ
        if move.from_sq == sq(7, 0) or move.to_sq == sq(7, 0):
            self.castling_rights &= ~CASTLE_WK
        if move.from_sq == sq(0, 7) or move.to_sq == sq(0, 7):
            self.castling_rights &= ~CASTLE_BQ
        if move.from_sq == sq(7, 7) or move.to_sq == sq(7, 7):
            self.castling_rights &= ~CASTLE_BK

        self.en_passant_square = (move.from_sq + move.to_sq) // 2 if move.is_double_push else None

        if move.piece == PAWN or move.captured_piece is not None:
            self.halfmove_clock = 0
        else:
            self.halfmove_clock += 1
        if color == BLACK:
            self.fullmove_number += 1

        self.side_to_move = enemy
        self._update_occupancy()
        self.history.append(undo)
        return undo

    def unmake_move(self):
        undo = self.history.pop()
        move = undo["move"]
        color = move.color
        from_bb = bit(move.from_sq)
        to_bb = bit(move.to_sq)

        final_piece = move.promotion if move.promotion is not None else move.piece
        self.piece_bb[color][final_piece] &= ~to_bb
        self.piece_bb[color][move.piece] |= from_bb

        if move.captured_piece is not None:
            self.piece_bb[move.captured_color][move.captured_piece] |= bit(move.captured_sq)

        if move.is_castle:
            self.piece_bb[color][ROOK] &= ~bit(undo["rook_to"])
            self.piece_bb[color][ROOK] |= bit(undo["rook_from"])

        self.castling_rights = undo["castling_rights"]
        self.en_passant_square = undo["en_passant_square"]
        self.halfmove_clock = undo["halfmove_clock"]
        if color == BLACK:
            self.fullmove_number -= 1

        self.side_to_move = color
        self._update_occupancy()

    PIECE_LETTERS = {PAWN: "P", KNIGHT: "N", BISHOP: "B", ROOK: "R", QUEEN: "Q", KING: "K"}

    def __repr__(self):
        rows = []
        for rank in range(7, -1, -1):
            row = []
            for file_idx in range(8):
                found = self.piece_at(sq(file_idx, rank))
                if found is None:
                    row.append(".")
                else:
                    color, p_type = found
                    letter = self.PIECE_LETTERS[p_type]
                    row.append(letter if color == WHITE else letter.lower())
            rows.append(" ".join(row))
        return "\n".join(rows)
