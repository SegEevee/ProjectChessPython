import socket
import threading

# The "Open All Doors" address. This allows local and Wi-Fi connections simultaneously.
SERVER_IP = "0.0.0.0"
PORT = 5555

# 1. Create the Phone
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# 2. Plug the Phone into the Wall
try:
    server.bind((SERVER_IP, PORT))
except socket.error as e:
    print(f"[ERROR] Failed to bind to port {PORT}. Is another server already running?")
    print(str(e))
    exit()

# 3. Turn the Ringer On (Allow up to 2 people in the waiting room)
server.listen(2)
print(f"[REFEREE] Awake and listening on port {PORT}...")

clients = []
COLORS = ["White", "Black"]


def handle_client(conn, player_id):
    """The Worker assigned to talk to a specific player."""
    color = COLORS[player_id]

    # Immediately tell the game client what color it is playing!
    conn.send(str.encode(color))
    print(f"[REFEREE] Assigned {color} to Player {player_id + 1}")

    while True:
        try:
            # Wait for the player to send a move
            data = conn.recv(2048)
            if not data:
                print(f"[REFEREE] Player {player_id + 1} ({color}) disconnected.")
                break

            msg = data.decode("utf-8")
            print(f"[MOVE] {color} played: {msg}")

            # Forward the move to the OTHER player (The Magic Mirror)
            for c in clients:
                if c != conn:
                    c.sendall(data)

        except Exception as e:
            print(f"[ERROR] Connection lost with {color}: {e}")
            break

    # Cleanup when someone rage quits
    print(f"[REFEREE] Closing connection for Player {player_id + 1}")
    if conn in clients:
        clients.remove(conn)
    conn.close()


# The Main Loop: The Referee standing at the door waiting for knocks
while True:
    conn, addr = server.accept()
    print(f"[REFEREE] New connection established from {addr}")

    if len(clients) >= 2:
        print("[REFEREE] Game is full. Rejecting extra connection.")
        conn.close()
        continue

    clients.append(conn)

    # Spawn a new thread (worker) so the server doesn't freeze while waiting for a move
    # The first person gets id 0 (White), the second gets id 1 (Black)
    thread = threading.Thread(target=handle_client, args=(conn, len(clients) - 1))
    thread.start()