"""Interactive chat client.

Logs in with a username, then sends each typed line as a chat message.
Commands: /list shows who is online, /quit leaves.
"""

import argparse
import socket
import threading

import protocol as p


def render(command: str, payload: str) -> str:
    """Turn a server message into a human-friendly line."""
    if command == p.CHAT:
        sender, _, text = payload.partition(" ")
        return f"[{sender}] {text}"
    if command == p.INFO:
        return f"* {payload}"
    if command == p.USERS:
        return f"Online: {payload.replace(',', ', ')}"
    if command == p.ERROR:
        return f"! {payload}"
    if command == p.BYE:
        return "Disconnected. Bye!"
    return f"{command} {payload}"


def login(sock: socket.socket, reader) -> str | None:
    """Ask for a username until the server accepts it. Returns None if the server hung up."""
    while True:
        name = input("Username: ").strip()
        sock.sendall(p.encode(p.JOIN, name))
        line = reader.readline()
        if not line:
            return None
        command, payload = p.decode(line)
        if command == p.WELCOME:
            username, _, online = payload.partition(" ")
            print(f"Welcome, {username}! {online} user(s) online. Type /list or /quit.")
            return username
        print(render(command, payload))


def receive_forever(reader) -> None:
    """Background thread: print everything the server sends until it says BYE."""
    for line in reader:
        command, payload = p.decode(line)
        print(render(command, payload), flush=True)
        if command == p.BYE:
            return
    print("Connection closed by server.", flush=True)


def chat(sock: socket.socket) -> None:
    while True:
        text = input().strip()
        if not text:
            continue
        if text == "/quit":
            sock.sendall(p.encode(p.QUIT))
            return
        if text == "/list":
            sock.sendall(p.encode(p.LIST))
        else:
            sock.sendall(p.encode(p.MSG, text))


def main() -> None:
    parser = argparse.ArgumentParser(description="SE239 chat client")
    parser.add_argument("--host", default=p.DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=p.DEFAULT_PORT)
    args = parser.parse_args()

    try:
        with socket.create_connection((args.host, args.port)) as sock, \
                sock.makefile("r", encoding=p.ENCODING) as reader:
            print(f"Connected to {args.host}:{args.port}")
            if login(sock, reader) is None:
                print("Server closed the connection.")
                return
            receiver = threading.Thread(target=receive_forever, args=(reader,), daemon=True)
            receiver.start()
            chat(sock)
            receiver.join(timeout=1)
    except ConnectionRefusedError:
        print(f"Could not connect to {args.host}:{args.port}. Is the server running?")
    except (KeyboardInterrupt, EOFError):
        print()


if __name__ == "__main__":
    main()
