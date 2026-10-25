"""Separate disposable UI preview; it can run alongside HTTP regression fixtures."""
import os,socket,sqlite3,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];children=[];flags=subprocess.CREATE_NO_WINDOW
fixture=ROOT/'verification/review-preview.sqlite';keep='--keep-fixture' in sys.argv and fixture.is_file();stop=ROOT/'verification/stop-review-preview';stop.unlink(missing_ok=True)
env={**os.environ,'SEASON_WEB_SQLITE':str(fixture),'SEASON_WEB_MAL_TEST_URL':'http://127.0.0.1:8099','SEASON_WEB_PLAYER_TEST_URL':'http://127.0.0.1:8098/__qa_player/frame.html','SEASON_WEB_ADMIN_EMAILS':'admin@example.test','PYTHONUTF8':'1'}
try:
    for port in [8098,8099]:
        with socket.socket() as probe:probe.bind(('127.0.0.1',port))
    assert fixture.parent==(ROOT/'verification').resolve()
    if not keep:
        for suffix in ['', '-wal','-shm','-journal']:Path(str(fixture)+suffix).unlink(missing_ok=True)
    with (ROOT/'verification/review-preview.log').open('w',encoding='utf8') as log:
        seed=(ROOT/'verification/seed_hardening.py').read_text(encoding='utf8').replace('hardening-2026-10-14.sqlite','review-preview.sqlite')
        code="__file__="+repr(str(ROOT/'verification/seed_hardening.py'))+"\n"+seed
        if not keep:subprocess.run([sys.executable,'-c',code],cwd=ROOT,env=env,stdout=log,stderr=log,check=True,timeout=45)
        mock="import sys;sys.path.insert(0,'verification');from mal_mock import Handler,ThreadingHTTPServer;ThreadingHTTPServer(('127.0.0.1',8099),Handler).serve_forever()"
        children.append(subprocess.Popen([sys.executable,'-c',mock],cwd=ROOT,env=env,stdout=log,stderr=log,creationflags=flags))
        setup=(ROOT/'verification/setup_player_preview.py').read_text(encoding='utf8').replace('hardening-2026-10-14.sqlite','review-preview.sqlite').replace('8096','8098').replace('8097','8099')
        if not keep:subprocess.run([sys.executable,'-c',"__file__="+repr(str(ROOT/'verification/setup_player_preview.py'))+"\n"+setup],cwd=ROOT,env=env,stdout=log,stderr=log,check=True,timeout=45)
        with sqlite3.connect(fixture) as db:
            db.execute("UPDATE sa1_episodes SET mirrors=(SELECT mirrors FROM sa1_episodes WHERE slug='naruto' AND number='6'),mirrors_at=strftime('%s','now') WHERE slug='naruto' AND number='7'")
            db.execute("INSERT INTO sa1_meta(name,value) VALUES('catalog_job_lock',?) ON CONFLICT(name) DO UPDATE SET value=excluded.value",(str(int(time.time())+1200),))
            ids=db.execute("SELECT id,number FROM sa1_episodes WHERE slug='naruto' AND number IN ('6','7')").fetchall()
        children.append(subprocess.Popen([r'C:/Users/Eduardo/.config/herd-lite/bin/php.exe','-S','127.0.0.1:8098','-t','htdocs'],cwd=ROOT,env=env,stdout=log,stderr=log,creationflags=flags))
        print('PREVIEW_READY http://127.0.0.1:8098/ synthetic episodes '+repr(ids),flush=True)
        deadline=time.monotonic()+1200
        while time.monotonic()<deadline and not stop.exists():time.sleep(1)
finally:
    for child in reversed(children):
        child.terminate()
        try:child.wait(timeout=5)
        except subprocess.TimeoutExpired:child.kill();child.wait()
