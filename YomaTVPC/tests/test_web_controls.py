import tempfile,threading,unittest
from pathlib import Path
from unittest.mock import patch
from seasonav1.config import Config
from seasonav1.database import Database
from seasonav1.downloader import Outcome
from seasonav1.runner import Runner
from seasonav1.web_import import import_plan,queue_status
from seasonav1.web_controls import check_files,control_queue,device_info,GroupToken

class WebControlTests(unittest.TestCase):
    def setUp(self):
        root=Path(__file__).parent/'.tmp';root.mkdir(exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=root);self.folder=Path(self.temp.name)
        Config(destination=str(self.folder/'videos'),notifications=False,autostart=False,workers=1).save(self.folder)
        self.installation='b'*32
        self.plan={'format':'seasonav1.web-plan/v1','installation':self.installation,'plan_id':'a'*24,'preferences':{'language':'SUB','selection':'favorites','favorites':[]},'items':[
            {'web_id':i,'slug':slug,'title':slug,'number':str(n),'weekday':1,'language':'SUB','url':f'https://animeav1.com/media/{slug}/{n}'}
            for i,slug,n in [(1,'anime-a',2),(2,'anime-a',1),(3,'anime-b',1)]]}
        import_plan(self.folder,self.plan)
    def tearDown(self):self.temp.cleanup()
    def control(self,action,ids=[1,2],**extra):
        return control_queue(self.folder,{'format':'seasonav1.web-control/v1','installation':self.installation,'ids':ids,'action':action,**extra})
    def test_redownload_revision_survives_import_and_is_echoed_in_receipts(self):
        from seasonav1.web_import import result_receipts
        self.plan['items'][0]['request_revision']='c'*32
        import_plan(self.folder,self.plan)
        db=Database(self.folder)
        try:
            job=db.query("SELECT id FROM episodes WHERE slug='anime-a' AND number='2'")[0]['id']
            db.update(job,status='completed',path='mock.mp4',bytes=2048,sha256='d'*64)
        finally:db.close()
        receipt=result_receipts(self.folder)['receipts'][0]
        item=next(j for p in receipt['plans'] for j in p['items'] if j['web_id']==1)
        self.assertEqual(item['request_revision'],'c'*32)

    def test_identity_stable_and_no_paths_or_tokens_in_files(self):
        self.assertEqual(device_info(self.folder)['id'],device_info(self.folder)['id'])
        r=check_files(self.folder,{'installation':self.installation,'ids':[1,900]})
        self.assertEqual([(n['known'],n['present']) for n in r['items']],[(True,None),(False,None)])
        self.assertNotIn(str(self.folder),str(r))
    def test_group_pause_and_priority_are_scoped_and_global_pause_preserved(self):
        cfg=Config.load(self.folder);cfg.paused=True;cfg.save(self.folder)
        self.control('pause');self.control('priority',priority=10)
        db=Database(self.folder)
        try:
            self.assertEqual(db.group_control('anime-a'),{'paused':1,'priority':10})
            self.assertEqual(db.group_control('anime-b')['paused'],0)
            token=GroupToken(threading.Event(),db,'anime-a');self.assertTrue(token.is_set())
        finally:db.close()
        self.assertTrue(self.control('resume')['global_paused'])
        self.assertTrue(Config.load(self.folder).paused)
    def test_unknown_or_cross_installation_and_multi_anime_controls_rejected(self):
        for ids in [[1,3],[1,999],[True]]:
            with self.assertRaises(ValueError):self.control('pause',ids)
        with self.assertRaises(ValueError):control_queue(self.folder,{'format':'seasonav1.web-control/v1','installation':'c'*32,'ids':[1],'action':'pause'})
    def test_existing_file_cannot_be_reset_but_missing_file_requires_explicit_confirmation(self):
        video=self.folder/'fixture.mp4';video.write_bytes(b'x'*2048)
        db=Database(self.folder)
        try:
            job=db.query("SELECT id FROM episodes WHERE slug='anime-a' AND number='2'")[0]['id']
            db.update(job,status='completed',path=str(video),bytes=2048,sha256='a'*64)
        finally:db.close()
        self.assertTrue(check_files(self.folder,{'installation':self.installation,'ids':[1]})['items'][0]['present'])
        with self.assertRaises(ValueError):self.control('redownload',[1],confirmation='REDESCARGAR')
        video.unlink()
        with self.assertRaises(ValueError):self.control('redownload',[1])
        self.control('redownload',[1],confirmation='REDESCARGAR')
        db=Database(self.folder)
        try:self.assertEqual(db.query('SELECT status FROM episodes WHERE id=?',(job,))[0]['status'],'pending')
        finally:db.close()
    def test_runner_priority_and_pause_affect_real_group_claiming_in_numeric_order(self):
        calls=[]
        def download(job,*args):
            calls.append((job['slug'],job['number']))
            return Outcome(self.folder/'mock.mp4','SUB','MP4Upload',{'bytes':2048,'sha256':'a'*64,'height':720})
        self.control('priority',[3],priority=10);self.control('pause')
        runner=Runner(self.folder,downloader=download)
        try:
            with patch.object(runner,'plan',side_effect=AssertionError('No schedule scraping')):runner.run(queue_only=True)
        finally:runner.close()
        self.assertEqual(calls,[('anime-b','1')]);self.control('resume')
        runner=Runner(self.folder,downloader=download)
        try:
            with patch.object(runner,'plan',side_effect=AssertionError('No schedule scraping')):runner.run(queue_only=True)
        finally:runner.close()
        self.assertEqual(calls,[('anime-b','1'),('anime-a','1'),('anime-a','2')])

if __name__=='__main__':unittest.main()
