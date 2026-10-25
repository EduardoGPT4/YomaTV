"""Web HTTP -> puente del EXE -> resultados HTTP, sin descargar otra vez."""
import http.client
import json
import secrets
import sqlite3
import subprocess
import sys
import threading
import time
from pathlib import Path

from test_web import Client
ROOT=Path(__file__).resolve().parent.parent;DESKTOP=ROOT.parent/('YomaTVPC' if (ROOT.parent/'YomaTVPC').is_dir() else 'SeasonAV1')
sys.path.insert(0,str(DESKTOP))
from seasonav1.config import Config
from seasonav1.database import Database
from seasonav1.engine.catalog import Episode
from seasonav1.instance import send
from seasonav1.schedule import ScheduledAnime
from seasonav1.web_bridge import PORT,SITE,pairing_token

def request(token,method,path,body=None,origin=SITE):
    connection=http.client.HTTPConnection('127.0.0.1',PORT,timeout=55)
    headers={'Origin':origin,'Authorization':'Bearer '+token}
    if body is not None:body=json.dumps(body).encode();headers['Content-Type']='application/json'
    try:
        connection.request(method,path,body,headers);response=connection.getresponse();value=json.loads(response.read())
        return response.status,value
    finally:connection.close()

def main():
    client=Client();client.call('register',name='Prueba del puente',email='qa-'+secrets.token_hex(4)+'@example.test',password='LocalTest-Only-8086')
    slug='doumo-suki-na-hito-ni-horegusuri-wo-irai-sareta-majo-desu'
    detail=client.call('detail',get=True,slug=slug)['detail'];ep=next(e for e in detail['episodes'] if e['number']=='1')
    queued=client.call('queue',slugs=[slug],mode='selected',episode_ids=[ep['id']])
    plan=client.call('export',job_ids=queued['queue_ids'])['plan']
    source=sqlite3.connect(f'file:{(DESKTOP/"datos/seasonav1.sqlite3").as_posix()}?mode=ro',uri=True);source.row_factory=sqlite3.Row
    completed=dict(source.execute("SELECT * FROM episodes WHERE slug=? AND number='1' AND language='SUB' AND status='completed'",(slug,)).fetchone());source.close()
    directory=ROOT/'verification/bridge-frozen-state';directory.mkdir(exist_ok=True)
    Config(destination=str(directory/'videos'),autostart=False,notifications=False,resident_tray=True,configured=True,paused=True).save(directory)
    db=Database(directory)
    db.upsert_anime(ScheduledAnime(slug,detail['anime']['title'],1,'1','2026-10-12T12:00:00-06:00'),completed['season'])
    db.add_episode(slug,Episode('1',completed['url']),'SUB',completed['season'])
    identifier=db.query("SELECT id FROM episodes WHERE number='1'")[0]['id']
    db.update(identifier,status='completed',bytes=completed['bytes'],sha256=completed['sha256'],verification=completed['verification'],progress=100,path=completed['path']);db.close()
    token=pairing_token(directory)
    exe=DESKTOP/'build/release/YomaTV.exe'
    if not exe.is_file():exe=DESKTOP/'YomaTV.exe'
    process=subprocess.Popen([str(exe),'--tray','--data-dir',str(directory)],creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        deadline=time.monotonic()+30
        while True:
            try:
                if request(token,'GET','/ping')[0]==200:break
            except (OSError,ValueError):pass
            if time.monotonic()>deadline:raise RuntimeError('El puente del EXE no se inició.')
            time.sleep(.1)
        assert request(token,'GET','/ping',origin='https://evil.example')[0]==403
        status,imported=request(token,'POST','/queue',plan);assert status==200 and imported['added']==0
        assert not Config.load(directory).paused
        status,result=request(token,'GET','/results?installation='+plan['installation']);assert status==200 and result['completed']>=1
        receipt=next(r for r in result['receipts'] if any(p['plan_id']==plan['plan_id'] for p in r['plans']))
        own=next(p for p in receipt['plans'] if p['plan_id']==plan['plan_id']);assert own['items'][0]['sha256']==completed['sha256']
        jobs=client.call('receipt',receipt=receipt)['data']['jobs'];assert len(jobs)==1 and jobs[0]['status']=='confirmed'
        assert request(token,'POST','/queue',plan)[1]['added']==0
        result={'ok':True,'frozen_exe':True,'http_queue_received':True,'automatic_resume':True,'idempotent':True,'foreign_origin_rejected':True,'web_confirmed':True,'real_verified_bytes':completed['bytes'],'video_redownloaded':False}
        (ROOT/'verification/frozen-bridge-check.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2),flush=True)
        if '--keep' in sys.argv:
            print('EXE temporal listo para comprobar el emparejamiento desde la web HTTPS.',flush=True);process.wait()
    finally:
        send(directory,'tray',{'action':'exit'});process.wait(timeout=30)

if __name__=='__main__':main()
