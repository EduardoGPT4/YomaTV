"""Textos breves y clasificación visual de mensajes de la cola."""
from __future__ import annotations

import re


def count_text(count: int, singular: str, plural: str | None = None) -> str:
    return f"{count} {singular if count == 1 else (plural or singular + 's')}"


def short_failure(message: str) -> str:
    lower = message.lower()
    if any(word in lower for word in ("getaddrinfo", "11001", "resolve", "name resolution", "dns",
                                      "sin conexión", "no se pudo conectar", "network", "connection")):
        return "sin conexión"
    if "timeout" in lower or "timed out" in lower:
        return "tiempo agotado"
    if "429" in lower:
        return "servidor saturado"
    if "403" in lower or "forbidden" in lower:
        return "acceso rechazado"
    if any(word in lower for word in ("404", "410", "deleted", "not found", "no está disponible")):
        return "archivo no disponible"
    if "no tiene un enlace" in lower:
        return "sin MP4Upload para este idioma"
    if any(word in lower for word in ("truncado", "corrupt", "no válido", "verificación", "decodific")):
        return "video no válido"
    if any(word in lower for word in ("500", "502", "503", "504")):
        return "error del servidor"
    # Quitar prefijos internos; el detalle completo permanece en el registro.
    text = re.sub(r"^(?:ERROR:|No se pudo completar el capítulo\.|Falló MP4Upload:)\s*", "", message.strip())
    text = " ".join(text.split()) or "consulta el registro"
    return text[:57] + "…" if len(text) > 58 else text


def log_level(message: str) -> str | None:
    lower = message.lower()
    if "falling back on generic information extractor" in lower:
        return None
    if "no se pudo escribir" in lower:
        return "warning"
    if any(word in lower for word in ("error:", "falló", "fallo", "getaddrinfo", "11001", "failed",
                                      "no se pudo", "sin conexión", "giving up")):
        return "error"
    if any(word in lower for word in ("warning:", "aviso", "no válido", "no se pudo escribir")):
        return "warning"
    return "info"


def progress_text(progress) -> str:
    downloaded = progress.downloaded / 1048576
    amount = f"{downloaded:.1f} / {progress.total / 1048576:.1f} MiB" if progress.total else f"{downloaded:.1f} MiB / tamaño desconocido"
    percent = f"{progress.percent:.1f}% · " if progress.total else ""
    eta = f" · Restante: {int(progress.eta // 60):02d}:{int(progress.eta % 60):02d}" if progress.eta is not None else ""
    return f"Capítulo {progress.episode} · {percent}{amount} · {progress.speed / 1048576:.2f} MiB/s{eta}"
