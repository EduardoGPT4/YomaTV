import unittest
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

from seasonav1.windows_tasks import NS,task_name,task_xml


class TaskTests(unittest.TestCase):
    def test_daily_logon_catchup_quotes_and_no_elevated_privileges(self):
        xml=task_xml([r"C:\A B\SeasonAV1.exe","--data-dir",r"C:\A B\datos","--scheduled"],Path("datos"),"12:00","S-1-5-21-123",True,datetime(2026,10,11,14))
        tree=ET.fromstring(xml);ns={"t":NS}
        self.assertEqual(tree.findtext("t:Triggers/t:CalendarTrigger/t:StartBoundary",namespaces=ns),"2026-10-12T12:00:00")
        self.assertIsNotNone(tree.find("t:Triggers/t:LogonTrigger",ns))
        self.assertEqual(tree.findtext("t:Settings/t:StartWhenAvailable",namespaces=ns),"true")
        self.assertEqual(tree.findtext("t:Settings/t:MultipleInstancesPolicy",namespaces=ns),"Parallel")
        self.assertEqual(tree.findtext("t:Principals/t:Principal/t:RunLevel",namespaces=ns),"LeastPrivilege")
        self.assertIn('"C:\\A B\\datos"',tree.findtext("t:Actions/t:Exec/t:Arguments",namespaces=ns))
        self.assertEqual(task_name(Path("datos"),"sid"),task_name(Path("datos"),"sid"))

    def test_autostart_can_be_disabled(self):
        tree=ET.fromstring(task_xml(["SeasonAV1.exe"],Path("datos"),"18:30","sid",False))
        self.assertIsNone(tree.find("{*}Triggers/{*}LogonTrigger"))

    def test_manual_mode_has_logon_without_daily_season_review(self):
        tree=ET.fromstring(task_xml(['AnimeAV1Plus.exe'],Path('datos'),'12:00','sid',True,schedule_enabled=False))
        self.assertIsNone(tree.find('{*}Triggers/{*}CalendarTrigger'))
        self.assertIsNotNone(tree.find('{*}Triggers/{*}LogonTrigger'))
