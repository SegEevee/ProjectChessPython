import socket
import json

MASTER_ADDRESS = "192.168.68.64"  # Make sure this matches the laptop's IP!


class Network:
    def __init__(self, ip_address=MASTER_ADDRESS):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server = ip_address
        self.port = 5555
        self.addr = (self.server, self.port)
        self.color = None
        self.sync_data = None

        self.connect()

    def connect(self):
        try:
            self.client.connect(self.addr)

            # 1. Grab the Color (The server sends this instantly)
            self.client.settimeout(5.0)
            response = self.client.recv(2048).decode()

            if response.startswith("COLOR|"):
                self.color = response.split("|")[1]
                print(f"[NETWORK] The Referee assigned me: {self.color}")
            elif response.startswith("REJECT|"):
                print("[NETWORK] Bouncer kicked us out: Room is full.")
                return False

            # 2. THE CRITICAL FIX: Make the socket non-blocking!
            # This allows Pygame to check the mail, see it's empty, and go back to drawing the screen.
            self.client.setblocking(False)
            return True

        except Exception as e:
            print(f"[ERROR] Connection failed: {e}")
            return False

    def send_message(self, tag: str, payload: str = ""):
        """The new way we talk to the server. We must tag everything!"""
        try:
            msg = f"{tag}|{payload}"
            self.client.send(str.encode(msg))
        except socket.error as e:
            print(f"[NETWORK ERROR] {e}")

    def peek_mailbox(self):
        """Reads the mail and separates the Tag from the Payload."""
        try:
            # We use 4096 because the JSON photocopy can be a bit large
            data = self.client.recv(4096).decode()
            if not data:
                return None, None

            # Split the string at the VERY FIRST pipe symbol
            parts = data.split("|", 1)
            if len(parts) == 2:
                tag, payload = parts[0], parts[1]
                return tag, payload
            return data, ""

        except BlockingIOError:
            # Mailbox is empty. No big deal.
            return None, None
        except Exception as e:
            # The server crashed or we lost Wi-Fi
            print(f"[NETWORK DISCONNECT] {e}")
            return "DISCONNECT", None