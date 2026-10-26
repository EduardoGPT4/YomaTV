"""OAuth/PKCE regression against a local provider; no real MAL account is used."""
import json
import secrets
import sqlite3
import urllib.request
from urllib.parse import parse_qs, urlsplit, urlencode
import test_web

test_web.BASE='http://127.0.0.1:8096/'
DB=test_web.ROOT/'verification/hardening-2026-10-14.sqlite'
checks=[]

def control(**options):
    url='http://127.0.0.1:8097/control'
    request=urllib.request.Request(url,data=json.dumps(options).encode(),headers={'Content-Type':'application/json'}) if options else url
    return json.load(urllib.request.urlopen(request,timeout=20))
def flow(c):
    result=c.call('mal_connect');query=parse_qs(urlsplit(result['authorization_url']).query)
    assert query['redirect_uri']==['https://hk-br035.gt.tc/seasonav1/mal-callback.php']
    assert query['code_challenge_method']==['plain'] and len(query['code_challenge'][0])==96
    assert 'client_secret' not in result['authorization_url']
    return query
def callback(c,query,code='local-code',**extra):
    params={'state':query['state'][0],'code':code,**extra}
    response=c.opener.open(test_web.BASE+'mal-callback.php?'+urlencode(params))
    assert response.status==200 and 'code=' not in response.url
    return response.url
def dbexec(query,args=()):
    with sqlite3.connect(DB) as db:return db.execute(query,args).fetchall()
def user(c):return c.state['user']['id']

