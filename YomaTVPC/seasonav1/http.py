from __future__ import annotations

import gzip
import io
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from .engine.catalog import Cancelled, DownloadError, USER_AGENT


class HttpClient:
    def __init__(self, database, token=None, interval=2, retry_delays=(2, 5, 15), opener=urlopen):
        self.database, self.token = database, token if token is not None else threading.Event()
        self.interval, self.retry_delays, self.opener = interval, retry_delays, opener
        self.lock = threading.Lock()
        self.next_request = 0
        self.requests = 0

    def wait(self, seconds):
        if self.token.wait(max(0, seconds)):
            raise Cancelled("Revisión pausada.")

    def fetch(self, url):
        parsed = urlsplit(url)
        if parsed.scheme != "https" or parsed.hostname != "animeav1.com" or not (parsed.path == "/horario" or parsed.path.startswith("/media/")):
            raise DownloadError("Dirección de consulta no permitida.")
        cached = self.database.cache(url)
        headers = {"User-Agent": USER_AGENT, "Accept": "text/html", "Accept-Encoding": "gzip"}
        if cached:
            if cached["etag"]: headers["If-None-Match"] = cached["etag"]
            if cached["modified"]: headers["If-Modified-Since"] = cached["modified"]
        for attempt in range(len(self.retry_delays) + 1):
            with self.lock:
                self.wait(self.next_request - time.monotonic())
                self.next_request = time.monotonic() + self.interval
                self.requests += 1
            try:
                with self.opener(Request(url, headers=headers), timeout=25) as response:
                    data = response.read(8 * 1024 * 1024 + 1)
                    if len(data) > 8 * 1024 * 1024:
                        raise DownloadError("El HTML supera el límite de tamaño esperado.")
                    if response.headers.get("Content-Encoding") == "gzip":
                        data = gzip.GzipFile(fileobj=io.BytesIO(data)).read(8 * 1024 * 1024 + 1)
                    if len(data) > 8 * 1024 * 1024:
                        raise DownloadError("El HTML descomprimido supera el límite esperado.")
                    body = data.decode("utf-8", errors="replace")
                    self.database.save_cache(url, body, response.headers.get("ETag"), response.headers.get("Last-Modified"))
                    return body
            except HTTPError as exc:
                if exc.code == 304 and cached:
                    exc.close()
                    self.database.save_cache(url,cached["body"],cached["etag"],cached["modified"])
                    return cached["body"]
                error = DownloadError(f"AnimeAV1 respondió HTTP {exc.code}.", retryable=exc.code == 429 or exc.code >= 500)
                try: wait = min(300, max(0, int(exc.headers.get("Retry-After", "0"))))
                except ValueError: wait = 0
                exc.close()
            except (URLError, TimeoutError, OSError) as exc:
                error, wait = DownloadError(f"Sin conexión con AnimeAV1: {exc}", retryable=True), 0
            if not error.retryable or attempt == len(self.retry_delays):
                raise error
            self.wait(max(self.retry_delays[attempt], wait))
