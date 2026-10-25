"""Account/security and payload checks against disposable SQLite on 8096."""
import json
import secrets
import sqlite3
import runpy
import copy
import sys
import urllib.request
import test_web

test_web.BASE='http://127.0.0.1:8096/'
DB=test_web.ROOT/'verification/hardening-2026-10-14.sqlite'
assert DB.resolve().is_relative_to((test_web.ROOT/'verification').resolve())
def clear_limits():
    with sqlite3.connect(DB) as db:db.execute('DELETE FROM sa1_limits')
def register(prefix):
    c=test_web.Client();email=prefix+'-'+secrets.token_hex(5)+'@example.test'
    c.call('register',name='Cuenta aislada',email=email,password='Original-Local-8096')
    return c,email

if '--security-only' not in sys.argv:
    clear_limits()
    runpy.run_path(str(test_web.ROOT/'verification/test_downloads_http.py'),run_name='__main__')
clear_limits();checks=[]
c,email=register('account');user=c.state['user']['id']
assert c.state['user']['is_admin'] is False
admin=test_web.Client();admin.call('login',email='admin@example.test',password='Admin-Local-Test-8096')
assert admin.state['user']['is_admin'] is True
admin.call('sync_anime',slug='not-a-real-catalog-entry',expected=404)
c.call('register',name='Impostor',email='admin@example.test',password='Original-Local-8096',expected=422,is_admin=True)
for action,data in [('sync',{}),('sync_catalog',{'page':1}),('sync_anime',{'slug':'naruto'})]:c.call(action,expected=403,**data)
unknown=next(a for a in c.call('catalog',get=True,page=187)['catalog']['items'] if not a['catalog_complete'])
anonymous=test_web.Client()
detail=anonymous.call('detail',get=True,slug=unknown['slug'])['detail'];assert detail['warning'] and not detail['anime']['catalog_complete']
assert not admin.call('detail',get=True,slug=unknown['slug'])['detail']['anime']['catalog_complete']
with sqlite3.connect(DB) as db:assert db.execute("SELECT COUNT(*) FROM sa1_limits WHERE name LIKE 'scraper-%'").fetchone()[0]==0
checks.append('admin_only_scraping_including_anonymous_detail_and_reserved_registration')

naruto=c.call('detail',get=True,slug='naruto')['detail'];episode=naruto['episodes'][0]
c.call('follow',slug='naruto',favorite=True,status='watching',score=9,notes='<script>private note</script>',is_admin=True)
assert c.last_raw.get('data') is None and len(c.last_raw['patch']['anime'])==1 and c.last_raw['patch']['jobs']==[]
c.call('watched',episode_id=episode['id'],watched=True)
assert c.last_raw.get('data') is None and c.last_raw['patch']['jobs']==[]
checks.append('follow_and_watched_return_only_changed_anime')

backup=c.call('library_export',get=True)['library'];assert backup['entries'][0]['favorite'] is True and backup['entries'][0]['score']==9
assert backup['watched'][0]['number']=='1' and 'password' not in json.dumps(backup) and 'token' not in json.dumps(backup)
other,other_email=register('import')
other_user=other.state['user']['id']
assert other.call('library_export',get=True)['library']['entries']==[]
other.call('library_import',library=backup)
assert next(a for a in other.state['anime'] if a['slug']=='naruto')['watched']==1
assert other.call('library_export',get=True)['library']['entries']==backup['entries']
other.call('library_import',library=backup);assert next(a for a in other.state['anime'] if a['slug']=='naruto')['watched']==1
bad=copy.deepcopy(backup);bad['entries'][0]['score']=99
other.call('library_import',library=bad,expected=422)
assert other.call('library_export',get=True)['library']['entries']==backup['entries']
bad=copy.deepcopy(backup);bad['entries'][0]['slug']=['naruto'];other.call('library_import',library=bad,expected=422)
checks.append('library_json_roundtrip_merge_validation_and_account_isolation')

codes=c.call('account_recovery_codes',current_password='Original-Local-8096')['recovery_codes']
assert len(codes)==10 and len(set(codes))==10
with sqlite3.connect(DB) as db:
    hashes=[row[0] for row in db.execute('SELECT code_hash FROM sa1_recovery WHERE user_id=?',(user,))]
assert len(hashes)==10 and all(len(value)==64 for value in hashes) and not any(code.replace('-','') in hashes for code in codes)
assert c.call('account',get=True)['account']['recovery_remaining']==10
checks.append('ten_unique_recovery_codes_stored_only_as_hashes')

