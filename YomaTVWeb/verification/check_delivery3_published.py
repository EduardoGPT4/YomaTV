"""Read-only checks of public files and anonymous authorization on production."""
import http.cookiejar,json,re,subprocess,urllib.error,urllib.request,zipfile,io,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BASE='https://hk-br035.gt.tc/seasonav1/'
opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()));checks=[]
def request(path='',headers=None):
    try:return opener.open(urllib.request.Request(BASE+path,headers={'User-Agent':'Mozilla/5.0 YomaTV anonymous verification',**(headers or {})}),timeout=40)
    except urllib.error.HTTPError as error:return error
page=request().read().decode();challenge=re.findall(r'toNumbers\("([a-f0-9]+)"\)',page)
if challenge:
    code='$v=json_decode(stream_get_contents(STDIN),true);echo bin2hex(openssl_decrypt(hex2bin($v[2]),"aes-128-cbc",hex2bin($v[0]),OPENSSL_RAW_DATA|OPENSSL_ZERO_PADDING,hex2bin($v[1])));'
    value=subprocess.run([r'C:/Users/Eduardo/.config/herd-lite/bin/php.exe','-r',code],input=json.dumps(challenge),text=True,capture_output=True,check=True).stdout.strip()
    assert re.fullmatch('[a-f0-9]{32}',value);opener.addheaders=[('Cookie','__test='+value)];page=request('?i=1&delivery=3').read().decode()
for name in ['player-experience.js','experience-ui.js','accessibility.js','radio-library.js']:assert 'assets/'+name+'?v=' in page
assert 'Saltar al contenido' in page and 'Cerrar menú' in page;checks.append('new_modules_and_accessible_navigation_are_published')
def api(action,status=200,**data):
    from urllib.parse import urlencode
    r=request('actions.php?'+urlencode({'action':action,**data}));assert r.status==status,(action,r.status);value=json.load(r)
    assert not any(key in json.dumps(value) for key in ['token_cipher','client_secret','refresh_token','access_token']);return value
state=api('state')['data'];assert state['user'] is None and not state['jobs'];checks.append('mysql_schema_upgrade_keeps_anonymous_state_private')
catalog=api('catalog')['catalog'];assert catalog['all_total']>=4485;checks.append('complete_catalog_is_preserved')
detail=api('detail',slug='naruto')['detail'];assert detail['watch_mode'] is None and all(ep['rewatched'] is False for ep in detail['episodes']);checks.append('public_details_expose_no_personal_rewatch_data')
for action,args in [('player',{'episode_id':1}),('presence',{'slug':'naruto'})]:assert not api(action,status=401,**args)['ok']
for action in ['queue_preview','player_save','watch_mode','file_presence','queue_redownload','mal_match_batch','mal_link_batch','progress_reconcile']:assert not api(action,status=405)['ok']
checks.append('player_presence_and_mutations_require_authorization_and_post')
names=json.loads((ROOT/'verification/delivery3-files.json').read_text())
public=[n for n in names if n.startswith('assets/') or n in ['sw.js','downloads/YomaTV-Brave.zip']]
for name in public:assert request(name+'?delivery=3&v='+hashlib.sha256((ROOT/'htdocs'/name).read_bytes()).hexdigest()[:16]).read()==(ROOT/'htdocs'/name).read_bytes(),name
checks.append('all_published_client_files_match_verified_bytes')
with zipfile.ZipFile(io.BytesIO(request('downloads/YomaTV-Brave.zip').read())) as z:
    manifest=json.loads(z.read('manifest.json'));assert manifest['version']=='1.2.0' and manifest['permissions']==['storage']
checks.append('extension_1_2_is_downloadable_with_unchanged_permissions')
for name in ['experience.php','match-review.php','library.php','queue.php']:assert request('private/'+name).status in [403,404]
checks.append('server_modules_cannot_be_downloaded')
result={'ok':True,'count':len(checks),'checks':checks,'catalog_titles':catalog['all_total'],'anonymous_only':True,'real_mal_changes':False,'real_video_downloads':0}
(ROOT/'verification/delivery3-published-check.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(result,indent=2))