def main():
    picture='https://cdn.myanimelist.net/images/userimages/12345.jpg?t=1'
    profile={'id':12345,'name':'LocalMAL_Test','picture':picture}
    control(mode='normal',refreshes=0,profile=profile,profile_calls=0)
    c=test_web.Client()
    c.call('mal_connect',expected=401)
    c.call('register',name='MAL prueba local',email='mal-'+secrets.token_hex(5)+'@example.test',password='Local-MAL-Test-8096')
    c.call('mal_connect',csrf=False,expected=403)
    c.call('mal_connect',get=True,expected=405)
    assert not c.call('account',get=True)['account']['mal']['connected']
    checks.append('session_csrf_post_only')
    q=flow(c);before=control()['refreshes']
    assert 'mal=expired' in callback(c,{'state':['wrong-state']})
    assert 'mal=connected' in callback(c,q)
    assert control()['exchange_ok']
    assert 'mal=expired' in callback(c,q)
    checks.append('exact_redirect_pkce_state_one_use')
    row=dbexec('SELECT token_cipher FROM sa1_mal_connections WHERE user_id=?',(user(c),))[0][0]
    assert 'mock-access-token' not in row and 'mock-refresh-token' not in row
    account=c.call('account',get=True)['account']['mal']
    assert account['connected'] and account['profile']['name']=='LocalMAL_Test'
    assert account['profile']['picture']==picture
    before_avatar=control()['profile_calls']
    assert c.call('mal_avatar')['mal']['profile']['picture']==picture
    assert control()['profile_calls']==before_avatar
    # Existing accounts created before this feature automatically fill their avatar cache.
    dbexec("DELETE FROM sa1_personal_data WHERE user_id=? AND kind='mal_avatar'",(user(c),))
    assert c.call('mal_avatar')['mal']['profile']['picture']==picture
    assert control()['profile_calls']==before_avatar+1
    def expire_avatar():
        raw=dbexec("SELECT payload FROM sa1_personal_data WHERE user_id=? AND kind='mal_avatar'",(user(c),))[0][0]
        entry=json.loads(raw);entry['next_refresh']=0
        dbexec("UPDATE sa1_personal_data SET payload=? WHERE user_id=? AND kind='mal_avatar'",(json.dumps(entry),user(c)))
    expire_avatar();control(mode='offline')
    cached=c.call('mal_avatar')['mal'];assert cached['connected'] and cached['profile']['picture']==picture
    assert cached['profile']['avatar_next_refresh']>0
    control(mode='normal',profile={**profile,'picture':'https://cdn.myanimelist.net@evil.example/a.jpg'})
    assert c.call('mal_profile')['mal']['profile']['picture']==''
    control(profile={**profile,'picture':None});assert c.call('mal_profile')['mal']['profile']['picture']==''
    control(profile=profile);assert c.call('mal_profile')['mal']['profile']['picture']==picture
    expire_avatar();control(profile={**profile,'id':67890,'picture':'https://cdn.myanimelist.net/images/userimages/67890.jpg'})
    assert c.call('mal_avatar')['mal']['profile']['picture']==picture
    control(profile=profile)
    checks.append('profile_avatar_cached_backfilled_and_isolated_with_safe_fallback_and_retry_lease')
    for action,kwargs in [('state',{}),('account',{}),('mal_profile',{})]:
        payload=c.call(action,get=action!='mal_profile',**kwargs)
        encoded=json.dumps(payload)
        assert not any(key in encoded for key in ['token_cipher','access_token','refresh_token','local-test-secret','encryption_key'])
    checks.append('encrypted_tokens_and_safe_responses')
    control(mode='unauthorized')
    c.call('mal_profile')
    assert control()['refreshes']==1
    control(mode='normal');before=control()['refreshes']
    checks.append('unauthorized_access_refreshes_and_retries_once')
    page=c.call('mal_list')['mal_list'];assert len(page['items'])==50 and page['has_more']
    page=c.call('mal_list',offset=50)['mal_list'];assert len(page['items'])==3 and not page['has_more']
    c.call('mal_list',offset=-1,expected=422);c.call('mal_list',offset=13,expected=422)
    checks.append('list_pagination_and_fixed_endpoints')
    other=test_web.Client();other.call('register',name='Otra MAL',email='mal-'+secrets.token_hex(5)+'@example.test',password='Local-MAL-Test-8096')
    assert not other.call('account',get=True)['account']['mal']['connected']
    other.call('mal_profile',expected=409)
    assert 'mal=expired' in callback(other,q)
    checks.append('user_isolation')
    dbexec('UPDATE sa1_mal_connections SET expires_at=0 WHERE user_id=?',(user(c),))
    dbexec('UPDATE sa1_mal_connections SET refresh_lock_until=strftime(\'%s\',\'now\')+60 WHERE user_id=?',(user(c),))
    c.call('mal_profile',expected=503)
    dbexec('UPDATE sa1_mal_connections SET refresh_lock_until=0 WHERE user_id=?',(user(c),))
    checks.append('concurrent_refresh_is_locked')
    c.call('mal_profile');assert control()['refreshes']==before+1
    assert dbexec('SELECT token_cipher FROM sa1_mal_connections WHERE user_id=?',(user(c),))[0][0]!=row
    checks.append('automatic_refresh_and_rotation')
    control(mode='offline');result=c.call('mal_list',expected=503)
    assert 'mock-' not in json.dumps(result)
    assert c.call('account',get=True)['account']['mal']['connected']
    control(mode='throttled');c.call('mal_list',expected=429);control(mode='normal')
    checks.append('network_errors_preserve_connection')
    dbexec('UPDATE sa1_mal_connections SET expires_at=0 WHERE user_id=?',(user(c),))
    control(mode='invalid_grant');c.call('mal_profile',expected=409)
    assert c.call('account',get=True)['account']['mal']['needs_auth']
    control(mode='normal');q=flow(c);assert 'mal=connected' in callback(c,q)
    checks.append('revoked_authorization_and_reconnect')
    q=flow(c);assert 'mal=denied' in callback(c,q,error='access_denied')
    assert c.call('account',get=True)['account']['mal']['connected']
    checks.append('cancelled_reconnect_preserves_previous_account')
    q=flow(c);c.call('logout');c.call('login',email=c.state['user']['email'] if c.state['user'] else 'invalid@example.test',password='x',expected=401)
    assert 'mal=expired' in callback(c,q)
    checks.append('logout_invalidates_callback')
    # Disconnect is idempotent and changes only the current user's connection.
    q=flow(other);assert 'mal=connected' in callback(other,q)
    other.call('mal_disconnect');other.call('mal_disconnect')
    assert not dbexec('SELECT * FROM sa1_mal_connections WHERE user_id=?',(user(other),))
    assert not dbexec("SELECT * FROM sa1_personal_data WHERE user_id=? AND kind='mal_avatar'",(user(other),))
    assert dbexec('SELECT * FROM sa1_mal_connections WHERE user_id=?',(user(c) if c.state['user'] else dbexec('SELECT user_id FROM sa1_mal_connections')[0][0],))
    checks.append('disconnect_is_idempotent_and_scoped')
    other_id=user(other);q=flow(other);assert 'mal=connected' in callback(other,q)
    assert dbexec('SELECT * FROM sa1_mal_connections WHERE user_id=?',(other_id,))
    other.call('account_delete',current_password='Local-MAL-Test-8096',confirmation='ELIMINAR')
    assert not dbexec('SELECT * FROM sa1_mal_connections WHERE user_id=?',(other_id,))
    checks.append('account_delete_cascades_connections')
    result={'ok':True,'checks':checks,'count':len(checks),'real_mal_account_used':False}
    (test_web.ROOT/'verification/mal-check.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
