import tempfile
import unittest
from email.message import Message
from io import BytesIO
from pathlib import Path
from urllib.error import HTTPError

from seasonav1.database import Database
from seasonav1.http import HttpClient


class HttpTests(unittest.TestCase):
    def test_conditional_304_reads_cached_html_and_not_images(self):
        root=Path(__file__).parent/".tmp";root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as directory:
            db=Database(Path(directory))
            url="https://animeav1.com/horario";db.save_cache(url,"<html>cached</html>","tag",None)
            def respond(request,timeout):
                self.assertEqual(request.get_header("If-none-match"),"tag")
                self.assertEqual(request.get_header("Accept"),"text/html")
                raise HTTPError(url,304,"Not modified",Message(),BytesIO())
            try:self.assertEqual(HttpClient(db,interval=0,opener=respond).fetch(url),"<html>cached</html>")
            finally:db.close()
