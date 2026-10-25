"""Lectura completa de paquetes, muestras decodificadas y huella SHA-256."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import threading
from pathlib import Path

import imageio_ffmpeg

from .catalog import Cancelled, DownloadError


def check_cancel(cancel):
    if cancel.is_set():
        raise Cancelled("Verificación interrumpida; el video se conserva.")


def ffmpeg_check(args, cancel, timeout=300):
    import time
    from .download import stop_process
    options = {"creationflags": subprocess.CREATE_NO_WINDOW} if hasattr(subprocess, "CREATE_NO_WINDOW") else {"start_new_session": True}
    process = subprocess.Popen([imageio_ffmpeg.get_ffmpeg_exe(), "-nostdin", "-threads", "2", *args],
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, **options)
    deadline = time.monotonic() + timeout
    try:
        while True:
            check_cancel(cancel)
            if time.monotonic() > deadline:
                raise DownloadError("La verificación superó el tiempo máximo. El archivo se conserva para revisión.")
            try:
                output, _ = process.communicate(timeout=0.2)
                break
            except subprocess.TimeoutExpired:
                pass
        text = output.decode("utf-8", errors="replace")
        if process.returncode != 0:
            raise DownloadError("El video está incompleto o no se puede leer: " + text[-1200:])
        return text
    finally:
        stop_process(process)
        if process.stdout:
            process.stdout.close()


def verify_video(path: Path, cancel=None, *, metadata_path: Path | None = None) -> dict:
    cancel = cancel if cancel is not None else threading.Event()
    check_cancel(cancel)
    before = path.stat()
    if before.st_size < 1024:
        raise DownloadError("El archivo es demasiado pequeño para ser un video completo.")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            check_cancel(cancel)
            digest.update(chunk)
    sha256 = digest.hexdigest()
    try:
        metadata = json.loads((metadata_path if metadata_path is not None else path.with_suffix(".json")).read_text(encoding="utf-8"))
        cached = metadata.get("verification", {})
    except (ValueError, OSError, AttributeError):
        cached = {}
    if isinstance(cached, dict) and cached.get("version") == 1 and cached.get("sha256") == sha256 and cached.get("bytes") == before.st_size:
        return cached
    # Se exige una pista de video y una de audio para los capítulos de anime.
    text = ffmpeg_check(["-hide_banner", "-nostats", "-xerror", "-i", str(path),
                         "-map", "0:v:0", "-map", "0:a:0", "-c", "copy", "-f", "null", "-"], cancel)
    duration_match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", text)
    if not duration_match:
        raise DownloadError("No se pudo comprobar la duración del video.")
    hours, minutes, seconds = map(float, duration_match.groups())
    duration = hours * 3600 + minutes * 60 + seconds
    if duration <= 0:
        raise DownloadError("La duración del video es inválida.")
    for start in sorted({0, round(duration / 2, 2), max(0, round(duration - 3, 2))}):
        ffmpeg_check(["-v", "error", "-xerror", "-ss", str(start), "-i", str(path),
                      "-t", "2", "-map", "0:v:0", "-map", "0:a:0", "-f", "null", "-"], cancel)
    after = path.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise DownloadError("El archivo cambió durante la verificación. Vuelve a intentarlo.")
    dimensions = re.search(r"Video:[^\n]*?\b(\d{2,5})x(\d{2,5})\b", text)
    return {"version": 1, "sha256": sha256, "bytes": before.st_size, "duration": duration,
            "width": int(dimensions.group(1)) if dimensions else None,
            "height": int(dimensions.group(2)) if dimensions else None,
            "method": "complete_packet_scan_and_three_decoded_samples"}
