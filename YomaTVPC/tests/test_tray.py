import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock,patch
import threading

from seasonav1.config import Config
from seasonav1.tray import Tray


class TrayTests(unittest.TestCase):
    def test_native_tray_run_stops_after_review_and_waits_without_polling(self):
        root=Path(__file__).parent/'.tmp';root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as directory:
            folder=Path(directory);Config(notifications=False,resident_tray=False,configured=True).save(folder)
            class Stub:
                def __init__(self,*_):pass
                def run(self,*_):return {'downloaded':0}
                def close(self):pass
            with patch('seasonav1.tray.Runner',Stub):
                tray=Tray(folder);started=time.monotonic();cpu=time.process_time()
                self.assertEqual(tray.run(),0)
                self.assertGreater(time.monotonic()-started,2.5)
                self.assertLess(time.process_time()-cpu,1)

    def test_resume_requested_during_shutdown_starts_another_review(self):
        root=Path(__file__).parent/'.tmp';root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as directory:
            folder=Path(directory);Config(notifications=False,resident_tray=False).save(folder)
            started=threading.Event();release=threading.Event();calls=[]
            class Stub:
                def __init__(self,directory,notify,token):self.token=token
                def run(self,force,**kwargs):
                    calls.append(force)
                    if len(calls)==1:started.set();self.token.wait(2);release.wait(2)
                def close(self):pass
            with patch('seasonav1.tray.Runner',Stub):
                tray=Tray(folder);tray.icon=Mock();tray.start(False)
                self.assertTrue(started.wait(2));tray.toggle_pause();tray.toggle_pause();release.set()
                deadline=time.monotonic()+3
                while len(calls)<2 and time.monotonic()<deadline:time.sleep(.02)
                self.assertEqual(calls,[False,False]);tray.thread.join(timeout=5)
                self.assertFalse(tray.busy)

    def test_existing_window_is_reused_and_daily_trigger_reaches_resident(self):
        root=Path(__file__).parent/'.tmp';root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as directory:
            folder=Path(directory);Config(configured=True).save(folder)
            tray=Tray(folder);tray.icon=Mock()
            with patch('seasonav1.tray.send',return_value=True) as send, patch('seasonav1.tray.spawn') as spawn:
                tray.open_window(True);tray.open_window()
                spawn.assert_not_called()
                self.assertEqual(send.call_count,2)
            with patch('seasonav1.schedule.work_due',return_value=False), patch.object(tray,'start') as start:
                tray.handle_command({'action':'scheduled'});start.assert_not_called()
            with patch('seasonav1.schedule.work_due',return_value=True), patch.object(tray,'start') as start:
                tray.handle_command({'action':'scheduled'});start.assert_called_once_with(False)
            tray.icon.stop()
