"""80% position scrobbling against a local MAL provider; no real list changes."""
import json,secrets,sqlite3
import test_web,test_mal
test_web.BASE='http://127.0.0.1:8096/'
DB=test_mal.DB
checks=[]
def sql(q,args=()):
    with sqlite3.connect(DB) as d:return d.execute(q,args).fetchall()
def main():
    test_mal.control(mode='normal',updates={},deleted=[],refreshes=0,patch_calls=[])
    c=test_web.Client();c.call('watch_scrobble',episode_id=1,position=8,duration=10,expected=401)
    c.call('watch_scrobble',get=True,expected=405)
    email='watch-'+secrets.token_hex(6)+'@example.test';password='Local-Watch-Test-8096'
    c.call('register',name='Watch QA',email=email,password=password);id=c.state['user']['id']
    q=test_mal.flow(c);test_mal.callback(c,q)
    c.call('mal_search',query='Naruto');c.call('mal_search',query='One Piece')
    c.call('mal_link',mal_id=20,slug='naruto')
    eps={n:i for i,n in sql("SELECT id,number FROM sa1_episodes WHERE slug='naruto'")}
    def mark(n,**args):return c.call('watch_scrobble',episode_id=eps[str(n)],position=8,duration=10,**args)
    c.call('watch_scrobble',csrf=False,expected=403,episode_id=eps['6'],position=8,duration=10)
    checks.append('auth_csrf_and_post_required')
    for pos,dur in [(7.999,10),(8,0),(8,'NaN'),(25,10),(-1,10)]:c.call('watch_scrobble',expected=422,episode_id=eps['6'],position=pos,duration=dur)
    assert not sql('SELECT 1 FROM sa1_watched WHERE user_id=? AND episode_id=?',(id,eps['6']))
    checks.append('invalid_or_below_80_positions_cannot_mark_an_episode')
    result=mark(6)['watch_sync'];assert result['state']=='synced'
    remote=test_mal.control()['updates']['20'];assert remote['num_episodes_watched']==6 and remote['score']==8
    assert 'score' not in test_mal.control()['patch_calls'][-1]['fields']
    assert sql('SELECT 1 FROM sa1_watched WHERE user_id=? AND episode_id=?',(id,eps['6']))
    checks.append('exact_80_marks_web_and_mal_without_overwriting_score')
    before=len(test_mal.control()['patch_calls']);mark(6)
    assert len(test_mal.control()['patch_calls'])==before
    assert sql('SELECT COUNT(*) FROM sa1_watched WHERE user_id=? AND episode_id=?',(id,eps['6']))[0][0]==1
    checks.append('duplicate_callback_does_not_add_marks_or_repeat_remote_patch')
    test_mal.control(updates={'20':{'status':'watching','score':3,'num_episodes_watched':50}})
    mark(7);assert test_mal.control()['updates']['20']['num_episodes_watched']==50 and test_mal.control()['updates']['20']['score']==3
    assert len(test_mal.control()['patch_calls'])==before
    checks.append('fresh_remote_progress_is_never_reduced_by_stale_web_data')
    test_mal.control(mode='offline',updates={'20':{'status':'watching','score':3,'num_episodes_watched':6}})
    result=mark(8)['watch_sync'];assert result['state']=='pending' and result['next_retry']>0
    assert sql('SELECT 1 FROM sa1_watched WHERE user_id=? AND episode_id=?',(id,eps['8']))
    assert c.call('watch_retry')['watch_sync']['state']=='idle'
    sql("UPDATE sa1_watch_sync SET next_retry=0,lock_until=strftime('%s','now')+90 WHERE user_id=?",(id,))
    assert c.call('watch_retry')['watch_sync']['state']=='idle'
    assert c.call('home',get=True)['home']['watch_pending']['next_retry']>0
    sql('UPDATE sa1_watch_sync SET lock_until=0 WHERE user_id=?',(id,))
    checks.append('mal_outage_preserves_web_mark_and_backoff_in_persistent_outbox')
    c2=test_web.Client();c2.call('login',email=email,password=password)
    assert c2.call('home',get=True)['home']['watch_pending']['count']==1
    sql('UPDATE sa1_watch_sync SET next_retry=0 WHERE user_id=?',(id,));test_mal.control(mode='normal')
    assert c2.call('watch_retry')['watch_sync']['state']=='synced'
    assert test_mal.control()['updates']['20']['num_episodes_watched']==8
    assert c2.call('home',get=True)['home']['watch_pending']['count']==0
    checks.append('outbox_survives_new_session_and_retries_to_confirm_mal')
    other=test_web.Client();other.call('register',name='Other watch',email='watch-'+secrets.token_hex(6)+'@example.test',password=password)
    assert other.call('home',get=True)['home']['watch_pending']['count']==0
    r=other.call('watch_scrobble',episode_id=eps['6'],position=9,duration=10)['watch_sync'];assert r['state']=='blocked' and 'Vincula' in r['message']
    other.call('mal_link',mal_id=20,slug='naruto')
    r=other.call('watch_scrobble',episode_id=eps['6'],position=9,duration=10)['watch_sync'];assert r['state']=='blocked' and 'Conecta' in r['message']
    test_mal.callback(other,test_mal.flow(other));assert other.call('home',get=True)['home']['watch_pending']['count']==1
    assert other.call('watch_retry')['watch_sync']['state']=='synced'
    checks.append('unlinked_disconnected_and_other_accounts_are_safe_and_can_resume')
    before=len(test_mal.control()['patch_calls'])
    sql("INSERT OR IGNORE INTO sa1_episodes(slug,number,number_value,url) VALUES('naruto','6.5',6.5,'https://animeav1.com/media/naruto/6.5')")
    special=sql("SELECT id FROM sa1_episodes WHERE slug='naruto' AND number='6.5'")[0][0]
    r=c.call('watch_scrobble',episode_id=special,position=8,duration=10)['watch_sync'];assert r['state']=='blocked'
    assert len(test_mal.control()['patch_calls'])==before
    sql('DELETE FROM sa1_watched WHERE episode_id=?',(special,));sql('DELETE FROM sa1_episodes WHERE id=?',(special,))
    checks.append('fractional_special_marks_only_web_without_invalid_mal_progress')
    mark(220);remote=test_mal.control()['updates']['20'];assert remote['status']=='completed' and remote['num_episodes_watched']==220 and remote['score']==3
    mark(6);assert test_mal.control()['updates']['20']==remote
    checks.append('last_episode_completes_mal_and_rewatch_does_not_reset_it')
    test_mal.control(mode='offline');mark(7);c.call('mal_link',mal_id=21,slug='naruto');test_mal.control(mode='normal')
    sql('UPDATE sa1_watch_sync SET next_retry=0 WHERE user_id=?',(id,));before=len(test_mal.control()['patch_calls'])
    r=c.call('watch_retry')['watch_sync'];assert r['state']=='blocked' and 'cambió' in r['message']
    assert len(test_mal.control()['patch_calls'])==before
    checks.append('changing_a_title_link_cannot_send_an_old_pending_mark_to_new_id')
    result={'ok':True,'count':len(checks),'checks':checks,'real_mal_changes':False}
    (test_web.ROOT/'verification/watch-auto-check.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
