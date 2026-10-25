"""Check the real pointer rollback and return, preserving the requested final version."""
import argparse,json,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import release
parser=argparse.ArgumentParser()
parser.add_argument('--release',default='watch-room-20261022-2')
parser.add_argument('--previous',default='watch-room-20261022-1')
options=parser.parse_args()
target=release.valid_id(options.release)
previous=release.valid_id(options.previous)
assert release.check_health()['release']==target
visited=[]
def rollback():
    result=subprocess.run([sys.executable,'release.py','--rollback'],cwd=ROOT,
        capture_output=True,text=True,timeout=120)
    if result.returncode:raise RuntimeError((result.stdout+result.stderr)[-1500:])
    return release.check_health()
try:
    health=rollback();assert health['ok'] and health['release']==previous
    visited.append(health)
finally:
    health=release.check_health()
    if health['release']==previous:health=rollback()
    assert health['ok'] and health['release']==target
    visited.append(health)
assert len(visited)==2 and visited[0]['release']==previous
path=ROOT/'verification/delivery4-rollback-check.json'
if path.exists():
    old=json.loads(path.read_text(encoding='utf8'))
    if old.get('final_release')==previous:
        (ROOT/'verification'/(previous+'-rollback-check.json')).write_text(json.dumps(old,indent=2),encoding='utf8')
result={'ok':True,'at':int(time.time()),'previous_release':previous,'final_release':target,
    'visited':visited,'real_mal_changes':False,'database_backup':'waived_by_owner'}
path.write_text(json.dumps(result,indent=2),encoding='utf8')
print(json.dumps({'ok':True,'final_release':target,'rollback_verified':True}))
