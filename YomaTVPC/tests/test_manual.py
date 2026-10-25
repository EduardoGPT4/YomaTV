import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from dataclasses import asdict
from datetime import datetime

from seasonav1.config import Config
from seasonav1.database import Database
from seasonav1.downloader import Outcome
from seasonav1.engine.catalog import Episode, parse_page
from seasonav1.engine.selection import select_episodes
from seasonav1.manual import enqueue_catalog, read_catalog, retry_jobs
from seasonav1.runner import Runner
from seasonav1.schedule import work_due
from support import FixtureClient, catalog_page


class ManualTests(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).parent / '.tmp'
        root.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=root)
        self.folder = Path(self.temp.name)
        self.cfg = Config(destination=str(self.folder / 'videos'), autostart=False, notifications=False,
                          schedule_enabled=False, selection='favorites', favorites=[])
        self.cfg.save(self.folder)
        self.url = 'https://animeav1.com/media/naruto'
        self.catalog = parse_page(catalog_page('naruto', (220, 100, 10, 2, 1, 12.5)), self.url)

    def tearDown(self):
        self.temp.cleanup()

    def test_new_install_does_not_enable_season_and_old_configuration_keeps_it(self):
        fresh = self.folder / 'fresh'
        self.assertFalse(Config.load(fresh).schedule_enabled)
        legacy = asdict(self.cfg)
        del legacy['schedule_enabled']
        (self.folder / 'config.json').write_text(json.dumps(legacy))
        self.assertTrue(Config.load(self.folder).schedule_enabled)

    def test_read_classic_anime_and_ranges_without_weekly_schedule(self):
        class Client(FixtureClient):
            pages = {self.url: catalog_page('naruto', (1, 2, 12.5, 220))}
        catalog = read_catalog(self.folder, self.url, Client)
        self.assertEqual([e.number for e in select_episodes('1-1000000000', catalog.episodes)], ['1', '2', '12.5', '220'])
        self.assertEqual([e.number for e in select_episodes('1-2,12.5', catalog.episodes)], ['1', '2', '12.5'])

    def test_manual_queue_is_ordered_deduplicated_and_keeps_requested_language(self):
        selected = ['100', '12.5', '2', '1']
        result = enqueue_catalog(self.folder, self.catalog, selected, {'language': 'DUB'})
        self.assertEqual(result['added'], 4)
        cfg = Config.load(self.folder)
        self.assertFalse(cfg.schedule_enabled)
        self.assertEqual(cfg.destination, self.cfg.destination)
        cfg.language = 'SUB'
        cfg.save(self.folder)
        calls = []
        def download(job, cfg, *_):
            calls.append((job['number'], cfg.language))
            return Outcome(self.folder / 'video.mp4', cfg.language, 'MP4Upload', {'bytes': 2048, 'sha256': 'a' * 64, 'height': 720})
        runner = Runner(self.folder, downloader=download)
        try:
            with patch.object(runner, 'plan', side_effect=AssertionError('No debe explorar temporada')):
                self.assertEqual(runner.run()['downloaded'], 4)
            self.assertEqual(calls, [('1', 'DUB'), ('2', 'DUB'), ('12.5', 'DUB'), ('100', 'DUB')])
            self.assertFalse(runner.db.meta('initialized', False))
            self.assertEqual(runner.db.anime('naruto')['active'], 0)
        finally:
            runner.close()
        self.assertEqual(enqueue_catalog(self.folder, self.catalog, selected, {'language': 'DUB'})['added'], 0)
        db = Database(self.folder)
        try:
            self.assertEqual(len(db.query("SELECT id FROM episodes WHERE status='completed'")), 4)
            self.assertEqual(len(db.requested_episode_ids()), 4)
        finally:
            db.close()

    def test_invalid_selection_or_remote_url_changes_no_data(self):
        before = (self.folder / 'config.json').read_bytes()
        with self.assertRaises(ValueError):
            enqueue_catalog(self.folder, self.catalog, ['999'])
        self.catalog.episodes = [Episode('1', 'https://example.com/media/naruto/1')]
        with self.assertRaises(Exception):
            enqueue_catalog(self.folder, self.catalog, ['1'])
        self.assertEqual((self.folder / 'config.json').read_bytes(), before)
        db = Database(self.folder)
        try:
            self.assertEqual(db.query('SELECT id FROM episodes'), [])
        finally:
            db.close()

    def test_manual_exclusions_still_apply_and_retry_preserves_completed_files(self):
        self.cfg.exclusions = ['naruto']
        self.cfg.save(self.folder)
        with self.assertRaisesRegex(ValueError, 'excluido'):
            enqueue_catalog(self.folder, self.catalog, ['1'])
        self.cfg.exclusions = []
        self.cfg.save(self.folder)
        enqueue_catalog(self.folder, self.catalog, ['1', '2'])
        db = Database(self.folder)
        try:
            rows = db.query('SELECT id FROM episodes ORDER BY id')
            db.update(rows[0]['id'], status='completed', path='saved.mp4', sha256='a' * 64)
            db.update(rows[1]['id'], status='failed', next_retry=9999999999)
            self.assertEqual(retry_jobs(self.folder, [r['id'] for r in rows]), 1)
            self.assertEqual(db.query('SELECT status,path FROM episodes ORDER BY id')[0], {'status': 'completed', 'path': 'saved.mp4'})
        finally:
            db.close()

    def test_manual_mode_startup_only_runs_when_queue_needs_it(self):
        db = Database(self.folder)
        try:
            self.assertFalse(work_due(db, self.cfg, datetime.now()))
            enqueue_catalog(self.folder, self.catalog, ['1'])
            self.assertTrue(work_due(db, self.cfg, datetime.now()))
        finally:
            db.close()