parallel=test_web.Client();parallel.call('login',email=email,password='Original-Local-8096')
c.call('account_password',current_password='wrong',new_password='Changed-Local-8096',password_confirm='Changed-Local-8096',expected=403)
c.call('account_password',current_password='Original-Local-8096',new_password='Changed-Local-8096',password_confirm='different',expected=422)
c.call('account_password',current_password='Original-Local-8096',new_password='Changed-Local-8096',password_confirm='Changed-Local-8096')
assert c.state['user']['id']==user and parallel.call('state',get=True)['data']['user'] is None
checks.append('password_change_requires_current_password_confirmation_and_revokes_other_sessions')

recover=test_web.Client()
recover.call('account_recover',email=email,recovery_code='f'*32,new_password='Recovered-Local-8096',expected=403)
recovered=recover.call('account_recover',email=email,recovery_code=codes[0],new_password='Recovered-Local-8096',password_confirm='Recovered-Local-8096')
assert recovered['data']['user'] is None
assert c.call('state',get=True)['data']['user'] is None
recover.call('account_recover',email=email,recovery_code=codes[0],new_password='Should-Not-Apply-8096',expected=403)
c.call('login',email=email,password='Recovered-Local-8096');assert c.call('account',get=True)['account']['recovery_remaining']==9
after_recovery=c.call('library_export',get=True)['library']
assert {k:v for k,v in after_recovery.items() if k!='exported_at'}=={k:v for k,v in backup.items() if k!='exported_at'}
checks.append('recovery_code_single_use_revokes_sessions_and_keeps_library')
fresh=c.call('account_recovery_codes',current_password='Recovered-Local-8096')['recovery_codes']
assert len(fresh)==10
recover.call('account_recover',email=email,recovery_code=codes[1],new_password='Should-Not-Apply-8096',expected=403)
checks.append('rotating_recovery_codes_invalidates_previous_codes')

clear_limits();perf,perf_email=register('payload');perf_user=perf.state['user']['id']
with sqlite3.connect(DB) as db:
    ids=[row[0] for row in db.execute("SELECT id FROM sa1_episodes WHERE slug='bleach' ORDER BY number_value LIMIT 2000")]
    db.executemany('INSERT INTO sa1_jobs(user_id,episode_id,language,server,height,status,added_at,bytes,sha256) VALUES(?,?,?,?,?,?,?,?,?)',[(perf_user,id,'SUB','MP4Upload',1080,'confirmed',1,1048576,'a'*64) for id in ids])
perf.call('state',get=True);full_bytes=perf.last_bytes;assert len(perf.state['jobs'])==80 and perf.state['queue_totals']['confirmed']==2000
perf.call('follow',slug='naruto',favorite=True);patch_bytes=perf.last_bytes
assert len(perf.state['jobs'])==80 and perf.last_raw['patch']['jobs']==[] and patch_bytes<full_bytes/20
checks.append('2000_jobs_follow_payload_reduced_without_losing_client_queue')
request=urllib.request.Request(test_web.BASE+'actions.php',data=json.dumps({'action':'follow','slug':'naruto','favorite':False}).encode(),headers={'Content-Type':'application/json','X-CSRF-Token':perf.csrf})
legacy=json.load(perf.opener.open(request,timeout=20))
assert legacy['ok'] and 'patch' not in legacy and len(legacy['data']['jobs'])==2000
checks.append('already_open_legacy_clients_keep_snapshot_compatibility')

other.call('account_delete',current_password='Original-Local-8096',confirmation='NO',expected=422)
other.call('account_delete',current_password='wrong',confirmation='ELIMINAR',expected=403)
deleted=other.call('account_delete',current_password='Original-Local-8096',confirmation='ELIMINAR');assert deleted['data']['user'] is None
with sqlite3.connect(DB) as db:
    assert not db.execute('SELECT id FROM sa1_users WHERE email=?',(other_email,)).fetchone()
    for table in ['sa1_follow','sa1_watched','sa1_jobs','sa1_preferences','sa1_history','sa1_recovery']:
        assert db.execute('SELECT COUNT(*) FROM '+table+' WHERE user_id=?',(other_user,)).fetchone()[0]==0
assert c.call('library_export',get=True)['library']['entries']==backup['entries']
admin.call('account_delete',current_password='Admin-Local-Test-8096',confirmation='ELIMINAR',expected=422)
checks.append('account_delete_requires_password_and_explicit_confirmation_protects_admin_and_other_accounts')
result={'ok':True,'checks':checks,'full_state_bytes':full_bytes,'follow_patch_bytes':patch_bytes,'reduction_percent':round(100*(1-patch_bytes/full_bytes),2),'fixtures_only':True}
(test_web.ROOT/'verification/hardening-http-check.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
