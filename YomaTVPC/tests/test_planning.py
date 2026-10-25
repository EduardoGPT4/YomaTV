import tempfile
import threading
import unittest
from unittest.mock import patch
from datetime import datetime,timezone
from pathlib import Path

from seasonav1.config import Config,season_folder
from seasonav1.database import Database
from seasonav1.downloader import Outcome
from seasonav1.engine.catalog import Cancelled,DownloadError,Episode
from seasonav1.runner import Runner
from seasonav1.schedule import SCHEDULE_URL,StructureChanged,due_date,missed_weekdays,parse_schedule,work_due
from support import FixtureClient,catalog_page,schedule_page


class PlanningTests(unittest.TestCase):
    def setUp(self):
        self.root=Path(__file__).parent/".tmp";self.root.mkdir(exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=self.root);self.folder=Path(self.temp.name)
        self.cfg=Config(destination=str(self.folder/"videos"),notifications=False,request_interval=1)
        self.cfg.save(self.folder)
        self.now=datetime(2026,10,11,14,tzinfo=timezone.utc)
        self.downloads=[]

    def tearDown(self):self.temp.cleanup()

    def complete(self,job,cfg,*args):
        self.downloads.append((job["slug"],job["number"]))
        video=Path(cfg.destination)/job["season"]/job["slug"]/(job["number"]+".mp4")
        video.parent.mkdir(parents=True,exist_ok=True);video.write_bytes(b"x"*2048)
        return Outcome(video,"SUB","MP4Upload",{"bytes":2048,"sha256":"a"*64,"height":1080})

    def runner(self,**kwargs):return Runner(self.folder,now=self.now,client_factory=FixtureClient,downloader=self.complete,retry_delays=(0,),**kwargs)

    def test_first_run_all_days_numeric_order_then_no_duplicates(self):
        runner=self.runner()
        try:
            result=runner.run()
            self.assertEqual(result["downloaded"],4)
            self.assertEqual(self.downloads,[("lunes","1"),("lunes","2"),("domingo","1"),("domingo","2")])
            self.assertTrue(runner.db.meta("initialized"))
            self.assertEqual(runner.db.meta("last_review"),"2026-10-11")
            self.assertEqual(runner.run(force=True)["downloaded"],0)
            self.assertEqual(len(self.downloads),4)
        finally:runner.close()

    def test_dry_run_never_marks_checkpoint_or_downloaded_episodes(self):
        runner=self.runner()
        try:
            self.assertEqual(len(runner.run(dry_run=True)["items"]),4)
            self.assertEqual(runner.db.query("SELECT * FROM episodes"),[])
            self.assertIsNone(runner.db.meta("last_review"))
            self.assertFalse(self.downloads)
        finally:runner.close()

    def test_later_review_only_day_and_changed_publications(self):
        runner=self.runner()
        try:runner.run()
        finally:runner.close()
        self.now=datetime(2026,10,12,14,tzinfo=timezone.utc)
        runner=self.runner()
        try:
            runner.run()
            self.assertIn("https://animeav1.com/media/lunes",runner.client.urls)
            self.assertNotIn("https://animeav1.com/media/domingo",runner.client.urls)
        finally:runner.close()

    def test_missed_days_cover_week_and_resume_unfinished(self):
        runner=self.runner()
        try:
            runner.run()
            self.assertEqual(missed_weekdays("2026-10-01",self.now.date()),set(range(1,8)))
            row=runner.db.query("SELECT id FROM episodes LIMIT 1")[0]
            runner.db.update(row["id"],status="downloading")
            runner.run(force=True)
            self.assertEqual(runner.db.query("SELECT status FROM episodes WHERE id=?",(row["id"],))[0]["status"],"completed")
        finally:runner.close()

    def test_favorites_exclusions_and_season_retained(self):
        self.cfg.selection="favorites";self.cfg.favorites=["domingo"];self.cfg.save(self.folder)
        runner=self.runner()
        try:
            self.assertEqual(runner.run()["downloaded"],2)
            self.assertEqual(runner.db.anime("domingo")["season"],"otoño2026")
        finally:runner.close()
        self.now=datetime(2027,1,11,14,tzinfo=timezone.utc)
        runner=self.runner()
        try:
            runner.run(force=True)
            self.assertEqual(runner.db.anime("domingo")["season"],"otoño2026")
        finally:runner.close()

    def test_temporary_download_retries_and_permanent_one_continues(self):
        runner=self.runner()
        attempts=[]
        def flaky(job,cfg,*args):
            attempts.append((job["slug"],job["number"]))
            if len(attempts)==1:raise DownloadError("DNS",retryable=True)
            if job["slug"]=="domingo" and job["number"]=="1":raise DownloadError("404")
            return self.complete(job,cfg,*args)
        runner.downloader=flaky
        try:
            result=runner.run();self.assertEqual(result["downloaded"],3)
            self.assertEqual(attempts[:2],[("lunes","1")]*2)
            self.assertEqual(attempts.count(("domingo","1")),1)
            self.assertIn(("domingo","2"),self.downloads)
        finally:runner.close()

    def test_dates_timezone_structure_and_seasons(self):
        source=schedule_page([("test",1,"2026-10-11T03:00:00Z")])
        from datetime import timedelta
        self.assertEqual(parse_schedule(source,timezone(timedelta(hours=-6)))[0].weekday,6)
        for source in ("<title>Just a moment</title>",'<script>kit.start(x,x,{data:{media:[]}})</script>'):
            with self.assertRaises(StructureChanged):parse_schedule(source)
        self.assertEqual(str(due_date(datetime(2026,10,11,11),"12:00")),"2026-10-10")
        self.assertEqual([season_folder(datetime(2026,m,1)) for m in (1,4,7,10)],["invierno2026","primavera2026","verano2026","otoño2026"])

    def test_paused_config_stays_paused_and_no_requests(self):
        self.cfg.paused=True;self.cfg.save(self.folder)
        runner=self.runner()
        try:
            self.assertTrue(runner.run()["paused"])
            self.assertEqual(runner.client.requests,0)
        finally:runner.close()

    def test_late_release_on_other_weekday_is_detected(self):
        runner=self.runner()
        try:runner.run()
        finally:runner.close()
        pages=dict(FixtureClient.pages)
        pages[SCHEDULE_URL]=schedule_page([('lunes',2,'2026-10-05T14:00:00Z'),('domingo',3,'2026-10-11T20:00:00Z')])
        pages['https://animeav1.com/media/domingo']=catalog_page('domingo',(1,2,3))
        self.now=datetime(2026,10,12,14,tzinfo=timezone.utc)
        with patch.object(FixtureClient,'pages',pages):
            runner=self.runner()
            try:
                self.assertEqual(runner.run()['downloaded'],1)
                self.assertEqual(self.downloads[-1],('domingo','3'))
            finally:runner.close()

    def test_long_series_split_and_bootstrap_is_sequential(self):
        self.cfg.workers=4;self.cfg.long_series='split';self.cfg.save(self.folder)
        runner=self.runner();peak=0;active=0;lock=threading.Lock()
        complete=runner.downloader
        def slow(*args):
            nonlocal peak,active
            import time
            with lock:active+=1;peak=max(peak,active)
            time.sleep(0.03)
            try:return complete(*args)
            finally:
                with lock:active-=1
        runner.downloader=slow
        try:
            runner.run();self.assertEqual(peak,1)
        finally:runner.close()
        pages=dict(FixtureClient.pages)
        pages[SCHEDULE_URL]=schedule_page([('lunes',3,'2027-01-11T14:00:00Z'),('domingo',3,'2027-01-10T14:00:00Z')])
        pages.update({f'https://animeav1.com/media/{s}':catalog_page(s,(1,2,3)) for s in ('lunes','domingo')})
        self.now=datetime(2027,1,11,14,tzinfo=timezone.utc)
        with patch.object(FixtureClient,'pages',pages):
            runner=self.runner();runner.downloader=slow
            try:
                runner.run(force=True)
                rows=runner.db.query("SELECT season FROM episodes WHERE number='3'")
                self.assertEqual([r['season'] for r in rows],['invierno2027']*2)
                self.assertLessEqual(peak,4)
                self.assertGreaterEqual(peak,2)
            finally:runner.close()

    def test_retry_sleep_can_be_paused_without_losing_job(self):
        token=threading.Event();runner=self.runner(token=token)
        def fail(*args):token.set();raise DownloadError('timeout',retryable=True)
        runner.downloader=fail
        try:
            self.assertTrue(runner.run()['paused'])
            self.assertTrue(runner.db.query("SELECT id FROM episodes WHERE status='paused'"))
        finally:runner.close()

    def test_startup_resumes_last_interrupted_episode_on_same_day(self):
        runner=self.runner()
        try:
            runner.run()
            self.assertFalse(work_due(runner.db,self.cfg,self.now))
            row=runner.db.query('SELECT id FROM episodes LIMIT 1')[0]
            runner.db.update(row['id'],status='downloading')
            self.assertTrue(work_due(runner.db,self.cfg,self.now))
            runner.run();self.assertFalse(work_due(runner.db,self.cfg,self.now))
        finally:runner.close()

    def test_catalog_interruption_cannot_erase_late_publication(self):
        runner=self.runner()
        try:runner.run()
        finally:runner.close()
        pages=dict(FixtureClient.pages)
        pages[SCHEDULE_URL]=schedule_page([('lunes',2,'2026-10-05T14:00:00Z'),('domingo',3,'2026-10-11T20:00:00Z')])
        pages['https://animeav1.com/media/domingo']=catalog_page('domingo',(1,2,3))
        self.now=datetime(2026,10,12,14,tzinfo=timezone.utc)
        class Interrupted(FixtureClient):
            def fetch(self,url):
                if url.endswith('/domingo'):raise Cancelled('cierre')
                return super().fetch(url)
        with patch.object(FixtureClient,'pages',pages):
            runner=self.runner();runner.client=Interrupted()
            try:
                self.assertTrue(runner.run()['paused'])
                self.assertIn('domingo',runner.db.meta('scan_failures'))
            finally:runner.close()
            runner=self.runner()
            try:
                self.assertEqual(runner.run()['downloaded'],1)
                self.assertEqual(self.downloads[-1],('domingo','3'))
            finally:runner.close()

    def test_new_anime_discovered_after_its_day_is_caught_up(self):
        runner=self.runner()
        try:runner.run()
        finally:runner.close()
        pages=dict(FixtureClient.pages)
        pages[SCHEDULE_URL]=schedule_page([('lunes',2,'2026-10-05T14:00:00Z'),('domingo',2,'2026-10-11T14:00:00Z'),('nuevo',1,'2026-10-11T20:00:00Z')])
        pages['https://animeav1.com/media/nuevo']=catalog_page('nuevo',(1,))
        self.now=datetime(2026,10,12,14,tzinfo=timezone.utc)
        with patch.object(FixtureClient,'pages',pages):
            runner=self.runner()
            try:
                self.assertEqual(runner.run()['downloaded'],1)
                self.assertEqual(self.downloads[-1],('nuevo','1'))
            finally:runner.close()
