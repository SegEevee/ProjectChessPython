import io
import json
import math
from keras.models import load_model


# <editor-fold desc="ACTUAL AI">
import zstandard as zstd
from keras.models import Sequential
from keras.layers import Dense, Dropout, Input
from keras.callbacks import EarlyStopping


# ==========================================
# 1. THE TRANSLATOR (FEN -> 768 Array)
# ==========================================


# ==========================================
# 2. THE DATA FACTORY (Raw JSON -> Big Data)
# ==========================================
def squish_score(cp: int) -> float:
    """Turns Centipawns (-300 to +300) into a Win Probability (0.0 to 1.0)."""
    # This is a classic chess math trick.
    # 0 cp = 0.5 probability.
    # +400 cp = ~0.99 probability.
    return 1 / (1 + math.exp(-0.004 * cp))


def build_chess_database(zst_file_path: str, output_name: str, max_rows: int = 10000):
    """Eats a compressed .zst file line by line without exploding your RAM."""
    X = []
    y = []

    print(f"Factory started. Streaming massive file: {zst_file_path}...")

    try:
        # 1. Open the compressed file in 'binary read' mode
        with open(zst_file_path, 'rb') as compressed_file:
            # 2. Attach the Zstandard unzipper
            dctx = zstd.ZstdDecompressor()

            # 3. Create a stream (a pipe) that reads the unzipped data as text
            with dctx.stream_reader(compressed_file) as reader:
                text_stream = io.TextIOWrapper(reader, encoding='utf-8')

                # 4. Read it line by line (Sipping from the firehose)
                for i, line in enumerate(text_stream):
                    if i >= max_rows:
                        break  # THE SAFETY VALVE

                    data = json.loads(line)
                    fen = data['fen']

                    try:
                        best_eval = data['evals'][0]['pvs'][0]

                        if 'mate' in best_eval:
                            mate_in = best_eval['mate']
                            score = 1.0 if mate_in > 0 else 0.0
                        else:
                            cp = best_eval['cp']
                            score = squish_score(cp)

                        X.append(fen_to_features(fen))
                        y.append(score)

                    except (KeyError, IndexError):
                        # Skip broken lines
                        continue

                        # A heartbeat monitor so you know it hasn't crashed
                    if (i + 1) % 5000 == 0:
                        print(f"Processed {i + 1} boards...")

        # 5. Save the translated numbers
        np.savez_compressed(f'data/{output_name}.npz', X=np.array(X), y=np.array(y))
        print(f"Success! Processed {len(X)} valid boards and saved to data/{output_name}.npz")

    except FileNotFoundError:
        print(f"ERROR: Could not find the file at {zst_file_path}. Check the path!")


# ==========================================
# 3. THE BLANK CANVAS (Your Neural Network)
# ==========================================
def train_chess_brain():
    """Load the processed data and train the AI."""
    print("Loading data...")
    data = np.load('data/chess_training_data.npz')
    X = data['X']
    y = data['y']

    print("Data loaded. Over to you, Segev.")
    # --- SEGEV, YOUR KERAS CODE GOES HERE ---

    model = Sequential([
        Input(shape=(768,)),  # 64 squares * 12 piece types
        Dense(512, activation='relu'),  # Big layer to find piece relationships
        Dropout(0.2),  # Prevents "Memorization" (Overfitting)
        Dense(256, activation='relu'),  # Finding positional patterns
        Dense(128, activation='relu'),  # Refining the score
        Dense(1, activation='sigmoid')  # Final Win Probability (0 to 1)
    ])

    # 2. THE JUDGE
    model.compile(
        optimizer='adam',
        loss='mean_squared_error',  # Since y is a continuous probability
        metrics=['mae']  # Mean Absolute Error (how far we miss)
    )

    # 3. THE KILL-SWITCH
    stop_early = EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True)

    print("Training Beginning. This might take a few minutes...")
    model.fit(
        X, y,
        epochs=250,
        batch_size=64,
        callbacks=[stop_early]
    )

    # 4. EXPORT THE KNOWLEDGE
    model.save('models/chess_brain.keras')
    print("Success! The Chess Brain is saved in models/chess_brain.keras")


# ==========================================
# 4. THE DEMI-BOARD (Headless Testing)
# ==========================================
def test_ai_without_graphics():
    """Runs a ghost board in memory so you don't have to load Pygame UI."""
    print("Summoning ghost board...")
    # You use your existing Board class, but we don't call the Pygame while-loop!
    ghost_board = Board(STARTING_POSITION)

    print(f"Ghost Board FEN: {ghost_board.generate_fen()}")

    # Test your translator
    features = fen_to_features(ghost_board.generate_fen())
    print(f"Features Array Shape: {features.shape}")
    print(f"Is White Rook on A1 (Index 3)? Value: {features[3]}")

    # In the future, this is where you will load your trained model
    # and ask it to predict the score of the ghost_board!


# </editor-fold>


def fen_to_features(fen: str) -> np.ndarray:
    """Takes a snapshot of the board and turns it into 768 Yes/No questions."""
    # Create an empty checklist of 768 zeros
    features = np.zeros(768, dtype=np.int8)

    # A dictionary to know which piece gets which slot (0 to 11)
    piece_to_idx = {
        'P': 0, 'N': 1, 'B': 2, 'R': 3, 'Q': 4, 'K': 5,  # White
        'p': 6, 'n': 7, 'b': 8, 'r': 9, 'q': 10, 'k': 11  # Black
    }

    # We only care about the board layout, not the clocks or castling for the basic brain
    board_part = fen.split()[0]
    square = 0

    for char in board_part:
        if char == '/':
            continue  # Skip to next row
        elif char.isdigit():
            square += int(char)  # Skip empty squares
        else:
            piece_idx = piece_to_idx[char]
            # THE MAGIC FORMULA: Which of the 768 boxes do we check?
            index = (square * 12) + piece_idx
            features[index] = 1
            square += 1

    return features


