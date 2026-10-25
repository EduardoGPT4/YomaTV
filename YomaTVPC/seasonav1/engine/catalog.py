from __future__ import annotations

import html
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from decimal import Decimal
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

import json5

ORIGIN = "https://animeav1.com"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130.0.0.0 Safari/537.36"
EXAMPLE_URL = ORIGIN + "/media/dark-summoner-to-dekiteiru/1"


class DownloadError(Exception):
    """Error que se puede mostrar directamente al usuario."""

    def __init__(self, message, retryable=False, retry_after=0):
        super().__init__(message)
        self.retryable = retryable
        self.retry_after = retry_after


class Cancelled(DownloadError):
    pass


@dataclass(frozen=True)
class Episode:
    number: str
    url: str


@dataclass(frozen=True)
class Mirror:
    server: str
    language: str
    url: str
    kind: str


@dataclass
class Catalog:
    title: str
    slug: str
    episodes: list[Episode]
    selected: str | None
    mirrors: list[Mirror]
    cover_url: str | None = None


def normalize_url(value: str) -> tuple[str, str, str | None]:
    value = value.strip()
    if "://" not in value:
        value = "https://" + value
    parsed = urlsplit(value)
    if (parsed.scheme not in ("http", "https")
            or parsed.hostname not in ("animeav1.com", "www.animeav1.com")
            or parsed.username or parsed.password or parsed.port not in (None, 80, 443)):
        raise DownloadError("Pega una URL de animeav1.com/media/nombre o /media/nombre/capítulo.")
    match = re.fullmatch(r"/media/([a-zA-Z0-9_-]+)(?:/(\d+(?:\.\d+)?))?/?", parsed.path)
    if not match:
        raise DownloadError("La dirección debe ser la ficha de un anime o uno de sus capítulos.")
    slug, number = match.groups()
    return ORIGIN + f"/media/{slug}" + (f"/{number}" if number else ""), slug, number


