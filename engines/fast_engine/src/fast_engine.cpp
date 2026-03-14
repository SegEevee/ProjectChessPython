#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include <array>
#include <cstdint>
#include <vector>
#include <unordered_map>
#include <algorithm>
#include <limits>
#include <cmath>

namespace py = pybind11;

// ============================
// Constants (match Python)
// ============================
static constexpr int INF = 100000;
static constexpr int MATE_SCORE = 99999;

static constexpr int EXACT = 0;
static constexpr int LOWER = 1;
static constexpr int UPPER = 2;

// ============================
// Piece encoding for Python<->C++
// ============================
enum Piece : int8_t {
    EMPTY = 0,
    WPAWN = 1, WKNIGHT=2, WBISHOP=3, WROOK=4, WQUEEN=5, WKING=6,
    BPAWN = -1, BKNIGHT=-2, BBISHOP=-3, BROOK=-4, BQUEEN=-5, BKING=-6
};

enum Color : uint8_t { WHITE=0, BLACK=1 };

static inline Color piece_color(int8_t p){
    return (p > 0) ? WHITE : BLACK;
}
static inline int abs_piece(int8_t p){
    return (p >= 0) ? p : -p;
}

// ============================
// PSTs
// ============================
static std::array<int,64> KNIGHT_PST;
static std::array<int,64> PAWN_PST_WHITE;

// Piece values (same)
static int PIECE_VALUE[7] = {0,100,320,330,500,900,20000};

static inline int pst_bonus(Color c, int absP, int idx){
    if (absP == 2) {
        return KNIGHT_PST[idx];
    }
    if (absP == 1) {
        if (c == WHITE) return PAWN_PST_WHITE[idx];
        int r = idx / 8;
        int col = idx % 8;
        int midx = (7 - r) * 8 + col;
        return PAWN_PST_WHITE[midx];
    }
    return 0;
}

// ============================
// Zobrist
// ============================
static uint64_t Z_PSQ[2][7][64];
static uint64_t Z_SIDE;
static uint64_t Z_CASTLE[16];
static uint64_t Z_EPFILE[9];

static inline uint64_t splitmix64(uint64_t &x){
    uint64_t z = (x += 0x9e3779b97f4a7c15ULL);
    z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
    z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
    return z ^ (z >> 31);
}

static void initialize_tables(uint64_t seed=1337ULL){
    int knight_2d[8][8] = {
        {-50,-40,-30,-30,-30,-30,-40,-50},
        {-40,-20,  0,  5,  5,  0,-20,-40},
        {-30,  5, 10, 15, 15, 10,  5,-30},
        {-30,  0, 15, 20, 20, 15,  0,-30},
        {-30,  5, 15, 20, 20, 15,  5,-30},
        {-30,  0, 10, 15, 15, 10,  0,-30},
        {-40,-20,  0,  0,  0,  0,-20,-40},
        {-50,-40,-30,-30,-30,-30,-40,-50}
    };
    int pawn_2d[8][8] = {
        {0,0,0,0,0,0,0,0},
        {50,50,50,50,50,50,50,50},
        {10,10,20,30,30,20,10,10},
        {5,5,10,27,27,10,5,5},
        {0,0,0,25,25,0,0,0},
        {5,-5,-10,0,0,-10,-5,5},
        {5,10,10,-25,-25,10,10,5},
        {0,0,0,0,0,0,0,0}
    };

    for(int r=0;r<8;r++){
        for(int c=0;c<8;c++){
            int idx = r*8+c;
            KNIGHT_PST[idx] = knight_2d[r][c];
            PAWN_PST_WHITE[idx] = pawn_2d[r][c];
        }
    }

    uint64_t x = seed;
    for(int c=0;c<2;c++){
        for(int p=1;p<=6;p++){
            for(int sq=0;sq<64;sq++){
                Z_PSQ[c][p][sq] = splitmix64(x);
            }
        }
    }
    Z_SIDE = splitmix64(x);
    for(int i=0;i<16;i++) Z_CASTLE[i] = splitmix64(x);
    for(int i=0;i<9;i++)  Z_EPFILE[i] = splitmix64(x);
}

// ============================
// Move representation
// ============================
enum MoveFlags : uint8_t {
    MF_NONE      = 0,
    MF_CAPTURE   = 1<<0,
    MF_EP        = 1<<1,
    MF_CASTLE    = 1<<2,
    MF_PROMO     = 1<<3
};

struct Move {
    uint8_t from;
    uint8_t to;
    uint8_t promo;
    uint8_t flags;
    int score;
};

