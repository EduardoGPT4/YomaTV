"""Own a bounded browser preview with disposable accounts and synthetic media."""
import os,subprocess,sys,time,socket
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
env={**os.environ,'SEASON_WEB_SQLITE':str(ROOT/'verification/hardening-2026-10-14.sqlite'),'SEASON_WEB_MAL_TEST_URL':'http://127.0.0.1:8097','SEASON_WEB_PLAYER_TEST_URL':'http://127.0.0.1:8096/__qa_player/frame.html','SEASON_WEB_ADMIN_EMAILS':'admin@example.test','PYTHONUTF8':'1'}
stop=ROOT/'verification/stop-delivery3-preview';stop.unlink(missing_ok=True)
children=[];flags=subprocess.CREATE_NO_WINDOW
try:
    for port in [8096,8097]:
        with socket.socket() as s:s.bind(('127.0.0.1',port))
    with (ROOT/'verification/delivery3-preview.log').open('w',encoding='utf8') as output:
        children.append(subprocess.Popen([sys.executable,'verification/mal_mock.py'],cwd=ROOT,env=env,stdout=output,stderr=output,creationflags=flags))
        time.sleep(.5)
        subprocess.run([sys.executable,'verification/setup_player_preview.py'],cwd=ROOT,env=env,check=True,stdout=output,stderr=output,timeout=30)
        children.append(subprocess.Popen([r'C:/Users/Eduardo/.config/herd-lite/bin/php.exe','-S','127.0.0.1:8096','-t','htdocs'],cwd=ROOT,env=env,stdout=output,stderr=output,creationflags=flags))
        print('PREVIEW_READY http://127.0.0.1:8096/ · disposable account and synthetic video',flush=True)
        deadline=time.monotonic()+1200
        while time.monotonic()<deadline and not stop.exists():time.sleep(1)
finally:
    for child in reversed(children):
        child.terminate()
        try:child.wait(timeout=5)
        except subprocess.TimeoutExpired:child.kill();child.wait()
