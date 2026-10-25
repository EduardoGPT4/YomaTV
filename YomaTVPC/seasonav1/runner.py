from __future__ import annotations

import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, replace
from datetime import date, datetime
from decimal import Decimal

from .config import Config, season_folder
from .brand import APP_NAME
from .database import Database
from .downloader import PreferenceUnavailable, download_job
from .engine.catalog import Cancelled, DownloadError, parse_page
from .engine.storage import FileLock
from .http import HttpClient
from .schedule import SCHEDULE_URL, ScheduledAnime, due_date, missed_weekdays, parse_schedule
from .web_controls import GroupToken


class Runner:
    def __init__(self, directory, notify=lambda *_: None, token=None, now=None, client_factory=HttpClient,
                 downloader=download_job, retry_delays=(10, 30, 90)):
        self.directory = directory
        self.db = Database(directory)
        self.cfg = Config.load(directory)
        self.notify = notify
        self.token = token if token is not None else threading.Event()
        self.now = now or datetime.now().astimezone()
        self.client = client_factory(self.db, self.token, self.cfg.request_interval)
        self.downloader, self.retry_delays = downloader, retry_delays
        self.failed_notifications = 0
        self.notification_lock = threading.Lock()

    def log(self, level, message, job=None):
        self.db.log(level, message, job["slug"] if job else None, job["number"] if job else None)

    def notify_error(self, message):
        with self.notification_lock:
            self.failed_notifications += 1
            if self.failed_notifications <= 4 and self.cfg.notifications:
                self.notify(APP_NAME + " · Error", message)

    def plan(self, force=False, dry_run=False):
        bootstrap = not self.db.meta("initialized", False)
        checkpoint = due_date(self.now, self.cfg.review_time)
        previous = self.db.meta("last_review")
        weekdays = missed_weekdays(previous, checkpoint)
        if force:
            weekdays = set(range(1,8))
        retry_scans = set(self.db.meta("scan_failures", []))
        if not bootstrap and not weekdays and not force and not retry_scans:
            return {"items": [], "selected": 0, "checkpoint": str(checkpoint), "initial": False, "skipped": True}
        schedule = parse_schedule(self.client.fetch(SCHEDULE_URL))
        selected = [a for a in schedule if self.cfg.accepts(a.slug)]
        historical = set()
        if retry_scans or (previous and (checkpoint-date.fromisoformat(previous)).days>1):
            current = {a.slug for a in schedule}
            for old in self.db.query("SELECT * FROM anime WHERE initialized=1"):
                if old["slug"] not in current and (old["weekday"] in weekdays or old["slug"] in retry_scans) and self.cfg.accepts(old["slug"]):
                    selected.append(ScheduledAnime(old["slug"],old["title"],old["weekday"],old["latest"] or "0","",old["start_date"]))
                    historical.add(old["slug"])
        items, failures = [], []
        if not dry_run:
            self.db.set_meta("weekly_schedule", [asdict(a) for a in schedule])
            with self.db.transaction() as connection:
                connection.execute("UPDATE anime SET active=0")
        for anime in selected:
            old = self.db.anime(anime.slug)
            season = old["season"] if old else season_folder(self.now.date())
            if not old and self.cfg.season_source == "premiere" and anime.start_date:
                try: season = season_folder(date.fromisoformat(anime.start_date))
                except ValueError: pass
            changed = old is not None and old["latest"] != anime.latest
            needs_catalog = not old or not old["initialized"] or (not bootstrap and anime.weekday in weekdays) or changed or anime.slug in retry_scans
            if not dry_run:
                if needs_catalog:
                    scans=set(self.db.meta("scan_failures",[]));scans.add(anime.slug)
                    self.db.set_meta("scan_failures",sorted(scans))
                self.db.upsert_anime(anime, season)
                if anime.slug in historical:
                    with self.db.transaction() as connection:
                        connection.execute("UPDATE anime SET active=0 WHERE slug=?",(anime.slug,))
            if not needs_catalog:
                continue
            if self.token.is_set():
                raise Cancelled("Revisión pausada.")
            try:
                catalog = parse_page(self.client.fetch(anime.url), anime.url)
                for episode in catalog.episodes:
                    if not self.db.completed(anime.slug, episode.number, self.cfg.language):
                        episode_season = season_folder(self.now.date()) if self.cfg.long_series == "split" else season
                        items.append({"slug": anime.slug, "title": anime.title, "number": episode.number,
                                      "url": episode.url, "language": self.cfg.language, "season": episode_season})
                        if not dry_run:
                            self.db.add_episode(anime.slug, episode, self.cfg.language, episode_season, bootstrap)
                if not dry_run:
                    self.db.mark_catalog(anime.slug)
                    scans=set(self.db.meta("scan_failures",[]));scans.discard(anime.slug)
                    self.db.set_meta("scan_failures",sorted(scans))
            except Cancelled:
                raise
            except DownloadError as exc:
                failures.append(anime.slug)
                if not dry_run:
                    self.log("error", f"No se pudo revisar {anime.title}: {exc}")
                    self.notify_error(f"No se pudo revisar {anime.title}: {exc}")
                else:
                    self.log("warning", f"Prueba: no se pudo revisar {anime.title}: {exc}")
        if not dry_run:
            self.db.set_meta("scan_failures", failures)
            if not failures:
                self.db.set_meta("initialized", True)
                self.db.set_meta("last_review", str(checkpoint))
        return {"items": items, "selected": len(selected), "checkpoint": str(checkpoint), "initial": bootstrap,
                "failures": failures, "requests": self.client.requests, "weekdays": sorted(weekdays)}

    def run(self, force=False, dry_run=False, queue_only=False):
        self.failed_notifications=0
        with FileLock(self.directory / "review.lock"):
            if self.cfg.paused and not dry_run:
                return {"paused": True, "downloaded": 0}
            if not dry_run:
                self.db.recover()
                if force:
                    with self.db.transaction() as connection:
                        connection.execute("UPDATE episodes SET next_retry=0 WHERE status='failed'")
                self.db.set_meta("running", {"started": time.time(), "phase": "review"})
            stopped = threading.Event()

            def monitor():
                while not stopped.wait(1):
                    try:
                        if Config.load(self.directory).paused:
                            self.token.set()
                    except Exception:
                        pass
            watcher = threading.Thread(target=monitor, daemon=True)
            if not dry_run: watcher.start()
            try:
                queue_only = queue_only or (not self.cfg.schedule_enabled and not force)
                plan = {"items":[],"failures":[]} if queue_only else self.plan(force, dry_run)
                if dry_run:
                    return plan
                web_ids=self.db.requested_episode_ids()
                pending = [j for j in self.db.pending() if (self.cfg.accepts(j["slug"]) or j["id"] in web_ids)
                           and j["slug"] not in self.cfg.exclusions and (j["language"] == self.cfg.language or j["id"] in web_ids)]
                groups = {}
                for job in pending:
                    groups.setdefault(job["slug"], []).append(job)
                for group in groups.values():
                    group.sort(key=lambda j: Decimal(j["number"]))
                # El primer lote siempre es secuencial, aunque se permitan varias descargas después.
                workers = 1 if not self.db.meta("bootstrap_processed",False) and any(j["bootstrap"] for j in pending) else self.cfg.workers
                self.db.set_meta("running", {"started": time.time(), "phase": "download", "total": len(pending), "workers": workers})
                downloaded = 0

                def process(group):
                    complete = 0
                    token=GroupToken(self.token,self.db,group[0]['slug'])
                    for job in group:
                        if token.is_set(): break
                        if self.process_job(job, workers, token): complete += 1
                    return complete

                remaining=dict(groups);claim_lock=threading.Lock()
                def worker():
                    complete=0
                    while not self.token.is_set():
                        with claim_lock:
                            controls={slug:self.db.group_control(slug) for slug in remaining}
                            ready=[slug for slug in remaining if not controls[slug]['paused']]
                            if not ready:break
                            slug=min(ready,key=lambda s:-controls[s]['priority'])
                            group=remaining.pop(slug)
                        complete+=process(group)
                    return complete
                with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="SeasonAV1") as pool:
                    futures = [pool.submit(worker) for _ in range(min(workers,len(groups)))]
                    for future in as_completed(futures):
                        downloaded += future.result()
                result = {"downloaded": downloaded, "failed": self.failed_notifications, "paused": self.token.is_set(),
                          "planned": len(plan["items"]), "requests": self.client.requests}
                if not queue_only and not self.token.is_set() and not plan.get("failures"):
                    self.db.set_meta("bootstrap_processed",True)
                self.log("info", f"Revisión terminada: {downloaded} capítulos descargados; {self.failed_notifications} incidencias.")
                if self.cfg.notifications and (downloaded or self.failed_notifications):
                    self.notify(APP_NAME, f"Revisión terminada: {downloaded} capítulos descargados, {self.failed_notifications} incidencias.")
                return result
            except Cancelled:
                self.log("info", "Cola pausada; se conservan los parciales.")
                return {"paused": True, "downloaded": 0}
            except Exception as exc:
                self.log("error", str(exc))
                self.notify_error(str(exc))
                raise
            finally:
                stopped.set()
                if not dry_run:
                    watcher.join(timeout=2)
                    self.db.set_meta("running", None)

    def process_job(self, job, workers, token=None):
        token=token or self.token
        last_progress = 0

        def report(progress):
            nonlocal last_progress
            if progress.message == "Descargando":
                if time.monotonic() - last_progress >= 2:
                    self.db.update(job["id"], progress=progress.percent)
                    last_progress = time.monotonic()
            elif progress.message.startswith("Verificando"):
                self.db.update(job["id"], status="verifying")

        for attempt in range(len(self.retry_delays) + 1):
            if token.is_set():
                self.db.update(job["id"], status="paused")
                return False
            job["attempts"] += 1
            self.db.update(job["id"], status="downloading", attempts=job["attempts"], error="")
            try:
                outcome = self.downloader(job, replace(self.cfg,language=job['language']), self.client, token, report, workers)
                verified = outcome.verification
                self.db.update(job["id"], status="completed", path=str(outcome.path), actual_language=outcome.language,
                               server=outcome.server, bytes=verified["bytes"], sha256=verified["sha256"],
                               verification=json.dumps(verified), completed_at=datetime.now().astimezone().isoformat(),
                               next_retry=0, progress=100, error="")
                self.log("info", f"Capítulo {job['number']} de {job['title']} descargado: {outcome.path}", job)
                if outcome.warning:
                    self.log("warning", outcome.warning, job)
                if self.cfg.notifications:
                    self.notify(APP_NAME + " · Descarga completa", f"Capítulo {job['number']} de {job['title']} descargado")
                return True
            except Cancelled:
                self.db.update(job["id"], status="paused")
                return False
            except (DownloadError, OSError) as exc:
                self.log("warning", f"{job['title']} / {job['number']}: {exc}", job)
                if getattr(exc, "retryable", False) and attempt < len(self.retry_delays):
                    self.db.update(job["id"], status="pending", error=str(exc))
                    if token.wait(self.retry_delays[attempt]):
                        self.db.update(job["id"], status="paused")
                        return False
                    continue
                wait = 86400 if isinstance(exc, PreferenceUnavailable) or not getattr(exc, "retryable", False) else min(86400, 300 * 2 ** min(job["attempts"], 8))
                self.db.update(job["id"], status="failed", error=str(exc), next_retry=time.time() + wait)
                self.log("error",f"{job['title']} / {job['number']}: {exc}",job)
                self.notify_error(f"{job['title']} / {job['number']}: {exc}")
                return False
        return False

    def close(self):
        self.db.close()
