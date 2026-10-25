"""Delivery 1 regressions against disposable SQLite and local MAL only."""
import json
import secrets
import sqlite3
import test_web
import test_mal

test_web.BASE = 'http://127.0.0.1:8096/'
DB = test_mal.DB
checks = []

def query(statement, args=()):
    with sqlite3.connect(DB) as connection:
        return connection.execute(statement, args).fetchall()

def main():
    test_mal.control(mode='normal', profile={'id':12345,'name':'LocalMAL_Test'}, updates={}, deleted=[], patch_calls=[])
    c = test_web.Client()
    c.call('register', name='Reliability QA', email='delivery1-'+secrets.token_hex(5)+'@example.test', password='Delivery1-Local-Only')
    user = c.state['user']['id']
    test_mal.callback(c, test_mal.flow(c))
    c.call('mal_search',query='Naruto')
    c.call('mal_link', mal_id=20, slug='naruto')
    c.call('follow',slug='naruto',notes='Keep local library',favorite=True)
    episodes = {number:id for id,number in query("SELECT id,number FROM sa1_episodes WHERE slug='naruto'")}
    def mark(number):
        return c.call('watch_scrobble',episode_id=episodes[str(number)],position=8,duration=10)['watch_sync']

    test_mal.control(mode='offline')
    assert mark(8)['state']=='pending'
    c.call('mal_disconnect')
    assert mark(2)['state']=='blocked'
    assert query('SELECT target,mal_account_id FROM sa1_watch_sync WHERE user_id=?',(user,))==[(8,12345)]
    checks.append('blocked_progress_keeps_episode8_after_episode2')

    test_mal.control(mode='normal')
    test_mal.callback(c,test_mal.flow(c))
    assert c.call('home',get=True)['home']['watch_pending']['count']==1
    assert c.call('watch_retry')['watch_sync']['state']=='synced'
    assert test_mal.control()['updates']['20']['num_episodes_watched']==8
    checks.append('same_account_reconnection_resumes_its_pending_progress')

    test_mal.control(mode='offline');mark(12);c.call('mal_disconnect')
    test_mal.control(mode='normal',profile={'id':54321,'name':'Another_Local_MAL'},updates={},patch_calls=[])
    assert 'mal=account_changed' in test_mal.callback(c,test_mal.flow(c))
    assert query('SELECT COUNT(*) FROM sa1_mal_links WHERE user_id=?',(user,))==[(0,)]
    assert query('SELECT COUNT(*) FROM sa1_mal_list WHERE user_id=?',(user,))==[(0,)]
    assert query('SELECT notes FROM sa1_follow WHERE user_id=? AND slug=?',(user,'naruto'))==[('Keep local library',)]
    assert query('SELECT COUNT(*) FROM sa1_watched WHERE user_id=?',(user,))[0][0]>=3
    c.call('mal_link',mal_id=20,slug='naruto')
    assert c.call('home',get=True)['home']['watch_pending']['count']==0
    assert c.call('watch_retry')['watch_sync']['state']=='idle'
    assert not test_mal.control()['patch_calls']
    assert query('SELECT error_kind,mal_account_id FROM sa1_watch_sync WHERE user_id=?',(user,))==[('account_changed',12345)]
    c.call('mal_save',mal_id=20,mal_account_id=12345,status='watching',watched=12,score=9,expected=409)
    stale=c.call('watch_scrobble',episode_id=episodes['13'],position=8,duration=10,mal_account_id=12345)['watch_sync']
    assert stale['state']=='blocked' and not test_mal.control()['patch_calls']
    assert mark(14)['state']=='synced'
    assert query('SELECT mal_account_id FROM sa1_watch_sync WHERE user_id=?',(user,))==[(54321,)]
    checks.append('different_mal_account_never_receives_old_pending_marks_and_local_library_survives')

    test_mal.control(mode='offline');mark(18)
    test_mal.control(mode='normal')
    c.call('mal_remove',mal_id=20,confirmation='QUITAR')
    before = len(test_mal.control()['patch_calls'])
    assert c.call('watch_retry')['watch_sync']['state']=='idle'
    assert mark(19)['state']=='blocked'
    assert len(test_mal.control()['patch_calls'])==before
    assert 20 in test_mal.control()['deleted']
    c.call('mal_save',mal_id=20,status='watching',watched=19,score=7)
    assert mark(20)['state']=='synced'
    assert test_mal.control()['updates']['20']['num_episodes_watched']==20
    checks.append('removal_cancels_pending_and_auto_recreation_until_explicit_add')

    query("UPDATE sa1_watch_sync SET lock_until=strftime('%s','now')+90 WHERE user_id=?",(user,))
    before=len(test_mal.control()['deleted'])
    c.call('mal_remove',mal_id=20,confirmation='QUITAR',expected=409)
    assert len(test_mal.control()['deleted'])==before
    query('UPDATE sa1_watch_sync SET mal_id=0 WHERE user_id=?',(user,))
    c.call('mal_remove',mal_id=20,confirmation='QUITAR',expected=409)
    assert len(test_mal.control()['deleted'])==before
    query('UPDATE sa1_watch_sync SET mal_id=20 WHERE user_id=?',(user,))
    query('UPDATE sa1_watch_sync SET lock_until=0 WHERE user_id=?',(user,))
    checks.append('removal_waits_for_inflight_write_instead_of_racing_it')

    # More than the previous global cap, with old active jobs and older history.
    with sqlite3.connect(DB) as connection:
        ids=[row[0] for row in connection.execute("SELECT id FROM sa1_episodes WHERE slug='bleach' ORDER BY number_value")]
        connection.executemany('INSERT INTO sa1_jobs(user_id,episode_id,language,server,height,status,added_at) VALUES(?,?,?,?,?,?,?)',
            [(user,id,'SUB','MP4Upload',1080,'pending',1) for id in ids]+[(user,id,'DUB','MP4Upload',1080,'confirmed',2) for id in ids])
        connection.execute('INSERT INTO sa1_jobs(user_id,episode_id,language,server,height,status,added_at) VALUES(?,?,?,?,?,?,?)',
            (user,episodes['1'],'SUB','MP4Upload',1080,'pending',0))
    snapshot=c.call('state',get=True)['data']
    assert sum(job['status']=='pending' for job in snapshot['jobs'])==80
    assert len(snapshot['jobs'])==160
    assert snapshot['queue_totals']['total']==4001 and snapshot['queue_totals']['confirmed']==2000
    assert sum(row['total'] for row in snapshot['queue_summary'])==4001
    seen=[];cursor=0
    while True:
        page=c.call('queue_history',get=True,slug='bleach',before=cursor)['queue_history']
        assert len(page['items'])<=200
        seen.extend(job['id'] for job in page['items']);cursor=page['next_before']
        if not cursor:break
    assert len(seen)==len(set(seen))==4000
    other=test_web.Client();other.call('register',name='Other QA',email='delivery1-'+secrets.token_hex(5)+'@example.test',password='Delivery1-Local-Only')
    assert not other.call('queue_history',get=True,slug='bleach')['queue_history']['items']
    checks.append('bounded_initial_jobs_and4000_anime_history_records_accessible_in_private_pages')

    # A backup rejected by the old 12 MiB upload can now be restored in ordered parts.
    rows=[{'slug':row[0],'status':'planned','favorite':False,'excluded':False,'score':7,'notes':'😀'*2000}
        for row in query('SELECT slug FROM sa1_anime ORDER BY slug LIMIT 1600')]
    backup={'format':'seasonav1.library/v1','entries':rows,'watched':[]}
    assert len(json.dumps(backup,ensure_ascii=False).encode())>12*1024*1024
    batch_id=secrets.token_hex(16)
    chunks=[rows[offset:offset+100] for offset in range(0,len(rows),100)]
    imported=0
    for index,chunk in enumerate(chunks):
        result=other.call('library_import',library={**backup,'entries':chunk},batch={'id':batch_id,'index':index,'total':len(chunks)})
        imported+=result['imported']['anime']
    exported=other.call('library_export',get=True)['library']
    assert imported==1600 and len(exported['entries'])==1600
    assert all(row['notes']=='😀'*2000 for row in exported['entries'])
    other.call('library_import',library={**backup,'entries':chunks[0]},batch={'id':secrets.token_hex(16),'index':1,'total':2},expected=409)
    checks.append('13mb_unicode_backup_restored_in16_ordered_parts_with_existing_12mb_request_limit')
    test_mal.control(mode='normal',profile={'id':12345,'name':'LocalMAL_Test'},updates={},deleted=[],patch_calls=[])
    result={'ok':True,'count':len(checks),'checks':checks,'real_mal_changes':False,'fixtures_only':True}
    (test_web.ROOT/'verification/reliability-http-check.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
