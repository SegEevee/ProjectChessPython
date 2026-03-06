#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include <array>
#include <cstdint>
#include <vector>
#include <unordered_map>
#include <algorithm>
#include <limits>

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
// Board squares: 64 bytes, int8 values
//   0 empty
//   +1..+6 white pawn..king
//   -1..-6 black pawn..king
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
// PSTs (same as your Python tables)
// White POV indexing: idx = r*8+c where r=0 is top.
// IMPORTANT: Your Python uses r=0 as top row (black home).
// We'll keep same.
// ============================
static std::array<int,64> KNIGHT_PST;
static std::array<int,64> PAWN_PST_WHITE;

// Piece values (same)
static int PIECE_VALUE[7] = {0,100,320,330,500,900,20000}; // index by abs piece 1..6

static inline int pst_bonus(Color c, int absP, int idx){
    if (absP == 2) { // knight
        return KNIGHT_PST[idx];
    }
    if (absP == 1) { // pawn
        if (c == WHITE) return PAWN_PST_WHITE[idx];
        // mirror for black
        int r = idx / 8;
        int col = idx % 8;
        int midx = (7 - r) * 8 + col;
        return PAWN_PST_WHITE[midx];
    }
    return 0;
}

// ============================
// Zobrist
// keys for (color, abs_piece_type 1..6, square)
// plus side-to-move
// plus castling rights (16)
// plus en-passant file (9: none or a..h)
// ============================
static uint64_t Z_PSQ[2][7][64];
static uint64_t Z_SIDE;
static uint64_t Z_CASTLE[16];
static uint64_t Z_EPFILE[9]; // 0..7 for file a..h, 8 = none

// Small deterministic RNG: splitmix64
static inline uint64_t splitmix64(uint64_t &x){
    uint64_t z = (x += 0x9e3779b97f4a7c15ULL);
    z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
    z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
    return z ^ (z >> 31);
}

static void initialize_tables(uint64_t seed=1337ULL){
    // PSTs
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

    // Zobrist
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
// flags bitfield
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
    uint8_t promo;   // abs piece type 0 (none) or 2..5 (N,B,R,Q) typically
    uint8_t flags;
    int score;       // for ordering (like your Python first element)
};

static inline bool same_move_key(const Move& m, uint8_t f, uint8_t t, uint8_t promoFlag){
    // promoFlag here is 0/1 (your python is_promotion)
    // We'll treat promoFlag==1 as "promotion to queen" for now.
    if(m.from != f || m.to != t) return false;
    if(promoFlag==0) return ( (m.flags & MF_PROMO) == 0 );
    return (m.flags & MF_PROMO) != 0;
}

// ============================
// Position / ShadowBoard equivalent
// Includes full rules:
// - side to move
// - castling rights
// - en-passant square
// - make/undo with captured piece + special handling
// - incremental eval + zobrist
// ============================
// Castling rights bits (like common):
// 1 = white king side
// 2 = white queen side
// 4 = black king side
// 8 = black queen side
// total 0..15
// EP square: 0..63 or 255 none
// ============================
struct Undo {
    int8_t captured;
    uint8_t prev_castle;
    uint8_t prev_ep;      // 0..63 or 255
    int prev_eval;
    uint64_t prev_hash;
    int8_t moved_piece_before; // original piece on from (includes color)
    uint8_t from;
    uint8_t to;

    // for EP capture we need victim square
    uint8_t ep_victim_sq;
    bool was_ep;

    // for castling: rook move info
    bool was_castle;
    uint8_t rook_from;
    uint8_t rook_to;
    int8_t rook_piece;
};

struct Position {
    std::array<int8_t,64> b{};
    Color stm = WHITE;
    uint8_t castle = 0;
    uint8_t ep = 255; // none
    int eval = 0;     // white - black
    int wking = -1;
    int bking = -1;
    uint64_t hash = 0;

    // recompute eval+hash+king positions from scratch
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

        // EP hashing usually by file only (standard)
        if(ep == 255) hash ^= Z_EPFILE[8];
        else hash ^= Z_EPFILE[ep % 8];
    }

    int evaluate() const {
        if(wking < 0) return -MATE_SCORE;
        if(bking < 0) return  MATE_SCORE;
        return eval;
    }
};

// ============================
// Attack detection (needed for legality + castling legality)
// ============================
static inline bool on_board(int r,int c){ return r>=0 && r<8 && c>=0 && c<8; }

