import socket

MASTER_ADDRESS = "192.168.68.64"

class Network:
    def __init__(self, ip_address=MASTER_ADDRESS):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server = ip_address
        self.port = 5555
        self.addr = (self.server, self.port)
        self.color = self.connect()

    def connect(self):
        try:
            self.client.connect(self.addr)

            # 1. Get the Color (White/Black)
            # We use a long timeout here because the other player might be slow!
            self.client.settimeout(30.0)
            color = self.client.recv(2048).decode()
            print(f"[NETWORK] My assigned color: {color}")

            # 2. THE LOBBY WAIT: Stay here until the Server says "START_GAME"
            print("[NETWORK] Waiting for opponent to join...")

            while True:
                # We wait for the "START_GAME" string from the server
                signal = self.client.recv(2048).decode()
                if signal == "START_GAME":
                    print("[NETWORK] Match Found! Game Starting...")
                    break
                elif signal == "ROOM_FULL":
                    print("[NETWORK] Error: Server is already full!")
                    return None

            # 3. SUCCESS: Now make the socket non-blocking for the actual game
            self.client.setblocking(False)
            return color

        except socket.timeout:
            print("[ERROR] Connection Timed Out. No one joined the lobby.")
            return None
        except Exception as e:
            print(f"[ERROR] Connection failed: {e}")
            return None


    def send_move(self, san_string):
        try:
            self.client.send(str.encode(san_string))
        except socket.error as e:
            print(f"Network error sending move: {e}")

    def peek_mailbox(self):
        """Runs 60 times a second. Peeks for an enemy move."""
        try:
            # Read whatever is in the pipe
            data = self.client.recv(2048).decode()
            return data
        except BlockingIOError:
            # Mailbox is empty. Nothing to worry about.
            return None
        except socket.error as e:
            # A real error occurred (like getting disconnected)
            return None