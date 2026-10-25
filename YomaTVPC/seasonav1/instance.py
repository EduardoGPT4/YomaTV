"""Una bandeja y una ventana por carpeta de datos, con mensajes locales."""
from __future__ import annotations

import hmac
import json
import os
import queue
import secrets
import socket
import threading
import time
from pathlib import Path

from .engine.catalog import DownloadError
from .engine.storage import FileLock, write_json


def send(directory: Path, role: str, command: dict, timeout=0.5):
    try:
        endpoint = json.loads((directory / f"{role}-instance.json").read_text(encoding="utf-8"))
        if role == "window" and os.name == "nt":
            import ctypes
            ctypes.windll.user32.AllowSetForegroundWindow(endpoint["pid"])
        message = json.dumps({"token": endpoint["token"], "command": command}).encode() + b"\n"
        with socket.create_connection(("127.0.0.1", endpoint["port"]), timeout=timeout) as client:
            client.sendall(message)
            return client.recv(16) == b"ok\n"
    except (OSError, ValueError, KeyError, TypeError):
        return False


class Instance:
    def __init__(self, directory: Path, role: str):
        self.directory, self.role = directory, role
        self.lock = FileLock(directory / f"{role}-instance.lock")
        self.path = directory / f"{role}-instance.json"
        self.commands = queue.Queue()
        self.closed = threading.Event()
        self.owner = False
        self.server = self.listener = self.dispatcher = None

    def claim(self, command: dict, timeout=10):
        deadline = time.monotonic() + timeout
        while True:
            try:
                self.lock.acquire()
                break
            except DownloadError:
                if send(self.directory, self.role, command):
                    return False
                if time.monotonic() >= deadline:
                    raise RuntimeError("La instancia abierta no responde. Espera a que termine de iniciarse y vuelve a intentarlo.")
                time.sleep(0.1)
        self.owner = True
        try:
            self.server = socket.socket()
            self.server.bind(("127.0.0.1", 0))
            self.server.listen(8)
            self.token = secrets.token_hex(32)
            write_json(self.path, {"port": self.server.getsockname()[1], "token": self.token, "pid": os.getpid()})
            self.listener = threading.Thread(target=self._listen, name=f"SeasonAV1-{self.role}-messages", daemon=True)
            self.listener.start()
            return True
        except Exception:
            self.close()
            raise

    def _listen(self):
        while not self.closed.is_set():
            try:
                client, _ = self.server.accept()
            except OSError:
                break
            with client:
                client.settimeout(2)
                try:
                    data = b""
                    while b"\n" not in data and len(data) <= 4096 and not self.closed.is_set():
                        block = client.recv(4096)
                        if not block:
                            break
                        data += block
                    message = json.loads(data)
                    token = message.get("token", "")
                    command = message.get("command")
                    if isinstance(token, str) and hmac.compare_digest(token, self.token) and isinstance(command, dict):
                        self.commands.put(command)
                        client.sendall(b"ok\n")
                except (OSError, ValueError, AttributeError):
                    pass

    def dispatch(self, handler):
        def work():
            while True:
                command = self.commands.get()
                if command is None:
                    return
                handler(command)
        self.dispatcher = threading.Thread(target=work, name="SeasonAV1-tray-commands", daemon=True)
        self.dispatcher.start()

    def close(self):
        self.closed.set()
        self.commands.put(None)
        if self.server is not None:
            # Despierta accept sin consultar periódicamente el disco ni la red.
            try:
                with socket.create_connection(self.server.getsockname(), timeout=0.3):
                    pass
            except OSError:
                pass
            if self.listener is not None:
                self.listener.join(timeout=3)
            self.server.close()
        if self.owner:
            self.path.unlink(missing_ok=True)
            self.lock.close()
            self.owner = False

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
