"""Estado local atómico y bloqueos liberados automáticamente por el sistema."""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

from .catalog import DownloadError


def app_directory() -> Path:
    return Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent


def data_directory() -> Path:
    return Path(os.environ.get("ANIMEAV1_DATA_DIR", str(app_directory() / "datos"))).resolve()


def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def read_json(path: Path, default=None):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:
        raise DownloadError(f"No se pudo leer {path.name}. Conserva ese archivo para recuperarlo: {exc}") from exc


class FileLock:
    def __init__(self, path: Path):
        self.path = path
        self.stream = None

    def acquire(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        stream = self.path.open("a+b")
        if stream.tell() == 0:
            stream.write(b"0")
            stream.flush()
        stream.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            stream.close()
            raise DownloadError("Otra instancia está usando esta sesión o descarga. Cierra esa instancia antes de continuar.") from exc
        self.stream = stream
        return self

    def close(self):
        if self.stream is not None:
            self.stream.close()
            self.stream = None

    def __enter__(self):
        return self.acquire()

    def __exit__(self, *_):
        self.close()


class Store:
    def __init__(self, directory: Path | None = None):
        self.directory = directory if directory is not None else data_directory()
        self.directory.mkdir(parents=True, exist_ok=True)
        self.lock = FileLock(self.directory / "session.lock").acquire()

    def preferences(self):
        value = read_json(self.directory / "preferences.json", {})
        if not isinstance(value, dict):
            raise DownloadError("El archivo de preferencias tiene un formato inválido.")
        return value

    def save_preferences(self, preferences):
        write_json(self.directory / "preferences.json", preferences)

    def load_session(self):
        return read_json(self.directory / "session.json")

    def save_session(self, session):
        write_json(self.directory / "session.json", session)

    def log(self, message):
        from datetime import datetime
        with (self.directory / "registro.log").open("a", encoding="utf-8") as stream:
            stream.write(f"{datetime.now().astimezone().isoformat(timespec='seconds')} {message}\n")

    def close(self):
        self.lock.close()
