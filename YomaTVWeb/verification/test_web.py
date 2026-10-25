"""Recorrido HTTP de una cuenta de prueba local, con cookies y CSRF reales."""
import http.cookiejar
import copy
import json
import re
import secrets
import os
import urllib.error
import urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
BASE=os.environ.get('SEASON_WEB_TEST_BASE','http://127.0.0.1:8086/')

class Client:
    def __init__(self):
        self.opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        page=self.opener.open(BASE,timeout=20).read().decode()
        self.csrf=re.search(r'name="csrf-token" content="([a-f0-9]+)"',page)[1]
        self.state=None
        self.last_raw=None
        self.last_bytes=0
    def call(self,action,get=False,expected=200,csrf=True,**data):
        if get:
            from urllib.parse import urlencode
            request=urllib.request.Request(BASE+'actions.php?'+urlencode({'action':action,**data}),headers={'X-Season-Response':'patch'})
        else:
            headers={'Content-Type':'application/json','X-Season-Response':'patch'}
            if csrf:headers['X-CSRF-Token']=self.csrf
            request=urllib.request.Request(BASE+'actions.php'+('?transfer=library' if action=='library_import' else ''),data=json.dumps({'action':action,**data}).encode(),headers=headers)
        try:response=self.opener.open(request,timeout=20)
        except urllib.error.HTTPError as error:response=error
        raw=response.read();self.last_bytes=len(raw);value=json.loads(raw);self.last_raw=copy.deepcopy(value)
        assert response.status==expected,(action,response.status,value)
        if value.get('data'):self.state=copy.deepcopy(value['data'])
        if value.get('patch') and self.state is not None:
            patch=value['patch'];assert int(patch['user_id'])==int((self.state['user'] or {}).get('id',0))
            next_state=copy.deepcopy(self.state)
            for name,key in [('anime','slug'),('jobs','id'),('history','id'),('queue_summary','slug')]:
                rows={} if name=='anime' and patch.get('replace_anime') else {str(row[key]):row for row in next_state.get(name,[])}
                rows.update({str(row[key]):row for row in patch.get(name,[])})
                if name=='anime':
                    for slug in patch.get('removed_anime',[]):rows.pop(slug,None)
                next_state[name]=list(rows.values())
            for key in ['csrf','settings','preferences_saved','updated_at','queue_totals']:
                if key in patch:next_state[key]=patch[key]
            next_state['history'].sort(key=lambda row:int(row['id']),reverse=True)
            next_state['history']=next_state['history'][:80]
            self.state=next_state;value['data']=copy.deepcopy(self.state)
        if self.state:self.csrf=self.state['csrf']
        return value

def main():
    c=Client();initial=c.call('state',get=True)['data']
    assert len(initial['anime'])==64 and not initial['user']
    c.call('follow',csrf=False,expected=403,slug=initial['anime'][0]['slug'])
    c.call('follow',expected=401,slug=initial['anime'][0]['slug'])
    email='qa-'+secrets.token_hex(5)+'@example.test'
    user=c.call('register',name='Cuenta de prueba',email=email,password='LocalTest-Only-8086')['data']['user']
    anime=initial['anime'][0];slug=anime['slug']
    r=c.call('follow',slug=slug,favorite=True,status='watching',score=9,notes='<b>Una nota privada</b>')
    assert next(a for a in r['data']['anime'] if a['slug']==slug)['favorite']
    detail=c.call('detail',get=True,slug=slug)['detail'];ep=detail['episodes'][0]
    c.call('watched',episode_id=ep['id'],watched=True)
    assert next(a for a in c.call('state',get=True)['data']['anime'] if a['slug']==slug)['watched']==1
    c.call('settings',review_time='99:99',expected=422)
    c.call('settings',server='Voe',height=720,workers=2,server_fallback='other',review_time='13:30')
    prepared=c.call('queue',slugs=[slug],mode='all');q=prepared['data']['jobs']
    assert len(q)==len(detail['episodes'])
    assert set(prepared['queue_ids'])=={j['id'] for j in q}
    again=c.call('queue',slugs=[slug],mode='all')['data']['jobs'];assert len(q)==len(again)
    selected=c.call('export',job_ids=[q[0]['id']])
    assert [j['web_id'] for j in selected['plan']['items']]==[q[0]['id']]
    assert sum(j['status']=='exported' for j in selected['data']['jobs'])==1
    c.call('export',job_ids=['invalid'],expected=422)
    exported=c.call('export');plan=exported['plan']
    assert len(plan['items'])==len(q) and plan['preferences']['height']==720
    assert all(j['status']=='exported' for j in exported['data']['jobs'])
    (ROOT/'verification/roundtrip-plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
    c.call('logout')
    c.call('login',email=email,password='wrong-password',expected=401)
    logged=c.call('login',email=email,password='LocalTest-Only-8086')['data'];assert logged['user']['id']==user['id']
    first=plan['items'][0]
    item={**first,'status':'completed','sha256':'a'*64,'bytes':1048576}
    receipt={'format':'seasonav1.web-results/v1','plans':[{'installation':plan['installation'],'plan_id':plan['plan_id'],'items':[item]}]}
    bad={**item,'sha256':'not-a-hash'}
    c.call('receipt',receipt={'format':receipt['format'],'plans':[{'installation':plan['installation'],'items':[bad]}]},expected=422)
    confirmed=c.call('receipt',receipt=receipt)['data']['jobs'];assert sum(j['status']=='confirmed' for j in confirmed)==1
    c.call('receipt',receipt=receipt);assert sum(j['status']=='confirmed' for j in c.call('state',get=True)['data']['jobs'])==1
    other=Client();other.call('register',name='Otra cuenta',email='qa-'+secrets.token_hex(5)+'@example.test',password='LocalTest-Only-8086')
    assert not other.call('state',get=True)['data']['jobs']
    other.call('cancel_job',id=first['web_id'])
    other.call('export',job_ids=[first['web_id']],expected=422)
    other.call('receipt',receipt=receipt)
    assert sum(j['status']=='confirmed' for j in c.call('state',get=True)['data']['jobs'])==1
    second=next((j for j in q if j['id']!=first['web_id']),None)
    if second:c.call('cancel_job',id=second['id']);assert next(j for j in c.call('state',get=True)['data']['jobs'] if j['id']==second['id'])['status']=='cancelled'
    result={'ok':True,'catalog_anime':len(initial['anime']),'known_episodes':sum(a['episodes'] for a in initial['anime']),'checks':['CSRF','registration','login_logout','private_accounts','favorites','watch_progress','validated_preferences','queue_deduplication','ordered_export','receipt_verification','receipt_idempotency','cross_account_isolation','cancel_web_job','selected_jobs_only_export','foreign_job_export_rejected']}
    (ROOT/'verification/http-check.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
