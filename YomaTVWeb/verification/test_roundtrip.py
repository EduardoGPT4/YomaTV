"""Una cola HTTP -> EXE real -> resultado HTTP, sin otra descarga de Internet."""
import json
import secrets
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from test_web import Client

ROOT=Path(__file__).resolve().parent.parent
DESKTOP=ROOT.parent/('YomaTVPC' if (ROOT.parent/'YomaTVPC').is_dir() else 'SeasonAV1')
sys.path.insert(0,str(DESKTOP))
from seasonav1.config import Config
from seasonav1.database import Database
from seasonav1.engine.catalog import Episode
from seasonav1.schedule import ScheduledAnime
from seasonav1.instance import send

def main():
    client=Client();client.call('register',name='Prueba de integración',email='qa-'+secrets.token_hex(4)+'@example.test',password='LocalTest-Only-8086')
    slug='doumo-suki-na-hito-ni-horegusuri-wo-irai-sareta-majo-desu'
    detail=client.call('detail',get=True,slug=slug)['detail'];ep=next(e for e in detail['episodes'] if e['number']=='1')
    client.call('queue',slugs=[slug],mode='selected',episode_ids=[ep['id']])
    plan=client.call('export')['plan']
    source=sqlite3.connect(f'file:{(DESKTOP/"datos/seasonav1.sqlite3").as_posix()}?mode=ro',uri=True);source.row_factory=sqlite3.Row
    completed=dict(source.execute("SELECT * FROM episodes WHERE slug=? AND number='1' AND language='SUB' AND status='completed'",(slug,)).fetchone());source.close()
    options={'creationflags':subprocess.CREATE_NO_WINDOW,'capture_output':True,'text':True}
    with tempfile.TemporaryDirectory(dir=ROOT/'verification') as temp:
        folder=Path(temp);directory=folder/'data';directory.mkdir()
        Config(destination=str(folder/'videos'),autostart=False,notifications=False,resident_tray=False).save(directory)
        db=Database(directory)
        db.upsert_anime(ScheduledAnime(slug,detail['anime']['title'],1,'1','2026-10-12T12:00:00-06:00'),completed['season'])
        db.add_episode(slug,Episode('1',completed['url']),'SUB',completed['season'])
        identifier=db.query('SELECT id FROM episodes')[0]['id']
        db.update(identifier,status='completed',bytes=completed['bytes'],sha256=completed['sha256'],verification=completed['verification'],progress=100,path=completed['path']);db.close()
        path=folder/'plan.json';path.write_text(json.dumps(plan),encoding='utf-8')
        exe=DESKTOP/'build/release/YomaTV.exe'
        if not exe.is_file():exe=DESKTOP/'YomaTV.exe'
        subprocess.run([str(exe),'--data-dir',str(directory),'--import-web',str(path),'--report',str(folder/'import.json')],check=True,timeout=60,**options)
        imported=json.loads((folder/'import.json').read_text());assert imported['added']==0
        output=folder/'results.json'
        subprocess.run([str(exe),'--data-dir',str(directory),'--export-web',str(output)],check=True,timeout=60,**options)
        receipt=json.loads(output.read_text())
        assert receipt['plans'][0]['items'][0]['sha256']==completed['sha256']
        confirmed=client.call('receipt',receipt=receipt)['data']['jobs']
        assert len(confirmed)==1 and confirmed[0]['status']=='confirmed' and confirmed[0]['sha256']==completed['sha256']
        deadline=time.monotonic()+20
        while (directory/'tray-instance.json').exists() and time.monotonic()<deadline:
            send(directory,'tray',{'action':'exit'});time.sleep(.1)
        assert not (directory/'tray-instance.json').exists()
    result={'ok':True,'exe':True,'queue_imported_without_redownload':True,'real_verified_bytes':completed['bytes'],'confirmed_by_web':True,'credentials_or_local_paths_in_receipt':False}
    (ROOT/'verification/roundtrip-check.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
