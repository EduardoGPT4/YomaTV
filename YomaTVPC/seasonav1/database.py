from __future__ import annotations

import json
import sqlite3
import threading
import time
import zlib
from contextlib import contextmanager
from pathlib import Path


class Database:
    def __init__(self, directory: Path):
        directory.mkdir(parents=True, exist_ok=True)
        self.directory = directory
        self.lock = threading.RLock()
        self.connection = sqlite3.connect(directory / "seasonav1.sqlite3", timeout=30, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript("""
            PRAGMA journal_mode=WAL;
            PRAGMA busy_timeout=30000;
            PRAGMA foreign_keys=ON;
            CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS anime(
                slug TEXT PRIMARY KEY,title TEXT NOT NULL,weekday INTEGER NOT NULL,season TEXT NOT NULL,
                start_date TEXT,latest TEXT,initialized INTEGER NOT NULL DEFAULT 0,active INTEGER NOT NULL DEFAULT 1,
                last_seen REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS episodes(
                id INTEGER PRIMARY KEY,slug TEXT NOT NULL REFERENCES anime(slug),number TEXT NOT NULL,
                url TEXT NOT NULL,language TEXT NOT NULL,season TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'pending',
                actual_language TEXT,server TEXT,path TEXT,bytes INTEGER,sha256 TEXT,verification TEXT,
                attempts INTEGER NOT NULL DEFAULT 0,error TEXT NOT NULL DEFAULT '',next_retry REAL NOT NULL DEFAULT 0,
                progress REAL NOT NULL DEFAULT 0,bootstrap INTEGER NOT NULL DEFAULT 0,completed_at TEXT,
                UNIQUE(slug,number,language));
            CREATE TABLE IF NOT EXISTS history(
                id INTEGER PRIMARY KEY,created REAL NOT NULL,level TEXT NOT NULL,message TEXT NOT NULL,
                slug TEXT,episode TEXT);
            CREATE TABLE IF NOT EXISTS http_cache(
                url TEXT PRIMARY KEY,body BLOB NOT NULL,etag TEXT,modified TEXT,updated REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS web_references(
                installation TEXT NOT NULL,web_id INTEGER NOT NULL,plan_id TEXT NOT NULL,
                episode_id INTEGER NOT NULL REFERENCES episodes(id),PRIMARY KEY(installation,web_id));
            CREATE TABLE IF NOT EXISTS manual_requests(
                episode_id INTEGER PRIMARY KEY REFERENCES episodes(id),requested REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS anime_controls(
                slug TEXT PRIMARY KEY REFERENCES anime(slug),paused INTEGER NOT NULL DEFAULT 0,
                priority INTEGER NOT NULL DEFAULT 0);
            CREATE TABLE IF NOT EXISTS web_reference_runs(installation TEXT NOT NULL,web_id INTEGER NOT NULL,revision TEXT NOT NULL,PRIMARY KEY(installation,web_id));
            PRAGMA user_version=1;
        """)
        self.connection.commit()
        if not self.meta('web_references_migrated',False):
            self.record_web_references(self.meta('web_imports',[]))
            self.set_meta('web_references_migrated',True)

    @contextmanager
    def transaction(self):
        with self.lock, self.connection:
            yield self.connection

    def query(self, sql, args=()):
        with self.lock:
            return [dict(row) for row in self.connection.execute(sql, args)]

    def meta(self, key, default=None):
        rows = self.query("SELECT value FROM meta WHERE key=?", (key,))
        return json.loads(rows[0]["value"]) if rows else default

    def set_meta(self, key, value):
        with self.transaction() as connection:
            connection.execute("INSERT INTO meta VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, json.dumps(value)))
        if key=='web_imports':self.record_web_references(value)

    def record_web_references(self,plans):
        with self.transaction() as connection:
            for plan in plans:
                for reference in plan['items']:
                    connection.execute('INSERT INTO web_reference_runs(installation,web_id,revision) VALUES(?,?,?) ON CONFLICT(installation,web_id) DO UPDATE SET revision=excluded.revision',(plan['installation'],reference['web_id'],reference.get('request_revision','')))
                    connection.execute('INSERT INTO web_references(installation,web_id,plan_id,episode_id) SELECT ?,?,?,id FROM episodes WHERE id=? ON CONFLICT(installation,web_id) DO UPDATE SET plan_id=excluded.plan_id,episode_id=excluded.episode_id',
                                       (plan['installation'],reference['web_id'],plan['plan_id'],reference['episode_id']))

    def web_episode_ids(self):
        return {row['episode_id'] for row in self.query('SELECT DISTINCT episode_id FROM web_references')}

    def requested_episode_ids(self):
        return self.web_episode_ids() | {row['episode_id'] for row in self.query('SELECT episode_id FROM manual_requests')}

    def log(self, level, message, slug=None, episode=None):
        with self.transaction() as connection:
            connection.execute("INSERT INTO history(created,level,message,slug,episode) VALUES(?,?,?,?,?)", (time.time(), level, message, slug, episode))
        with self.lock, (self.directory / "seasonav1.log").open("a", encoding="utf-8") as stream:
            stream.write(time.strftime("%Y-%m-%d %H:%M:%S") + f" [{level}] {message}\n")

    def recover(self):
        with self.transaction() as connection:
            connection.execute("UPDATE episodes SET status='pending' WHERE status IN ('downloading','verifying','paused')")

    def anime(self, slug):
        rows = self.query("SELECT * FROM anime WHERE slug=?", (slug,))
        return rows[0] if rows else None

    def upsert_anime(self, anime, season):
        with self.transaction() as connection:
            connection.execute("""INSERT INTO anime(slug,title,weekday,season,start_date,latest,last_seen)
                VALUES(?,?,?,?,?,?,?) ON CONFLICT(slug) DO UPDATE SET title=excluded.title,weekday=excluded.weekday,
                start_date=excluded.start_date,latest=excluded.latest,last_seen=excluded.last_seen,active=1""",
                (anime.slug, anime.title, anime.weekday, season, anime.start_date, anime.latest, time.time()))

    def mark_catalog(self, slug):
        with self.transaction() as connection:
            connection.execute("UPDATE anime SET initialized=1 WHERE slug=?", (slug,))

    def add_episode(self, slug, episode, language, season, bootstrap=False):
        with self.transaction() as connection:
            connection.execute("INSERT OR IGNORE INTO episodes(slug,number,url,language,season,bootstrap) VALUES(?,?,?,?,?,?)",
                               (slug, episode.number, episode.url, language, season, int(bootstrap)))

    def completed(self, slug, number, language):
        return bool(self.query("SELECT id FROM episodes WHERE slug=? AND number=? AND language=? AND status='completed'", (slug, number, language)))

    def pending(self, now=None):
        return self.query("""SELECT e.*,a.title,a.start_date FROM episodes e JOIN anime a ON a.slug=e.slug
            WHERE e.status IN ('pending','failed','paused') AND next_retry<=? ORDER BY a.weekday,a.slug""", (time.time() if now is None else now,))

    def group_control(self, slug):
        rows=self.query('SELECT paused,priority FROM anime_controls WHERE slug=?',(slug,))
        return rows[0] if rows else {'paused':0,'priority':0}

    def update(self, identifier, **values):
        allowed = {"status", "actual_language", "server", "path", "bytes", "sha256", "verification", "attempts", "error", "next_retry", "progress", "completed_at"}
        if not values or not set(values) <= allowed:
            raise ValueError("Campos de descarga inválidos.")
        with self.transaction() as connection:
            connection.execute("UPDATE episodes SET " + ",".join(k + "=?" for k in values) + " WHERE id=?", [*values.values(), identifier])

    def cache(self, url):
        rows = self.query("SELECT * FROM http_cache WHERE url=?", (url,))
        if rows:
            row = rows[0]
            row["body"] = zlib.decompress(row["body"]).decode("utf-8")
            return row
        return None

    def save_cache(self, url, body, etag=None, modified=None):
        with self.transaction() as connection:
            connection.execute("""INSERT INTO http_cache VALUES(?,?,?,?,?) ON CONFLICT(url) DO UPDATE SET
                body=excluded.body,etag=excluded.etag,modified=excluded.modified,updated=excluded.updated""",
                (url, zlib.compress(body.encode("utf-8")), etag, modified, time.time()))
            connection.execute("DELETE FROM http_cache WHERE updated<?", (time.time() - 14 * 86400,))

    def close(self):
        with self.lock:
            self.connection.close()
