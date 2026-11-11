"""Wire protocol shared by the server and the client.

Every message is a single UTF-8 text line:  COMMAND [payload]\\n

Client -> server             Server -> client
  JOIN <username>              WELCOME <username> <online-count>
  MSG <text>                   CHAT <username> <text>
  LIST                         INFO <text>
  QUIT                         USERS <name,name,...>
                               ERROR <reason>
                               BYE
"""

ENCODING = "utf-8"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 5050
MAX_USERNAME_LENGTH = 16

# Client -> server
JOIN = "JOIN"
MSG = "MSG"
LIST = "LIST"
QUIT = "QUIT"

# Server -> client
WELCOME = "WELCOME"
CHAT = "CHAT"
INFO = "INFO"
USERS = "USERS"
ERROR = "ERROR"
BYE = "BYE"


def encode(command: str, payload: str = "") -> bytes:
    """Build one protocol line ready to be sent on the socket."""
    line = f"{command} {payload}" if payload else command
    return (line + "\n").encode(ENCODING)


def decode(line: str) -> tuple[str, str]:
    """Split a received line into (COMMAND, payload)."""
    command, _, payload = line.strip().partition(" ")
    return command.upper(), payload.strip()
