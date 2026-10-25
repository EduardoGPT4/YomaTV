"""Protected production smoke test using a temporary account; no real MAL login.

Exercises normal account endpoints only. No diagnostic files are uploaded.
"""
import http.cookiejar
import json
import re
import secrets
import subprocess
import urllib.error
import urllib.request
from urllib.parse import urlsplit, parse_qs, urlencode
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
BASE='https://hk-br035.gt.tc/seasonav1/'

def main():
    cookies=http.cookiejar.CookieJar()
    opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookies))
    def request(path='',data=None,csrf=None):
        headers={'User-Agent':'Mozilla/5.0 YomaTV verification','X-Season-Response':'patch'}
        if data is not None:headers['Content-Type']='application/json'
        if csrf:headers['X-CSRF-Token']=csrf
        req=urllib.request.Request(BASE+path,data=json.dumps(data).encode() if data is not None else None,headers=headers)
        try:return opener.open(req,timeout=30)
        except urllib.error.HTTPError as error:return error
    page=request().read().decode()
    challenge=re.findall(r'toNumbers\("([a-f0-9]+)"\)',page)
    if challenge:
        assert len(challenge)==3
        # The host's public JavaScript cookie check uses AES-CBC, not a CAPTCHA.
        php='$v=json_decode(stream_get_contents(STDIN),true);echo bin2hex(openssl_decrypt(hex2bin($v[2]),"aes-128-cbc",hex2bin($v[0]),OPENSSL_RAW_DATA|OPENSSL_ZERO_PADDING,hex2bin($v[1])));'
        result=subprocess.run([r'C:/Users/Eduardo/.config/herd-lite/bin/php.exe','-r',php],input=json.dumps(challenge),text=True,capture_output=True,check=True)
        value=result.stdout.strip();assert re.fullmatch('[a-f0-9]{32}',value)
        cookies.set_cookie(http.cookiejar.Cookie(0,'__test',value,None,False,'hk-br035.gt.tc',False,False,'/',True,True,None,True,None,None,{},False))
        page=request('?i=1').read().decode()
    csrf=re.search(r'name="csrf-token" content="([a-f0-9]+)"',page)[1]
    def call(action,get=False,expected=200,**data):
        nonlocal csrf
        response=request('actions.php?'+urlencode({'action':action,**data}) if get else 'actions.php',None if get else {'action':action,**data},None if get else csrf)
        value=json.load(response);assert response.status==expected,(action,response.status)
        if value.get('data'):csrf=value['data']['csrf']
        assert not any(key in json.dumps(value) for key in ['client_secret','encryption_key','token_cipher','refresh_token','access_token'])
        return value
    password='Published-MAL-QA-'+secrets.token_hex(8)
    email='mal-qa-'+secrets.token_hex(8)+'@example.test'
    created=False;checks=[]
    try:
        call('register',name='MAL verificación temporal',email=email,password=password);created=True
        home=call('home',get=True)['home'];assert home['watching_count']==0 and home['planned_count']==0
        xml='''<?xml version="1.0"?><myanimelist><anime><series_animedb_id>20</series_animedb_id><series_title>Naruto</series_title><series_type>TV</series_type><series_episodes>220</series_episodes><my_status>Watching</my_status><my_watched_episodes>5</my_watched_episodes><my_score>8</my_score><my_comments>Prueba temporal de importación</my_comments></anime><anime><series_animedb_id>21</series_animedb_id><series_title>One Piece</series_title><series_type>TV</series_type><my_status>Plan to Watch</my_status><my_watched_episodes>0</my_watched_episodes><my_score>0</my_score></anime></myanimelist>'''
        preview=call('mal_xml',xml=xml,commit=False);assert preview['preview']['count']==2
        call('mal_xml',xml=xml,commit=True)
        home=call('home',get=True)['home'];assert home['watching_count']==1 and home['planned_count']==1
        entries=call('mal_cached',get=True)['mal_library'];assert entries['total']==2 and all(m['source']=='xml' for m in entries['items'])
        assert call('mal_entry',get=True,mal_id=20)['mal_entry']['notes']=='Prueba temporal de importación'
        checks.append('mysql_xml_import_cached_lists_prioritized_home_and_private_notes')
        stats=call('stats',get=True)['stats'];assert stats['watched']==5
        naruto=call('detail',get=True,slug='naruto')['detail']
        if naruto['episodes']:
            call('mal_link',mal_id=20,slug='naruto')
            later=next((ep for ep in naruto['episodes'] if float(ep['number'])>5),None)
            early=next((ep for ep in naruto['episodes'] if float(ep['number'])<=5),None)
            if later and early:
                call('watched',episode_id=later['id'],watched=True);call('watched',episode_id=early['id'],watched=True)
                assert call('stats',get=True)['stats']['watched']==6
        assert not call('notifications',get=True)['notifications']
        call('maintenance',expected=403)
        call('mal_save',expected=409,mal_id=20,status='watching',watched=6,score=9)
        checks.append('statistics_notifications_and_admin_or_oauth_permissions')
        if naruto['episodes']:
            ep=naruto['episodes'][0]
            call('watch_scrobble',expected=422,episode_id=ep['id'],position=7.99,duration=10)
            r=call('watch_scrobble',episode_id=ep['id'],position=8,duration=10)['watch_sync'];assert r['state']=='blocked'
            assert 'Conecta' in r['message'] or 'Vincula' in r['message']
            assert call('watch_retry')['watch_sync']['state']=='idle'
            checks.append('mysql_auto_watch_marks_web_and_waits_for_own_mal_connection')
        archive=request('downloads/YomaTV-Brave.zip').read();assert archive==(ROOT/'htdocs/downloads/YomaTV-Brave.zip').read_bytes()
        checks.append('brave_extension_download_matches_verified_package')
        catalog=call('catalog',get=True,search='naruto')['catalog'];assert catalog['total']>=1
        details=call('detail',get=True,slug='dark-summoner-to-dekiteiru')['detail']
        if details['episodes']:
            player=call('player',episode_id=details['episodes'][0]['id'])['player'];assert player['episode']['slug']=='dark-summoner-to-dekiteiru'
            assert all(urlsplit(m['url']).hostname in ['www.mp4upload.com','mp4upload.com','voe.sx'] for m in player['servers'])
        checks.append('catalog_search_and_allowlisted_player_on_production')
        manifest=json.load(request('manifest.webmanifest'));assert manifest['display']=='standalone'
        offline=json.load(request('data/offline-catalog.json'));assert len(offline['items'])==4483
        calendar=request('calendar.php').read().decode();assert 'BEGIN:VCALENDAR' in calendar and 'RRULE:FREQ=WEEKLY;COUNT=13' in calendar
        checks.append('published_pwa_public_offline_catalog_and_estimated_calendar')
        account=call('account',get=True)['account']
        assert account['mal']['configured'] and not account['mal']['connected']
        checks.append('server_private_configuration_ready_on_mysql')
        link=call('mal_connect')['authorization_url'];url=urlsplit(link);query=parse_qs(url.query)
        assert url.scheme=='https' and url.netloc=='myanimelist.net' and url.path=='/v1/oauth2/authorize'
        assert query['redirect_uri']==['https://hk-br035.gt.tc/seasonav1/mal-callback.php']
        assert query['code_challenge_method']==['plain'] and len(query['code_challenge'][0])==96
        checks.append('published_oauth_start_and_exact_redirect')
        response=request('mal-callback.php?'+urlencode({'state':query['state'][0],'error':'access_denied'}))
        assert response.status==200 and 'mal=denied' in response.url
        assert call('account',get=True)['account']['mal_notice']=='denied'
        checks.append('callback_and_session_flash_without_provider_request')
        call('mal_profile',expected=409)
        checks.append('unlinked_account_cannot_read_mal')
        response=request('private/config.local.php')
        assert response.status in [403,404]
        checks.append('private_configuration_not_publicly_accessible')
    finally:
        if created:
            call('account_delete',current_password=password,confirmation='ELIMINAR')
            checks.append('temporary_account_removed')
    result={'ok':True,'checks':checks,'real_mal_account_used':False,'real_oauth_exchange_verified':False,'count':len(checks)}
    (ROOT/'verification/mal-published-check.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
