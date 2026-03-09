import socket
import threading
import time
import json

# --- CONFIG ---
SERVER_IP = "0.0.0.0"
PORT = 5555
STARTING_TIME = 300.0  # 5 minutes in seconds


class ChessMatch:
    """The Referee's Brain."""

    def __init__(self):
        # The Chairs: Maps a Color to an IP Address (Allows Reconnection)
        self.seats = {"White": None, "Black": None}
        # The Phones: Maps a Color to an active Socket Connection
        self.connections = {"White": None, "Black": None}

        self.move_history = []
        self.active_turn = "White"
        self.status = "WAITING"  # WAITING, PLAYING, GAME_OVER

        self.clocks = {"White": STARTING_TIME, "Black": STARTING_TIME}
        self.last_clock_update = 0.0

    def update_clocks(self):
        """The Master Stopwatch. Updates the active player's time."""
        if self.status != "PLAYING" or self.last_clock_update == 0:
            return

        now = time.time()
        elapsed = now - self.last_clock_update
        self.clocks[self.active_turn] -= elapsed
        self.last_clock_update = now

        # Did someone's flag fall?
        if self.clocks[self.active_turn] <= 0:
            self.clocks[self.active_turn] = 0
            self.status = "GAME_OVER"
            self.broadcast(f"FLAG|{self.active_turn}")

    def get_sync_data(self):
        """Photocopies the referee's notebook into a JSON string."""
        self.update_clocks()
        data = {
            "status": self.status,
            "history": self.move_history,
            "turn": self.active_turn,
            "time_w": max(0, self.clocks["White"]),
            "time_b": max(0, self.clocks["Black"])
        }
        return "SYNC|" + json.dumps(data)

    def broadcast(self, message):
        """Shouts a message to both players (if they are currently connected)."""
        print(f"[BROADCAST] {message}")
        for color, conn in self.connections.items():
            if conn:
                try:
                    conn.sendall(str.encode(message))
                except Exception as e:
                    print(f"[ERROR] Failed to broadcast to {color}: {e}")


# --- THE OFFICE ---
MATCH = ChessMatch()
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

try:
    server.bind((SERVER_IP, PORT))
    server.listen(2)
    print(f"[REFEREE] Server is LIVE on port {PORT}. Waiting for players...")
except socket.error as e:
    print(f"[FATAL] Port {PORT} is blocked! {e}")
    exit()


def handle_client(conn, addr, my_color):
    """The worker assigned to listen to one specific player."""
    global MATCH

    # 1. THE SYNC: Send them the current state of the game
    print(f"[LOBBY] Sending notebook photocopy to {my_color}...")
    conn.send(str.encode(MATCH.get_sync_data()))

    # 2. THE STARTING GUN: If the room is now full, start the match!
    if MATCH.connections["White"] and MATCH.connections["Black"] and MATCH.status == "WAITING":
        time.sleep(0.5)  # The Anti-Squish Pause
        MATCH.status = "PLAYING"
        MATCH.last_clock_update = time.time()
        MATCH.broadcast("START|")
        print("[REFEREE] --- GAME STARTED ---")

    # 3. THE MATCH LOOP: Listen for moves or resignations
    while True:
        try:
            data = conn.recv(2048)
            if not data:
                break  # Client disconnected

            msg = data.decode("utf-8")

            if msg.startswith("MOVE|"):
                san = msg.split("|")[1]
                print(f"[GAME] {my_color} played: {san}")

                # Update the Referee's notebook
                MATCH.update_clocks()
                MATCH.move_history.append(san)
                MATCH.active_turn = "Black" if MATCH.active_turn == "White" else "White"
                MATCH.last_clock_update = time.time()

                # Forward the move to the OTHER player
                other_color = "Black" if my_color == "White" else "White"
                if MATCH.connections[other_color]:
                    MATCH.connections[other_color].sendall(str.encode(f"MOVE|{san}"))

            elif msg == "RESIGN":
                print(f"[GAME] {my_color} has resigned!")
                MATCH.status = "GAME_OVER"
                MATCH.broadcast(f"RESIGN|{my_color}")

        except Exception as e:
            print(f"[ERROR] Connection lost with {my_color}: {e}")
            break

    # --- DISCONNECT HANDLING ---
    print(f"[DISCONNECT] {my_color} ({addr[0]}) dropped the call.")
    MATCH.connections[my_color] = None

    # If the game was active, tell the other guy to wait
    other_color = "Black" if my_color == "White" else "White"
    if MATCH.status == "PLAYING" and MATCH.connections[other_color]:
        MATCH.connections[other_color].sendall(str.encode("OPPONENT_DISCONNECTED|"))

    conn.close()


# --- THE FRONT DOOR ---
while True:
    conn, addr = server.accept()
    ip_address = addr[0]
    print(f"[DOOR] Knock from {ip_address}")

    assigned_color = None

    # RECONNECTION LOGIC: Did this IP sit down previously?
    if MATCH.seats["White"] == ip_address:
        assigned_color = "White"
    elif MATCH.seats["Black"] == ip_address:
        assigned_color = "Black"
    else:
        # NEW PLAYER LOGIC: Find an empty seat
        if MATCH.seats["White"] is None:
            assigned_color = "White"
        elif MATCH.seats["Black"] is None:
            assigned_color = "Black"

    # THE BOUNCER: Room is full, and you don't own a seat!
    if assigned_color is None:
        print(f"[BOUNCER] Rejected {ip_address}. Room is full.")
        conn.send(str.encode("REJECT|ROOM_FULL"))
        conn.close()
        continue

    # Seat the player
    MATCH.seats[assigned_color] = ip_address
    MATCH.connections[assigned_color] = conn

    # Tell the client what color they are
    conn.send(str.encode(f"COLOR|{assigned_color}"))
    time.sleep(0.2)  # Anti-Squish Pause before starting the worker loop

    # Hand them to a worker thread
    thread = threading.Thread(target=handle_client, args=(conn, addr, assigned_color))
    thread.start()