static inline bool same_move_key(const Move& m, uint8_t f, uint8_t t, uint8_t promoFlag){
    if(m.from != f || m.to != t) return false;
    if(promoFlag==0) return ( (m.flags & MF_PROMO) == 0 );
    return (m.flags & MF_PROMO) != 0;
}

struct Undo {
    int8_t captured;
    uint8_t prev_castle;
    uint8_t prev_ep;
    int prev_eval;
    uint64_t prev_hash;
    int8_t moved_piece_before;
    uint8_t from;
    uint8_t to;
    uint8_t ep_victim_sq;
    bool was_ep;
    bool was_castle;
    uint8_t rook_from;
    uint8_t rook_to;
    int8_t rook_piece;
};

// ============================
// NEW FIX: MOP-UP EVALUATION
// This teaches the King how to corner the enemy in the endgame
// ============================
static int mop_up_eval(int winning_king_sq, int losing_king_sq) {
    int bonus = 0;
    int loser_r = losing_king_sq / 8;
    int loser_c = losing_king_sq % 8;

    // 1. Push losing king to the edges/corners
    int center_dist_r = std::max(3 - loser_r, loser_r - 4);
    int center_dist_c = std::max(3 - loser_c, loser_c - 4);
    bonus += (center_dist_r + center_dist_c) * 10;

    // 2. Bring winning king closer to assist the checkmate
    int winner_r = winning_king_sq / 8;
    int winner_c = winning_king_sq % 8;
    int dist = std::max(std::abs(winner_r - loser_r), std::abs(winner_c - loser_c));
    bonus += (14 - dist) * 4;

    return bonus;
}

struct Position {
    std::array<int8_t,64> b{};
    Color stm = WHITE;
    uint8_t castle = 0;
    uint8_t ep = 255;
    int eval = 0;
    int wking = -1;
    int bking = -1;
    uint64_t hash = 0;

    void sync(){
        eval = 0;
        hash = 0;
        wking = bking = -1;

        for(int sq=0;sq<64;sq++){
            int8_t p = b[sq];
            if(p == 0) continue;

            Color c = piece_color(p);
            int ap = abs_piece(p);
            int v = PIECE_VALUE[ap];
            int pst = pst_bonus(c, ap, sq);

            if(c == WHITE){
                eval += (v + pst);
                if(ap==6) wking = sq;
            } else {
                eval -= (v + pst);
                if(ap==6) bking = sq;
            }

            hash ^= Z_PSQ[c][ap][sq];
        }

        if(stm == BLACK) hash ^= Z_SIDE;
        hash ^= Z_CASTLE[castle];

        if(ep == 255) hash ^= Z_EPFILE[8];
        else hash ^= Z_EPFILE[ep % 8];
    }

    int evaluate() const {
        if(wking < 0) return -MATE_SCORE;
        if(bking < 0) return  MATE_SCORE;

        int score = eval;

        // Use the mop-up rule ONLY if we are crushing them (up by 1000 points)
        if (score > 1000) {
            score += mop_up_eval(wking, bking);
        } else if (score < -1000) {
            score -= mop_up_eval(bking, wking);
        }

        return score;
    }
};

static inline bool on_board(int r,int c){ return r>=0 && r<8 && c>=0 && c<8; }