def fetch_html(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = response.read(8 * 1024 * 1024 + 1)
            if len(data) > 8 * 1024 * 1024:
                raise DownloadError("La página excede el tamaño esperado.")
            return data.decode(response.headers.get_content_charset() or "utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            try:
                delay = min(300, max(5, int(exc.headers.get("Retry-After", "15"))))
            except ValueError:
                delay = 15
            raise DownloadError("El sitio está limitando las solicitudes (429).", retryable=True, retry_after=delay) from exc
        raise DownloadError(f"La página respondió HTTP {exc.code}. Comprueba que siga disponible.", retryable=exc.code >= 500) from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise DownloadError(f"No se pudo conectar con la página: {exc}", retryable=True) from exc


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links: list[str] = []
        self.scripts: list[str] = []
        self.title = ""
        self.in_title = False
        self.in_script = False
        self.cover_url = None
        self.poster_url = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a" and attrs.get("href"):
            self.links.append(attrs["href"])
        elif tag == "title":
            self.in_title = True
        elif tag == "script":
            self.in_script = True
        elif tag == "meta" and attrs.get("property", attrs.get("name")) in ("og:image", "twitter:image"):
            self.cover_url = self.cover_url or attrs.get("content")
        elif tag == "img" and ("aspect-poster" in attrs.get("class", "") or attrs.get("alt", "").endswith(" Poster")):
            self.poster_url = self.poster_url or attrs.get("src")

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False
        elif tag == "script":
            self.in_script = False

    def handle_data(self, data):
        if self.in_title:
            self.title += data
        if self.in_script:
            self.scripts.append(data)


def literal_property(source: str, name: str):
    """Lee solo literales; nunca evalúa JavaScript recibido del sitio."""
    start = None
    # Saltar cadenas completas impide confundir texto de la sinopsis con claves.
    tokens = re.finditer(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[A-Za-z_$][\w$]*', source)
    for token in tokens:
        key = token.group()
        if key not in (name, '"' + name + '"', "'" + name + "'"):
            continue
        colon = re.match(r"\s*:\s*", source[token.end():])
        if colon:
            start = token.end() + colon.end()
            break
    if start is None:
        return None
    if start >= len(source):
        return None
    if source[start] not in "[{\"'":
        return None
    stack = []
    quote = None
    escaped = False
    for index in range(start, len(source)):
        char = source[index]
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
                if not stack:
                    return json5.loads(source[start:index + 1])
        elif char in "\"'":
            quote = char
        elif char in "[{":
            stack.append(char)
        elif char in "]}":
            if not stack or (stack.pop(), char) not in (("[", "]"), ("{", "}")):
                raise DownloadError("La estructura de datos de la página cambió.")
            if not stack:
                try:
                    return json5.loads(source[start:index + 1])
                except ValueError as exc:
                    raise DownloadError(f"No se pudo leer el campo {name} de la página.") from exc
    raise DownloadError(f"El campo {name} está incompleto en la página.")


def parse_page(source: str, url: str) -> Catalog:
    _, slug, selected = normalize_url(url)
    parser = PageParser()
    parser.feed(source)
    # El estado de Svelte viene incluido en el HTML, sin solicitudes /api.
    state = next((s for s in parser.scripts if "kit.start(" in s and "data:" in s), "")
    title = literal_property(state, "title") if state else None
    if not isinstance(title, str) or not title.strip():
        title = re.split(r"\s+(?:Episodio\s|Sub Español|Online|[-|]\s*AnimeAV1)", parser.title)[0].strip()
    numbers: set[str] = set()
    for link in parser.links:
        match = re.fullmatch(r"(?:https://(?:www\.)?animeav1\.com)?/media/" + re.escape(slug) + r"/(\d+(?:\.\d+)?)/?", link)
        if match:
            numbers.add(match.group(1))
    for episode in literal_property(state, "episodes") or []:
        number = str(episode.get("number", "")) if isinstance(episode, dict) else ""
        if re.fullmatch(r"\d+(?:\.\d+)?", number):
            numbers.add(number)
    mirrors = []
    for key in ("embeds", "downloads"):
        groups = literal_property(state, key) or {}
        if not isinstance(groups, dict):
            continue
        for language, entries in groups.items():
            if not isinstance(entries, list):
                continue
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                target = entry.get("url", "")
                if isinstance(target, str) and urlsplit(target).scheme in ("https", "http"):
                    mirrors.append(Mirror(str(entry.get("server", "Servidor")), str(language), target, key))
    if selected and mirrors:
        numbers.add(selected)
    if not numbers:
        raise DownloadError("No se encontraron capítulos en el HTML. La URL puede no existir, el sitio puede pedir verificación o haber cambiado.")
    cover = parser.cover_url or parser.poster_url
    if not cover and state:
        try:
            media = literal_property(state, "media")
            media_id = media.get("id") if isinstance(media, dict) else None
            # La ficha pública sirve las portadas desde /covers/<id>.jpg.
            if isinstance(media_id, int) and media_id > 0:
                cover = f"https://cdn.animeav1.com/covers/{media_id}.jpg"
        except DownloadError:
            pass  # La imagen opcional no debe impedir leer los capítulos.
    return Catalog(html.unescape(title or slug), slug,
                   [Episode(n, ORIGIN + f"/media/{slug}/{n}") for n in sorted(numbers, key=Decimal)],
                   selected, mirrors, public_image_url(cover, url))


def public_image_url(value, page_url):
    if not isinstance(value, str) or not value:
        return None
    target = urljoin(page_url, value)
    parsed = urlsplit(target)
    if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password:
        return None
    return target


def load_catalog(url: str) -> Catalog:
    normalized, _, _ = normalize_url(url)
    return parse_page(fetch_html(normalized), normalized)


def supported_mirrors(catalog: Catalog, language: str = "SUB", server: str = "MP4Upload") -> list[Mirror]:
    if server != "MP4Upload":
        raise DownloadError("El único servidor de descarga habilitado es MP4Upload.")
    results = []
    seen = set()
    for mirror in catalog.mirrors:
        if mirror.language.upper() != language.upper() or mirror.server != "MP4Upload":
            continue
        parsed = urlsplit(mirror.url)
        valid_mp4 = parsed.hostname in ("www.mp4upload.com", "mp4upload.com") and mirror.kind == "embeds"
        if not valid_mp4 or mirror.url in seen:
            continue
        seen.add(mirror.url)
        results.append(mirror)
    return results
