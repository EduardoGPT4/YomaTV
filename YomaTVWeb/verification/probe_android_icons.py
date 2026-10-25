"""Check the published Android installation resources, not a physical launcher."""
from __future__ import annotations

import io
import json
import secrets
import sys
import time
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://hk-br035.gt.tc/seasonav1/'
# A request profile only; this does not emulate Brave or Android installation.
ANDROID_UA = ('Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 '
              '(KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36')


class AndroidHeaders(urllib.request.BaseHandler):
    def http_request(self, request):
        request.add_header('User-Agent', ANDROID_UA)
        return request

    https_request = http_request


class IconLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'link':
            rel = set(attrs.get('rel', '').split())
            if rel.intersection({'manifest', 'icon', 'apple-touch-icon'}):
                self.links.append(attrs)


def fetch(url, cookie=''):
    target = urllib.parse.urlsplit(url)
    origin = urllib.parse.urlsplit(BASE)
    if (target.scheme, target.netloc) != (origin.scheme, origin.netloc):
        raise RuntimeError('Installation resource is outside the application origin.')
    headers = {'User-Agent': ANDROID_UA}
    if cookie:
        headers['Cookie'] = '__test=' + cookie
    # No cookie jar, no host-handshake retry, and no cookie for PNG requests.
    with urllib.request.build_opener().open(
            urllib.request.Request(url, headers=headers), timeout=40) as response:
        return response.status, response.read(), response.headers.get_content_type()


def main():
    sys.path.insert(0, str(ROOT))
    import release

    client = release.PublicClient()
    # Obtain the host cookie with the same request profile, as a browser does.
    client.opener.add_handler(AndroidHeaders())
    status, page, kind = client.get('?android_icons=' + secrets.token_hex(5))
    assert status == 200 and kind.split(';')[0] == 'text/html'
    assert b'aes.js' not in page and b'toNumbers(' not in page
    parser = IconLinks()
    parser.feed(page.decode('utf8'))
    manifest_link = next(link for link in parser.links if link.get('rel') == 'manifest')
    assert manifest_link.get('crossorigin') == 'use-credentials'
    status, data, kind = fetch(urllib.parse.urljoin(BASE, manifest_link['href']), client.cookie)
    assert status == 200 and kind == 'application/manifest+json'
    manifest = json.loads(data)
    assert manifest['id'] == manifest['scope'] == '/seasonav1/'
    assert manifest['start_url'] == '/seasonav1/#discover'
    assert manifest['display'] == 'standalone'

    resources = {}
    for link in parser.links:
        if link.get('rel') != 'manifest':
            url = urllib.parse.urljoin(BASE, link['href'])
            resources.setdefault(url, []).append(('html:' + link['rel'], link.get('sizes')))
    for icon in manifest['icons']:
        url = urllib.parse.urljoin(BASE, icon['src'])
        resources.setdefault(url, []).append(('manifest:' + icon.get('purpose', 'any'), icon['sizes']))

    checks = []
    manifest_sizes = set()
    for url, declarations in resources.items():
        status, data, kind = fetch(url)
        assert status == 200 and kind == 'image/png' and data.startswith(b'\x89PNG\r\n\x1a\n')
        with Image.open(io.BytesIO(data)) as image:
            image.load()
            size = f'{image.width}x{image.height}'
            assert all(expected == size for _, expected in declarations)
            opaque = image.convert('RGBA').getchannel('A').getextrema() == (255, 255)
        if any(source.startswith('manifest:') for source, _ in declarations):
            manifest_sizes.add(size)
        if any(source == 'manifest:maskable' for source, _ in declarations):
            assert opaque
        checks.append({'path': urllib.parse.urlsplit(url).path,
                       'declarations': [source for source, _ in declarations],
                       'status': status, 'type': kind, 'pixels': size,
                       'bytes': len(data), 'cookies_sent': False})
    assert {'192x192', '512x512'}.issubset(manifest_sizes)
    assert any('html:apple-touch-icon' in check['declarations'] and check['pixels'] == '180x180'
               for check in checks)
    active_ids = {check['path'].split('/releases/')[1].split('/')[0]
                  for check in checks if '/releases/' in check['path']}
    assert len(active_ids) == 1
    report = {'ok': True, 'at': int(time.time()), 'release': active_ids.pop(),
              'android_user_agent_requests': True, 'browser_emulated': False,
              'manifest_with_host_cookie': True, 'stable_app_identity': True,
              'physical_android_tested': False, 'icons': checks}
    (ROOT / 'verification/android-icon-check.json').write_text(
        json.dumps(report, indent=2), encoding='utf8')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
