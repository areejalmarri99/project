"""Multi-client TCP chat server.

Each client gets its own thread. A client must log in with
`JOIN <username>` before it can chat; usernames are unique.
"""

import argparse
import logging
import re
import socket
import threading

import protocol as p

USERNAME_PATTERN = re.compile(rf"^[A-Za-z0-9_]{{1,{p.MAX_USERNAME_LENGTH}}}$")

log = logging.getLogger("server")


class Connection:
    """A client socket with a lock so concurrent threads never interleave writes."""

    def __init__(self, sock: socket.socket):
        self.sock = sock
        self._send_lock = threading.Lock()

    def send(self, command: str, payload: str = "") -> None:
        with self._send_lock:
            self.sock.sendall(p.encode(command, payload))


class ChatServer:
    def __init__(self, host: str, port: int):
        self._listener = socket.create_server((host, port))
        self.address = self._listener.getsockname()[:2]
        self._clients: dict[str, Connection] = {}
        self._clients_lock = threading.Lock()

    # ---- lifecycle -------------------------------------------------------

    def serve_forever(self) -> None:
        log.info("Server listening on %s:%d", *self.address)
        while True:
            try:
                sock, addr = self._listener.accept()
            except OSError:  # listener closed
                break
            threading.Thread(target=self._handle_client, args=(sock, addr), daemon=True).start()

    def close(self) -> None:
        self._listener.close()

    # ---- per-client thread -----------------------------------------------

    def _handle_client(self, sock: socket.socket, addr: tuple) -> None:
        client_id = f"{addr[0]}:{addr[1]}"
        log.info("New connection from %s", client_id)
        conn = Connection(sock)
        username = None
        try:
            with sock, sock.makefile("r", encoding=p.ENCODING) as reader:
                username = self._login(conn, reader)
                if username:
                    log.info("%s logged in as '%s' (%d online)", client_id, username, self.online_count())
                    self._chat(conn, reader, username)
        except OSError:
            pass  # client vanished; clean up below
        finally:
            if username:
                self._unregister(username)
                log.info("'%s' left (%d online)", username, self.online_count())
                self._broadcast(p.INFO, f"{username} left the chat")
            log.info("Connection from %s closed", client_id)

    def _login(self, conn: Connection, reader) -> str | None:
        """Read lines until a valid JOIN arrives. Returns the username, or None if the client quit."""
        for line in reader:
            command, name = p.decode(line)
            if command == p.QUIT:
                conn.send(p.BYE)
                return None
            if command != p.JOIN:
                conn.send(p.ERROR, "Please log in first: JOIN <username>")
                continue
            error = self._register(name, conn)
            if error:
                conn.send(p.ERROR, error)
                continue
            conn.send(p.WELCOME, f"{name} {self.online_count()}")
            self._broadcast(p.INFO, f"{name} joined the chat", exclude=name)
            return name
        return None

    def _chat(self, conn: Connection, reader, username: str) -> None:
        for line in reader:
            command, payload = p.decode(line)
            if command == p.MSG and payload:
                log.info("%s: %s", username, payload)
                self._broadcast(p.CHAT, f"{username} {payload}")
            elif command == p.LIST:
                conn.send(p.USERS, ",".join(self.usernames()))
            elif command == p.QUIT:
                conn.send(p.BYE)
                return
            else:
                conn.send(p.ERROR, f"Unknown command: {command}")

    # ---- shared state (guarded by _clients_lock) -------------------------

    def _register(self, name: str, conn: Connection) -> str | None:
        """Add a user. Returns an error message, or None on success."""
        if not USERNAME_PATTERN.match(name):
            return f"Invalid username (1-{p.MAX_USERNAME_LENGTH} letters, digits or _)"
        with self._clients_lock:
            if name in self._clients:
                return f"Username '{name}' is already taken"
            self._clients[name] = conn
        return None

    def _unregister(self, name: str) -> None:
        with self._clients_lock:
            self._clients.pop(name, None)

    def usernames(self) -> list[str]:
        with self._clients_lock:
            return sorted(self._clients)

    def online_count(self) -> int:
        with self._clients_lock:
            return len(self._clients)

    def _broadcast(self, command: str, payload: str, exclude: str | None = None) -> None:
        with self._clients_lock:
            recipients = [c for name, c in self._clients.items() if name != exclude]
        for conn in recipients:  # send outside the lock so a slow client can't block others
            try:
                conn.send(command, payload)
            except OSError:
                pass  # that client's own thread will clean it up


def main() -> None:
    parser = argparse.ArgumentParser(description="SE239 chat server")
    parser.add_argument("--host", default=p.DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=p.DEFAULT_PORT)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s", datefmt="%H:%M:%S")
    server = ChatServer(args.host, args.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("Shutting down")
    finally:
        server.close()


if __name__ == "__main__":
    main()
