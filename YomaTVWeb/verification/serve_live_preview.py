"""Isolated PC fixture: a verified synthetic MP4 and slow progress for UI QA."""
import json
import os
import shutil
import subprocess
import sys
import threading
from pathlib import Path
import imageio_ffmpeg

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT.parent/('YomaTVPC' if (ROOT.parent/'YomaTVPC').is_dir() else 'SeasonAV1')))
from seasonav1.config import Config
from seasonav1.downloader import Outcome
from seasonav1.engine.download import Progress
from seasonav1.engine.validation import verify_video
from seasonav1.runner import Runner
from seasonav1.web_bridge import WebBridge

folder=ROOT/'verification/bridge-live-state';folder.mkdir(exist_ok=True)
cfg=Config(destination=str(folder/'videos'),autostart=False,notifications=False,configured=True)
if not (folder/'config.json').exists():cfg.save(folder)
clip=folder/'sample.mp4'
if not clip.exists():
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-loglevel','error','-f','lavfi','-i','testsrc=size=1280x720:rate=24','-f','lavfi','-i','sine=frequency=440:sample_rate=44100','-t','1.5','-pix_fmt','yuv420p','-c:v','libx264','-preset','ultrafast','-crf','30','-c:a','aac','-movflags','+faststart','-y',str(clip)],check=True,creationflags=subprocess.CREATE_NO_WINDOW)
verified=verify_video(clip)
threads=[]
def download(job,cfg,client,token,report,workers):
    from seasonav1.engine.catalog import Cancelled
    for step in range(1,26):
        if token.wait(1):raise Cancelled('Prueba pausada.')
        report(Progress(job['number'],'MP4Upload',downloaded=int(verified['bytes']*step/25),total=verified['bytes'],percent=step*4,message='Descargando'))
    destination=Path(cfg.destination)/('test-'+job['slug']+'-'+job['number']+'.mp4')
    destination.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(clip,destination)
    return Outcome(destination,cfg.language,cfg.server,verify_video(destination))
def accept(result):
    def run():
        runner=Runner(folder,downloader=download)
        try:runner.run(queue_only=True)
        finally:runner.close()
    thread=threading.Thread(target=run,daemon=True);threads.append(thread);thread.start()
bridge=WebBridge(folder,accept,port=47654,origins=('http://127.0.0.1:8096',)).start()
print('PC aislada de prueba lista en 127.0.0.1:47654. Los videos son sintéticos.',flush=True)
try:threading.Event().wait()
finally:bridge.close()
