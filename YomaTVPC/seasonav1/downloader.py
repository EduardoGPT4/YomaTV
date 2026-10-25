from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path

import imageio_ffmpeg

from .engine.catalog import Cancelled, DownloadError, USER_AGENT, parse_page
from .engine.download import Progress, run_download, safe_name, worker_command
from .engine.storage import FileLock, write_json
from .engine.validation import verify_video


class PreferenceUnavailable(DownloadError):
    pass


@dataclass
class Outcome:
    path: Path
    language: str
    server: str
    verification: dict
    warning: str = ""


def episode_name(title, number, language):
    whole, dot, fraction = number.partition(".")
    return f"{safe_name(title)[:85]} - {whole.zfill(4)}{dot}{fraction} [{language}].mp4"


def anime_directory(slug):
    clean=safe_name(slug)
    return clean if len(slug)<=90 else clean[:80]+"-"+hashlib.sha256(slug.encode()).hexdigest()[:8]


def choices(catalog, cfg):
    supported = [m for m in catalog.mirrors if m.kind == "embeds" and m.server in {"MP4Upload", "Voe"}]
    if cfg.server_fallback != "other":
        supported = [m for m in supported if m.server == cfg.server]
    language = cfg.language
    if not any(m.language.upper() == language for m in supported) and cfg.language_fallback == "SUB":
        language = "SUB"
    supported = [m for m in supported if m.language.upper() == language]
    if not supported:
        raise PreferenceUnavailable(f"Sin {cfg.server} / {cfg.language} según las alternativas configuradas. Se comprobará de nuevo en otra revisión.")
    return sorted(supported, key=lambda m: m.server != cfg.server)


def quality_check(verification, cfg):
    height = verification.get("height")
    if cfg.quality_fallback == "wait" and height != cfg.height:
        raise PreferenceUnavailable(f"Se solicitó {cfg.height}p exacto, pero la fuente es {height or 'de resolución desconocida'}. Se conserva el parcial completo.")
    if cfg.quality_fallback == "lower" and (not height or height > cfg.height):
        raise PreferenceUnavailable(f"La fuente no cumple el límite de {cfg.height}p. Se conserva el archivo para otra revisión.")
    return f"La fuente disponible es {height}p; se aceptó según la configuración." if height and height != cfg.height else ""


def download_job(job, cfg, client, token, report=lambda _: None, workers=1):
    folder = Path(cfg.destination) / job["season"] / anime_directory(job["slug"])
    files = folder / "archivos"
    files.mkdir(parents=True, exist_ok=True)
    job_key = hashlib.sha256(f"{job['url']}|{job['language']}".encode()).hexdigest()[:20]
    with FileLock(files / (job_key + ".lock")):
        languages = [cfg.language] + (["SUB"] if cfg.language_fallback == "SUB" and cfg.language != "SUB" else [])
        for language in languages:
            target = folder / episode_name(job["title"], job["number"], language)
            metadata_path = files / target.with_suffix(".json").name
            if not target.exists():
                continue
            report(Progress(job["number"], cfg.server, message="Verificando archivo existente…"))
            try:
                verification = verify_video(target, token, metadata_path=metadata_path)
                warning = quality_check(verification, cfg)
                try: metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                except (OSError, ValueError): metadata = {}
                return Outcome(target, language, metadata.get("server", cfg.server), verification, warning)
            except Cancelled:
                raise
            except PreferenceUnavailable:
                raise
            except DownloadError:
                invalid = files / "invalidos"
                invalid.mkdir(exist_ok=True)
                target.rename(invalid / (target.stem + f".{time.time_ns()}.mp4"))
        catalog = parse_page(client.fetch(job["url"]), job["url"])
        failures = []
        for mirror in choices(catalog, cfg):
            if token.is_set():
                raise Cancelled("Descarga pausada.")
            language = mirror.language.upper()
            target = folder / episode_name(job["title"], job["number"], language)
            identity = hashlib.sha256(f"{job['url']}|{language}|{mirror.url}".encode()).hexdigest()[:20]
            work = files / "parciales" / identity
            work.mkdir(parents=True, exist_ok=True)
            try:
                with FileLock(work / ".lock"):
                    command = [*worker_command(), "--ignore-config", "--no-playlist", "--no-simulate", "--newline",
                               "--progress", "--no-color", "--socket-timeout", "25", "--retries", "5", "--extractor-retries", "3",
                               "--fragment-retries", "5", "--retry-sleep", "http:exp=2:30", "--retry-sleep", "extractor:exp=2:15",
                               "--retry-sleep", "fragment:exp=2:30", "--concurrent-fragments", "1", "--abort-on-unavailable-fragments",
                               "--continue", "--no-overwrites", "--fixup", "force", "--remux-video", "mp4",
                               "--ffmpeg-location", imageio_ffmpeg.get_ffmpeg_exe(), "--user-agent", USER_AGENT, "--referer", mirror.url,
                               "--format", f"bv*[height={cfg.height}]+ba/b[height={cfg.height}]/bv*[height<=?{cfg.height}]+ba/b[height<=?{cfg.height}]/b",
                               "--output", str(work / "video.%(ext)s"),
                               "--progress-template", "download:__PROGRESS__%(progress.downloaded_bytes)s|%(progress.total_bytes)s|%(progress.total_bytes_estimate)s|%(progress.speed)s|%(progress.fragment_index)s|%(progress.fragment_count)s",
                               "--print", "after_move:__FILE__%(filepath)s"]
                    if cfg.speed_kib:
                        command.extend(["--limit-rate", str(max(1, cfg.speed_kib * 1024 // workers))])
                    command.append(mirror.url)
                    report(Progress(job["number"], mirror.server, message=f"Conectando con {mirror.server}…"))
                    downloaded = run_download(command, job["number"], mirror.server, token, report)
                    if downloaded.resolve().parent != work.resolve():
                        raise DownloadError("Ubicación de descarga inesperada.")
                    report(Progress(job["number"], mirror.server, message="Verificando audio y video…"))
                    try:
                        verification = verify_video(downloaded, token, metadata_path=work / "verification.json")
                    except Cancelled:
                        raise
                    except DownloadError:
                        invalid = files / "invalidos"
                        invalid.mkdir(exist_ok=True)
                        downloaded.rename(invalid / (downloaded.stem + f".{time.time_ns()}.mp4"))
                        raise
                    write_json(work / "verification.json", {"verification": verification})
                    warning = quality_check(verification, cfg)
                    if token.is_set():
                        raise Cancelled("Descarga pausada antes de guardar.")
                    if target.exists():
                        raise DownloadError("El archivo final ya existe; no se sobrescribe.")
                    downloaded.rename(target)
                    try:
                        write_json(files / target.with_suffix(".json").name,
                                   {"title": job["title"], "episode": job["number"], "language": language,
                                    "server": mirror.server, "page": job["url"], "verification": verification})
                    except OSError:
                        warning = (warning + " Video verificado; no se pudo escribir su ficha JSON.").strip()
                    return Outcome(target, language, mirror.server, verification, warning)
            except Cancelled:
                raise
            except PreferenceUnavailable as exc:
                failures.append(exc)
            except (DownloadError, OSError) as exc:
                failures.append(exc)
        if failures and all(isinstance(exc,PreferenceUnavailable) for exc in failures):
            raise failures[-1]
        raise DownloadError("No se pudo completar el capítulo: " + "; ".join(map(str, failures)),
                            retryable=any(getattr(e, "retryable", False) for e in failures))
