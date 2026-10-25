import tempfile
import gc
import unittest
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch

from seasonav1.config import Config
from seasonav1.gui import App
from seasonav1.instance import Instance
from seasonav1.schedule import parse_schedule
from support import FixtureClient
from seasonav1.engine.catalog import parse_page
from support import catalog_page


class GuiTests(unittest.TestCase):
    def setUp(self):
        root=Path(__file__).parent/'.tmp';root.mkdir(exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=root);self.folder=Path(self.temp.name)
        self.app=App(self.folder);self.app.withdraw()
    def tearDown(self):
        self.app.destroy();self.app=None;gc.collect();self.temp.cleanup()
    def test_weekly_filter_and_favorite_and_pause_persist(self):
        schedule=parse_schedule(FixtureClient.pages['https://animeav1.com/horario'])
        self.app.db.set_meta('weekly_schedule',[asdict(a) for a in schedule]);self.app.refresh_table()
        self.assertEqual(len(self.app.tree.get_children()),2)
        self.app.tree.selection_set('domingo');self.app.mark_list('favorites')
        self.assertEqual(Config.load(self.folder).favorites,['domingo'])
        self.app.day_filter.set('Domingo');self.app.refresh_table()
        self.assertEqual(self.app.tree.get_children(),('domingo',))
        with patch('seasonav1.gui.spawn'):
            self.app.pause();self.app.refresh_table();self.assertEqual(self.app.pause_button['text'],'Continuar')
            self.assertTrue(Config.load(self.folder).paused)
    def test_invalid_clock_does_not_activate_scheduler(self):
        self.app.vars['review_time'].set('99:00')
        with patch('seasonav1.gui.install') as scheduler:
            self.app.save_activate();scheduler.assert_not_called()
        self.assertIn('HH:MM',self.app.status.get())

    def test_general_download_is_default_and_range_selection_updates_real_table(self):
        panel=self.app.download_tab
        self.assertEqual(self.app.tabs.select(),str(panel))
        self.assertIn('YomaTV',self.app.title())
        panel.show_catalog(parse_page(catalog_page('classic',(1,2,12.5,100)), 'https://animeav1.com/media/classic'))
        panel.ranges.set('1-2,12.5');panel.apply_range()
        self.assertEqual(panel.tree.selection(),('1','2','12.5'))
        self.assertEqual(str(panel.download_button['state']),'normal')
        self.assertFalse(self.app.vars['schedule_enabled'].get())
        self.app.deiconify();self.app.update()
        self.assertGreater(panel.tree.winfo_height(),150)

    def test_continue_general_queue_never_forces_full_season_review(self):
        with patch('seasonav1.gui.spawn') as spawn:
            self.app.resume_queue()
            spawn.assert_called_once_with(self.folder,'--resume-queue')

    def test_saving_general_settings_preserves_existing_pause(self):
        cfg=Config.load(self.folder);cfg.paused=True;cfg.save(self.folder)
        with patch.object(self.app,'background',side_effect=lambda work,done:done(work())), patch('seasonav1.gui.install',return_value='test-task'), patch('seasonav1.gui.spawn') as spawn:
            self.app.save_activate()
            spawn.assert_called_once_with(self.folder,'--tray')
        self.assertTrue(Config.load(self.folder).paused)
        self.assertFalse(Config.load(self.folder).schedule_enabled)

    def test_disabling_season_also_updates_form_without_deleting_data(self):
        with patch.object(self.app,'background',side_effect=lambda work,done:done(work())), patch('seasonav1.gui.uninstall'):
            self.app.remove_task()
        self.assertFalse(self.app.vars['schedule_enabled'].get())
        self.assertFalse(self.app.vars['autostart'].get())

    def test_scheduler_error_restores_configuration_instead_of_leaving_pause(self):
        before=(self.folder/'config.json').read_bytes() if (self.folder/'config.json').exists() else None
        cfg=Config.load(self.folder);cfg.save(self.folder);before=(self.folder/'config.json').read_bytes()
        with patch.object(self.app,'background',side_effect=lambda work,done:done(work())), patch('seasonav1.gui.install',side_effect=RuntimeError('Windows no disponible')):
            with self.assertRaisesRegex(RuntimeError,'Windows no disponible'):
                self.app.save_activate()
        self.assertEqual((self.folder/'config.json').read_bytes(),before)

    def test_repeated_activation_restores_same_window_and_opens_history(self):
        with Instance(self.folder,'window') as owner, Instance(self.folder,'window') as second:
            self.assertTrue(owner.claim({'action':'show'}))
            self.app.instance=owner
            original_id=self.app.winfo_id()
            self.assertFalse(second.claim({'action':'show','history':True}))
            self.app.poll();self.app.update()
            self.assertEqual(self.app.winfo_id(),original_id)
            self.assertEqual(self.app.state(),'normal')
            self.assertEqual(self.app.tabs.select(),str(self.app.history_tab))
            self.app.instance=None
