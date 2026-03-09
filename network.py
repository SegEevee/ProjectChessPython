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

            # 1. Get your color
            self.client.settimeout(5.0)  # Give it time to talk
            color = self.client.recv(2048).decode()
            print(f"I am playing as: {color}")

            # 2. WAIT FOR START SIGNAL
            # This will 'freeze' here until the second player joins the server!
            print("Waiting for opponent...")
            start_signal = self.client.recv(2048).decode()

            if start_signal == "START_GAME":
                print("Game is LIVE!")
                self.client.setblocking(False)  # Go back to non-blocking for the game
                return color

        except Exception as e:
            print(f"Connection failed: {e}")
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