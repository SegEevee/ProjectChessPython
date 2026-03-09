import socket
import threading

# 0.0.0.0 means "Listen to anyone on my Wi-Fi router"
SERVER_IP = "0.0.0.0"
PORT = 5555

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

try:
    server.bind((SERVER_IP, PORT))
except socket.error as e:
    print(f"Error binding to port: {e}")

server.listen(2)
print("Referee is waiting for 2 players to connect...")

players = []


def handle_client(conn, player_id):
    # Tell the player what color they are! Player 0 is White, Player 1 is Black.
    color = "White" if player_id == 0 else "Black"
    conn.send(str.encode(color))

    while True:
        try:
            # Wait for a message (up to 2048 bytes)
            data = conn.recv(2048).decode('utf-8')

            if not data:
                print("Player disconnected.")
                break

            print(f"Received from {color}: {data}")

            # Send the move to the OTHER player
            other_player_id = 1 if player_id == 0 else 0
            if len(players) > other_player_id:
                players[other_player_id].send(str.encode(data))

        except:
            break

    print(f"Lost connection to {color}")
    players.remove(conn)
    conn.close()


current_player = 0
while True:
    # The Referee waits for someone to knock on the door
    conn, addr = server.accept()
    print(f"Connected to: {addr}")

    players.append(conn)

    # Give them a dedicated thread (a helper) to listen to them forever
    threading.Thread(target=handle_client, args=(conn, current_player)).start()
    current_player += 1