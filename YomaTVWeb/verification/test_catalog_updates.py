"""Delivery 2 HTTP tests: disposable users/SQLite only, no upstream requests."""
import json,secrets,sqlite3,urllib.error,subprocess,os
import test_web
test_web.BASE='http://127.0.0.1:8096/'
ROOT=test_web.ROOT;DB=ROOT/'verification/hardening-2026-10-14.sqlite'
assert DB.resolve().is_relative_to((ROOT/'verification').resolve())
checks=[]
def check(ok,name):
 assert ok,name
 checks.append(name)
def sql(q,args=()):
 with sqlite3.connect(DB) as db:return db.execute(q,args).fetchall()
def account():
 c=test_web.Client();c.call('register',name='Catálogo QA',email='catalog2-'+secrets.token_hex(6)+'@example.test',password='Local-Delivery2-8096');return c
c=account();other=account();anon=test_web.Client();admin=test_web.Client();admin.call('login',email='admin@example.test',password='Admin-Local-Test-8096')
uid=c.state['user']['id']
try:
 query=dict(category='QA Source',include_genres=json.dumps(['Acción','Comedia']))
 all_=anon.call('catalog',get=True,**query)['catalog'];any_=anon.call('catalog',get=True,genre_mode='any',**query)['catalog']
 check(all_['total']==1 and any_['total']==2,'genre_all_and_any_query_entire_source_catalog')
 check(c.call('catalog',get=True,genre_mode='any',exclude_genres=json.dumps(['Comedia']),**query)['catalog']['total']==1,'genre_any_keeps_exclusions')
 c.call('catalog',get=True,genre_mode='bogus',expected=422)
 filters=dict(search='Náruto',genre_mode='any',include_genres=['Acción','Comedia'],exclude_genres=['Ecchi'])
 saved=c.call('save_filter',name='Para después',filters=filters)['saved_filters'];sid=saved[0]['id']
 check(saved[0]['filters']==filters and not other.call('saved_filters',get=True)['saved_filters'],'saved_filters_are_private_and_preserve_full_combination')
 other.call('delete_filter',id=sid)
 check(len(c.call('saved_filters',get=True)['saved_filters'])==1,'other_account_cannot_remove_saved_filter')
 c.call('save_filter',name='Para después',filters={**filters,'year':'2002'})
 check(len(c.call('saved_filters',get=True)['saved_filters'])==1,'named_search_upsert_does_not_duplicate')
 c.call('save_filter',name='malformed',filters={'include_genres':'not json'},expected=422)
 c.call('delete_filter',id=sid)
 check(not c.call('saved_filters',get=True)['saved_filters'],'saved_filter_can_be_deleted')

 anon.call('catalog_request',slug='qa-source-a',expected=401)
 c.call('catalog_request',slug='https://attacker.invalid',expected=404)
 c.call('catalog_request',slug='qa-source-a',episode_id=999999999,expected=404)
 r=c.call('catalog_request',slug='qa-source-a');r2=other.call('catalog_request',slug='qa-source-a')
 check(r['task']['state']=='pending' and r2['task']['state']=='pending' and sql("SELECT COUNT(*) FROM sa1_catalog_tasks WHERE kind='detail' AND target='qa-source-a'")[0][0]==1,'user_requests_are_deduplicated_central_jobs_without_scraping')
 for action in ['maintenance','catalog_retry','relation_review']:c.call(action,expected=403,slug='naruto',target='naruto-shippuuden',relation='sequel')
 checks.append('ordinary_members_cannot_run_worker_retry_or_review_relations')
 ep=sql("SELECT id FROM sa1_episodes WHERE slug='naruto' ORDER BY id LIMIT 1")[0][0]
 sql('UPDATE sa1_episodes SET mirrors_at=0 WHERE id=?',(ep,));c.call('catalog_request',slug='naruto',episode_id=ep)
 check(sql("SELECT COUNT(*) FROM sa1_catalog_tasks WHERE kind='mirrors' AND target=?",(str(ep),))[0][0]==1,'server_requests_use_known_episode_ids_only')
 d=c.call('detail',get=True,slug='qa-source-a')['detail'];coverage=c.call('catalog',get=True)['catalog']['freshness']
 check(d['freshness']['episodes_at']==0 and d['freshness']['genres_at']>0 and all(k in coverage for k in ['episodes','servers','genres','airing','directory']),'independent_coverage_and_dates_do_not_claim_unchecked_episodes')

 c.call('relation_review',slug='naruto',target='naruto-shippuuden',relation='sequel',expected=403)
 admin.call('relation_review',slug='naruto',target='naruto-shippuuden',relation='sequel')
 check(any(r['target']=='naruto-shippuuden' and r['relation']=='sequel' for r in anon.call('detail',get=True,slug='naruto')['detail']['relations']),'reviewed_relations_visible_in_public_details')
 check(any(r['target']=='naruto' and r['relation']=='prequel' for r in anon.call('detail',get=True,slug='naruto-shippuuden')['detail']['relations']),'reviewed_sequel_has_consistent_reverse_prequel')
 admin.call('relation_review',slug='naruto',target='naruto-shippuuden',relation='sequel',state='rejected')
 check(not anon.call('detail',get=True,slug='naruto')['detail']['relations'],'rejected_relations_hidden_from_non_admin')

 slug=c.state['anime'][0]['slug'];c.call('follow',slug=slug,status='watching')
 # More than one new episode during an absence becomes one anime card.
 for n in ['9001','9002','9003']:sql('INSERT INTO sa1_notifications(user_id,slug,number,created_at) VALUES(?,?,?,?)',(uid,slug,n,1792000000))
 rows=c.call('notifications',get=True);notice=rows['notifications'][0]
 check(len(rows['notifications'])==1 and int(notice['episode_count'])==3 and int(notice['unread'])==3 and c.call('home',get=True)['home']['notifications']==1,'notices_group_unread_and_missed_episodes_per_anime')
 c.call('notifications_read',up_to=rows['notifications_up_to'])
 sql('INSERT INTO sa1_notifications(user_id,slug,number,created_at) VALUES(?,?,?,?)',(uid,slug,'9004',1792000001))
 check(int(c.call('notifications',get=True)['notifications'][0]['unread'])==1,'read_watermark_keeps_later_new_episodes_unread')
 check(not other.call('notifications',get=True)['notifications'],'notifications_remain_private')

 anon.call('calendar_feed',get=True,expected=401)
 sql("UPDATE sa1_anime SET published=?,active=1 WHERE slug=?",(__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),slug))
 f=c.call('calendar_create',scope='followed')['calendar_feed'];url=f['url']
 body=anon.opener.open(test_web.BASE+url).read().decode().replace('\r\n ','')
 check('BEGIN:VCALENDAR' in body and 'RRULE:FREQ=WEEKLY;UNTIL=' in body and 'URL:https://animeav1.com/media/'+slug in body and body.count('BEGIN:VEVENT')==1,'private_static_subscription_is_readable_without_session_and_filters_followed')
 check(not other.call('calendar_feed',get=True)['calendar_feed'],'subscription_secret_not_exposed_to_other_users')
 c.call('unfollow',slug=slug)
 check('BEGIN:VEVENT' not in anon.opener.open(test_web.BASE+url).read().decode(),'subscription_updates_after_library_change')
 replacement=c.call('calendar_create',scope='all')['calendar_feed']
 try:anon.opener.open(test_web.BASE+url)
 except urllib.error.HTTPError as error:check(error.code==404,'rotating_calendar_revokes_old_url')
 else:raise AssertionError('Old subscription still accessible')
 c.call('calendar_revoke');check(c.call('calendar_feed',get=True)['calendar_feed'] is None,'calendar_subscription_is_revocable')
 public=json.load(anon.opener.open(test_web.BASE+'catalog-public.php'))
 check(len(public['items'])>=4485 and all(set(a)=={'slug','title','category'} for a in public['items']) and len(public['version'])==64,'live_offline_projection_is_complete_and_contains_no_personal_data')
finally:
 c.call('calendar_revoke')
 for user in [uid,other.state['user']['id']]:sql('DELETE FROM sa1_users WHERE id=?',(user,))
 sql("DELETE FROM sa1_relations WHERE (slug='naruto' AND target='naruto-shippuuden') OR (slug='naruto-shippuuden' AND target='naruto')")
 sql("DELETE FROM sa1_catalog_tasks WHERE target IN ('qa-source-a',?)",(str(ep),))
result={'ok':True,'count':len(checks),'checks':checks,'upstream_requests':0,'real_mal_changes':False}
(ROOT/'verification/delivery2-http-check.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(result,indent=2))
