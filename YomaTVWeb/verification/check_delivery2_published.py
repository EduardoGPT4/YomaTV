"""Anonymous, read-only production checks. Never logs in or starts upstream scraping."""
import http.cookiejar,json,re,subprocess,urllib.error,urllib.request
from urllib.parse import urlencode
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
BASE='https://hk-br035.gt.tc/seasonav1/'
opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
checks=[]
def request(path='',headers=None):
 try:return opener.open(urllib.request.Request(BASE+path,headers={'User-Agent':'Mozilla/5.0 YomaTV anonymous verification',**(headers or {})}),timeout=35)
 except urllib.error.HTTPError as error:return error
page=request().read().decode();challenge=re.findall(r'toNumbers\("([a-f0-9]+)"\)',page)
if challenge:
 code='$v=json_decode(stream_get_contents(STDIN),true);echo bin2hex(openssl_decrypt(hex2bin($v[2]),"aes-128-cbc",hex2bin($v[0]),OPENSSL_RAW_DATA|OPENSSL_ZERO_PADDING,hex2bin($v[1])));'
 value=subprocess.run([r'C:/Users/Eduardo/.config/herd-lite/bin/php.exe','-r',code],input=json.dumps(challenge),text=True,capture_output=True,check=True).stdout.strip()
 assert re.fullmatch('[a-f0-9]{32}',value)
 opener.addheaders=[('Cookie','__test='+value)]
 page=request('?i=1&delivery=2').read().decode()
assert 'assets/catalog-tools.js?v=' in page and 'name="csrf-token"' in page
checks.append('new_catalog_module_is_published')
def api(action,status=200,**data):
 r=request('actions.php?'+urlencode({'action':action,**data}));assert r.status==status,(action,r.status)
 value=json.load(r);assert not any(key in json.dumps(value) for key in ['token_cipher','client_secret','refresh_token','access_token'])
 return value
state=api('state')['data'];assert state['user'] is None and not state['jobs']
catalog=api('catalog')['catalog'];assert catalog['all_total']>=4485 and all(k in catalog['freshness'] for k in ['episodes','servers','genres','airing','directory'])
checks.append('mysql_upgrade_preserves_catalog_and_exposes_separate_coverage')
query={'include_genres':json.dumps(['Acción','Comedia'])}
intersection=api('catalog',**query)['catalog'];union=api('catalog',genre_mode='any',**query)['catalog']
assert union['total']>intersection['total']>0
checks.append('all_and_any_genres_work_on_full_production_catalog')
detail=api('detail',slug='naruto')['detail'];assert 'freshness' in detail and 'relations' in detail and all(r['state']=='approved' for r in detail['relations'])
checks.append('details_show_independent_dates_and_only_reviewed_relations')
for action in ['saved_filters','calendar_feed','notifications']:assert api(action,status=401)['ok'] is False
checks.append('personal_searches_calendar_links_and_notices_require_login')
r=request('catalog-public.php');projection=json.load(r);etag=r.headers['ETag']
assert len(projection['items'])==catalog['all_total'] and all(set(row)=={'slug','title','category'} for row in projection['items'])
assert request('catalog-public.php',{'If-None-Match':etag}).status==304
checks.append('live_offline_index_is_complete_public_only_and_revalidates_with_etag')
offline=json.load(request('data/offline-catalog.json'));assert len(offline['items'])==4485
checks.append('distributed_offline_snapshot_contains_4485_titles')
calendar=request('calendar.php');assert calendar.status==200 and calendar.read().startswith(b'BEGIN:VCALENDAR')
assert request('calendar.php?scope=followed').status==401
checks.append('ics_export_works_and_personal_scope_is_protected')
for name in ['assets/catalog-tools.js','assets/catalog.js','assets/feature-ui.js','assets/app.js','assets/offline.js','sw.js']:
 assert request(name+'?delivery=2').read()==(ROOT/'htdocs'/name).read_bytes(),name
checks.append('published_client_matches_verified_files')
for name in ['catalog-updates.php','catalog-relations.php','calendar-feed.php']:
 assert request('private/'+name).status in [403,404]
checks.append('new_server_modules_are_not_public')
raw=urllib.request.urlopen(BASE+'feeds/horario.ics',timeout=25).read()
blocked=not raw.startswith(b'BEGIN:VCALENDAR')
assert blocked and b'toNumbers' in raw
checks.append('external_calendar_block_is_confirmed_without_user_cookies')
result={'ok':True,'count':len(checks),'checks':checks,'catalog_titles':catalog['all_total'],'anonymous_only':True,'real_mal_changes':False,'external_subscription_blocked_by_host':blocked}
(ROOT/'verification/delivery2-published-check.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(result,indent=2))