static bool square_attacked(const Position& pos, int sq, Color by){
    int r = sq/8, c = sq%8;

    if(by == WHITE){
        int rr = r+1;
        if(rr<8){
            if(c-1>=0 && pos.b[rr*8+(c-1)] == WPAWN) return true;
            if(c+1<8 && pos.b[rr*8+(c+1)] == WPAWN) return true;
        }
    } else {
        int rr = r-1;
        if(rr>=0){
            if(c-1>=0 && pos.b[rr*8+(c-1)] == BPAWN) return true;
            if(c+1<8 && pos.b[rr*8+(c+1)] == BPAWN) return true;
        }
    }

    static const int kdr[8]={2,1,-1,-2,-2,-1,1,2};
    static const int kdc[8]={1,2,2,1,-1,-2,-2,-1};
    for(int i=0;i<8;i++){
        int nr=r+kdr[i], nc=c+kdc[i];
        if(!on_board(nr,nc)) continue;
        int8_t p = pos.b[nr*8+nc];
        if(p==0) continue;
        if(by==WHITE && p==WKNIGHT) return true;
        if(by==BLACK && p==BKNIGHT) return true;
    }

    for(int dr=-1; dr<=1; dr++){
        for(int dc=-1; dc<=1; dc++){
            if(dr==0 && dc==0) continue;
            int nr=r+dr, nc=c+dc;
            if(!on_board(nr,nc)) continue;
            int8_t p = pos.b[nr*8+nc];
            if(by==WHITE && p==WKING) return true;
            if(by==BLACK && p==BKING) return true;
        }
    }

    static const int rdr[4]={0,1,0,-1};
    static const int rdc[4]={1,0,-1,0};
    for(int d=0; d<4; d++){
        int nr=r+rdr[d], nc=c+rdc[d];
        while(on_board(nr,nc)){
            int8_t p = pos.b[nr*8+nc];
            if(p!=0){
                if(by==WHITE && (p==WROOK || p==WQUEEN)) return true;
                if(by==BLACK && (p==BROOK || p==BQUEEN)) return true;
                break;
            }
            nr += rdr[d]; nc += rdc[d];
        }
    }

    static const int bdr[4]={1,1,-1,-1};
    static const int bdc[4]={1,-1,1,-1};
    for(int d=0; d<4; d++){
        int nr=r+bdr[d], nc=c+bdc[d];
        while(on_board(nr,nc)){
            int8_t p = pos.b[nr*8+nc];
            if(p!=0){
                if(by==WHITE && (p==WBISHOP || p==WQUEEN)) return true;
                if(by==BLACK && (p==BBISHOP || p==BQUEEN)) return true;
                break;
            }
            nr += bdr[d]; nc += bdc[d];
        }
    }

    return false;
}

static inline Color other(Color c){ return (c==WHITE)?BLACK:WHITE; }

