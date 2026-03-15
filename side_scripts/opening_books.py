# import sys
# import os
#
# # ELI5: We are inside the 'side_scripts' folder. main.py is one folder up.
# # We have to build a staircase so Python knows how to go up and find it!
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
#
# # Now we can just steal all the heavy lifting tools directly from your main file!
# from chess import Board, STARTING_POSITION, pgn_to_move_list, get_move_from_san, MoveType
#
#
# def forge_book_from_pgn():
#     import sys
#     import os
#
#     # We build the staircase inside the function
#     sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
#
#     # THE FIX: We import the tools HERE. This breaks the circle!
#     from chess import Board, STARTING_POSITION, pgn_to_move_list, get_move_from_san, MoveType
#
#     print("\n" + "=" * 40)
#     print("📚 THE OPENING BOOK FORGE 📚")
#     print("=" * 40)
#
#     print("\nPaste your PGN below. (Press Enter TWICE when you are done pasting):")
#
#     lines = []
#     while True:
#         line = input()
#         if line.strip() == "":
#             break
#         lines.append(line)
#
#     raw_pgn = " ".join(lines)
#
#     if not raw_pgn.strip():
#         print("You didn't type anything! Shutting down.")
#         return
#
#     ghost_board = Board(STARTING_POSITION)
#     san_moves = pgn_to_move_list(raw_pgn)
#
#     if not san_moves:
#         print("ERROR: I couldn't find any real chess moves in that text.")
#         return
#
#     print(f"\nForging {len(san_moves)} moves into a dictionary...")
#
#     book = {}
#
#     for san in san_moves:
#         short_fen = ghost_board.generate_fen().split()[0]
#         move = get_move_from_san(ghost_board, san)
#
#         if not move:
#             print(f"CRITICAL ERROR: My brain broke trying to read '{san}'. Did you paste an invalid PGN?")
#             break
#
#         uci_move = move.from_pos.to_notation() + move.to_pos.to_notation()
#         if move.move_type == MoveType.PROMOTION and move.promotion_choice:
#             uci_move += move.promotion_choice.value.lower()
#
#         book[short_fen] = uci_move
#         ghost_board.execute_move(move)
#
#     print("\n" + "=" * 40)
#     print("✅ COPY PASTE THIS INTO YOUR BOT SCRIPT:")
#     print("=" * 40)
#     print("PERSONAL_OPENING_BOOK = {")
#     for fen, move_str in book.items():
#         print(f'    "{fen}": "{move_str}",')
#     print("}")
#     print("=" * 40 + "\n")
#
#
# if __name__ == "__main__":
#     forge_book_from_pgn()
# if __name__ == "__main__":
#     forge_book_from_pgn()