static bool square_attacked(const Position& pos, int sq, Color by){
    int r = sq/8, c = sq%8;

    // Pawn attacks
    if(by == WHITE){
        // white pawns attack up (towards decreasing r): (r-1,c-1),(r-1,c+1) are attacked squares by a white pawn at (r+1, c±1)
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

    // Knight attacks
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

    // King attacks (adjacent)
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

    // Sliding: rook/queen lines
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

    // Sliding: bishop/queen diagonals
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

// ============================
// Move generation (pseudo-legal) + legality filter
// Score matches your python idea:
// - promotions get +8000
// - captures get MVV-LVA-like: victim*10 - attacker
// ============================
static void gen_pseudo_moves(const Position& pos, Color side, bool only_captures, std::vector<Move>& out){
    out.clear();
    Color enemy = other(side);

    for(int from=0; from<64; from++){
        int8_t p = pos.b[from];
        if(p==0) continue;
        if(piece_color(p) != side) continue;

        int ap = abs_piece(p);
        int r = from/8, c = from%8;

        // Pawn
        if(ap==1){
            int dir = (side==WHITE) ? -1 : 1;
            int prom_row = (side==WHITE) ? 0 : 7;
            int start_row = (side==WHITE) ? 6 : 1;

            // pushes
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
                        m.promo = prom ? 5 : 0; // queen by default
                        m.score = prom ? 8000 : 0;
                        out.push_back(m);

                        // double push
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

            // captures (including EP)
            for(int dc : {-1, +1}){
                int nc = c + dc;
                int nr = r + dir;
                if(nr<0 || nr>=8 || nc<0 || nc>=8) continue;
                int to = nr*8 + nc;

                // normal capture
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

                // en-passant
                if(pos.ep != 255 && to == pos.ep){
                    // EP is only possible if target square equals ep and there is an enemy pawn adjacent
                    // Victim pawn is behind ep square (relative to moving side)
                    int victim_r = r; // pawn was on same row as from
                    int victim_sq = victim_r*8 + nc;
                    int8_t vp = pos.b[victim_sq];
                    if(side==WHITE && vp==BPAWN){
                        Move m;
                        m.from=(uint8_t)from; m.to=(uint8_t)to;
                        m.flags = (uint8_t)(MF_CAPTURE | MF_EP);
                        m.promo=0;
                        // victim pawn value
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

        // Knight
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

        // Bishop/Rook/Queen
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

        // King (including castling)
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

            // Castling (only if not only_captures)
            if(!only_captures){
                // need to check rook squares, empty squares, and check conditions
                // We'll generate castle moves here; legality filter will also ensure not leaving king in check,
                // but castling has extra rules (cannot pass through check), so we check here.

                if(side==WHITE){
                    int king_sq = from; // should be e1 = 60 in your board coords? careful:
                    // In your indexing r=0 is top, r=7 is bottom.
                    // White king starts at e1 => row 7, col 4 => 7*8+4 = 60.
                    // Good.

                    // King side: e1->g1 (60->62), rook h1->f1 (63->61)
                    if((pos.castle & 1) != 0){
                        if(pos.b[61]==0 && pos.b[62]==0){
                            // king not in check, and squares f1,g1 not attacked
                            if(!square_attacked(pos, king_sq, BLACK) &&
                               !square_attacked(pos, 61, BLACK) &&
                               !square_attacked(pos, 62, BLACK)){
                                // rook exists
                                if(pos.b[63]==WROOK){
                                    Move m;
                                    m.from=(uint8_t)king_sq; m.to=62;
                                    m.flags=MF_CASTLE; m.promo=0; m.score=0;
                                    out.push_back(m);
                                }
                            }
                        }
                    }
                    // Queen side: e1->c1 (60->58), rook a1->d1 (56->59)
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
                    // Black king starts at e8 => row 0 col 4 => 4
                    int king_sq = from;

                    // King side: e8->g8 (4->6), rook h8->f8 (7->5)
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
                    // Queen side: e8->c8 (4->2), rook a8->d8 (0->3)
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

    // sort like your python: highest score first
    std::sort(out.begin(), out.end(), [](const Move& a, const Move& b){
        return a.score > b.score;
    });
}

// ============================
// Make/Undo (full rules)
// Also maintains incremental eval+hash like your Python.
// ============================
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

    // remove EP hash (file)
    if(pos.ep == 255) pos.hash ^= Z_EPFILE[8];
    else pos.hash ^= Z_EPFILE[pos.ep % 8];

    pos.ep = 255;
    // add new EP hash later

    // handle captures
    if(m.flags & MF_EP){
        // victim is pawn behind target square
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

    // incremental: remove moving piece from from
    {
        Color c = piece_color(moving);
        int ap = abs_piece(moving);
        pos.hash ^= Z_PSQ[c][ap][m.from];

        int v = PIECE_VALUE[ap] + pst_bonus(c, ap, m.from);
        if(c==WHITE) pos.eval -= v;
        else pos.eval += v;
    }

    // incremental: remove captured piece (if any)
    if(captured != 0){
        Color cc = piece_color(captured);
        int cap = abs_piece(captured);
        int cap_sq = (m.flags & MF_EP) ? (int)u.ep_victim_sq : (int)m.to;

        pos.hash ^= Z_PSQ[cc][cap][cap_sq];

        int v = PIECE_VALUE[cap] + pst_bonus(cc, cap, cap_sq);
        if(cc==WHITE) pos.eval -= v;
        else pos.eval += v;
    }

    // move piece (promotion)
    pos.b[m.from] = 0;
    int8_t placed = moving;

    if(m.flags & MF_PROMO){
        // promote pawn to queen by default (abs piece 5)
        Color c = piece_color(moving);
        placed = (c==WHITE) ? (int8_t)WQUEEN : (int8_t)BQUEEN;
    }

    // castling rook move
    if(m.flags & MF_CASTLE){
        u.was_castle = true;
        // determine rook moves by destination square
        if(placed == WKING){
            if(m.to == 62){ // O-O
                u.rook_from=63; u.rook_to=61;
            } else {        // O-O-O (58)
                u.rook_from=56; u.rook_to=59;
            }
            u.rook_piece = pos.b[u.rook_from];
            pos.b[u.rook_from]=0;
            pos.b[u.rook_to]=u.rook_piece;
        }
        if(placed == BKING){
            if(m.to == 6){ // O-O
                u.rook_from=7; u.rook_to=5;
            } else {       // O-O-O (2)
                u.rook_from=0; u.rook_to=3;
            }
            u.rook_piece = pos.b[u.rook_from];
            pos.b[u.rook_from]=0;
            pos.b[u.rook_to]=u.rook_piece;
        }
    }

    pos.b[m.to] = placed;

    // update king pos
    if(abs_piece(placed)==6){
        if(piece_color(placed)==WHITE) pos.wking = m.to;
        else pos.bking = m.to;
    }

    // incremental: add moved (possibly promoted) piece to to
    {
        Color c = piece_color(placed);
        int ap = abs_piece(placed);
        pos.hash ^= Z_PSQ[c][ap][m.to];

        int v = PIECE_VALUE[ap] + pst_bonus(c, ap, m.to);
        if(c==WHITE) pos.eval += v;
        else pos.eval -= v;
    }

    // rook incremental updates if castling
    if(u.was_castle){
        // rook removed from rook_from and added to rook_to
        Color rc = piece_color(u.rook_piece);
        int rap = abs_piece(u.rook_piece);

        pos.hash ^= Z_PSQ[rc][rap][u.rook_from];
        pos.hash ^= Z_PSQ[rc][rap][u.rook_to];

        // eval rook pst change
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

    // update castling rights (standard: king/rook move or rook captured)
    auto clear_castle = [&](uint8_t mask){
        if((pos.castle & mask) != 0){
            // hash remove old
            pos.hash ^= Z_CASTLE[pos.castle];
            pos.castle = (uint8_t)(pos.castle & ~mask);
            pos.hash ^= Z_CASTLE[pos.castle];
        }
    };

    // remove old castle hash (we will re-add with new via helper)
    // We'll do it by toggling exact old/new:
    pos.hash ^= Z_CASTLE[pos.castle]; // remove current (before modifications)
    // modify castle flags based on move effects
    // (we already stored prev in u.prev_castle)

    // king moves
    if(u.moved_piece_before == WKING) pos.castle &= ~(1|2);
    if(u.moved_piece_before == BKING) pos.castle &= ~(4|8);

    // rook moves
    if(u.moved_piece_before == WROOK){
        if(m.from==63) pos.castle &= ~1;
        if(m.from==56) pos.castle &= ~2;
    }
    if(u.moved_piece_before == BROOK){
        if(m.from==7) pos.castle &= ~4;
        if(m.from==0) pos.castle &= ~8;
    }

    // rook captured
    if(u.captured == WROOK){
        if((m.flags & MF_EP)==0){ // EP can't capture rook
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

    pos.hash ^= Z_CASTLE[pos.castle]; // add new

    // set en-passant square if double pawn push
    int ap_moved_before = abs_piece(u.moved_piece_before);
    if(ap_moved_before==1){
        int fr = m.from/8, tr = m.to/8;
        if(std::abs(tr - fr) == 2){
            // ep square is between
            int midr = (fr + tr)/2;
            pos.ep = (uint8_t)(midr*8 + (m.from%8));
        }
    }

    // add EP hash
    if(pos.ep == 255) pos.hash ^= Z_EPFILE[8];
    else pos.hash ^= Z_EPFILE[pos.ep % 8];

    // flip side to move
    pos.stm = other(pos.stm);
    pos.hash ^= Z_SIDE;

    return u;
}

static void undo_move(Position& pos, const Move& m, const Undo& u){
    // restore everything exactly (fast + safe)
    pos.b = pos.b; // no-op, but keeping structure in mind

    // easiest: restore full state from stored snapshot fields + do board restoration explicitly
    // We'll restore board squares changes:

    // flip side back
    pos.stm = other(pos.stm);

    // restore hash/eval/castle/ep directly (they fully encode incremental changes)
    pos.castle = u.prev_castle;
    pos.ep = u.prev_ep;
    pos.eval = u.prev_eval;
    pos.hash = u.prev_hash;

    // restore moved piece to from
    pos.b[u.from] = u.moved_piece_before;

    // restore destination square piece:
    // if it was a normal move, pos.b[to] becomes captured (or empty)
    // but for EP, destination square becomes empty and victim restored separately
    if(u.was_ep){
        pos.b[u.to] = 0;
        pos.b[u.ep_victim_sq] = u.captured;
    } else {
        pos.b[u.to] = u.captured;
    }

    // undo castling rook movement
    if(u.was_castle){
        pos.b[u.rook_from] = u.rook_piece;
        pos.b[u.rook_to] = 0;
    }

    // restore king squares (cheap recompute from stored board is possible,
    // but we keep it incremental: just find kings)
    pos.wking = -1; pos.bking = -1;
    for(int sq=0;sq<64;sq++){
        if(pos.b[sq]==WKING) pos.wking=sq;
        else if(pos.b[sq]==BKING) pos.bking=sq;
    }
}

// ============================
// Legal move filter:
// make move, check own king not attacked, undo
// ============================
static void gen_legal_moves(Position& pos, Color side, bool only_captures, std::vector<Move>& out){
    std::vector<Move> pseudo;
    gen_pseudo_moves(pos, side, only_captures, pseudo);

    out.clear();
    out.reserve(pseudo.size());

    for(const auto& m : pseudo){
        Undo u = do_move(pos, m);

        // after move, side flipped, so "side" is the one who just moved
        // ensure that mover's king is not attacked by opponent
        Color mover = other(pos.stm);
        int kingSq = (mover==WHITE) ? pos.wking : pos.bking;

        bool illegal = square_attacked(pos, kingSq, pos.stm); // pos.stm is opponent now
        undo_move(pos, m, u);

        if(!illegal){
            out.push_back(m);
        }
    }

    // keep same ordering (already sorted in pseudo), but legality filtering can disturb it
    // We'll keep relative order by not re-sorting.
}

// ============================
// Transposition Table
// ============================
struct TTEntry {
    int depth;
    int flag;
    int score;
    uint8_t best_from;
    uint8_t best_to;
    uint8_t best_is_prom; // 0/1
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

// ============================
// Quiescence (same logic style)
// ============================
static int quiescence(Position& pos, int alpha, int beta, Color side){
    int stand_pat = pos.evaluate();

    // mate-ish checks like your python
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

// ============================
// PVS Search (same logic style)
// ============================
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

    // get TT best move key if exists
    uint8_t tt_from=255, tt_to=255, tt_prom=0;
    auto it = TT.find(pos.hash);
    if(it != TT.end()){
        tt_from = it->second.best_from;
        tt_to   = it->second.best_to;
        tt_prom = it->second.best_is_prom;
    }

    std::vector<Move> moves;
    gen_legal_moves(pos, side, false, moves);

    if(moves.empty()){
        // like your python: return static eval for now
        return eval_score;
    }

    // bring TT move to front if present
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
                // PVS null window
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

// ============================
// Root: iterative deepening + aspiration like your python
// Returns best move as (from,to,promo)
// promo: 0 none, else abs piece type (we return 5 for queen)
// ============================
static std::tuple<int,int,int> search_best_move_bytes(
    py::bytes board_bytes,
    int side_to_move,     // 0 white, 1 black
    int castle_rights,    // 0..15
    int ep_square,        // -1 none, else 0..63
    int depth
){
    // decode bytes -> Position
    std::string data = board_bytes;
    if(data.size() != 64){
        throw std::runtime_error("board_bytes must be exactly 64 bytes (int8 pieces).");
    }

    Position pos;
    for(int i=0;i<64;i++){
        // interpret as signed int8
        int8_t v = (int8_t)(uint8_t)data[i];
        pos.b[i] = v;
    }
    pos.stm = (side_to_move==0) ? WHITE : BLACK;
    pos.castle = (uint8_t)(castle_rights & 15);
    pos.ep = (ep_square < 0) ? (uint8_t)255 : (uint8_t)ep_square;

    pos.sync();

    Color ai = pos.stm;
    Color enemy = other(ai);

    // generate root legal moves
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

// ============================
// Module init
// ============================
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