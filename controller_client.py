"""Tiny helper: send one JSON command to the controller app and return its reply."""
import json
import socket


def send(cmd, host='127.0.0.1', port=9999, timeout=5):
    with socket.create_connection((host, port), timeout=timeout) as s:
        s.sendall(json.dumps(cmd).encode())
        return json.loads(s.recv(4096).decode())
