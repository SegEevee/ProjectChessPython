import socket
import threading
import time

# The "Open All Doors" address
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

# 3. Turn the Ringer On
server.listen(2)
print(f"[REFEREE] Awake and listening on port {PORT}...")

clients = []
COLORS = ["White", "Black"]

def handle_client(conn, player_id):
    """The Worker assigned to talk to a specific player."""
    color = COLORS[player_id]

    # 1. Immediately tell the game client what color it is playing!
    conn.send(str.encode(color))
    print(f"[REFEREE] Assigned {color} to Player {player_id + 1}")

    # 2. THE WAITING ROOM: Hang out here until the 2nd player joins
    print(f"[REFEREE] Waiting for opponent for {color}...")
    while len(clients) < 2:
        time.sleep(0.1) # Check the door every 0.1 seconds

    # 3. THE STARTING GUN! Both players are here.
    time.sleep(0.5) # The Anti-Squish Pause
    conn.send(str.encode("START_GAME"))
    print(f"[REFEREE] Told {color} to START!")

    # 4. THE MATCH LOOP
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


def main_game_loop():
    """The Main Loop: The Referee standing at the door waiting for knocks."""
    while True:
        conn, addr = server.accept()
        print(f"[REFEREE] New connection established from {addr}")

        if len(clients) >= 2:
            print("[REFEREE] Game is full. Rejecting extra connection.")
            # Tell the late client the room is full so it doesn't freeze
            conn.send(str.encode("ROOM_FULL"))
            conn.close()
            continue

        clients.append(conn)

        # Spawn a new thread (worker) so the server doesn't freeze
        thread = threading.Thread(target=handle_client, args=(conn, len(clients) - 1))
        thread.start()

if __name__ == "__main__":
    main_game_loop()