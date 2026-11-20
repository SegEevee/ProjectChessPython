import io
import itertools
import json
import zstandard as zstd
from chess import Board

def main():


  file_path = "lichess_db_eval.jsonl.zst"
  max_records = 1000
  subset = []

  with open(file_path, "rb") as fh:
    # max_window_size prevents memory errors on large archives (e.g., Reddit dumps)
    dctx = zstd.ZstdDecompressor(max_window_size=2147483648)
    with dctx.stream_reader(fh) as reader:
      text_stream = io.TextIOWrapper(reader, encoding="utf-8")

      for line in itertools.islice(text_stream, max_records):
        if line.strip():
          subset.append(json.loads(line))

  print(f"Loaded {len(subset)} records")

  def prepare_pos(index):
    data = subset[index]
    return str(data['fen']) + " 0 1"

  def get_best_score_from_index(index):
    pos = prepare_pos(index)

    parts = pos.strip().split()
    if len(parts) != 6: raise ValueError("Invalid FEN")

    piece_data, active, castling, en_passant_str, halfmove, fullmove = parts

    white_starts = active == 'w'

    print(prepare_pos(index))

    data = subset[index]
    evals = data['evals']

    sum_scores = 0
    sum_depths = 0
    for eval in evals:
      depth = eval['depth']
      sum_depths += depth

    for eval in evals:
      scores = eval['pvs']
      if not scores: continue
      best_score = scores[int(white_starts) - 1]['cp']
      depth = eval['depth']

      sum_scores += best_score * depth

    return sum_scores / sum_depths

  def fen_to_ai_data(fen):
    # Turn a FEN string into a flat numeric feature vector for the model,
    # the input (X) that pairs with the score label from
    # get_best_score_from_index (y).
    #
    # Layout (789 floats):
    #   [0   : 768]  12 piece planes of 64 squares each, ordered
    #                white  P,N,B,R,Q,K  then  black  P,N,B,R,Q,K.
    #                1.0 if that piece sits on that square, else 0.0.
    #   [768]        side to move: 1.0 = white, 0.0 = black.
    #   [769 : 773]  castling rights: white K, white Q, black K, black Q.
    #   [773 : 781]  en-passant target file (one-hot a..h), 0 if none.
    #   [781 : 789]  en-passant target rank (one-hot 1..8), 0 if none.
    #
    # Squares use a1 = 0 .. h8 = 63 (file + rank * 8) to match AiBoard, and
    # the plane order P,N,B,R,Q,K matches PAWN..KING = 0..5 in ai_chess_bot.
    #
    # The FEN is parsed directly (like get_best_score_from_index) rather than
    # through Board: a data pipeline only needs the static position, and
    # building a Board would run the full legal-move / game-state machinery.
    parts = fen.strip().split()
    if len(parts) < 4: raise ValueError("Invalid FEN")
    piece_data, active, castling, en_passant_str = parts[:4]

    # Plane index per FEN piece letter (uppercase), 0..5 = white, 6..11 = black.
    PLANE_OF = {"P": 0, "N": 1, "B": 2, "R": 3, "Q": 4, "K": 5}

    planes = [0.0] * 768
    rows = piece_data.split('/')          # rows[0] is rank 8, rows[7] is rank 1
    for row_index, row in enumerate(rows):
      col = 0
      for ch in row:
        if ch.isdigit():
          col += int(ch)
          continue
        plane = PLANE_OF[ch.upper()]
        if ch.islower():                  # lowercase = black piece
          plane += 6
        rank = 7 - row_index              # rank index, 0 = rank 1
        square = col + rank * 8
        planes[plane * 64 + square] = 1.0
        col += 1

    features = planes
    features.append(1.0 if active == 'w' else 0.0)

    features.append(1.0 if "K" in castling else 0.0)  # White kingside
    features.append(1.0 if "Q" in castling else 0.0)  # White queenside
    features.append(1.0 if "k" in castling else 0.0)  # Black kingside
    features.append(1.0 if "q" in castling else 0.0)  # Black queenside

    ep_file = [0.0] * 8
    ep_rank = [0.0] * 8
    if en_passant_str != '-' and len(en_passant_str) == 2:
      ep_file[ord(en_passant_str[0]) - ord('a')] = 1.0
      ep_rank[int(en_passant_str[1]) - 1] = 1.0
    features.extend(ep_file)
    features.extend(ep_rank)

    return features













if __name__ == "__main__":
  main()