def ai_get_evaluation(board):
    """Asks the trained brain: 'Who is winning right now?'"""
    global CHESS_MODEL, EVALUATION_CACHE

    current_fen = board.generate_fen()

    # THE SPEED HACK: Did we already calculate this exact board today?
    if current_fen in EVALUATION_CACHE:
        return EVALUATION_CACHE[current_fen]

    if CHESS_MODEL is None:
        try:
            CHESS_MODEL = load_model('models/chess_brain.keras')
            print("AI Brain Loaded Successfully.")
        except Exception as e:
            print(f"Error loading AI model: {e}")
            return 0.5

    features = fen_to_features(current_fen)
    features_reshaped = features.reshape(1, 768)

    raw_tensor = CHESS_MODEL(features_reshaped, training=False)
    prediction = float(raw_tensor[0][0])

    # Save it to the memory card before returning!
    EVALUATION_CACHE[current_fen] = prediction

    return prediction


def get_all_legal_moves_for_color(board, color, prioritize=True):
    moves = []
    for piece in board.get_all_pieces():
        if piece.color == color:
            for move in piece.legal_moves.values():
                moves.append(move)

    if prioritize:
        # THE MOVE FILTER:
        # 1. Captures are high priority (Value 10)
        # 2. Checks are high priority (Value 5)
        # 3. Everything else is 0
        def move_value(m):
            val = 0
            if board.get_piece_at(m.victim_pos): val += 10
            # If we step into the future and the enemy is in check, that's a good move!
            return val

        moves.sort(key=move_value, reverse=True)

    return moves

def minimax(board, depth, alpha, beta):
    """The Time Machine: Imagines the future and uses the Scissors (Alpha-Beta)."""
    # 1. We hit the bottom of our imagination, or the game ended. Ask the Judge!
    if depth == 0 or PLAYERS[ChessColor.WHITE].lost or PLAYERS[ChessColor.BLACK].lost:
        return ai_get_evaluation(board)

    # 2. WHITE'S TURN (White wants the score to be exactly 1.0)
    if board.active_color == ChessColor.WHITE:
        max_eval = -999.0
        moves = get_all_legal_moves_for_color(board, ChessColor.WHITE)
        moves.sort(key=lambda m: 1 if m.victim_pos else 0, reverse=True)

        for move in moves:
            if move.move_type == MoveType.PROMOTION: move.promotion_choice = ChessPieceType.QUEEN

            # Imagine the move
            board.execute_move(move,is_imagining=True)
            eval_score = minimax(board, depth - 1, alpha, beta)
            board.undo_move()

            max_eval = max(max_eval, eval_score)
            alpha = max(alpha, eval_score)

            # The Scissors!
            if beta <= alpha:
                break
        return max_eval

    # 3. BLACK'S TURN (Black wants the score to be exactly 0.0)
    else:
        min_eval = 999.0
        moves = get_all_legal_moves_for_color(board, ChessColor.BLACK)
        moves.sort(key=lambda m: 1 if m.victim_pos else 0, reverse=True)

        for move in moves:
            if move.move_type == MoveType.PROMOTION: move.promotion_choice = ChessPieceType.QUEEN

            # Imagine the move
            board.execute_move(move,is_imagining=True)
            eval_score = minimax(board, depth - 1, alpha, beta)
            board.undo_move()

            min_eval = min(min_eval, eval_score)
            beta = min(beta, eval_score)

            # The Scissors!
            if beta <= alpha:
                break
        return min_eval

def ai_get_best_move(board, ai_color, search_depth=3):
    """The General: Uses Minimax to test futures and picks the best path."""
    best_move = None
    moves = get_all_legal_moves_for_color(board, ai_color)
    moves.sort(key=lambda m: 1 if m.victim_pos else 0, reverse=True)

    if not moves: return None

    best_score = -999.0 if ai_color == ChessColor.WHITE else 999.0

    print(f"\n--- AI is looking {search_depth} steps into the future ---")

    for move in moves:
        if move.move_type == MoveType.PROMOTION: move.promotion_choice = ChessPieceType.QUEEN

        # 1. Step into the timeline
        board.execute_move(move,is_imagining=True)

        # --- THE HARD SKIP ---
        # Get a 'quick look' evaluation of the board immediately
        quick_eval = ai_get_evaluation(board)

        # If the move looks like a disaster (dropping a Queen), skip the deep search!
        threshold = AGREED_GET_BEST_MOVE_THRESHOLD  # 20% margin
        if ai_color == ChessColor.WHITE and quick_eval < (best_score - threshold):
            board.undo_move()
            continue
        if ai_color == ChessColor.BLACK and quick_eval > (best_score + threshold):
            board.undo_move()
            continue
        # ---------------------

        # 2. Start the Time Machine (alpha starts at -999, beta at 999)
        move_score = minimax(board, search_depth - 1, -999.0, 999.0)

        # 3. Step back to reality
        board.undo_move()

        # 4. Did we find a better path?
        if ai_color == ChessColor.WHITE:
            if move_score > best_score:
                best_score = move_score
                best_move = move
        else:
            if move_score < best_score:
                best_score = move_score
                best_move = move

    print(f"AI chose move based on future score: {best_score:.3f}")
    return best_move
