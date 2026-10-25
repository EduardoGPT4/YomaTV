"""Fetch installation metadata as declared by HTML, without solving a second host gate."""
import argparse,json,secrets,sys,time,urllib.parse,urllib.request
from html.parser import HTMLParser
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE='https://hk-br035.gt.tc/seasonav1/'

class InstallLink(HTMLParser):
    def __init__(self):super().__init__();self.manifest=None
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag=='link' and 'manifest' in attrs.get('rel','').split():self.manifest=attrs

def probe(page,client):
    parser=InstallLink();parser.feed(page);attrs=parser.manifest
    if not attrs:raise RuntimeError('The page has no installation manifest.')
    url=urllib.parse.urljoin(BASE,attrs['href']);target=urllib.parse.urlsplit(url);origin=urllib.parse.urlsplit(BASE)
    if (target.scheme,target.netloc)!=(origin.scheme,origin.netloc):raise RuntimeError('Refusing to send the host cookie outside this site.')
    include=attrs.get('crossorigin')=='use-credentials'
    headers={'User-Agent':'Mozilla/5.0 YomaTV release verification'}
    if include and client.cookie:headers['Cookie']='__test='+client.cookie
    url+=('&' if '?' in url else '?')+'install_check='+secrets.token_hex(5)
    # Deliberately no CookieJar, JS handshake or retry with added credentials here.
    with urllib.request.build_opener().open(urllib.request.Request(url,headers=headers),timeout=40) as response:
        body=response.read();kind=response.headers.get_content_type();status=response.status
    try:manifest=json.loads(body)
    except (ValueError,UnicodeDecodeError):manifest={}
    valid=isinstance(manifest,dict) and isinstance(manifest.get('icons'),list) and bool(manifest['icons'])
    return {'ok':bool(include and status==200 and valid and kind=='application/manifest+json'),
        'declared_credentials':'include' if include else 'omit','status':status,'type':kind,
        'valid_manifest':bool(valid),'challenge_html':b'aes.js' in body and b'toNumbers(' in body,
        'second_host_handshake_performed':False,'physical_android_tested':False}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--expect-blocked',action='store_true');args=parser.parse_args()
    sys.path.insert(0,str(ROOT));import release
    client=release.PublicClient();status,body,_=client.get('?install_page='+secrets.token_hex(5))
    if status!=200:raise RuntimeError('Public page is unavailable.')
    report=probe(body.decode('utf8'),client);report['at']=int(time.time())
    name='brave-install-before.json' if args.expect_blocked else 'brave-install-after.json'
    (ROOT/'verification'/name).write_text(json.dumps(report,indent=2),encoding='utf8')
    print(json.dumps(report))
    if args.expect_blocked:assert not report['ok'] and report['challenge_html']
    else:assert report['ok']

if __name__=='__main__':main()
