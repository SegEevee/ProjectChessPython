import json
import os

# ELI5: We find the exact folder where this factory script is running
PERMANENT_ROOT = os.path.abspath(os.path.dirname(__file__))
DIRECTORY_OF_BOTS = os.path.join(PERMANENT_ROOT, "bots")


def forge_bot():
    print("\n" + "=" * 40)
    print("🤖 THE BOT FACTORY 🤖")
    print("=" * 40)

    name = input("\n1. What is the bot's display name? (e.g., 'Toddler Gary'): ")
    bot_id = input("2. What should the bot's ID be? (No spaces, e.g., 'gary_noob'): ").lower().strip().replace(" ", "_")

    bot_data = {"name": name}

    print("\n3. What kind of brain does this bot have?")
    print("   [1] Custom Python Script (Factory builds the split-logic template)")
    print("   [2] Engine Bot (Factory builds the Stockfish middleman)")
    brain_choice = input("   Choose 1 or 2: ").strip()

    if not os.path.exists(DIRECTORY_OF_BOTS):
        os.makedirs(DIRECTORY_OF_BOTS)

    # --- THE OPENING BOOK PROMPT ---
    print("\n   [Opening Books]")
    print("   -> Enter book names separated by commas (e.g., sicilian, alapin)")
    print("   -> Or leave blank if this bot doesn't read.")
    books_input = input("   -> Books: ").strip()

    # ELI5: Turn "sicilian, alapin" into ['sicilian', 'alapin']
    if books_input:
        book_list = [b.strip() for b in books_input.split(',')]
    else:
        book_list = []

    books_str = str(book_list)

    # --- PATH A: THE CUSTOM SCRIPT TEMPLATE ---
    if brain_choice == "1":
        bot_data["type"] = "script"
        bot_data["script_file"] = f"{bot_id}.py"
        bot_data["function_name"] = "get_move"

        python_code = f'''import random
import json
import os

PERSONAL_OPENING_BOOK = {{}}
# Factory injected library card:
OPENING_BOOKS_LIST = {books_str} 

Move = None; MoveType = None; ChessPieceType = None; SquarePosition = None; Board = None; ChessColor = None

def init_bot(passed_Move, passed_MoveType, passed_ChessPieceType, passed_SquarePosition, passed_Board, passed_ChessColor):
    """The Care Package. Main.py hands us the tools, and we read our books."""
    global Move, MoveType, ChessPieceType, SquarePosition, Board, ChessColor, PERSONAL_OPENING_BOOK
    Move = passed_Move; MoveType = passed_MoveType; ChessPieceType = passed_ChessPieceType
    SquarePosition = passed_SquarePosition; Board = passed_Board; ChessColor = passed_ChessColor

    openings_dir = os.path.join(os.path.dirname(__file__), "..", "openings")
    for book_name in OPENING_BOOKS_LIST:
        book_path = os.path.join(openings_dir, f"{{book_name}}.json")
        if os.path.exists(book_path):
            try:
                with open(book_path, "r", encoding="utf-8") as f:
                    book_data = json.load(f)
                    PERSONAL_OPENING_BOOK.update(book_data)
                print(f"📖 {bot_id} loaded opening book: {{book_name}}.json")
            except Exception as e:
                print(f"❌ {bot_id} failed to read {{book_name}}.json: {{e}}")
        else:
            print(f"⚠️ {bot_id} could not find {{book_name}}.json")

def get_move(board, ai_color):
    """The Traffic Cop. Checks the book first, then asks your custom brain."""
    current_fen = board.generate_fen()

    # THE UPGRADE: We MUST include the turn color (w or b) so White doesn't play Black's moves!
    core_fen = current_fen.split()[0] + " " + current_fen.split()[1]

    if core_fen in PERSONAL_OPENING_BOOK:
        toybox = PERSONAL_OPENING_BOOK[core_fen]

        # Backward compatibility: If it's an old book with a string, make it a list
        if isinstance(toybox, str): 
            toybox = [toybox]

        # THE MAGIC TRICK: Pull a random move out of the toybox!
        move_str = random.choice(toybox)

        for piece in board.get_all_pieces():
            if piece.color == ai_color and piece.position.to_notation() == move_str[:2]:
                for target_pos, move in piece.legal_moves.items():
                    if target_pos.to_notation() == move_str[2:]:
                        print(f"{bot_id} played a random book move: {{move_str}}")
                        return move

    return get_custom_move(board, ai_color)

def get_custom_move(board, ai_color):
    all_possible_moves = []
    for piece in board.get_all_pieces():
        if piece.color == ai_color:
            for move in piece.legal_moves.values():
                all_possible_moves.append(move)

    if not all_possible_moves: return None
    return random.choice(all_possible_moves)
'''
        py_filepath = os.path.join(DIRECTORY_OF_BOTS, f"{bot_id}.py")
        with open(py_filepath, "w", encoding="utf-8") as py_file:
            py_file.write(python_code)

        print(f"\n   -> Generated custom split-logic script: {bot_id}.py")

    # --- PATH B: THE GENERATED MIDDLEMAN ---
    elif brain_choice == "2":
        print("\n   [Engine Power Settings]")
        depth_str = input("   -> Search Depth? (e.g., 4. Type 9999 for Max Depth): ").strip()
        depth = int(depth_str) if depth_str.isdigit() else 4

        elo = 9999
        use_elo = input("   -> Limit the bot's ELO? (y/n): ").strip().lower()
        if use_elo == 'y':
            elo_str = input("      -> Enter ELO (e.g., 1200): ").strip()
            elo = int(elo_str) if elo_str.isdigit() else 1200

        bot_data["type"] = "script"
        bot_data["script_file"] = f"{bot_id}.py"
        bot_data["function_name"] = "get_move"

        python_code = f'''import json
import random
import os
from engines.stockfish import stockfishpy as stockfish

PERSONAL_OPENING_BOOK = {{}}
OPENING_BOOKS_LIST = {books_str}

Move = None; MoveType = None; ChessPieceType = None; SquarePosition = None; Board = None; ChessColor = None

def init_bot(passed_Move, passed_MoveType, passed_ChessPieceType, passed_SquarePosition, passed_Board, passed_ChessColor):
    global Move, MoveType, ChessPieceType, SquarePosition, Board, ChessColor, PERSONAL_OPENING_BOOK
    Move = passed_Move; MoveType = passed_MoveType; ChessPieceType = passed_ChessPieceType
    SquarePosition = passed_SquarePosition; Board = passed_Board; ChessColor = passed_ChessColor

    openings_dir = os.path.join(os.path.dirname(__file__), "..", "openings")
    for book_name in OPENING_BOOKS_LIST:
        book_path = os.path.join(openings_dir, f"{{book_name}}.json")
        if os.path.exists(book_path):
            try:
                with open(book_path, "r", encoding="utf-8") as f:
                    book_data = json.load(f)
                    PERSONAL_OPENING_BOOK.update(book_data)
                print(f"📖 {bot_id} loaded opening book: {{book_name}}.json")
            except Exception as e:
                print(f"❌ {bot_id} failed to read {{book_name}}.json: {{e}}")
        else:
            print(f"⚠️ {bot_id} could not find {{book_name}}.json")

def get_move(board, ai_color):
    """Generated Middleman for {name}"""
    current_fen = board.generate_fen()
    core_fen = current_fen.split()[0] + " " + current_fen.split()[1]

    if core_fen in PERSONAL_OPENING_BOOK:
        toybox = PERSONAL_OPENING_BOOK[core_fen]
        if isinstance(toybox, str): toybox = [toybox]

        move_str = random.choice(toybox)

        for piece in board.get_all_pieces():
            if piece.color == ai_color and piece.position.to_notation() == move_str[:2]:
                for target_pos, move in piece.legal_moves.items():
                    if target_pos.to_notation() == move_str[2:]:
                        print(f"{bot_id} played a random book move: {{move_str}}")
                        return move

    print(f"{bot_id} is thinking with Stockfish (ELO: {elo}, Depth: {depth})...")
    return stockfish.get_stockfish_move(board, elo={elo}, depth={depth})
'''
        py_filepath = os.path.join(DIRECTORY_OF_BOTS, f"{bot_id}.py")
        with open(py_filepath, "w", encoding="utf-8") as py_file:
            py_file.write(python_code)

        print(f"\n   -> Generated middleman script: {bot_id}.py")

    else:
        print("\n❌ Invalid choice. The factory is shutting down.")
        return

    json_filepath = os.path.join(DIRECTORY_OF_BOTS, f"{bot_id}.json")
    with open(json_filepath, "w", encoding="utf-8") as f:
        json.dump(bot_data, f, indent=4)

    print("\n" + "=" * 40)
    print(f"✅ SUCCESS! '{bot_id}' has been forged.")
    print("=" * 40 + "\n")


if __name__ == "__main__":
    while True:
        forge_bot()
        again = input("Forge another bot? (y/n): ").strip().lower()
        if again != 'y':
            break