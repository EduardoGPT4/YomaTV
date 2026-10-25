"""Anonymous production smoke checks. No accounts, MAL requests or scraping actions."""
import http.cookiejar
import json
import re
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlencode

ROOT=Path(__file__).resolve().parent.parent
BASE='https://hk-br035.gt.tc/seasonav1/'
cookies=http.cookiejar.CookieJar()
opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookies))
checks=[]
def request(path=''):
    req=urllib.request.Request(BASE+path,headers={'User-Agent':'Mozilla/5.0 YomaTV read-only verification'})
    try:return opener.open(req,timeout=30)
    except urllib.error.HTTPError as error:return error

page=request().read().decode()
challenge=re.findall(r'toNumbers\("([a-f0-9]+)"\)',page)
if challenge:
    assert len(challenge)==3
    # Execute the host's ordinary first-party JS cookie check; it is not a CAPTCHA.
    code='$v=json_decode(stream_get_contents(STDIN),true);echo bin2hex(openssl_decrypt(hex2bin($v[2]),"aes-128-cbc",hex2bin($v[0]),OPENSSL_RAW_DATA|OPENSSL_ZERO_PADDING,hex2bin($v[1])));'
    value=subprocess.run([r'C:/Users/Eduardo/.config/herd-lite/bin/php.exe','-r',code],input=json.dumps(challenge),text=True,capture_output=True,check=True).stdout.strip()
    assert re.fullmatch('[a-f0-9]{32}',value)
    cookies.set_cookie(http.cookiejar.Cookie(0,'__test',value,None,False,'hk-br035.gt.tc',False,False,'/',True,True,None,True,None,None,{},False))
    page=request('?i=1&delivery=20261017').read().decode()
assert 'assets/library-transfer.js?v=' in page and 'name="csrf-token"' in page
checks.append('published_page_loads_new_backup_module')
def api(action,expected=200,**values):
    response=request('actions.php?'+urlencode({'action':action,**values}))
    assert response.status==expected,(action,response.status)
    payload=json.load(response)
    assert not any(secret in json.dumps(payload) for secret in ['token_cipher','client_secret','encryption_key','refresh_token','access_token'])
    return payload

state=api('state')['data']
assert state['user'] is None and state['jobs']==[] and state['queue_summary']==[] and state['queue_totals']['total']==0
assert state['anime']
checks.append('mysql_bootstrap_and_new_summary_schema_work_without_exposing_private_jobs')
catalog=api('catalog',include_genres=json.dumps(['Antropomórfico']))['catalog']
assert catalog['all_total']>=4485 and catalog['total']>0 and catalog['metadata_source']=='AnimeAV1'
checks.append('complete_animeav1_catalog_filters_preserved')
assert api('queue_history',expected=401,slug='naruto')['ok'] is False
checks.append('private_history_requires_authentication')
for name in ['assets/library-transfer.js','assets/state-client.js','assets/feature-ui.js','assets/downloads.js','assets/bridge-ui.js','assets/app.js']:
    assert request(name+'?delivery=20261017').read()==(ROOT/'htdocs'/name).read_bytes(),name
checks.append('published_javascript_matches_verified_source')
assert request('private/mal-safety.php').status in [403,404]
checks.append('new_private_module_is_not_public')
result={'ok':True,'checks':checks,'anonymous_only':True,'real_mal_changes':False,'catalog_titles':catalog['all_total'],'filtered_titles':catalog['total']}
(ROOT/'verification/delivery1-published-check.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print(json.dumps(result,indent=2))
