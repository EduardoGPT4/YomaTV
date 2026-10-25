import hashlib
import json
import subprocess
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

import imageio_ffmpeg

from seasonav1.config import Config
from seasonav1.downloader import PreferenceUnavailable,anime_directory,choices,download_job,episode_name,quality_check
from seasonav1.engine.catalog import Cancelled,parse_page
from support import catalog_page


class DownloadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).parent/".tmp";cls.root.mkdir(exist_ok=True)
        cls.temp=tempfile.TemporaryDirectory(dir=cls.root);cls.folder=Path(cls.temp.name)
        cls.fixture=cls.folder/"fixture.mp4"
        subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),"-v","error","-f","lavfi","-i","testsrc2=size=320x180:rate=24",
                        "-f","lavfi","-i","sine=frequency=440:sample_rate=44100","-t","8","-c:v","mpeg4","-q:v","3",
                        "-c:a","aac","-shortest",str(cls.fixture)],capture_output=True,check=True)

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def test_preferences_strict_fallback_and_safe_consistent_names(self):
        cfg=Config();catalog=parse_page(catalog_page("test",server="Voe",language="SUB"),"https://animeav1.com/media/test/1")
        with self.assertRaises(PreferenceUnavailable):choices(catalog,cfg)
        cfg.server_fallback="other";self.assertEqual(choices(catalog,cfg)[0].server,"Voe")
        cfg.language="DUB"
        with self.assertRaises(PreferenceUnavailable):choices(catalog,cfg)
        cfg.language_fallback="SUB";self.assertEqual(choices(catalog,cfg)[0].language,"SUB")
        cfg.quality_fallback="wait"
        with self.assertRaises(PreferenceUnavailable):quality_check({"height":720},cfg)
        cfg.quality_fallback="lower";self.assertEqual(quality_check({"height":720},cfg).startswith("La fuente"),True)
        name=episode_name('A/B:C?','5','SUB');self.assertNotIn('/',name);self.assertIn('0005',name)

    def test_real_download_pause_resume_verify_and_reuse_without_duplicates(self):
        content=self.fixture.read_bytes();ranges=[]
        release_first_response=threading.Event()
        class Handler(BaseHTTPRequestHandler):
            def do_HEAD(self):
                self.send_response(200);self.send_header('Content-Type','video/mp4');self.send_header('Content-Length',str(len(content)));self.end_headers()
            def do_GET(self):
                value=self.headers.get('Range','');start=int(value.split('=')[1].split('-')[0]) if value else 0
                ranges.append(start);self.send_response(206 if value else 200)
                self.send_header('Content-Type','video/mp4');self.send_header('Content-Length',str(len(content)-start))
                self.send_header('Accept-Ranges','bytes')
                if value:self.send_header('Content-Range',f'bytes {start}-{len(content)-1}/{len(content)}')
                self.end_headers()
                try:
                    for i in range(start,len(content),8192):
                        self.wfile.write(content[i:i+8192]);self.wfile.flush();time.sleep(0.015)
                        # Keep the first response incomplete until the real pause.
                        # A fast CI runner may otherwise finish before yt-dlp's
                        # next progress line reaches the parent process.
                        if not value and i < len(content)//2 <= i+8192:
                            release_first_response.wait(30)
                except (BrokenPipeError,ConnectionResetError,ConnectionAbortedError):pass
            def log_message(self,*_):pass
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        url=f'http://127.0.0.1:{server.server_port}/video.mp4'
        page=catalog_page('test',mirror=url)
        class Client:
            def fetch(self,request):return page
        cfg=Config(destination=str(self.folder/'videos'))
        job={'slug':'test','title':'Test','number':'5','url':'https://animeav1.com/media/test/5','language':'SUB','season':'otoño2026'}
        token=threading.Event();partial_observed=threading.Event();monitor_stop=threading.Event()
        def pause_when_partial_exists():
            deadline=time.monotonic()+30
            while time.monotonic()<deadline and not monitor_stop.is_set():
                for part in (self.folder/'videos').rglob('*.part'):
                    try:size=part.stat().st_size
                    except FileNotFoundError:continue
                    if 0<size<len(content):
                        partial_observed.set();token.set();return
                monitor_stop.wait(.01)
        monitor=threading.Thread(target=pause_when_partial_exists,daemon=True);monitor.start()
        try:
            with self.assertRaises(Cancelled):download_job(job,cfg,Client(),token)
            self.assertTrue(partial_observed.is_set())
            parts=list((self.folder/'videos').rglob('*.part'));self.assertTrue(parts)
            self.assertTrue(any(0<part.stat().st_size<len(content) for part in parts))
            release_first_response.set()
            token.clear();outcome=download_job(job,cfg,Client(),token)
            self.assertEqual(outcome.path.parent,self.folder/'videos/otoño2026/test')
            self.assertEqual(outcome.verification['height'],180)
            self.assertEqual(hashlib.sha256(outcome.path.read_bytes()).digest(),hashlib.sha256(content).digest())
            self.assertTrue(any(r>0 for r in ranges))
            self.assertFalse(outcome.path.with_suffix('.json').exists())
            self.assertTrue((outcome.path.parent/'archivos'/outcome.path.with_suffix('.json').name).is_file())
            with patch('seasonav1.downloader.run_download') as worker,patch('seasonav1.engine.validation.ffmpeg_check') as verify:
                again=download_job(job,cfg,Client(),token)
                self.assertEqual(again.path,outcome.path);worker.assert_not_called();verify.assert_not_called()
        finally:
            monitor_stop.set();release_first_response.set();monitor.join(timeout=2)
            server.shutdown();server.server_close();thread.join(timeout=3)

    def test_speed_limit_is_shared_between_workers(self):
        cfg=Config(destination=str(self.folder/'limited'),speed_kib=1)
        job={'slug':'limited','title':'Limited','number':'1','url':'https://animeav1.com/media/limited/1','language':'SUB','season':'otoño2026'}
        class Client:
            def fetch(self,_):return catalog_page('limited')
        def worker(command,*args):
            self.assertEqual(command[command.index('--limit-rate')+1],'256')
            raise Cancelled('checked')
        with patch('seasonav1.downloader.run_download',side_effect=worker),self.assertRaises(Cancelled):
            download_job(job,cfg,Client(),threading.Event(),workers=4)

    def test_exact_quality_can_fall_back_to_other_server_without_moving_rejected_video(self):
        cfg=Config(destination=str(self.folder/'fallback'),quality_fallback='wait',server_fallback='other')
        job={'slug':'fallback','title':'Fallback','number':'1','url':'https://animeav1.com/media/fallback/1','language':'SUB','season':'otoño2026'}
        page=catalog_page('fallback')
        page=page.replace('"server": "MP4Upload", "url": "https://www.mp4upload.com/embed-test.html"',
                          '"server": "MP4Upload", "url": "https://www.mp4upload.com/embed-test.html"}, {"server":"Voe","url":"https://voe.sx/test"')
        class Client:
            def fetch(self,_):return page
        def worker(command,*_):
            target=Path(command[command.index('--output')+1].replace('%(ext)s','mp4'))
            target.write_bytes(b'x'*2048);return target
        checks=[{'version':1,'height':720,'bytes':2048,'sha256':'a'*64},{'version':1,'height':1080,'bytes':2048,'sha256':'b'*64}]
        with patch('seasonav1.downloader.run_download',side_effect=worker),patch('seasonav1.downloader.verify_video',side_effect=checks):
            outcome=download_job(job,cfg,Client(),threading.Event())
        self.assertEqual(outcome.server,'Voe');self.assertEqual(outcome.verification['height'],1080)
        self.assertEqual(len(list(outcome.path.parent.glob('*.mp4'))),1)
        self.assertEqual(len(list((outcome.path.parent/'archivos/parciales').glob('*/video.mp4'))),1)

    def test_long_slugs_do_not_collide_after_truncation(self):
        self.assertNotEqual(anime_directory('a'*150+'-one'),anime_directory('a'*150+'-two'))
