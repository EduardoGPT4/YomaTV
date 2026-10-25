import json
import os
import socket
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from seasonav1.instance import Instance, send


class InstanceTests(unittest.TestCase):
    def setUp(self):
        root=Path(__file__).parent/'.tmp';root.mkdir(exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=root)
        self.folder=Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_second_process_forwards_to_owner_and_stale_endpoint_recovers(self):
        with Instance(self.folder,'window') as owner:
            self.assertTrue(owner.claim({'action':'show'}))
            code="from pathlib import Path; import sys; from seasonav1.instance import Instance; i=Instance(Path(sys.argv[1]),'window'); print(i.claim({'action':'show','history':True})); i.close()"
            result=subprocess.run([sys.executable,'-X','utf8','-c',code,str(self.folder)],capture_output=True,text=True,timeout=10)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(result.stdout.strip(),'False')
            self.assertEqual(owner.commands.get(timeout=2),{'action':'show','history':True})
            self.assertTrue((self.folder/'window-instance.json').is_file())
        self.assertFalse((self.folder/'window-instance.json').exists())
        (self.folder/'window-instance.json').write_text('{"port":1,"token":"stale"}')
        with Instance(self.folder,'window') as recovered:
            self.assertTrue(recovered.claim({'action':'show'}))
            self.assertTrue(send(self.folder,'window',{'action':'show'}))
            self.assertEqual(recovered.commands.get(timeout=2),{'action':'show'})

    def test_tray_and_window_are_independent_and_reject_unauthorized_message(self):
        with Instance(self.folder,'window') as window, Instance(self.folder,'tray') as tray:
            self.assertTrue(window.claim({'action':'show'}))
            self.assertTrue(tray.claim({'action':'scheduled'}))
            info=json.loads((self.folder/'tray-instance.json').read_text())
            with socket.create_connection(('127.0.0.1',info['port']),timeout=1) as client:
                client.sendall(b'{"token":"incorrect","command":{"action":"exit"}}\n')
                self.assertEqual(client.recv(16),b'')
            self.assertTrue(tray.commands.empty())
            self.assertTrue(send(self.folder,'tray',{'action':'scheduled'}))
            self.assertEqual(tray.commands.get(timeout=2),{'action':'scheduled'})
            self.assertTrue(window.commands.empty())

    @unittest.skipUnless(os.name=='nt','Canales nativos de Windows')
    def test_worker_without_console_preserves_redirected_output(self):
        pythonw=Path(sys.executable).with_name('pythonw.exe')
        result=subprocess.run([str(pythonw),'-X','utf8','-m','seasonav1','--worker','--version'],capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(result.stdout.strip(),'2026.08.19')
