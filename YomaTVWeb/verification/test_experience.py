"""Delivery 3 against disposable SQLite and mock MAL only."""
import json,secrets,sqlite3
import test_web,test_mal
test_web.BASE='http://127.0.0.1:8096/'
checks=[]
def sql(q,args=()):
    with sqlite3.connect(test_mal.DB) as db:return db.execute(q,args).fetchall()
def main():
    test_mal.control(mode='normal',updates={},deleted=[],patch_calls=[],refreshes=0)
    c=test_web.Client();c.call('player_save',expected=401)
    c.call('register',name='Experience QA',email='experience-'+secrets.token_hex(5)+'@example.test',password='Local-Experience-Test-8096');user=c.state['user']['id']
    test_mal.callback(c,test_mal.flow(c));c.call('mal_refresh',offset=0);c.call('mal_refresh',offset=50)
    c.call('mal_link',mal_id=20,slug='naruto')
    eps={n:i for i,n in sql("SELECT id,number FROM sa1_episodes WHERE slug='naruto'")}
    # Cached mirrors avoid any AnimeAV1 requests in this test.
    for n in ['6','7']:
        sql('UPDATE sa1_episodes SET mirrors=?,mirrors_at=strftime(\'%s\',\'now\') WHERE id=?',(json.dumps([{'server':'MP4Upload','language':'SUB','url':'https://www.mp4upload.com/embed-abcd12345678.html'}]),eps[n]))
    p=c.call('player',episode_id=eps['6'])['player']['playback']
    args={'episode_id':eps['6'],'mode':'first','revision':p['revision'],'session_key':p['session_key'],'sequence':2,'position':120.25,'duration':1380}
    assert c.call('player_save',**args)['position_saved']
    assert not c.call('player_save',**{**args,'sequence':1,'position':10})['position_saved']
    p2=c.call('player',episode_id=eps['6'])['player']['playback'];assert p2['position']==120.25
    assert not c.call('player_save',**{**args,'sequence':3,'position':5})['position_saved']
    c.call('player_save',**{**args,'duration':0},expected=422)
    checks.append('exact_position_persists_and_old_session_or_sequence_cannot_overwrite')
    sql('INSERT OR REPLACE INTO sa1_player_preferences(user_id,settings) VALUES(?,?)',(user,json.dumps({'rate':1.25,'autoplay_next':False})))
    sql('INSERT OR REPLACE INTO sa1_player_anime(user_id,slug,settings) VALUES(?,?,?)',(user,'naruto',json.dumps({'rate':2,'autoplay_next':False})))
    legacy=c.call('player',episode_id=eps['6'])['player']['playback']['preferences']
    assert legacy['autoplay_next'] and not legacy['anime_override'] and legacy['rate']==1.25
    c.call('player_settings',slug='naruto',settings={'rate':1.5,'volume':0.35,'muted':True,'server':'MP4Upload','language':'LAT','autoplay_next':False},anime_override=True)
    p3=c.call('player',episode_id=eps['6'])['player']['playback'];assert not p3['preferences']['anime_override'] and p3['preferences']['rate']==1.5 and p3['preferences']['autoplay_next']
    c.call('player_settings',slug='naruto',settings={'rate':3},expected=422)
    c.call('player_settings',slug='naruto',settings={'rate':1.25},anime_override=False)
    assert not c.call('player',episode_id=eps['6'])['player']['playback']['preferences']['anime_override']
    checks.append('global_preferences_and_always_on_next_override_legacy_disabled_and_per_anime_settings')
    c.call('watch_mode',slug='naruto',mode='rewatch')
    before=len(test_mal.control()['patch_calls']);p4=c.call('player',episode_id=eps['6'])['player']['playback']
    c.call('watch_scrobble',episode_id=eps['6'],position=1200,duration=1380,progress_revision=p3['revision'],expected=409)
    r=c.call('watch_scrobble',episode_id=eps['6'],position=1200,duration=1380,progress_revision=p4['revision'])
    assert r['watch_sync']['state']=='rewatched' and len(test_mal.control()['patch_calls'])==before
    assert not sql('SELECT 1 FROM sa1_watched WHERE user_id=? AND episode_id=?',(user,eps['6']))
    assert sql('SELECT 1 FROM sa1_rewatched WHERE user_id=? AND episode_id=?',(user,eps['6']))
    c.call('player_save',**{**args,'session_key':p4['session_key'],'mode':'rewatch','revision':p4['revision'],'sequence':1})
    checks.append('rewatch_is_separate_and_old_player_cannot_scrobble_after_mode_change')
    c.call('watched',episode_id=eps['7'],watched=True,progress_revision=p4['revision']);assert not sql('SELECT 1 FROM sa1_watched WHERE user_id=? AND episode_id=?',(user,eps['7']))
    assert next(ep for ep in c.call('detail',get=True,slug='naruto')['detail']['episodes'] if ep['id']==eps['7'])['rewatched']
    c.call('watch_mode',slug='naruto',mode='first');p5=c.call('player',episode_id=eps['6'])['player']['playback'];assert p5['position']==120.25
    c.call('watched',episode_id=eps['7'],watched=True)
    c.call('progress_reconcile',slug='naruto',direction='mal_to_web',confirmation='CORREGIR')
    assert not sql('SELECT 1 FROM sa1_watched WHERE user_id=? AND episode_id=?',(user,eps['7']))
    assert sql('SELECT COUNT(*) FROM sa1_watched WHERE user_id=? AND episode_id IN (SELECT id FROM sa1_episodes WHERE slug=?)',(user,'naruto'))[0][0]==5
    c.call('player_save',**{**args,'session_key':p5['session_key'],'revision':p5['revision'],'sequence':1},expected=409)
    c.call('mal_save',mal_id=20,status='watching',watched=2,score=8,expected=409)
    c.call('mal_save',mal_id=20,status='watching',watched=2,score=8,confirmation='CORREGIR')
    assert test_mal.control()['updates']['20']['num_episodes_watched']==2
    checks.append('explicit_downward_correction_reconciles_local_and_mal_and_fences_old_players')
    batch=c.call('mal_match_batch',page=1)['match_batch'];assert batch['items'] and 'candidates' in batch['items'][0]
    c.call('mal_link_batch',pairs=[{'mal_id':1002,'slug':'bleach'}],mal_account_id=batch['mal_account_id'])
    assert c.call('detail',get=True,slug='bleach')['detail']['anime']['mal']['confirmed']
    c.call('mal_link_batch',pairs=[{'mal_id':1002,'slug':'bleach'},{'mal_id':1002,'slug':'naruto'}],expected=422)
    checks.append('batch_matches_show_metadata_and_validate_whole_batch_before_write')
    p=c.call('queue_preview',slugs=['naruto'],mode='selected',episode_ids=[eps['6'],eps['7']])['preview'];assert p['eligible']==2
    assert not sql('SELECT 1 FROM sa1_jobs WHERE user_id=?',(user,))
    q=c.call('queue',slugs=['naruto'],mode='selected',episode_ids=p['episode_ids']);ids=q['queue_ids'];assert len(ids)==2
    p=c.call('queue_preview',slugs=['naruto'],mode='selected',episode_ids=[eps['6'],eps['7']])['preview'];assert p['eligible']==0 and p['queued']==2
    checks.append('preview_is_read_only_and_excludes_already_queued')
    job=ids[0];sql("UPDATE sa1_jobs SET status='confirmed' WHERE id=?",(job,));device='c'*32
    c.call('queue_redownload',job_id=job,device_id=device,confirmation='REDESCARGAR',expected=409)
    c.call('file_presence',device_id=device,items=[{'web_id':job,'present':True,'known':True}])
    c.call('queue_redownload',job_id=job,device_id=device,confirmation='REDESCARGAR',expected=409)
    c.call('file_presence',device_id=device,items=[{'web_id':job,'present':None,'known':True}])
    assert c.call('presence',get=True,slug='naruto')['file_presence'][0]['present']==1
    c.call('file_presence',device_id=device,items=[{'web_id':job,'present':False,'known':True}])
    reset=c.call('queue_redownload',job_id=job,device_id=device,confirmation='REDESCARGAR');assert reset['patch']['reset_jobs']==[job]
    c.call('receipt',receipt={'format':'seasonav1.web-results/v1','plans':[{'installation':c.state['installation'],'items':[{'web_id':job,'slug':'naruto','number':next(j['number'] for j in c.state['jobs'] if j['id']==job),'language':'SUB','status':'completed','sha256':'d'*64,'bytes':2048}]}]})
    assert sql('SELECT status FROM sa1_jobs WHERE id=?',(job,))[0][0]=='pending'
    revision=c.call('export',job_ids=[job])['plan']['items'][0]['request_revision'];assert len(revision)==32
    checks.append('old_receipt_cannot_confirm_new_redownload_revision')
    other=test_web.Client();other.call('register',name='Other QA',email='experience-'+secrets.token_hex(5)+'@example.test',password='Local-Experience-Test-8096')
    assert not other.call('presence',get=True,slug='naruto')['file_presence']
    assert not other.call('player',episode_id=eps['6'])['player']['playback']['position']
    checks.append('presence_is_device_and_user_scoped_and_redownload_requires_recent_missing_file')
    result={'ok':True,'count':len(checks),'checks':checks,'real_mal_changes':False,'real_video_downloads':0}
    (test_web.ROOT/'verification/experience-check.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
