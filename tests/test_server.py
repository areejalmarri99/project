"""End-to-end tests: real server on a free port, real TCP clients."""

import os
import socket
import sys
import threading
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import protocol as p  # noqa: E402
from server import ChatServer  # noqa: E402


class TestClient:
    def __init__(self, address):
        self.sock = socket.create_connection(address, timeout=2)
        self.reader = self.sock.makefile("r", encoding=p.ENCODING)

    def send(self, command, payload=""):
        self.sock.sendall(p.encode(command, payload))

    def receive(self):
        return p.decode(self.reader.readline())

    def join(self, name):
        self.send(p.JOIN, name)
        return self.receive()

    def close(self):
        self.reader.close()
        self.sock.close()


class ChatServerTest(unittest.TestCase):
    def setUp(self):
        self.server = ChatServer("127.0.0.1", 0)  # port 0 = any free port
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.clients = []

    def tearDown(self):
        for client in self.clients:
            client.close()
        self.server.close()

    def connect(self):
        client = TestClient(self.server.address)
        self.clients.append(client)
        return client

    # Week 6: one client connects and exchanges a message
    def test_single_client_exchanges_message(self):
        alice = self.connect()
        self.assertEqual(alice.join("alice"), (p.WELCOME, "alice 1"))
        alice.send(p.MSG, "hello server")
        self.assertEqual(alice.receive(), (p.CHAT, "alice hello server"))

    # Week 8: three clients at the same time + login/join
    def test_three_clients_connected_at_once(self):
        alice, bob, carol = self.connect(), self.connect(), self.connect()
        self.assertEqual(alice.join("alice"), (p.WELCOME, "alice 1"))
        self.assertEqual(bob.join("bob"), (p.WELCOME, "bob 2"))
        self.assertEqual(alice.receive(), (p.INFO, "bob joined the chat"))
        self.assertEqual(carol.join("carol"), (p.WELCOME, "carol 3"))
        for client in (alice, bob):
            self.assertEqual(client.receive(), (p.INFO, "carol joined the chat"))

        carol.send(p.LIST)
        self.assertEqual(carol.receive(), (p.USERS, "alice,bob,carol"))

        bob.send(p.MSG, "hi everyone")
        for client in (alice, bob, carol):
            self.assertEqual(client.receive(), (p.CHAT, "bob hi everyone"))

    def test_must_join_before_chatting(self):
        client = self.connect()
        client.send(p.MSG, "sneaky")
        command, _ = client.receive()
        self.assertEqual(command, p.ERROR)

    def test_duplicate_and_invalid_usernames_rejected(self):
        self.connect().join("alice")
        second = self.connect()
        self.assertEqual(second.join("alice")[0], p.ERROR)
        self.assertEqual(second.join("bad name!")[0], p.ERROR)
        self.assertEqual(second.join("alice2"), (p.WELCOME, "alice2 2"))

    def test_quit_notifies_others(self):
        alice, bob = self.connect(), self.connect()
        alice.join("alice")
        bob.join("bob")
        alice.receive()  # "bob joined"
        bob.send(p.QUIT)
        self.assertEqual(bob.receive(), (p.BYE, ""))
        self.assertEqual(alice.receive(), (p.INFO, "bob left the chat"))


if __name__ == "__main__":
    unittest.main()
