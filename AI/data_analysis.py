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

  index = 11

  print(prepare_pos(index))

  data = subset[index]
  evals = data['evals']

  sum_depths = 0
  for eval in evals:
    print(eval)
    scores = eval['pvs']
    best_score = scores[0]['cp']
    depth = eval['depth']
    sum_depths += depth





if __name__ == "__main__":
  main()