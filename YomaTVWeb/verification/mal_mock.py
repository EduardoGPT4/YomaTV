"""Local fake MAL provider. It never contacts MyAnimeList or stores real credentials."""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

STATE = {'refreshes': 0, 'exchange_ok': False, 'mode': 'normal','updates':{},'deleted':[],'patch_calls':[]}

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_): pass
    def respond(self, data, status=200):
        raw=json.dumps(data).encode()
        self.send_response(status); self.send_header('Content-Type','application/json')
        self.send_header('Content-Length',str(len(raw))); self.end_headers(); self.wfile.write(raw)
    def do_POST(self):
        if self.path == '/control':
            STATE.update(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
            return self.respond({'ok':True})
        body=parse_qs(self.rfile.read(int(self.headers['Content-Length'])).decode())
        if self.path != '/token': return self.respond({},404)
        if body.get('client_secret') != ['local-test-secret']: return self.respond({'error':'bad_secret'},401)
        if body.get('grant_type') == ['authorization_code']:
            STATE['exchange_ok']=(body.get('redirect_uri') == ['https://hk-br035.gt.tc/seasonav1/mal-callback.php']
                and len(body.get('code_verifier',[''])[0]) == 96)
            if body.get('code') == ['provider-error']: return self.respond({'error':'invalid_grant','secret':'must-not-leak'},400)
        else:
            STATE['refreshes']+=1
            if STATE['mode']=='invalid_grant': return self.respond({'error':'invalid_grant'},400)
        return self.respond({'token_type':'Bearer','expires_in':3600,
          'access_token':'mock-access-token-refreshed' if STATE['refreshes'] else 'mock-access-token',
          'refresh_token':'mock-refresh-token-rotated' if STATE['refreshes'] else 'mock-refresh-token'})
    def do_GET(self):
        url=urlsplit(self.path)
        if url.path=='/control': return self.respond(STATE)
        if STATE['mode']=='offline': return self.respond({'error':'temporary'},503)
        if STATE['mode']=='throttled': return self.respond({'error':'rate_limit'},429)
        if not self.headers.get('Authorization','').startswith('Bearer mock-access-token'):
            return self.respond({'error':'invalid_token'},401)
        if STATE['mode']=='unauthorized' and self.headers.get('Authorization')=='Bearer mock-access-token':
            return self.respond({'error':'invalid_token'},401)
        if url.path=='/profile': return self.respond(STATE.get('profile',{'id':12345,'name':'LocalMAL_Test'}))
        if url.path.startswith('/anime:'):
            id=int(url.path.split(':')[1])
            status=STATE['updates'].get(str(id),{'status':'watching','score':8,'num_episodes_watched':5})
            return self.respond({'id':id,'title':'Naruto' if id==20 else 'One Piece','num_episodes':220 if id==20 else 0,'my_list_status':status} if id not in STATE['deleted'] else {'id':id,'title':'Naruto','num_episodes':220})
        if url.path=='/list':
            offset=int(parse_qs(url.query).get('offset',['0'])[0]);count=50 if offset==0 else 3
            if 'alternative_titles' in parse_qs(url.query).get('fields',[''])[0]:
                data=[]
                for n in range(offset,offset+count):
                    id=20 if n==0 else 21 if n==1 else 1000+n
                    if id in STATE['deleted']:continue
                    title='Naruto' if n==0 else 'One Piece' if n==1 else f'Anime de prueba {n+1}'
                    node={'id':id,'title':title,'alternative_titles':{'en':'Ninja Adventures' if n==0 else title,'synonyms':[]},'media_type':'tv','start_date':'2002-10-03' if n==0 else '1999-10-20','status':'finished_airing' if n==0 else 'currently_airing','num_episodes':220 if n==0 else 0,'average_episode_duration':1440,'genres':[{'id':1,'name':'Action'}]}
                    status=STATE['updates'].get(str(id),{'status':'plan_to_watch' if n==1 else 'watching','score':8,'num_episodes_watched':5})
                    data.append({'node':node,'list_status':status})
                return self.respond({'data':data,'paging':{'next':'https://untrusted.invalid/never-follow-this'} if offset==0 else {}})
            return self.respond({'data':[{'node':{'id':offset+n+1,'title':f'Anime de prueba {offset+n+1}'},
                'list_status':{'status':'watching','score':8,'num_episodes_watched':5}} for n in range(count)],
                'paging':{'next':'https://untrusted.invalid/never-follow-this'} if offset==0 else {}})
        if url.path=='/search':
            other='one piece' in parse_qs(url.query).get('q',[''])[0].lower()
            return self.respond({'data':[{'node':{'id':21 if other else 20,'title':'One Piece' if other else 'Naruto','media_type':'tv','start_date':'1999-10-20' if other else '2002-10-03','num_episodes':0 if other else 220}}]})
        return self.respond({},404)
    def do_PATCH(self):
        if not self.path.startswith('/list-status:'):return self.respond({},404)
        if STATE['mode']=='offline':return self.respond({'error':'temporary'},503)
        body=parse_qs(self.rfile.read(int(self.headers['Content-Length'])).decode());id=self.path.split(':')[1]
        STATE['patch_calls'].append({'id':int(id),'fields':body})
        previous=STATE['updates'].get(id,{'status':'watching','score':8,'num_episodes_watched':5})
        status={'status':body.get('status',[previous['status']])[0],'score':int(body.get('score',[previous['score']])[0]),'num_episodes_watched':int(body.get('num_watched_episodes',[previous['num_episodes_watched']])[0])}
        STATE['updates'][id]=status;STATE['deleted']=[value for value in STATE['deleted'] if value!=int(id)];return self.respond(status)
    def do_DELETE(self):
        if not self.path.startswith('/list-status:'):return self.respond({},404)
        if STATE['mode']=='offline':return self.respond({'error':'temporary'},503)
        STATE['deleted'].append(int(self.path.split(':')[1]));return self.respond({},204)

if __name__=='__main__':
    print('MAL mock: http://127.0.0.1:8097',flush=True)
    ThreadingHTTPServer(('127.0.0.1',8097),Handler).serve_forever()