static void gen_pseudo_moves(const Position& pos, Color side, bool only_captures, std::vector<Move>& out){
    out.clear();
    Color enemy = other(side);

    for(int from=0; from<64; from++){
        int8_t p = pos.b[from];
        if(p==0) continue;
        if(piece_color(p) != side) continue;

        int ap = abs_piece(p);
        int r = from/8, c = from%8;

        if(ap==1){
            int dir = (side==WHITE) ? -1 : 1;
            int prom_row = (side==WHITE) ? 0 : 7;
            int start_row = (side==WHITE) ? 6 : 1;

            if(!only_captures){
                int nr = r + dir;
                if(nr>=0 && nr<8){
                    int to = nr*8 + c;
                    if(pos.b[to]==0){
                        bool prom = (nr==prom_row);
                        Move m;
                        m.from = (uint8_t)from;
                        m.to   = (uint8_t)to;
                        m.flags = prom ? MF_PROMO : MF_NONE;
                        m.promo = prom ? 5 : 0;
                        m.score = prom ? 8000 : 0;
                        out.push_back(m);

                        if(r==start_row){
                            int to2 = (r + 2*dir)*8 + c;
                            if(pos.b[to2]==0){
                                Move d;
                                d.from=(uint8_t)from; d.to=(uint8_t)to2;
                                d.flags=MF_NONE; d.promo=0; d.score=0;
                                out.push_back(d);
                            }
                        }
                    }
                }
            }

            for(int dc : {-1, +1}){
                int nc = c + dc;
                int nr = r + dir;
                if(nr<0 || nr>=8 || nc<0 || nc>=8) continue;
                int to = nr*8 + nc;

                int8_t tp = pos.b[to];
                if(tp!=0 && piece_color(tp)==enemy){
                    bool prom = (nr==prom_row);
                    int victimVal = PIECE_VALUE[abs_piece(tp)];
                    int attackerVal = PIECE_VALUE[1];
                    int score = victimVal*10 - attackerVal + (prom ? 8000 : 0);

                    Move m;
                    m.from=(uint8_t)from; m.to=(uint8_t)to;
                    m.flags = (uint8_t)(MF_CAPTURE | (prom?MF_PROMO:0));
                    m.promo = prom ? 5 : 0;
                    m.score = score;
                    out.push_back(m);
                }

                if(pos.ep != 255 && to == pos.ep){
                    int victim_r = r;
                    int victim_sq = victim_r*8 + nc;
                    int8_t vp = pos.b[victim_sq];
                    if(side==WHITE && vp==BPAWN){
                        Move m;
                        m.from=(uint8_t)from; m.to=(uint8_t)to;
                        m.flags = (uint8_t)(MF_CAPTURE | MF_EP);
                        m.promo=0;
                        m.score = PIECE_VALUE[1]*10 - PIECE_VALUE[1];
                        out.push_back(m);
                    }
                    if(side==BLACK && vp==WPAWN){
                        Move m;
                        m.from=(uint8_t)from; m.to=(uint8_t)to;
                        m.flags = (uint8_t)(MF_CAPTURE | MF_EP);
                        m.promo=0;
                        m.score = PIECE_VALUE[1]*10 - PIECE_VALUE[1];
                        out.push_back(m);
                    }
                }
            }
        }

        else if(ap==2){
            static const int kdr[8]={2,1,-1,-2,-2,-1,1,2};
            static const int kdc[8]={1,2,2,1,-1,-2,-2,-1};
            for(int i=0;i<8;i++){
                int nr=r+kdr[i], nc=c+kdc[i];
                if(!on_board(nr,nc)) continue;
                int to = nr*8+nc;
                int8_t tp = pos.b[to];
                if(tp==0){
                    if(!only_captures){
                        Move m{(uint8_t)from,(uint8_t)to,0,MF_NONE,0};
                        out.push_back(m);
                    }
                } else if(piece_color(tp)==enemy){
                    int score = PIECE_VALUE[abs_piece(tp)]*10 - PIECE_VALUE[2];
                    Move m{(uint8_t)from,(uint8_t)to,0,(uint8_t)MF_CAPTURE,score};
                    out.push_back(m);
                }
            }
        }

        else if(ap==3 || ap==4 || ap==5){
            std::vector<std::pair<int,int>> dirs;
            if(ap==4 || ap==5){
                dirs.push_back({0,1}); dirs.push_back({1,0}); dirs.push_back({0,-1}); dirs.push_back({-1,0});
            }
            if(ap==3 || ap==5){
                dirs.push_back({1,1}); dirs.push_back({1,-1}); dirs.push_back({-1,1}); dirs.push_back({-1,-1});
            }
            for(auto [dr,dc]:dirs){
                int nr=r+dr, nc=c+dc;
                while(on_board(nr,nc)){
                    int to = nr*8+nc;
                    int8_t tp = pos.b[to];
                    if(tp==0){
                        if(!only_captures){
                            Move m{(uint8_t)from,(uint8_t)to,0,MF_NONE,0};
                            out.push_back(m);
                        }
                    } else {
                        if(piece_color(tp)==enemy){
                            int attackerVal = PIECE_VALUE[ap];
                            int score = PIECE_VALUE[abs_piece(tp)]*10 - attackerVal;
                            Move m{(uint8_t)from,(uint8_t)to,0,(uint8_t)MF_CAPTURE,score};
                            out.push_back(m);
                        }
                        break;
                    }
                    nr+=dr; nc+=dc;
                }
            }
        }

        else if(ap==6){
            for(int dr=-1; dr<=1; dr++){
                for(int dc=-1; dc<=1; dc++){
                    if(dr==0 && dc==0) continue;
                    int nr=r+dr, nc=c+dc;
                    if(!on_board(nr,nc)) continue;
                    int to = nr*8+nc;
                    int8_t tp = pos.b[to];
                    if(tp==0){
                        if(!only_captures){
                            Move m{(uint8_t)from,(uint8_t)to,0,MF_NONE,0};
                            out.push_back(m);
                        }
                    } else if(piece_color(tp)==enemy){
                        int score = PIECE_VALUE[abs_piece(tp)]*10 - PIECE_VALUE[6];
                        Move m{(uint8_t)from,(uint8_t)to,0,(uint8_t)MF_CAPTURE,score};
                        out.push_back(m);
                    }
                }
            }

            if(!only_captures){
                if(side==WHITE){
                    int king_sq = from;
                    if((pos.castle & 1) != 0){
                        if(pos.b[61]==0 && pos.b[62]==0){
                            if(!square_attacked(pos, king_sq, BLACK) &&
                               !square_attacked(pos, 61, BLACK) &&
                               !square_attacked(pos, 62, BLACK)){
                                if(pos.b[63]==WROOK){
                                    Move m;
                                    m.from=(uint8_t)king_sq; m.to=62;
                                    m.flags=MF_CASTLE; m.promo=0; m.score=0;
                                    out.push_back(m);
                                }
                            }
                        }
                    }
                    if((pos.castle & 2) != 0){
                        if(pos.b[59]==0 && pos.b[58]==0 && pos.b[57]==0){
                            if(!square_attacked(pos, king_sq, BLACK) &&
                               !square_attacked(pos, 59, BLACK) &&
                               !square_attacked(pos, 58, BLACK)){
                                if(pos.b[56]==WROOK){
                                    Move m;
                                    m.from=(uint8_t)king_sq; m.to=58;
                                    m.flags=MF_CASTLE; m.promo=0; m.score=0;
                                    out.push_back(m);
                                }
                            }
                        }
                    }
                } else {
                    int king_sq = from;
                    if((pos.castle & 4) != 0){
                        if(pos.b[5]==0 && pos.b[6]==0){
                            if(!square_attacked(pos, king_sq, WHITE) &&
                               !square_attacked(pos, 5, WHITE) &&
                               !square_attacked(pos, 6, WHITE)){
                                if(pos.b[7]==BROOK){
                                    Move m;
                                    m.from=(uint8_t)king_sq; m.to=6;
                                    m.flags=MF_CASTLE; m.promo=0; m.score=0;
                                    out.push_back(m);
                                }
                            }
                        }
                    }
                    if((pos.castle & 8) != 0){
                        if(pos.b[3]==0 && pos.b[2]==0 && pos.b[1]==0){
                            if(!square_attacked(pos, king_sq, WHITE) &&
                               !square_attacked(pos, 3, WHITE) &&
                               !square_attacked(pos, 2, WHITE)){
                                if(pos.b[0]==BROOK){
                                    Move m;
                                    m.from=(uint8_t)king_sq; m.to=2;
                                    m.flags=MF_CASTLE; m.promo=0; m.score=0;
                                    out.push_back(m);
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    std::sort(out.begin(), out.end(), [](const Move& a, const Move& b){
        return a.score > b.score;
    });
}

static Undo do_move(Position& pos, const Move& m){
    Undo u{};
    u.prev_castle = pos.castle;
    u.prev_ep = pos.ep;
    u.prev_eval = pos.eval;
    u.prev_hash = pos.hash;
    u.from = m.from; u.to = m.to;
    u.was_ep = false;
    u.was_castle = false;
    u.ep_victim_sq = 255;

    int8_t moving = pos.b[m.from];
    u.moved_piece_before = moving;

    int8_t captured = 0;

    if(pos.ep == 255) pos.hash ^= Z_EPFILE[8];
    else pos.hash ^= Z_EPFILE[pos.ep % 8];

    pos.ep = 255;

    if(m.flags & MF_EP){
        int from_r = m.from / 8;
        int to_c   = m.to % 8;
        int victim_sq = from_r*8 + to_c;
        u.was_ep = true;
        u.ep_victim_sq = (uint8_t)victim_sq;
        captured = pos.b[victim_sq];
        pos.b[victim_sq] = 0;
    } else {
        captured = pos.b[m.to];
    }
    u.captured = captured;

    {
        Color c = piece_color(moving);
        int ap = abs_piece(moving);
        pos.hash ^= Z_PSQ[c][ap][m.from];

        int v = PIECE_VALUE[ap] + pst_bonus(c, ap, m.from);
        if(c==WHITE) pos.eval -= v;
        else pos.eval += v;
    }

    if(captured != 0){
        Color cc = piece_color(captured);
        int cap = abs_piece(captured);
        int cap_sq = (m.flags & MF_EP) ? (int)u.ep_victim_sq : (int)m.to;

        pos.hash ^= Z_PSQ[cc][cap][cap_sq];

        int v = PIECE_VALUE[cap] + pst_bonus(cc, cap, cap_sq);
        if(cc==WHITE) pos.eval -= v;
        else pos.eval += v;
    }

    pos.b[m.from] = 0;
    int8_t placed = moving;

    if(m.flags & MF_PROMO){
        Color c = piece_color(moving);
        placed = (c==WHITE) ? (int8_t)WQUEEN : (int8_t)BQUEEN;
    }

    if(m.flags & MF_CASTLE){
        u.was_castle = true;
        if(placed == WKING){
            if(m.to == 62){
                u.rook_from=63; u.rook_to=61;
            } else {
                u.rook_from=56; u.rook_to=59;
            }
            u.rook_piece = pos.b[u.rook_from];
            pos.b[u.rook_from]=0;
            pos.b[u.rook_to]=u.rook_piece;
        }
        if(placed == BKING){
            if(m.to == 6){
                u.rook_from=7; u.rook_to=5;
            } else {
                u.rook_from=0; u.rook_to=3;
            }
            u.rook_piece = pos.b[u.rook_from];
            pos.b[u.rook_from]=0;
            pos.b[u.rook_to]=u.rook_piece;
        }
    }

    pos.b[m.to] = placed;

    if(abs_piece(placed)==6){
        if(piece_color(placed)==WHITE) pos.wking = m.to;
        else pos.bking = m.to;
    }

    {
        Color c = piece_color(placed);
        int ap = abs_piece(placed);
        pos.hash ^= Z_PSQ[c][ap][m.to];

        int v = PIECE_VALUE[ap] + pst_bonus(c, ap, m.to);
        if(c==WHITE) pos.eval += v;
        else pos.eval -= v;
    }

    if(u.was_castle){
        Color rc = piece_color(u.rook_piece);
        int rap = abs_piece(u.rook_piece);

        pos.hash ^= Z_PSQ[rc][rap][u.rook_from];
        pos.hash ^= Z_PSQ[rc][rap][u.rook_to];

        int v_from = PIECE_VALUE[rap] + pst_bonus(rc, rap, u.rook_from);
        int v_to   = PIECE_VALUE[rap] + pst_bonus(rc, rap, u.rook_to);
        if(rc==WHITE){
            pos.eval -= v_from;
            pos.eval += v_to;
        } else {
            pos.eval += v_from;
            pos.eval -= v_to;
        }
    }

    pos.hash ^= Z_CASTLE[pos.castle];

    if(u.moved_piece_before == WKING) pos.castle &= ~(1|2);
    if(u.moved_piece_before == BKING) pos.castle &= ~(4|8);

    if(u.moved_piece_before == WROOK){
        if(m.from==63) pos.castle &= ~1;
        if(m.from==56) pos.castle &= ~2;
    }
    if(u.moved_piece_before == BROOK){
        if(m.from==7) pos.castle &= ~4;
        if(m.from==0) pos.castle &= ~8;
    }

    if(u.captured == WROOK){
        if((m.flags & MF_EP)==0){
            if(m.to==63) pos.castle &= ~1;
            if(m.to==56) pos.castle &= ~2;
        }
    }
    if(u.captured == BROOK){
        if((m.flags & MF_EP)==0){
            if(m.to==7) pos.castle &= ~4;
            if(m.to==0) pos.castle &= ~8;
        }
    }

    pos.hash ^= Z_CASTLE[pos.castle];

    int ap_moved_before = abs_piece(u.moved_piece_before);
    if(ap_moved_before==1){
        int fr = m.from/8, tr = m.to/8;
        if(std::abs(tr - fr) == 2){
            int midr = (fr + tr)/2;
            pos.ep = (uint8_t)(midr*8 + (m.from%8));
        }
    }

    if(pos.ep == 255) pos.hash ^= Z_EPFILE[8];
    else pos.hash ^= Z_EPFILE[pos.ep % 8];

    pos.stm = other(pos.stm);
    pos.hash ^= Z_SIDE;

    return u;
}

static void undo_move(Position& pos, const Move& m, const Undo& u){
    pos.b = pos.b;

    pos.stm = other(pos.stm);

    pos.castle = u.prev_castle;
    pos.ep = u.prev_ep;
    pos.eval = u.prev_eval;
    pos.hash = u.prev_hash;

    pos.b[u.from] = u.moved_piece_before;

    if(u.was_ep){
        pos.b[u.to] = 0;
        pos.b[u.ep_victim_sq] = u.captured;
    } else {
        pos.b[u.to] = u.captured;
    }

    if(u.was_castle){
        pos.b[u.rook_from] = u.rook_piece;
        pos.b[u.rook_to] = 0;
    }

    pos.wking = -1; pos.bking = -1;
    for(int sq=0;sq<64;sq++){
        if(pos.b[sq]==WKING) pos.wking=sq;
        else if(pos.b[sq]==BKING) pos.bking=sq;
    }
}

static void gen_legal_moves(Position& pos, Color side, bool only_captures, std::vector<Move>& out){
    std::vector<Move> pseudo;
    gen_pseudo_moves(pos, side, only_captures, pseudo);

    out.clear();
    out.reserve(pseudo.size());

    for(const auto& m : pseudo){
        Undo u = do_move(pos, m);

        Color mover = other(pos.stm);
        int kingSq = (mover==WHITE) ? pos.wking : pos.bking;

        bool illegal = square_attacked(pos, kingSq, pos.stm);
        undo_move(pos, m, u);

        if(!illegal){
            out.push_back(m);
        }
    }
}

struct TTEntry {
    int depth;
    int flag;
    int score;
    uint8_t best_from;
    uint8_t best_to;
    uint8_t best_is_prom;
};

static std::unordered_map<uint64_t, TTEntry> TT;

static inline bool tt_probe(uint64_t h, int depth, int alpha, int beta, int &outScore){
    auto it = TT.find(h);
    if(it == TT.end()) return false;
    const TTEntry& e = it->second;
    if(e.depth < depth) return false;

    if(e.flag == EXACT){
        outScore = e.score;
        return true;
    }
    if(e.flag == LOWER && e.score >= beta){
        outScore = e.score;
        return true;
    }
    if(e.flag == UPPER && e.score <= alpha){
        outScore = e.score;
        return true;
    }
    return false;
}

static inline void tt_store(uint64_t h, int depth, int flag, int score, const Move* best){
    auto it = TT.find(h);
    if(it == TT.end() || depth >= it->second.depth){
        TTEntry e;
        e.depth = depth;
        e.flag = flag;
        e.score = score;
        if(best){
            e.best_from = best->from;
            e.best_to = best->to;
            e.best_is_prom = (best->flags & MF_PROMO) ? 1 : 0;
        } else {
            e.best_from = e.best_to = 0;
            e.best_is_prom = 0;
        }
        TT[h] = e;
    }
}

static int quiescence(Position& pos, int alpha, int beta, Color side){
    int stand_pat = pos.evaluate();

    if(stand_pat >= 90000 && side == BLACK) return stand_pat;
    if(stand_pat <= -90000 && side == WHITE) return stand_pat;

    if(side == WHITE){
        if(stand_pat >= beta) return beta;
        if(stand_pat > alpha) alpha = stand_pat;

        std::vector<Move> moves;
        gen_legal_moves(pos, WHITE, true, moves);

        for(const auto& m : moves){
            Undo u = do_move(pos, m);
            int score = quiescence(pos, alpha, beta, BLACK);
            undo_move(pos, m, u);

            if(score >= beta) return beta;
            if(score > alpha) alpha = score;
        }
        return alpha;
    } else {
        if(stand_pat <= alpha) return alpha;
        if(stand_pat < beta) beta = stand_pat;

        std::vector<Move> moves;
        gen_legal_moves(pos, BLACK, true, moves);

        for(const auto& m : moves){
            Undo u = do_move(pos, m);
            int score = quiescence(pos, alpha, beta, WHITE);
            undo_move(pos, m, u);

            if(score <= alpha) return alpha;
            if(score < beta) beta = score;
        }
        return beta;
    }
}

static int search_pvs(Position& pos, int depth, int alpha, int beta, Color side){
    if(depth == 0){
        return quiescence(pos, alpha, beta, side);
    }

    int eval_score = pos.evaluate();
    if(eval_score >= 90000 || eval_score <= -90000) return eval_score;

    int ttScore;
    if(tt_probe(pos.hash, depth, alpha, beta, ttScore)) return ttScore;

    Color enemy = other(side);
    Move bestMove{};
    bool haveBest = false;
    int alpha_orig = alpha;
    int beta_orig = beta;

    uint8_t tt_from=255, tt_to=255, tt_prom=0;
    auto it = TT.find(pos.hash);
    if(it != TT.end()){
        tt_from = it->second.best_from;
        tt_to   = it->second.best_to;
        tt_prom = it->second.best_is_prom;
    }

    std::vector<Move> moves;
    gen_legal_moves(pos, side, false, moves);

    // ============================
    // NEW FIX: CHECKMATE DETECTOR
    // Stop ignoring the end of the game!
    // ============================
    if(moves.empty()){
        int kingSq = (side==WHITE) ? pos.wking : pos.bking;
        if(square_attacked(pos, kingSq, enemy)){
            // The bot is getting checkmated.
            // We punish it slightly based on depth so it prefers FASTER mates!
            if(side == WHITE) return -MATE_SCORE + (100 - depth);
            else return MATE_SCORE - (100 - depth);
        }
        // If it can't move but isn't attacked, it's stalemate.
        return 0;
    }

    if(tt_from != 255){
        for(size_t j=0;j<moves.size();j++){
            if(same_move_key(moves[j], tt_from, tt_to, tt_prom)){
                std::swap(moves[0], moves[j]);
                break;
            }
        }
    }

    if(side == WHITE){
        int value = -INF;
        bool first = true;

        for(const auto& m : moves){
            Undo u = do_move(pos, m);

            int score;
            if(first){
                score = search_pvs(pos, depth-1, alpha, beta, enemy);
                first = false;
            } else {
                score = search_pvs(pos, depth-1, alpha, alpha+1, enemy);
                if(score > alpha && score < beta){
                    score = search_pvs(pos, depth-1, alpha, beta, enemy);
                }
            }

            undo_move(pos, m, u);

            if(score > value){
                value = score;
                bestMove = m;
                haveBest = true;
            }
            if(score > alpha) alpha = score;
            if(alpha >= beta) break;
        }

        int flag;
        if(value <= alpha_orig) flag = UPPER;
        else if(value >= beta_orig) flag = LOWER;
        else flag = EXACT;

        tt_store(pos.hash, depth, flag, value, haveBest ? &bestMove : nullptr);
        return value;

    } else {
        int value = INF;
        bool first = true;

        for(const auto& m : moves){
            Undo u = do_move(pos, m);

            int score;
            if(first){
                score = search_pvs(pos, depth-1, alpha, beta, enemy);
                first = false;
            } else {
                score = search_pvs(pos, depth-1, beta-1, beta, enemy);
                if(score < beta && score > alpha){
                    score = search_pvs(pos, depth-1, alpha, beta, enemy);
                }
            }

            undo_move(pos, m, u);

            if(score < value){
                value = score;
                bestMove = m;
                haveBest = true;
            }
            if(score < beta) beta = score;
            if(alpha >= beta) break;
        }

        int flag;
        if(value <= alpha_orig) flag = UPPER;
        else if(value >= beta_orig) flag = LOWER;
        else flag = EXACT;

        tt_store(pos.hash, depth, flag, value, haveBest ? &bestMove : nullptr);
        return value;
    }
}

static std::tuple<int,int,int> search_best_move_bytes(
    py::bytes board_bytes,
    int side_to_move,
    int castle_rights,
    int ep_square,
    int depth
){
    std::string data = board_bytes;
    if(data.size() != 64){
        throw std::runtime_error("board_bytes must be exactly 64 bytes (int8 pieces).");
    }

    Position pos;
    for(int i=0;i<64;i++){
        int8_t v = (int8_t)(uint8_t)data[i];
        pos.b[i] = v;
    }
    pos.stm = (side_to_move==0) ? WHITE : BLACK;
    pos.castle = (uint8_t)(castle_rights & 15);
    pos.ep = (ep_square < 0) ? (uint8_t)255 : (uint8_t)ep_square;

    pos.sync();

    Color ai = pos.stm;
    Color enemy = other(ai);

    std::vector<Move> moves;
    gen_legal_moves(pos, ai, false, moves);
    if(moves.empty()){
        return { -1, -1, 0 };
    }

    Move bestMove = moves[0];
    int bestScore = (ai==WHITE) ? -INF : INF;

    for(int current_depth=1; current_depth<=depth; current_depth++){
        int window_alpha, window_beta;
        if(current_depth==1){
            window_alpha = -INF;
            window_beta = INF;
        } else {
            int margin = 50;
            window_alpha = bestScore - margin;
            window_beta = bestScore + margin;
        }

        auto root_search_window = [&](int a, int b){
            int localBestScore = (ai==WHITE) ? -INF : INF;
            Move localBest = moves[0];

            for(const auto& m : moves){
                Undo u = do_move(pos, m);
                int score = search_pvs(pos, current_depth-1, a, b, enemy);
                undo_move(pos, m, u);

                if(ai==WHITE){
                    if(score > localBestScore){
                        localBestScore = score;
                        localBest = m;
                    }
                } else {
                    if(score < localBestScore){
                        localBestScore = score;
                        localBest = m;
                    }
                }
            }
            bestMove = localBest;
            bestScore = localBestScore;
        };

        root_search_window(window_alpha, window_beta);

        if(bestScore <= window_alpha || bestScore >= window_beta){
            root_search_window(-INF, INF);
        }
    }

    int promo = (bestMove.flags & MF_PROMO) ? (int)bestMove.promo : 0;
    return { (int)bestMove.from, (int)bestMove.to, promo };
}

PYBIND11_MODULE(_core, m){
    initialize_tables(1337ULL);

    m.doc() = "Fast C++ chess AI core (movegen+search)";

    m.def(
        "search",
        &search_best_move_bytes,
        py::arg("board_bytes"),
        py::arg("side_to_move"),
        py::arg("castle_rights"),
        py::arg("ep_square"),
        py::arg("depth"),
        "Return (from_idx, to_idx, promo_piece_abs) for best move."
    );

    m.def("reset_tt", [](){
        TT.clear();
    });
}