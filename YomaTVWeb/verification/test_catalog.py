"""Integration checks against the local HTTP app, including an older series."""
import gzip
import json
import secrets
from pathlib import Path
from test_web import Client,ROOT

c=Client();checks=[]
catalog=c.call('catalog',get=True)['catalog']
seed=json.loads(gzip.decompress((ROOT/'htdocs/data/catalog.json.gz').read_bytes()))
facets=json.loads(gzip.decompress((ROOT/'htdocs/data/catalog-facets.json.gz').read_bytes()))
expected_total=len({row['slug'] for row in seed['anime']} | {row['slug'] for row in facets['directory']})
assert catalog['all_total']==expected_total
assert len(catalog['items'])==24 and catalog['pages']==187
assert len(c.call('state',get=True)['data']['anime'])==64
checks.append('complete_index_and_bounded_responses')
last=c.call('catalog',get=True,page=9999)['catalog'];assert last['page']==catalog['pages'] and len(last['items'])==(expected_total%24 or 24)
checks.append('pagination_and_last_page')
naruto=c.call('catalog',get=True,search='Naruto')['catalog'];assert naruto['total']>10 and any(a['slug']=='naruto' for a in naruto['items']) and all('naruto' in a['title'].lower() for a in naruto['items'])
assert c.call('catalog',get=True,search='%')['catalog']['total']<10
assert c.call('catalog',get=True,search="' OR 1=1 --")['catalog']['total']==0
checks.append('search_and_literal_wildcards')
movies=c.call('catalog',get=True,category='Película',order='title')['catalog'];assert movies['total']>100 and all(a['category']=='Película' for a in movies['items'])
season=c.call('catalog',get=True,scope='season')['catalog'];assert season['total']==64 and all(a['active'] for a in season['items'])
checks.append('format_and_season_filters')
detail=c.call('detail',get=True,slug='naruto')['detail'];assert detail['anime']['catalog_complete'] and len(detail['episodes'])==220
numbers=[float(e['number']) for e in detail['episodes']];assert numbers==sorted(numbers)
assert detail['anime']['start_date'].startswith('2002')
checks.append('cached_episode_listing_220')
c.call('register',name='Catálogo QA',email='catalog-'+secrets.token_hex(5)+'@example.test',password='Catalog-Local-Test-8086')
c.call('follow',slug='naruto',favorite=True,notes='Private catalog test')
assert c.call('detail',get=True,slug='naruto')['detail']['anime']['favorite']
checks.append('favorites_outside_schedule')
prepared=c.call('queue',slugs=['naruto'],mode='all');assert len(prepared['queue_ids'])==220
plan=c.call('export',job_ids=prepared['queue_ids'])['plan'];assert [float(item['number']) for item in plan['items']]==numbers
assert all(item['weekday'] in range(1,8) for item in plan['items'])
(ROOT/'verification/catalog-plan.json').write_text(json.dumps(plan,ensure_ascii=False),encoding='utf-8')
again=c.call('queue',slugs=['naruto'],mode='all');assert len(again['queue_ids'])==220 and len(again['data']['jobs'])==220
checks.append('classic_series_ordered_export_and_deduplication')
other=Client();assert not next(a for a in other.call('catalog',get=True,search='Naruto')['catalog']['items'] if a['slug']=='naruto')['favorite']
assert other.call('detail',get=True,slug='naruto')['detail']['anime']['notes']==''
checks.append('catalog_private_account_isolation')
radio=other.call('radio',get=True)['radio'];assert len(radio['tracks'])==43 and {t['type'] for t in radio['tracks']}=={'OP','ED','OST'}
assert len({t['id'] for t in radio['tracks']})==43
assert all(t['url']=='https://www.youtube.com/watch?v='+t['id'] for t in radio['tracks'])
checks.append('verified_music_metadata_and_types')
result={'ok':True,'catalog_titles':expected_total,'classic_episodes':220,'checks':checks}
(ROOT/'verification/catalog-http-check.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
