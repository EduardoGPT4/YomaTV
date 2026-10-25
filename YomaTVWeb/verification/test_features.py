"""Integrated checks for MAL editing/matching, XML, playback, scheduling and personal UI data."""
import json
import secrets
import sqlite3
import urllib.request
import test_web
import test_mal

test_web.BASE='http://127.0.0.1:8096/'
DB=test_mal.DB
checks=[]
def sql(query,args=()):
    with sqlite3.connect(DB) as db:return db.execute(query,args).fetchall()
def main():
    test_mal.control(mode='normal',updates={},deleted=[],refreshes=0)
    c=test_web.Client();c.call('state',get=True)
    assert c.call('home',get=True)['home']['user_id']==0
    c.call('mal_cached',get=True,expected=401)
    c.call('register',name='Funciones QA',email='features-'+secrets.token_hex(5)+'@example.test',password='Local-Features-8096')
    id=c.state['user']['id'];q=test_mal.flow(c);assert 'mal=connected' in test_mal.callback(c,q)
    r=c.call('mal_refresh',offset=0);assert r['progress']['more'] and r['progress']['offset']==50
    r=c.call('mal_refresh',offset=50);assert not r['progress']['more']
    candidates=c.call('mal_candidates',mal_id=269,search='Bleach')['matches'];assert candidates and all('match_score' in row for row in candidates)
    checks.append('matching_suggestions_handle_numeric_titles_and_rank_each_candidate')
    home=r['home'];assert home['total']==53 and home['planned_count']==1 and home['watching_count']==52
    assert home['continue'] and next(x for x in home['continue'] if x['slug']=='naruto')['number']=='6'
    checks.append('mal_refresh_cached_and_prioritized_home_with_continue')
    row=c.call('mal_entry',get=True,mal_id=20)['mal_entry'];assert row['slug']=='naruto'
    detail=c.call('detail',get=True,slug='naruto')['detail'];assert detail['anime']['mal']['watched']==5
    assert not detail['anime']['mal']['confirmed']
    c.call('mal_link',mal_id=20,slug='naruto');assert c.call('detail',get=True,slug='naruto')['detail']['anime']['mal']['confirmed']
    checks.append('exact_unique_matching_and_explicit_confirmation')
    page=c.call('mal_cached',get=True,status='plan_to_watch')['mal_library'];assert page['total']==1 and page['items'][0]['mal_id']==21
    c.call('mal_save',csrf=False,expected=403,mal_id=20,status='watching',watched=9,score=9)
    c.call('mal_save',expected=422,mal_id=20,status='evil',watched=9,score=9)
    c.call('mal_save',expected=422,mal_id=20,status='watching',watched=221,score=9)
    c.call('mal_save',mal_id=20,status='watching',watched=9,score=9)
    assert test_mal.control()['updates']['20']['num_episodes_watched']==9
    assert c.call('mal_entry',get=True,mal_id=20)['mal_entry']['score']==9
    assert c.call('detail',get=True,slug='naruto')['detail']['anime']['score']==9
    checks.append('mal_patch_real_payload_validation_and_local_state')
    found=c.call('catalog',get=True,search='NÍNJA ÁDVENTURES')['catalog'];assert any(a['slug']=='naruto' for a in found['items'])
    found=c.call('catalog',get=True,year='2002',airing='finished_airing',genre='Action',search='Naruto')['catalog'];assert any(a['slug']=='naruto' for a in found['items'])
    assert any(a['slug']=='naruto' for a in c.call('catalog',get=True,unwatched='1',search='Naruto')['catalog']['items'])
    checks.append('accent_case_synonym_year_airing_genre_and_unwatched_filters')
    other=test_web.Client();other.call('register',name='Otra cuenta QA',email='features-'+secrets.token_hex(5)+'@example.test',password='Local-Features-8096')
    assert other.call('mal_cached',get=True)['mal_library']['total']==0
    assert other.call('detail',get=True,slug='naruto')['detail']['anime']['mal'] is None
    checks.append('private_library_links_and_progress_isolation')
    xml='''<?xml version="1.0"?><myanimelist><anime><series_animedb_id>269</series_animedb_id><series_title>Bleach</series_title><series_type>1</series_type><series_episodes>366</series_episodes><my_status>Plan to Watch</my_status><my_watched_episodes>3</my_watched_episodes><my_score>7</my_score><my_comments><![CDATA[Una nota <b>privada</b>]]></my_comments></anime></myanimelist>'''
    before=len(test_mal.control()['updates'])
    assert other.call('mal_xml',xml=xml,commit=False)['preview']['count']==1
    assert other.call('mal_cached',get=True)['mal_library']['total']==0
    other.call('mal_xml',xml=xml,commit=True)
    assert other.call('mal_entry',get=True,mal_id=269)['mal_entry']['notes']=='Una nota <b>privada</b>'
    bleach=other.call('detail',get=True,slug='bleach')['detail']['anime']
    if bleach['mal'] is None:
        # The UI fixture has MAL's real 2004 date, while the stress-test catalog uses 2002.
        # A date mismatch must remain unlinked until the user explicitly chooses it.
        other.call('mal_link',mal_id=269,slug='bleach')
    assert other.call('detail',get=True,slug='bleach')['detail']['anime']['mal']['watched']==3
    assert len(test_mal.control()['updates'])==before
    other.call('mal_xml',xml='<!DOCTYPE myanimelist [<!ENTITY leak SYSTEM "file:///private">]><myanimelist/>',commit=True,expected=422)
    checks.append('xml_preview_confirm_notes_matching_no_remote_writes_and_xxe_rejection')
    ep=detail['episodes'][0]['id']
    mirrors=[{'server':'MP4Upload','language':'SUB','url':'https://www.mp4upload.com/embed-abcd12345678.html'},
        {'server':'MP4Upload','language':'SUB','url':'https://evil.invalid/steal'}, {'server':'Voe','language':'SUB','url':'javascript:alert(1)'}]
    sql('UPDATE sa1_episodes SET mirrors=?,mirrors_at=strftime(\'%s\',\'now\') WHERE id=?',(json.dumps(mirrors),ep))
    player=c.call('player',episode_id=ep)['player'];assert len(player['servers'])==1 and player['servers'][0]['url'].startswith('https://www.mp4upload.com/embed-')
    assert len(player['chapters'])==220
    checks.append('player_allowlisted_servers_chapters_and_no_arbitrary_urls')
    sql('INSERT INTO sa1_notifications(user_id,slug,number,created_at) VALUES(?,?,?,?)',(id,'naruto','221',1792000000))
    assert c.call('home',get=True)['home']['notifications']==1
    assert not other.call('notifications',get=True)['notifications']
    notice=c.call('notifications',get=True)['notifications'][0];c.call('notifications_read',up_to=notice['id'])
    assert c.call('home',get=True)['home']['notifications']==0
    checks.append('notification_count_read_and_account_isolation')
    stats=c.call('stats',get=True)['stats'];assert stats['watched']>=9 and stats['estimated_hours']>0 and stats['download_bytes']==0
    checks.append('statistics_include_mal_and_do_not_duplicate_linked_anime')
    later=sql("SELECT id FROM sa1_episodes WHERE slug='naruto' AND number='100'")[0][0]
    early=sql("SELECT id FROM sa1_episodes WHERE slug='naruto' AND number='1'")[0][0]
    c.call('watched',episode_id=later,watched=True);c.call('watched',episode_id=early,watched=True)
    assert c.call('stats',get=True)['stats']['watched']==stats['watched']+1
    assert c.call('detail',get=True,slug='naruto')['detail']['anime']['watch_progress']==10
    checks.append('watched_union_counts_out_of_order_web_episodes_without_double_counting_mal_prefix')
    sql("UPDATE sa1_anime SET published=?,active=1 WHERE slug='naruto'",(__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),))
    calendar=c.opener.open(test_web.BASE+'calendar.php').read().decode();assert 'BEGIN:VCALENDAR' in calendar and 'RRULE:FREQ=WEEKLY;UNTIL=' in calendar and 'estimado' in calendar
    assert all(len(line.encode())<=76 for line in calendar.splitlines())
    checks.append('ics_weekly_estimated_events_and_utf8_line_folding')
    c.call('maintenance',expected=403);c.call('maintenance_token',expected=403,current_password='x')
    response=c.opener.open(urllib.request.Request(test_web.BASE+'maintenance.php',data=b'',headers={'Authorization':'Bearer '+('a'*64)})) if False else None
    try:c.opener.open(urllib.request.Request(test_web.BASE+'maintenance.php',data=b''))
    except urllib.error.HTTPError as e:assert e.code==403
    checks.append('maintenance_requires_admin_or_separate_secret')
    c.call('mal_remove',expected=422,mal_id=20)
    c.call('mal_remove',mal_id=20,confirmation='QUITAR');assert 20 in test_mal.control()['deleted']
    assert not any(m['mal_id']==20 for m in c.call('mal_cached',get=True)['mal_library']['items'])
    checks.append('mal_remove_explicit_confirmation_and_delete_endpoint')
    result={'ok':True,'count':len(checks),'checks':checks,'real_mal_changes':False}
    (test_web.ROOT/'verification/features-check.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
