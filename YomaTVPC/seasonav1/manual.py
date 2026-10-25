"""Descargas por enlace del catálogo completo, en la misma cola de la web."""
from __future__ import annotations

import time
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from .config import Config, season_folder
from .database import Database
from .engine.catalog import Catalog, DownloadError, normalize_url, parse_page
from .engine.storage import FileLock
from .http import HttpClient
from .schedule import ScheduledAnime


def read_catalog(directory: Path, url: str, client_factory=HttpClient) -> Catalog:
    normalized, _, _ = normalize_url(url)
    db = Database(directory)
    try:
        return parse_page(client_factory(db, None, Config.load(directory).request_interval).fetch(normalized), normalized)
    finally:
        db.close()


def enqueue_catalog(directory: Path, catalog: Catalog, numbers, preferences=None):
    # Comprobar todo antes de guardar o pausar; solo capítulos realmente publicados.
    if not isinstance(catalog, Catalog):
        raise ValueError("Analiza primero un enlace de AnimeAV1.")
    normalized, slug, _ = normalize_url(f"https://animeav1.com/media/{catalog.slug}")
    available = {episode.number: episode for episode in catalog.episodes}
    chosen = sorted(set(numbers), key=Decimal)
    if not chosen or any(number not in available for number in chosen):
        raise ValueError("Selecciona capítulos disponibles de este anime.")
    for number in chosen:
        episode_url, episode_slug, episode_number = normalize_url(available[number].url)
        if episode_slug != slug or episode_number != number:
            raise ValueError("La dirección no corresponde al capítulo seleccionado.")
    cfg, old = Config.load(directory), Config.load(directory)
    preferences = preferences or {}
    if not isinstance(preferences, dict) or not set(preferences) <= {'language', 'server', 'height', 'destination'}:
        raise ValueError("Preferencias de descarga inválidas.")
    for key, value in preferences.items():
        setattr(cfg, key, value)
    cfg.validate()
    if slug in cfg.exclusions:
        raise ValueError("Este anime está excluido. Quita su exclusión en Temporada o en la web antes de descargarlo.")
    cfg.configured = True
    paused = Config.load(directory)
    paused.paused = True
    paused.save(directory)
    db = None
    lock = FileLock(directory / 'review.lock')
    try:
        deadline = time.monotonic() + 35
        while True:
            try:
                lock.acquire()
                break
            except DownloadError:
                if time.monotonic() > deadline:
                    raise RuntimeError("La descarga todavía se está pausando. Intenta añadir la selección de nuevo.")
                time.sleep(.2)
        db = Database(directory)
        existing = db.anime(slug)
        season = existing['season'] if existing else season_folder(date.today())
        latest = max([*(available.keys()), str(existing['latest']) if existing else '0'], key=Decimal)
        anime = ScheduledAnime(slug, catalog.title, existing['weekday'] if existing else date.today().isoweekday(), latest,
                               datetime.now().astimezone().isoformat(), existing['start_date'] if existing else None)
        added = 0
        with db.transaction() as connection:
            connection.execute('''INSERT INTO anime(slug,title,weekday,season,start_date,latest,last_seen)
                VALUES(?,?,?,?,?,?,?) ON CONFLICT(slug) DO UPDATE SET title=excluded.title,latest=excluded.latest,last_seen=excluded.last_seen''',
                (slug, anime.title, anime.weekday, season, anime.start_date, latest, time.time()))
            # Una petición manual no convierte una serie antigua en emisión semanal.
            if not existing:
                connection.execute('UPDATE anime SET active=0 WHERE slug=?', (slug,))
            for number in chosen:
                before = connection.execute('SELECT id FROM episodes WHERE slug=? AND number=? AND language=?', (slug, number, cfg.language)).fetchone()
                target_season = season_folder(date.today()) if cfg.long_series == 'split' else season
                connection.execute('INSERT OR IGNORE INTO episodes(slug,number,url,language,season) VALUES(?,?,?,?,?)', (slug, number, available[number].url, cfg.language, target_season))
                row = connection.execute('SELECT id,status FROM episodes WHERE slug=? AND number=? AND language=?', (slug, number, cfg.language)).fetchone()
                connection.execute('INSERT INTO manual_requests VALUES(?,?) ON CONFLICT(episode_id) DO UPDATE SET requested=excluded.requested', (row['id'], time.time()))
                if row['status'] != 'completed':
                    connection.execute("UPDATE episodes SET status='pending',error='',next_retry=0 WHERE id=?", (row['id'],))
                added += not before
        db.set_meta('manual_last_url', normalized)
        db.log('info', f"Selección manual: {catalog.title}, {len(chosen)} capítulos en orden ({added} nuevos).", slug)
        cfg.paused = False
        cfg.save(directory)
        return {'added': added, 'items': len(chosen), 'slug': slug}
    except Exception:
        old.save(directory)
        raise
    finally:
        lock.close()
        if db:
            db.close()


def retry_jobs(directory: Path, identifiers):
    db = Database(directory)
    try:
        count = 0
        with db.transaction() as connection:
            for identifier in set(identifiers):
                count += connection.execute("UPDATE episodes SET status='pending',next_retry=0,error='' WHERE id=? AND status='failed'", (int(identifier),)).rowcount
                connection.execute('INSERT OR IGNORE INTO manual_requests SELECT id,? FROM episodes WHERE id=?', (time.time(), int(identifier)))
        return count
    finally:
        db.close()
