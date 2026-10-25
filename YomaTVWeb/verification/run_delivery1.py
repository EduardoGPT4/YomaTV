"""Bounded local-only HTTP regression harness; owns and stops both child servers."""
import json
import os
import socket
import sqlite3
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from delivery4_evidence import application_hashes

ROOT = Path(__file__).resolve().parent.parent
PHP = r'C:/Users/Eduardo/.config/herd-lite/bin/php.exe'
source_before = application_hashes()
env = {**os.environ, 'SEASON_WEB_SQLITE':str(ROOT/'verification/hardening-2026-10-14.sqlite'),
    'SEASON_WEB_ADMIN_EMAILS':'admin@example.test','SEASON_WEB_MAL_TEST_URL':'http://127.0.0.1:8097',
    'NO_PROXY':'127.0.0.1,localhost','PYTHONUTF8':'1','SEASON_WEB_TEST_BASE':'http://127.0.0.1:8096/'}
children=[]
results=[]
flags = subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0
def run(arguments):
    return subprocess.run(arguments,cwd=ROOT,env=env,capture_output=True,text=True,encoding='utf8',timeout=180)

try:
    for port in [8096,8097]:
        with socket.socket() as probe:probe.bind(('127.0.0.1',port))
    fixture_path=Path(env['SEASON_WEB_SQLITE']).resolve()
    assert fixture_path.parent==(ROOT/'verification').resolve() and fixture_path.name=='hardening-2026-10-14.sqlite'
    for suffix in ['', '-wal','-shm','-journal']:
        Path(str(fixture_path)+suffix).unlink(missing_ok=True)
    seeded=run([sys.executable,'verification/seed_hardening.py'])
    if seeded.returncode:raise RuntimeError(seeded.stderr)
    with (ROOT/'verification/delivery1-servers.log').open('w',encoding='utf8') as output:
        children.append(subprocess.Popen([sys.executable,'verification/mal_mock.py'],cwd=ROOT,env=env,stdout=output,stderr=output,creationflags=flags))
        children.append(subprocess.Popen([PHP,'-S','127.0.0.1:8096','-t','htdocs'],cwd=ROOT,env=env,stdout=output,stderr=output,creationflags=flags))
        deadline=time.monotonic()+15
        for url in ['http://127.0.0.1:8097/control','http://127.0.0.1:8096/']:
            while True:
                try:
                    with urllib.request.urlopen(url,timeout=1) as response:response.read()
                    break
                except Exception:
                    if time.monotonic()>deadline:raise
                    time.sleep(.2)
        scripts=sys.argv[1:] or ['test_reliability_http.py','test_hardening.py','test_mal.py','test_watch_auto.py','test_schema_upgrade.py']
        for index,script in enumerate(scripts):
            if not script.startswith('test_') or '/' in script or '\\' in script:raise RuntimeError('Only local test files are accepted.')
            if index:
                for suffix in ['', '-wal','-shm','-journal']:
                    Path(str(fixture_path)+suffix).unlink(missing_ok=True)
                seeded=run([sys.executable,'verification/seed_hardening.py'])
                if seeded.returncode:raise RuntimeError(seeded.stderr)
            with sqlite3.connect(env['SEASON_WEB_SQLITE']) as fixture:fixture.execute('DELETE FROM sa1_limits')
            fixture.close()
            if script in ['test_features.py','test_catalog_filters.py','test_catalog_updates.py']:
                seed='seed_feature_preview.php' if script=='test_features.py' else 'seed_catalog_filters.php'
                prepared=run([PHP,'verification/'+seed])
                if prepared.returncode:raise RuntimeError(prepared.stderr)
            result=run([sys.executable,'verification/'+script])
            entry={'test':script,'ok':result.returncode==0}
            results.append(entry)
            print(json.dumps(entry),flush=True)
            if result.returncode:
                print(result.stdout[-5000:]);print(result.stderr[-5000:]);raise RuntimeError('Regression failed: '+script)
finally:
    for child in reversed(children):
        child.terminate()
        try:child.wait(timeout=10)
        except subprocess.TimeoutExpired:child.kill();child.wait(timeout=5)
    unchanged = source_before == application_hashes()
    report = {'ok':bool(results) and all(row['ok'] for row in results) and unchanged,
        'tests':results,'real_mal_changes':False,'application_sha256':source_before}
    (ROOT/'verification/delivery1-http-suite.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    if any(row['test']=='test_infrastructure_http.py' for row in results):
        (ROOT/'verification/delivery4-http-suite.json').write_text(json.dumps(report,indent=2),encoding='utf8')
