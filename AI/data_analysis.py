import io
import itertools
import json
import zstandard as zstd
from chess import Board

def main():


  file_path = "lichess_db_eval.jsonl.zst"
  max_records = 1000  # Change this to however many rows you want
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

  data = subset[0]
  add = "KQkq "
  pos = str(data['fen']) + " 0 1"
  print(pos) #  r1bqkbnr/pp1ppppp/2n5/2p5/4P3/5N2/PPPP1PPP/RNBQKB1R b KQkq - 1 3
  b = Board()
  b.actual_load_fen(pos)
  b.print_board()

if __name__ == "__main__":
  main()