"""HTTP checks in disposable SQLite; receipts are synthetic test records, not downloaded anime."""
import json
import secrets
import runpy
import test_web

test_web.BASE='http://127.0.0.1:8096/'
test_web.main()
runpy.run_path(str(test_web.ROOT/'verification/test_catalog.py'),run_name='__main__')
c=test_web.Client();checks=[]
email='grouped-'+secrets.token_hex(5)+'@example.test'
c.call('register',name='Vista de prueba',email=email,password='Grouped-Only-Local-8096')
detail=c.call('detail',get=True,slug='naruto')['detail'];episodes=detail['episodes']
assert len(episodes)==220 and all(ep['download_job_id'] is None for ep in episodes)
checks.append('new_account_episode_download_state_empty')
prepared=c.call('queue',slugs=['naruto'],mode='all');ids=prepared['queue_ids'];assert len(ids)==220
plan=c.call('export',job_ids=ids)['plan'];items=plan['items'][:10]
receipt={'format':'seasonav1.web-results/v1','plans':[{'installation':plan['installation'],'plan_id':plan['plan_id'],'items':[{**item,'status':'completed','sha256':'b'*64,'bytes':1048576} for item in items]}]}
jobs=c.call('receipt',receipt=receipt)['data']['jobs'];assert sum(j['status']=='confirmed' for j in jobs)==10
downloaded=c.call('detail',get=True,slug='naruto')['detail']['episodes']
assert all(ep['download_status']=='confirmed' and ep['download_job_id'] in ids and not ep['watched'] for ep in downloaded[:10])
checks.append('detail_links_confirmations_without_changing_watched')
again=c.call('queue',slugs=['naruto'],mode='selected',episode_ids=[ep['id'] for ep in episodes[:10]])
assert again['queue_ids']==[] and len(again['data']['jobs'])==220
checks.append('confirmed_selection_cannot_be_downloaded_again')
again=c.call('queue',slugs=['naruto'],mode='all');assert len(again['queue_ids'])==210
assert all(j['status']=='confirmed' for j in again['data']['jobs'] if j['id'] in {i['web_id'] for i in items})
checks.append('prepare_all_returns_only_remaining_episodes')
c.call('settings',language='DUB')
other_language=c.call('detail',get=True,slug='naruto')['detail']['episodes'];assert all(ep['download_status'] is None for ep in other_language)
c.call('settings',language='SUB')
other=test_web.Client();other.call('register',name='Otra vista',email='grouped-other-'+secrets.token_hex(5)+'@example.test',password='Grouped-Only-Local-8096')
assert all(ep['download_status'] is None for ep in other.call('detail',get=True,slug='naruto')['detail']['episodes'])
checks.append('confirmed_status_scoped_to_account_and_language')
result={'ok':True,'chapters':220,'confirmed_fixture_chapters':10,'checks':checks}
(test_web.ROOT/'verification/downloads-http-check.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
(test_web.ROOT/'verification/grouped-fixture.json').write_text(json.dumps({'email':email,'synthetic':True},indent=2),encoding='utf-8')
print(json.dumps(result,indent=2));print('LOCAL_FIXTURE_EMAIL='+email)
