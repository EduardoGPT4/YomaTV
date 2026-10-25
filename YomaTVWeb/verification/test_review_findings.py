"""Reproduce review findings using disposable accounts and the MAL mock only."""
import json,secrets,sqlite3,time
import test_web,test_mal
test_web.BASE='http://127.0.0.1:8096/'
def sql(query,args=()):
    with sqlite3.connect(test_mal.DB) as db:return db.execute(query,args).fetchall()
test_mal.control(mode='normal',updates={},deleted=[],refreshes=0,patch_calls=[])
c=test_web.Client();c.call('register',name='Review QA',email='review-'+secrets.token_hex(5)+'@example.test',password='Review-Local-Only-8096')
test_mal.callback(c,test_mal.flow(c));c.call('mal_refresh',offset=0)
uid=c.state['user']['id']
link=sql("SELECT mal_id,confirmed FROM sa1_mal_links WHERE user_id=? AND slug='naruto'",(uid,))[0]
assert link==(20,0),link
ep=sql("SELECT id FROM sa1_episodes WHERE slug='naruto' AND number='6'")[0][0]
p=c.call('player',episode_id=ep)['player']
sync=c.call('watch_scrobble',episode_id=ep,position=1200,duration=1380,progress_revision=p['playback']['revision'],mal_account_id=p['mal_account_id'])['watch_sync']
assert sync['state']=='blocked' and not test_mal.control()['updates']
assert sql('SELECT 1 FROM sa1_watched WHERE user_id=? AND episode_id=?',(uid,ep))
c.call('progress_reconcile',slug='naruto',direction='web_to_mal',confirmation='CORREGIR',expected=409)
c.call('mal_confirm',slug='naruto',mal_id=20,mal_account_id=p['mal_account_id'],confirmation='CONFIRMAR')
assert c.call('watch_retry')['watch_sync']['state']=='synced'
assert test_mal.control()['updates']['20']['num_episodes_watched']==6
findings=['unconfirmed_link_blocks_mal_but_keeps_local_mark_and_confirmation_resumes_outbox']
now=int(time.time());key=secrets.token_hex(32)
sql('UPDATE sa1_episodes SET mirrors_at=0 WHERE id=?',(ep,))
sql("INSERT INTO sa1_catalog_tasks(task_key,kind,target,payload,state,priority,attempts,next_retry,lock_until,error,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",(key,'mirrors',str(ep),'{}','failed',10,5,0,0,'fixture',now,now))
# Use the same stable key as the production enqueue helper, not an arbitrary task.
import hashlib
sql('UPDATE sa1_catalog_tasks SET task_key=? WHERE task_key=?',(hashlib.sha256(('mirrors:'+str(ep)).encode()).hexdigest(),key))
result=c.call('catalog_request',slug='naruto',episode_id=ep)
assert result['task']['state']=='failed' and 'falló' in result['message']
findings.append('failed_catalog_task_is_quarantined_and_message_is_honest')
report={'ok':True,'findings_reproduced':findings,'real_mal_changes':False,'real_video_downloads':0}
(test_web.ROOT/'verification/project-review-findings.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps(report))
