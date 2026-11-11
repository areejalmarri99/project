# SE239 Network Programming: Multi-Client Chat

A TCP chat application in Python, using only the standard library. One server
accepts many clients at once. Each client must **log in (join) with a unique
username** before it can chat.

## Team

| Name | Student ID |
|------|------------|
| _member 1_ | |
| _member 2_ | |
| _member 3_ | |

## Requirements

- Python 3.10 or newer (no third-party packages)

## Running

Start the server (default `127.0.0.1:5050`):

```bash
python3 server.py
```

In separate terminals, start as many clients as you like:

```bash
python3 client.py
```

To run across machines on the same network, start the server with
`--host 0.0.0.0` and connect clients with `--host <server-ip>`. Both programs
accept `--port`.

Inside the client:

| Input        | Action                       |
|--------------|------------------------------|
| any text     | send a chat message to all   |
| `/list`      | show who is online           |
| `/quit`      | leave the chat               |

## Tests

```bash
python3 -m unittest discover -s tests -v
```

The tests start a real server on a free port and connect real TCP clients.

## Design

```
client.py ──TCP──┐
client.py ──TCP──┼──> server.py (one thread per client, shared user registry)
client.py ──TCP──┘
```

- **`protocol.py`**: the shared wire format. Every message is one UTF-8 line,
  `COMMAND [payload]\n`.
- **`server.py`**: `accept()` loop. Each connection gets its own thread. Logged-in
  users are stored in a dictionary protected by a lock. Each socket has its own
  send lock, so broadcasts from different threads never interleave.
- **`client.py`**: the main thread reads the keyboard and a background thread
  prints messages from the server.

### Protocol

| Direction        | Message                    | Meaning                                  |
|------------------|----------------------------|------------------------------------------|
| client → server  | `JOIN <username>`          | log in (required first)                  |
| client → server  | `MSG <text>`               | send a chat message                      |
| client → server  | `LIST`                     | ask who is online                        |
| client → server  | `QUIT`                     | leave                                    |
| server → client  | `WELCOME <username> <n>`   | login accepted, `n` users online         |
| server → client  | `ERROR <reason>`           | e.g. name taken, invalid, not logged in  |
| server → client  | `CHAT <username> <text>`   | a chat message, broadcast to everyone    |
| server → client  | `INFO <text>`              | join/leave notifications                 |
| server → client  | `USERS <a,b,c>`            | reply to `LIST`                          |
| server → client  | `BYE`                      | reply to `QUIT`                          |

Usernames are 1 to 16 letters, digits or `_`, and must be unique.

## Milestones

See [docs/EVIDENCE.md](docs/EVIDENCE.md) for screenshots and the demo video.

- [x] **Week 6: First connection.** One client connects and exchanges a message.
- [x] **Week 8: Multiple clients.** Three clients are connected at once and the login/join step works.
