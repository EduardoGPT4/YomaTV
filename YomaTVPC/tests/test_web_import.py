import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from seasonav1.config import Config,season_folder
from seasonav1.database import Database
from seasonav1.runner import Runner
from seasonav1.web_import import import_plan,export_results
from seasonav1.downloader import Outcome


class WebImportTests(unittest.TestCase):
    def setUp(self):
        root=Path(__file__).parent/'.tmp';root.mkdir(exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=root);self.folder=Path(self.temp.name)
        Config(destination=str(self.folder/'videos'),autostart=False,notifications=False).save(self.folder)
        self.plan={'format':'seasonav1.web-plan/v1','plan_id':'a'*24,'installation':'b'*32,
                   'preferences':{'language':'SUB','server':'MP4Upload','height':720,'selection':'favorites','favorites':[]},
                   'items':[{'web_id':n,'slug':'anime','title':'Anime','weekday':1,'number':str(n),'url':f'https://animeav1.com/media/anime/{n}','language':'SUB'} for n in [2,1]]}
        self.file=self.folder/'plan.json';self.save()
    def save(self):self.file.write_text(json.dumps(self.plan),encoding='utf-8')
    def tearDown(self):self.temp.cleanup()

    def test_import_keeps_destination_deduplicates_and_queue_only_has_no_schedule_requests(self):
        self.assertEqual(import_plan(self.folder,self.file)['added'],2)
        self.assertEqual(import_plan(self.folder,self.file)['added'],0)
        cfg=Config.load(self.folder);self.assertEqual(cfg.destination,str((self.folder/'videos').resolve()));self.assertEqual(cfg.height,720)
        calls=[]
        def download(job,*_):
            calls.append(job['number'])
            return Outcome(self.folder/'video.mp4','SUB','MP4Upload',{'bytes':2048,'sha256':'c'*64,'height':720})
        runner=Runner(self.folder,downloader=download)
        try:
            with patch.object(runner,'plan',side_effect=AssertionError('No debe consultar el horario')):
                result=runner.run(queue_only=True)
            self.assertEqual(result['downloaded'],2);self.assertEqual(calls,['1','2'])
            self.assertFalse(runner.db.meta('bootstrap_processed',False))
        finally:runner.close()
        result=export_results(self.folder,self.folder/'receipt.json')
        receipt=json.loads(Path(result['files'][0]).read_text())
        self.assertEqual(result['completed'],2)
        self.assertEqual(receipt['format'],'seasonav1.web-results/v1')
        self.assertEqual({r['web_id'] for r in receipt['plans'][0]['items']},{1,2})
        self.assertNotIn(str(self.folder),json.dumps(receipt))

    def test_invalid_remote_url_changes_neither_settings_nor_queue(self):
        self.plan['items'][1]['url']='http://127.0.0.1/private';self.save()
        before=(self.folder/'config.json').read_bytes()
        with self.assertRaises(Exception):import_plan(self.folder,self.file)
        self.assertEqual(before,(self.folder/'config.json').read_bytes())
        db=Database(self.folder)
        try:self.assertFalse(db.query('SELECT * FROM episodes'))
        finally:db.close()

    def test_existing_completed_episode_is_confirmed_without_queue_reset(self):
        import_plan(self.folder,self.file);db=Database(self.folder)
        try:
            identifier=db.query("SELECT id FROM episodes WHERE number='1'")[0]['id']
            db.update(identifier,status='completed',bytes=3000,sha256='d'*64,progress=100)
        finally:db.close()
        import_plan(self.folder,self.file)
        result=export_results(self.folder,self.folder/'results.json')
        self.assertEqual(result['completed'],1)

    def test_reexported_web_jobs_do_not_accumulate_duplicate_receipts(self):
        import_plan(self.folder,self.file)
        self.plan['plan_id']='e'*24;self.save();import_plan(self.folder,self.file)
        db=Database(self.folder)
        try:
            plans=db.meta('web_imports')
            self.assertEqual(len(plans),1)
            self.assertEqual(len(plans[0]['items']),2)
        finally:db.close()

    def test_split_series_places_new_episodes_in_current_season_and_keeps_completed_paths(self):
        self.plan['preferences'].update(season_source='premiere',long_series='keep')
        for item in self.plan['items']:item['start_date']='2024-01-01'
        later=self.plan['items'].pop(0);self.save();import_plan(self.folder,self.file)
        db=Database(self.folder)
        try:
            first=db.query('SELECT * FROM episodes')[0]
            db.update(first['id'],status='completed',path='invierno2024/Anime/01.mp4')
        finally:db.close()
        self.plan['preferences']['long_series']='split'
        self.plan['items'].append(later);self.save()
        with patch('seasonav1.web_import.date',wraps=date) as calendar:
            calendar.today.return_value=date(2026,10,12)
            import_plan(self.folder,self.file)
        db=Database(self.folder)
        try:
            episodes={row['number']:row for row in db.query('SELECT * FROM episodes')}
            self.assertEqual(episodes['2']['season'],season_folder(date(2026,10,12)))
            self.assertEqual(episodes['1']['season'],'invierno2024')
            self.assertEqual(episodes['1']['path'],'invierno2024/Anime/01.mp4')
            self.assertEqual(episodes['1']['status'],'completed')
            self.assertEqual(db.anime('anime')['season'],'invierno2024')
        finally:db.close()

    def test_large_result_files_stay_under_web_upload_limit(self):
        import_plan(self.folder,self.file);db=Database(self.folder)
        try:
            identifier=db.query("SELECT id FROM episodes WHERE number='1'")[0]['id']
            db.update(identifier,status='completed',bytes=2048,sha256='d'*64)
            plans=[]
            for p in range(20):
                items=[{'web_id':p*400+n+1,'episode_id':identifier,'slug':'a'*240,'number':'1','language':'SUB'} for n in range(400)]
                plans.append({'plan_id':str(p).zfill(24),'installation':'b'*32,'items':items})
            db.set_meta('web_imports',plans)
        finally:db.close()
        result=export_results(self.folder,self.folder/'large.json')
        self.assertEqual(result['completed'],8000)
        self.assertGreater(len(result['files']),1)
        self.assertTrue(all(Path(p).stat().st_size<2*1024*1024 for p in result['files']))
