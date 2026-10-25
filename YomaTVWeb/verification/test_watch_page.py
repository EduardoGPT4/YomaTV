"""Manual MAL marking without media telemetry, against the local mock only."""
import json,secrets,sqlite3,time
import test_web,test_mal
test_web.BASE='http://127.0.0.1:8096/'
checks=[]
def sql(query,args=()):
    with sqlite3.connect(test_mal.DB) as db:return db.execute(query,args).fetchall()
def main():
    test_mal.control(mode='normal',updates={},deleted=[],refreshes=0,patch_calls=[])
    c=test_web.Client();c.call('watch_manual',episode_id=1,expected=401)
    c.call('watch_manual',get=True,expected=405)
    c.call('register',name='Watch page QA',email='page-'+secrets.token_hex(6)+'@example.test',password='Local-Page-Test-8096')
    uid=c.state['user']['id'];eps={str(number):int(id) for id,number in sql("SELECT id,number FROM sa1_episodes WHERE slug='naruto'")}
    admin=test_web.Client();admin.call('login',email='admin@example.test',password='Admin-Local-Test-8096')
    c.call('player_servers',episode_id=eps['6'],expected=403)
    admin.call('player_servers',get=True,episode_id=eps['6'],expected=405)
    admin.call('player_servers',csrf=False,episode_id=eps['6'],expected=403)
    original=sql('SELECT id,mirrors,mirrors_at FROM sa1_episodes WHERE id IN (?,?)',(eps['6'],eps['9']))
    reset=int(time.time())+90
    sql('UPDATE sa1_episodes SET mirrors=?,mirrors_at=0 WHERE id=?',(json.dumps([{'server':'MP4Upload','language':'SUB','url':'https://www.mp4upload.com/abc123def456'}]),eps['6']))
    sql("UPDATE sa1_episodes SET mirrors='[]',mirrors_at=0 WHERE id=?",(eps['9'],))
    sql("INSERT OR REPLACE INTO sa1_limits(name,hits,reset_at) VALUES('scraper-global',121,?)",(reset,))
    for number in ['6','9']:
        page=admin.call('player',episode_id=eps[number])['player']
        assert page['episode']['id']==eps[number] and page['server_refresh']['can_refresh']
        assert bool(page['servers'])==(number=='6')
        key=page['playback']['session_key']
        r=admin.call('player_servers',episode_id=eps[number])['player_servers']
        assert r['server_refresh']['state']=='waiting' and r['server_refresh']['retry_at']>=reset
        assert bool(r['servers'])==(number=='6')
        assert sql('SELECT session_key FROM sa1_playback WHERE user_id=? AND episode_id=?',(admin.state['user']['id'],eps[number]))[0][0]==key
    assert r['server_refresh']['message']
    sql("DELETE FROM sa1_limits WHERE name LIKE 'scraper-%'")
    sql('UPDATE sa1_episodes SET mirrors_at=? WHERE id=?',(int(time.time()),eps['6']))
    assert admin.call('player_servers',episode_id=eps['6'])['player_servers']['servers'][0]['url']=='https://www.mp4upload.com/embed-abc123def456.html'
    assert not sql("SELECT name FROM sa1_limits WHERE name LIKE 'scraper-%'")
    for episode,mirrors,at in original:sql('UPDATE sa1_episodes SET mirrors=?,mirrors_at=? WHERE id=?',(mirrors,at,episode))
    checks.append('scraper_quota_cannot_hide_cached_or_empty_watch_page_and_refresh_preserves_playback_session')
    checks.append('server_refresh_requires_admin_post_csrf_and_fresh_cache_never_scrapes')
    p=c.call('player',episode_id=eps['6'])['player']
    c.call('offline_plan',get=True,episode_id=eps['6'],expected=405)
    c.call('offline_plan',csrf=False,episode_id=eps['6'],expected=403)
    c.call('offline_plan',episode_id=eps['6'],language='UNKNOWN',expected=422)
    plan=c.call('offline_plan',episode_id=eps['6'],language='SUB')['offline_plan']
    assert plan['owner']==uid and plan['slug']=='naruto' and len(plan['episodes'])>=220
    assert plan['progress_revision']==p['playback']['revision']
    assert plan['episodes'][5]['episode_id']==eps['6'] and plan['episodes'][5]['next_episode_id']==eps['7']
    assert sql('SELECT session_key FROM sa1_playback WHERE user_id=? AND episode_id=?',(uid,eps['6']))[0][0]==p['playback']['session_key']
    mobile=c.call('mobile_session',get=True)['mobile_session']
    assert mobile['user_id']==uid and mobile['csrf'] and 'token' not in json.dumps(mobile).lower()
    checks.append('android_download_plan_is_account_scoped_csrf_protected_and_preserves_active_playback_session')
    assert p['anime']['title'] and len(p['chapters'])>=220
    assert all(isinstance(ep['watched'],bool) for ep in p['chapters'])
    assert p['related']['source_genres'] and p['related']['genres']
    assert all(a['slug']!='naruto' and a['shared_count']>0 for a in p['related']['genres'])
    assert any(not a['confirmed'] for a in p['related']['saga'])
    sql("INSERT OR REPLACE INTO sa1_relations(slug,target,relation,evidence,state,updated_at) VALUES('naruto','one-piece','prequel','Fixture only','pending',0)")
    assert not any(a['slug']=='one-piece' for a in c.call('player',episode_id=eps['6'])['player']['related']['saga'])
    sql("UPDATE sa1_relations SET state='approved' WHERE slug='naruto' AND target='one-piece'")
    related=c.call('player',episode_id=eps['6'])['player']['related']
    assert related['saga'][0]['slug']=='one-piece' and related['saga'][0]['reason']=='Precuela' and related['saga'][0]['confirmed']
    sql("DELETE FROM sa1_relations WHERE slug='naruto' AND target='one-piece'")
    checks.append('recommendations_use_public_catalog_genres_and_only_approved_relations')
    c.call('watch_manual',episode_id=eps['6'],mal_account_id=0,progress_revision=p['playback']['revision'],expected=422)
    assert not sql('SELECT 1 FROM sa1_watched WHERE user_id=?',(uid,))
    checks.append('anonymous_post_and_unconnected_account_cannot_mark')
    test_mal.callback(c,test_mal.flow(c));c.call('mal_search',query='Naruto');c.call('mal_link',mal_id=20,slug='naruto')
    p=c.call('player',episode_id=eps['6'])['player'];identity=p['mal_account_id'];revision=p['playback']['revision']
    assert p['mal']['connected'] and p['mal']['linked']
    def mark(number,**extra):
        return c.call('watch_manual',episode_id=eps[str(number)],mal_account_id=identity,progress_revision=revision,**extra)
    mark(6,csrf=False,expected=403)
    before=len(test_mal.control()['patch_calls'])
    result=mark(6)['watch_sync'];assert result['state']=='synced'
    remote=test_mal.control()['updates']['20'];assert remote['num_episodes_watched']==6 and remote['score']==8
    assert len(test_mal.control()['patch_calls'])==before+1
    p=c.call('player',episode_id=eps['6'])['player']
    assert p['mal']['watched']==6 and next(ep for ep in p['chapters'] if ep['id']==eps['6'])['watched']
    checks.append('eye_updates_mal_without_position_or_duration_and_preserves_score')
    before=len(test_mal.control()['patch_calls']);mark(6)
    assert len(test_mal.control()['patch_calls'])==before
    test_mal.control(updates={'20':{'status':'watching','score':5,'num_episodes_watched':30}})
    mark(7);assert test_mal.control()['updates']['20']['num_episodes_watched']==30
    checks.append('repeated_manual_marks_are_idempotent_and_never_reduce_remote_progress')
    c.call('watch_manual',episode_id=eps['8'],mal_account_id=identity+1,progress_revision=revision,expected=409)
    assert not sql('SELECT 1 FROM sa1_watched WHERE user_id=? AND episode_id=?',(uid,eps['8']))
    c.call('watch_mode',slug='naruto',mode='rewatch')
    mark(8,expected=409)
    p=c.call('player',episode_id=eps['8'])['player'];revision=p['playback']['revision']
    c.call('watch_scrobble',episode_id=eps['8'],mal_account_id=identity,progress_revision=revision,position=8,duration=10)
    assert not sql('SELECT 1 FROM sa1_watched WHERE user_id=? AND episode_id=?',(uid,eps['8']))
    test_mal.control(updates={'20':{'status':'watching','score':5,'num_episodes_watched':7}})
    assert mark(8)['watch_sync']['state']=='synced'
    assert test_mal.control()['updates']['20']['num_episodes_watched']==8
    checks.append('old_identity_or_revision_is_rejected_and_rewatch_requires_explicit_manual_intent')
    test_mal.control(mode='offline')
    result=mark(9)['watch_sync'];assert result['state']=='pending' and result['next_retry']>0
    assert sql('SELECT 1 FROM sa1_watched WHERE user_id=? AND episode_id=?',(uid,eps['9']))
    checks.append('manual_mark_uses_the_persistent_retry_outbox_on_mal_outage')
    test_mal.control(mode='normal')
    result={'ok':True,'checks':checks,'real_mal_changes':False}
    (test_web.ROOT/'verification/watch-page-http-check.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    print(json.dumps(result))
if __name__=='__main__':main()
