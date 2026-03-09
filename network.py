import socket


class Network:
    def __init__(self, ip_address="127.0.0.1"):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server = ip_address  # 127.0.0.1 means "My Own Computer" for testing
        self.port = 5555
        self.addr = (self.server, self.port)
        self.color = self.connect()

    def connect(self):
        try:
            self.client.connect(self.addr)
            # The Mailbox Trick!
            # This tells Python NOT to freeze if there is no message waiting.
            self.client.setblocking(False)

            # The first thing the server says is our color
            # We must force a tiny wait here just for the initial connection handshake
            self.client.settimeout(2.0)
            color = self.client.recv(2048).decode()
            self.client.setblocking(False)  # Go back to non-blocking!
            return color
        except Exception as e:
            print(f"Failed to connect: {e}")
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