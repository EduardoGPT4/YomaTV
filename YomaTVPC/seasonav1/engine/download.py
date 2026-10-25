from __future__ import annotations

import hashlib
import json
import os
import queue
import re
import subprocess
import sys
import threading
import time
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import imageio_ffmpeg

from .catalog import Cancelled, Catalog, DownloadError, Episode, USER_AGENT, load_catalog, supported_mirrors
from .storage import FileLock, write_json
from .validation import verify_video


@dataclass
class Progress:
    episode: str
    server: str
    downloaded: int = 0
    total: int = 0
    speed: float = 0
    percent: float = 0
    message: str = ""
    eta: float | None = None


def worker_command():
    if getattr(sys, "frozen", False):
        return [sys.executable, "--worker"]
    executable = Path(sys.executable)
    if executable.name.lower() == "pythonw.exe":
        executable = executable.with_name("python.exe")
    return [str(executable), "-X", "utf8", "-m", "seasonav1", "--worker"]


def classify_failure(message):
    lower = message.lower()
    permanent = ("404", "410", "has been deleted", "file was deleted", "not found", "removed", "unsupported url", "no video formats", "403", "forbidden")
    temporary = ("timed out", "timeout", "connection", "resolve", "getaddrinfo", "11001", "name resolution", "dns", "429", "500", "502", "503", "504", "reset", "temporar", "network", "incomplete read")
    if any(word in lower for word in permanent):
        return DownloadError("MP4Upload no permite acceder al archivo o ya no está disponible. " + message)
    return DownloadError(message, retryable=any(word in lower for word in temporary))


def safe_name(value: str) -> str:
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value).strip(" .")[:110]
    if not value or re.fullmatch(r"(?i)(CON|PRN|AUX|NUL|COM\d|LPT\d)(?:\..*)?", value):
        value = "anime_" + value
    return value


def file_number(number: str) -> str:
    whole, dot, fraction = number.partition(".")
    return whole.zfill(3) + dot + fraction


def stop_process(process):
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       creationflags=subprocess.CREATE_NO_WINDOW, timeout=10, check=False)
    else:
        import signal
        os.killpg(process.pid, signal.SIGTERM)
    if process.poll() is None:
        process.kill()
    process.wait(timeout=10)


def run_download(command: list[str], episode: str, server: str, cancel: threading.Event,
                 report: Callable[[Progress], None]) -> Path:
    if cancel.is_set():
        raise Cancelled("Descarga cancelada; puedes reanudarla con la misma carpeta y servidor.")
    options = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {"start_new_session": True}
    lines: queue.Queue[str | None] = queue.Queue()
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, encoding="utf-8", errors="replace", **options)

    def read_output():
        try:
            for line in process.stdout:
                lines.put(line.strip())
        finally:
            process.stdout.close()
            lines.put(None)

    reader = threading.Thread(target=read_output, daemon=True)
    reader.start()
    output = None
    errors = []
    ended = False
    try:
        while not ended or process.poll() is None:
            if cancel.is_set():
                raise Cancelled("Descarga cancelada. Los archivos parciales quedan guardados para reanudar.")
            try:
                line = lines.get(timeout=0.15)
            except queue.Empty:
                continue
            if line is None:
                ended = True
            elif line.startswith("__PROGRESS__"):
                values = line.removeprefix("__PROGRESS__").split("|")
                try:
                    downloaded, total, estimate, speed, fragment, fragments = [float(v) if v not in ("NA", "None", "") else 0 for v in values]
                    total = total or estimate
                    percent = 100 * fragment / fragments if fragments else (100 * downloaded / total if total else 0)
                    eta = max(0, (total - downloaded) / speed) if total and speed else None
                    report(Progress(episode, server, int(downloaded), int(total), speed, min(100, percent), "Descargando", eta))
                except (ValueError, ZeroDivisionError):
                    pass
            elif line.startswith("__FILE__"):
                output = Path(line.removeprefix("__FILE__"))
            elif line:
                errors.append(line)
                errors = errors[-12:]
                report(Progress(episode, server, message=line))
        if process.wait() != 0:
            raise classify_failure("\n".join(errors[-5:]) or "El servidor no permitió descargar el video.")
        if not output or not output.is_file() or output.stat().st_size < 1024:
            raise DownloadError("El servidor no produjo un archivo de video completo.")
        return output
    finally:
        stop_process(process)
        reader.join(timeout=2)


def download_episode(catalog: Catalog, episode: Episode, destination: Path,
                     language: str = "SUB", server: str = "MP4Upload",
                     cancel: threading.Event | None = None,
                     report: Callable[[Progress], None] = lambda _: None) -> Path:
    cancel = cancel if cancel is not None else threading.Event()
    if cancel.is_set():
        raise Cancelled("Descarga cancelada.")
    if server != "MP4Upload":
        raise DownloadError("El único servidor de descarga habilitado es MP4Upload.")
    folder = destination.resolve() / safe_name(catalog.slug)
    chapters = folder / "capitulos"
    files = folder / "archivos"
    chapters.mkdir(parents=True, exist_ok=True)
    files.mkdir(parents=True, exist_ok=True)
    stem = f"{safe_name(catalog.slug)} - {file_number(episode.number)} [{safe_name(language)}]"
    output_path = chapters / (stem + ".mp4")
    metadata_path = files / (stem + ".json")
    legacy_path = folder / (stem + ".mp4")
    with ExitStack() as locks:
        locks.enter_context(FileLock(files / ("." + stem + ".lock")))
        # Respetar los bloqueos anteriores sin crear auxiliares junto a los videos.
        legacy_lock = folder / ("." + stem + ".lock")
        if legacy_lock.exists():
            locks.enter_context(FileLock(legacy_lock))
        return _download_locked(catalog, episode, destination, language, server, cancel, report,
                                output_path, metadata_path, legacy_path, files)


