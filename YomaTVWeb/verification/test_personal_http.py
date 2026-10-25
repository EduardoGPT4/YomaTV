"""Account features against disposable SQLite and the local MAL mock only."""
import json,secrets,sqlite3,time
import test_web,test_mal
test_web.BASE='http://127.0.0.1:8096/'
checks=[]
def sql(query,args=()):
    with sqlite3.connect(test_mal.DB) as d:return d.execute(query,args).fetchall()
c=test_web.Client();c.call('personal',get=True,expected=401)
c.call('register',name='Personal QA',email='personal-'+secrets.token_hex(5)+'@example.test',password='Personal-Local-Test-8096')
user=c.state['user']['id'];ep=sql("SELECT id FROM sa1_episodes WHERE slug='naruto' AND number='6'")[0][0]
c.call('player',get=True,episode_id=ep,expected=405)
p=c.call('player',episode_id=ep)['player'];key=p['playback']['session_key']
assert c.call('player_state',get=True,episode_id=ep)['player_state'] is not None
assert sql('SELECT session_key FROM sa1_playback WHERE user_id=? AND episode_id=?',(user,ep))[0][0]==key
checks.append('opening_is_post_only_and_reading_state_does_not_invalidate_session')
c.call('personal_save',kind='intro',key='naruto',data={'start':80,'end':20},expected=422)
c.call('personal_save',kind='intro',key='naruto',data={'start':10,'end':95})
bookmark=secrets.token_hex(16);collection=secrets.token_hex(8)
c.call('personal_save',kind='bookmark',key=bookmark,data={'slug':'naruto','number':'6','position':321.5,'note':'Private scene <b>test</b>'})
c.call('personal_save',kind='collection',key=collection,data={'name':'With friends','slugs':['naruto']})
assert not test_mal.control()['patch_calls']
notes=c.call('player_notes',episode_id=ep)['personal'];assert notes['intro']['end']==95 and notes['bookmarks'][0]['data']['position']==321.5
checks.append('intro_scene_bookmarks_and_collections_are_private_and_do_not_write_mal')
other=test_web.Client();other.call('register',name='Other QA',email='personal-'+secrets.token_hex(5)+'@example.test',password='Personal-Local-Test-8096')
assert not other.call('personal',get=True)['personal']['collections']
other.call('personal_delete',kind='collection',key=collection)
assert c.call('personal',get=True)['personal']['collections'][0]['key']==collection
checks.append('personal_data_cannot_be_read_or_deleted_by_another_account')
radio={'favorites':['abcdefghijk'],'lists':[{'id':secrets.token_hex(8),'name':'Night','ids':['abcdefghijk']}]}
revision=c.call('personal_save',kind='radio',key='library',expected_revision='',data=radio)['saved']['revision']
c.call('personal_save',kind='radio',key='library',expected_revision='',data=radio,expected=409)
c.call('personal_save',kind='radio',key='library',expected_revision='a'*32,data=radio,expected=409)
radio['favorites'].append('lmnopqrstuv')
saved=c.call('personal_save',kind='radio',key='library',expected_revision=revision,data=radio)['saved']
assert len(saved['favorites'])==2
c2=test_web.Client();c2.call('login',email=c.state['user']['email'],password='Personal-Local-Test-8096')
assert c2.call('personal',get=True)['personal']['radio']['revision']==saved['revision']
checks.append('radio_sync_survives_new_sessions_and_stale_devices_cannot_overwrite_changes')
c.call('player_save',episode_id=ep,mode='first',revision=p['playback']['revision'],session_key=key,sequence=1,position=1200,duration=1380)
c.call('watched',episode_id=ep,watched=True)
home=c.call('home',get=True)['home'];resume=next(a for a in home['continue'] if a['slug']=='naruto');assert resume['episode_id']==ep and resume['position']==1200
checks.append('continue_home_keeps_unfinished_tail_even_after_local_watched_mark')
c.call('save_filter',name='Movies',filters={'category':'movie'})
c.call('personal_save',kind='options',key='account',data={'shared':True,'forget_pc':True,'onboarding_done':True})
export=c.call('library_export',get=True)['library'];extra=export['extras']
assert extra['positions'][0]['position']==1200 and extra['bookmark'] and extra['collection'] and extra['radio'] and extra['filters']
serialized=json.dumps(extra);assert all(s not in serialized for s in ['token_cipher','session_key','csrf','recovery','password_hash'])
other.call('library_import',library=export)
assert other.call('personal',get=True)['personal']['collections'][0]['data']['name']=='With friends'
assert other.call('player_state',get=True,episode_id=ep)['player_state']['position']==1200
bad={**export,'extras':{**extra,'intro':[{'key':'naruto','data':{'start':0,'end':99999}}]}}
other.call('library_import',library=bad,expected=422)
checks.append('expanded_export_import_restores_account_features_without_credentials_and_validates_extras_atomically')
# A large queue is summarized initially; ordered chapter pages fetch only their own 36 rows.
now=int(time.time())
sql("INSERT OR IGNORE INTO sa1_episodes(slug,number,number_value,url) SELECT 'naruto','1000',1000,'https://animeav1.com/media/naruto/1000'")
eps=sql("SELECT id FROM sa1_episodes WHERE slug='naruto' ORDER BY number_value LIMIT 100")
for (id_,) in eps:sql("INSERT OR IGNORE INTO sa1_jobs(user_id,episode_id,language,server,height,status,added_at) VALUES(?,?,'SUB','MP4Upload',1080,'pending',?)",(user,id_,now))
state=c.call('state',get=True)['data'];assert len(state['jobs'])<=160 and state['queue_totals']['total']==len(eps)
page1=c.call('queue_page',get=True,slug='naruto',page=1)['queue_page'];page2=c.call('queue_page',get=True,slug='naruto',page=2)['queue_page']
assert len(page1['items'])==36 and len(page2['items'])==36
assert max(float(e['number']) for e in page1['items'])<min(float(e['number']) for e in page2['items'])
assert not {r['id'] for r in page1['items']}&{r['id'] for r in page2['items']}
assert not other.call('queue_page',get=True,slug='naruto')['queue_page']['items']
checks.append('large_queues_are_bounded_and_lazy_pages_are_numeric_disjoint_and_account_scoped')
job=page1['items'][0]['id'];device='a'*32
c.call('download_events',installation=state['installation'],device_id=device,items=[{'id':job,'state':'failed','attempts':3,'error_kind':'connection'}])
failed=c2.call('queue_page',get=True,slug='naruto',phase='failed')['queue_page'];assert failed['items'][0]['id']==job and failed['events'][0]['attempts']==3
assert sql('SELECT status FROM sa1_jobs WHERE user_id=? AND id=?',(user,job))[0][0]=='pending'
c.call('download_events',installation=state['installation'],device_id=device,items=[{'id':job,'state':'failed','attempts':4,'error_kind':'connection'},{'id':job,'state':'invalid','attempts':0}],expected=422)
assert sql('SELECT attempts FROM sa1_job_events WHERE user_id=? AND job_id=?',(user,job))[0][0]==3
other.call('download_events',installation=state['installation'],device_id=device,items=[{'id':job,'state':'completed','attempts':1}])
assert c.call('queue_page',get=True,slug='naruto',phase='failed')['queue_page']['total']==1
checks.append('observed_pc_failures_persist_without_faking_verified_downloads_or_crossing_accounts')
c.call('support_report',expected=403);c.call('radio_report',track='abcdefghijk',reason='association')
c.call('personal_save',csrf=False,expected=403,kind='options',key='account',data={})
c.call('catalog_task',get=True,slug='naruto',episode_id=999999,expected=404)
# Empty central queue: an ordinary user can run a bounded central worker without any network calls.
sql('DELETE FROM sa1_catalog_tasks');sql('UPDATE sa1_catalog_freshness SET episodes_at=?',(now,))
assert c.call('catalog_pulse')['catalog_worker']['skipped']
checks.append('csrf_admin_boundaries_and_central_member_worker_do_not_grant_arbitrary_scraping')
other_user=other.state['user']['id']
other.call('account_delete',current_password='Personal-Local-Test-8096',confirmation='ELIMINAR')
assert not sql('SELECT 1 FROM sa1_personal_data WHERE user_id=?',(other_user,))
assert not sql('SELECT 1 FROM sa1_job_events WHERE user_id=?',(other_user,))
checks.append('deleting_test_account_cascades_new_personal_data_and_device_events')
result={'ok':True,'checks':checks,'real_mal_changes':False,'real_downloads':0}
(test_web.ROOT/'verification/personal-http-check.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(result))
