import http.client
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from seasonav1.config import Config
from seasonav1.database import Database
from seasonav1.downloader import Outcome
from seasonav1.runner import Runner
from seasonav1.web_bridge import WebBridge,pairing_token,SITE


class BridgeTests(unittest.TestCase):
    def setUp(self):
        root=Path(__file__).parent/'.tmp';root.mkdir(exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=root);self.folder=Path(self.temp.name)
        Config(autostart=False,notifications=False,resident_tray=True).save(self.folder)
        self.received=[];self.downloads=[]
        def accept(result):
            self.received.append(result)
            def download(job,*_):
                self.downloads.append(job['number'])
                return Outcome(self.folder/'video.mp4','SUB','MP4Upload',{'bytes':2048,'sha256':'c'*64,'height':720})
            runner=Runner(self.folder,downloader=download)
            try:
                with patch.object(runner,'plan',side_effect=AssertionError('No debe consultar el horario')):
                    runner.run(queue_only=True)
            finally:runner.close()
        self.bridge=WebBridge(self.folder,accept,port=0).start()
        self.token=pairing_token(self.folder)
        self.plan={'format':'seasonav1.web-plan/v1','installation':'b'*32,'plan_id':'a'*24,
                   'preferences':{'language':'SUB','selection':'favorites','favorites':[]},
                   'items':[{'web_id':n,'slug':'anime','title':'Anime','number':str(n),'weekday':1,'language':'SUB','url':f'https://animeav1.com/media/anime/{n}'} for n in [2,1]]}
    def tearDown(self):self.bridge.close();self.temp.cleanup()
    def request(self,method,path,body=None,headers=None):
        values={'Origin':SITE,'Authorization':'Bearer '+self.token}
        if body is not None:values['Content-Type']='application/json';body=json.dumps(body).encode()
        for key,value in (headers or {}).items():
            if value is None:values.pop(key,None)
            else:values[key]=value
        connection=http.client.HTTPConnection('127.0.0.1',self.bridge.port,timeout=8)
        try:
            connection.request(method,path,body,values);response=connection.getresponse();data=response.read()
            return response.status,dict(response.headers),json.loads(data) if data else {}
        finally:connection.close()

    def test_only_loopback_and_exact_https_origin_are_accepted(self):
        self.assertEqual(self.bridge.server.server_address[0],'127.0.0.1')
        before=(self.folder/'config.json').read_bytes()
        for origin in [None,'null','http://hk-br035.gt.tc','https://evil.example','https://hk-br035.gt.tc.evil.example']:
            with self.subTest(origin=origin):
                status,headers,_=self.request('POST','/queue',self.plan,{'Origin':origin})
                self.assertEqual(status,403);self.assertNotIn('Access-Control-Allow-Origin',headers)
        self.assertEqual(before,(self.folder/'config.json').read_bytes());self.assertFalse(self.received)

    def test_pairing_is_required_and_rotation_revokes_old_code(self):
        for token in [None,'Bearer invalid']:
            self.assertEqual(self.request('GET','/ping',headers={'Authorization':token})[0],401)
        self.assertEqual(self.request('GET','/ping')[0],200)
        new=pairing_token(self.folder,rotate=True)
        self.assertNotEqual(self.token,new)
        self.assertEqual(self.request('GET','/ping')[0],401)
        self.token=new;self.assertEqual(self.request('GET','/ping')[0],200)

    def test_preflight_allows_authorized_origin_and_private_network_without_wildcards(self):
        status,headers,_=self.request('OPTIONS','/queue',headers={'Authorization':None,'Access-Control-Request-Method':'POST','Access-Control-Request-Headers':'authorization,content-type','Access-Control-Request-Private-Network':'true'})
        self.assertEqual(status,204)
        self.assertEqual(headers['Access-Control-Allow-Origin'],SITE)
        self.assertEqual(headers['Access-Control-Allow-Private-Network'],'true')
        self.assertNotIn('Access-Control-Allow-Credentials',headers)
        self.assertEqual(self.request('OPTIONS','/queue',headers={'Access-Control-Request-Method':'DELETE'})[0],403)
        self.assertEqual(self.request('OPTIONS','/queue',headers={'Access-Control-Request-Method':'POST','Access-Control-Request-Headers':'x-unexpected'})[0],403)

    def test_group_control_and_file_checks_use_authenticated_scoped_bridge_routes(self):
        self.request('POST','/queue',self.plan)
        status,_,ping=self.request('GET','/ping')
        self.assertEqual(status,200);self.assertIn('group_control',ping['capabilities']);self.assertEqual(len(ping['device']['id']),32)
        body={'format':'seasonav1.web-control/v1','installation':'b'*32,'ids':[1,2],'action':'priority','priority':10}
        status,_,result=self.request('POST','/control',body)
        self.assertEqual(status,200);self.assertEqual(result['control']['priority'],10)
        status,_,result=self.request('POST','/files',{'installation':'b'*32,'ids':[1,999]})
        self.assertEqual(status,200);self.assertEqual([n['known'] for n in result['items']],[True,False])
        self.assertNotIn(str(self.folder),str(result))
        self.assertEqual(self.request('POST','/control',body,{'Origin':'https://evil.example'})[0],403)
        self.assertEqual(self.request('POST','/files',{'installation':'b'*32,'ids':[1]},{'Authorization':None})[0],401)
        self.assertEqual(self.request('POST','/control',{**body,'ids':[999]})[0],422)

    def test_dns_rebinding_host_is_rejected(self):
        self.assertEqual(self.request('POST','/queue',self.plan,{'Host':'evil.example'})[0],403)
        self.assertFalse(self.received)

    def test_import_starts_ordered_download_and_is_idempotent_and_results_are_scoped(self):
        status,_,result=self.request('POST','/queue',self.plan)
        self.assertEqual(status,200);self.assertEqual(result['added'],2)
        self.assertEqual(self.downloads,['1','2'])
        self.assertEqual(self.request('POST','/queue',self.plan)[2]['added'],0)
        self.assertEqual(self.downloads,['1','2'])
        status,_,result=self.request('GET','/results?installation='+self.plan['installation'])
        self.assertEqual(status,200);self.assertEqual(result['completed'],2)
        self.assertNotIn(str(self.folder),json.dumps(result))
        self.assertNotIn(self.token,json.dumps(result))
        self.assertEqual(self.request('GET','/results?installation='+'d'*32)[2]['completed'],0)

    def test_invalid_payload_cannot_modify_settings_and_oversize_is_rejected(self):
        before=(self.folder/'config.json').read_bytes()
        self.plan['items'][0]['url']='http://127.0.0.1/private'
        self.assertEqual(self.request('POST','/queue',self.plan)[0],422)
        self.assertEqual(self.request('POST','/queue',self.plan,{'Content-Type':'text/plain'})[0],415)
        self.assertEqual(self.request('POST','/queue',headers={'Content-Length':str(2*1024*1024+1),'Content-Type':'application/json'})[0],413)
        self.assertEqual(before,(self.folder/'config.json').read_bytes());self.assertFalse(self.received)

    def test_overlapping_import_is_rejected_and_ping_remains_responsive(self):
        with self.bridge.importing:
            self.assertEqual(self.request('POST','/queue',self.plan)[0],409)
            self.assertEqual(self.request('GET','/ping')[0],200)
        self.assertFalse(self.received)

    def test_settings_apply_without_queue_and_preserve_pause_and_destination(self):
        cfg=Config.load(self.folder);cfg.paused=True;cfg.destination=str(self.folder/'videos');cfg.save(self.folder)
        changed=[];self.bridge.on_settings=changed.append
        value={'format':'seasonav1.web-settings/v1','preferences':{'workers':3,'speed_kib':1200,'height':720,'review_time':'13:25','favorites':['anime']}}
        self.assertEqual(self.request('OPTIONS','/settings',headers={'Access-Control-Request-Method':'POST'})[0],204)
        status,_,result=self.request('POST','/settings',value)
        self.assertEqual(status,200);self.assertTrue(result['paused']);self.assertEqual(len(changed),1)
        saved=Config.load(self.folder);self.assertEqual(saved.workers,3);self.assertEqual(saved.speed_kib,1200);self.assertEqual(saved.destination,cfg.destination)
        self.assertTrue(saved.paused);self.assertFalse(self.received)
        self.assertEqual(self.request('POST','/settings',value)[0],200);self.assertEqual(len(changed),1)
        before=(self.folder/'config.json').read_bytes()
        for prefs in [{'destination':'C:/unexpected'},{'workers':True},{'workers':8},{'favorites':['../private']}]:
            self.assertEqual(self.request('POST','/settings',{'format':'seasonav1.web-settings/v1','preferences':prefs})[0],422)
        self.assertEqual((self.folder/'config.json').read_bytes(),before)

    def test_live_status_is_filtered_and_errors_do_not_expose_paths(self):
        self.bridge.on_queue=lambda result:None
        self.request('POST','/queue',self.plan)
        db=Database(self.folder)
        try:
            identifier=db.query("SELECT id FROM episodes WHERE number='1'")[0]['id']
            db.update(identifier,status='downloading',progress=62.5)
            url='/status?installation='+self.plan['installation']+'&ids=1,999'
            status,_,value=self.request('GET',url)
            self.assertEqual(status,200);self.assertEqual(value['jobs'],[{'web_id':1,'status':'downloading','progress':62.5,'reason':'','priority':0,'group_paused':False}])
            db.update(identifier,status='failed',error='getaddrinfo failed C:/private/path')
            value=self.request('GET',url)[2];self.assertEqual(value['jobs'][0]['reason'],'Sin conexión');self.assertNotIn('private',json.dumps(value))
            self.assertEqual(self.request('GET','/status?installation='+'d'*32+'&ids=1')[2]['jobs'],[])
            self.assertEqual(self.request('GET','/status?installation='+self.plan['installation']+'&ids=0')[0],422)
        finally:db.close()

    def test_more_than_fifty_plans_keep_their_receipts(self):
        self.bridge.on_queue=lambda result:None
        for n in range(1,52):
            plan=json.loads(json.dumps(self.plan));plan['plan_id']=f'{n:024x}';plan['items']=[{'web_id':n,'slug':'anime','title':'Anime','number':str(n),'weekday':1,'language':'SUB','url':f'https://animeav1.com/media/anime/{n}'}]
            self.assertEqual(self.request('POST','/queue',plan)[0],200)
        db=Database(self.folder)
        try:
            first=db.query("SELECT id FROM episodes WHERE number='1'")[0]['id'];db.update(first,status='completed',bytes=2048,sha256='e'*64)
        finally:db.close()
        result=self.request('GET','/results?installation='+self.plan['installation']+'&ids=1')[2]
        self.assertEqual(result['completed'],1);self.assertEqual(result['receipts'][0]['plans'][0]['items'][0]['web_id'],1)

    def test_existing_web_jobs_keep_their_requested_language_after_preferences_change(self):
        self.bridge.on_queue=lambda result:None
        self.request('POST','/queue',self.plan)
        self.request('POST','/settings',{'format':'seasonav1.web-settings/v1','preferences':{'language':'DUB'}})
        languages=[]
        def download(job,cfg,*_):
            languages.append(cfg.language)
            return Outcome(self.folder/'video.mp4',cfg.language,'MP4Upload',{'bytes':2048,'sha256':'c'*64,'height':720})
        runner=Runner(self.folder,downloader=download)
        try:runner.run(queue_only=True)
        finally:runner.close()
        self.assertEqual(languages,['SUB','SUB'])