def _download_locked(catalog, episode, destination, language, server, cancel, report,
                     output_path, metadata_path, legacy_path, files):
    existing = output_path if output_path.exists() else legacy_path
    if existing.exists():
        report(Progress(episode.number, server, message="Verificando archivo existente…"))
        try:
            cache = metadata_path if metadata_path.exists() else existing.with_suffix(".json")
            verification = verify_video(existing, cancel, metadata_path=cache)
        except Cancelled:
            raise
        except DownloadError as exc:
            # Nunca sobrescribir el archivo que no superó la verificación.
            invalid = files / "invalidos"
            invalid.mkdir(exist_ok=True)
            preserved = invalid / (existing.stem + f".invalido-{time.time_ns()}.mp4")
            existing.rename(preserved)
            report(Progress(episode.number, server, message=f"Se conserva el archivo no válido como {preserved.name}: {exc}"))
        else:
            save_metadata(existing, catalog, episode, language, verification, metadata_path)
            report(Progress(episode.number, server, percent=100, message=f"Ya verificado: {existing.name}"))
            return existing
    report(Progress(episode.number, server, message="Leyendo los servidores del capítulo…"))
    fresh = load_catalog(episode.url)
    candidates = supported_mirrors(fresh, language, server)
    if not candidates:
        raise DownloadError(f"Este capítulo no tiene un enlace compatible de MP4Upload para {language}.")
    failures = []
    for mirror in candidates:
        if cancel.is_set():
            raise Cancelled("Descarga cancelada.")
        identity = f"{episode.url}|{language}|{mirror.server}|{mirror.url}"
        identity = hashlib.sha256(identity.encode()).hexdigest()[:20]
        work = files / "parciales" / identity
        legacy_work = destination.resolve() / ".animeav1-work" / identity
        # Continuar un parcial anterior evita volver a bajar los mismos bytes.
        if legacy_work.is_dir() and any(p.is_file() and not p.name.startswith("video.invalido-")
                                        for p in legacy_work.glob("video.*")):
            work = legacy_work
        work.mkdir(parents=True, exist_ok=True)
        lock = FileLock(work / ".lock").acquire()
        try:
            ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
            command = [*worker_command(),
                       "--ignore-config", "--no-playlist", "--no-simulate", "--newline", "--progress", "--no-color",
                       "--socket-timeout", "20", "--retries", "5", "--fragment-retries", "5",
                       "--extractor-retries", "3", "--retry-sleep", "http:exp=2:20",
                       "--retry-sleep", "extractor:exp=2:10", "--retry-sleep", "fragment:exp=2:20",
                       "--concurrent-fragments", "1", "--abort-on-unavailable-fragments",
                       "--continue", "--no-overwrites", "--fixup", "force",
                       "--remux-video", "mp4", "--ffmpeg-location", ffmpeg,
                       "--user-agent", USER_AGENT, "--referer", mirror.url,
                       "--output", str(work / "video.%(ext)s"),
                       "--progress-template", "download:__PROGRESS__%(progress.downloaded_bytes)s|%(progress.total_bytes)s|%(progress.total_bytes_estimate)s|%(progress.speed)s|%(progress.fragment_index)s|%(progress.fragment_count)s",
                       "--print", "after_move:__FILE__%(filepath)s", mirror.url]
            report(Progress(episode.number, mirror.server, message=f"Conectando con {mirror.server}…"))
            downloaded = run_download(command, episode.number, mirror.server, cancel, report)
            if cancel.is_set():
                raise Cancelled("Descarga cancelada antes de guardar el archivo final.")
            if downloaded.resolve().parent != work.resolve():
                raise DownloadError("El descargador devolvió una ubicación inesperada.")
            report(Progress(episode.number, mirror.server, message="Verificando audio y video descargados…"))
            try:
                verification = verify_video(downloaded, cancel)
            except Cancelled:
                raise
            except DownloadError:
                downloaded.rename(downloaded.with_name(f"video.invalido-{time.time_ns()}.mp4"))
                raise
            # En Windows rename nunca sobrescribe un archivo existente.
            if output_path.exists():
                raise DownloadError(f"Ya existe un archivo con el nombre {output_path.name}.")
            downloaded.rename(output_path)
            try:
                save_metadata(output_path, catalog, episode, language, verification, metadata_path)
            except OSError:
                report(Progress(episode.number, mirror.server, message="Video guardado; no se pudo escribir su ficha JSON."))
            report(Progress(episode.number, mirror.server, percent=100, message=f"Completado: {output_path.name}"))
            return output_path
        except Cancelled:
            raise
        except (DownloadError, OSError, RuntimeError) as exc:
            failures.append(exc)
            report(Progress(episode.number, mirror.server, message=f"Falló {mirror.server}: {exc}"))
        finally:
            lock.close()
    raise DownloadError("No se pudo completar el capítulo.\n" + "\n".join(str(e) for e in failures),
                        retryable=any(getattr(e, "retryable", False) for e in failures))


def save_metadata(path, catalog, episode, language, verification, metadata_path):
    metadata = {"title": catalog.title, "episode": episode.number, "language": language,
                "page": episode.url, "server": "MP4Upload", "bytes": path.stat().st_size,
                "completed_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "verification": verification}
    write_json(metadata_path, metadata)
