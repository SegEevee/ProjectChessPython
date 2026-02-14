from PIL import Image
import os
from chess_pieces import chess_pieces

def main():

    # --- CONFIG ---
    INPUT_PATH = "chess_pieces.png"  # change to your image path
    OUTPUT_FOLDER = "sliced_pieces"
    COLUMNS = 6
    ROWS = 2

    # --- LOAD IMAGE ---
    img = Image.open(INPUT_PATH)
    width, height = img.size

    piece_width = width // COLUMNS
    piece_height = height // ROWS

    # --- CREATE OUTPUT FOLDER ---
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    count = 0

    colors = ["WHITE", "BLACK"]
    types = ["KING", "QUEEN", "BISHOP", "KNIGHT","ROOK", "PAWN"]

    for row in range(ROWS):
        for col in range(COLUMNS):
            left = col * piece_width
            top = row * piece_height
            right = left + piece_width
            bottom = top + piece_height
            color_str = colors[row]
            type_str = types[col]
            piece = img.crop((left, top, right, bottom))
            piece.save(f"{OUTPUT_FOLDER}/{color_str}_{type_str}.png")
            count += 1

    print("Done slicing!")
