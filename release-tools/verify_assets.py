"""Verify release URLs anonymously against SHA-256, size and file signatures."""
from pathlib import Path
import hashlib,json,urllib.request
ROOT=Path(__file__).resolve().parents[1]
manifest=json.loads((ROOT/'release-artifacts/yomatv-downloads.json').read_text())
results=[]
for row in manifest['apps']:
    assert row['url'].startswith('https://github.com/EduardoGPT4/YomaTV/releases/download/')
    request=urllib.request.Request(row['url'],headers={'User-Agent':'YomaTV-public-verification'})
    digest=hashlib.sha256();size=0;signature=b''
    with urllib.request.urlopen(request,timeout=120)as response:
        while True:
            chunk=response.read(1024*1024)
            if not chunk:break
            if not signature:signature=chunk[:2]
            digest.update(chunk);size+=len(chunk)
    assert size==row['bytes'] and digest.hexdigest()==row['sha256']
    assert signature==(b'PK'if row['platform']=='android'else b'MZ')
    results.append({'platform':row['platform'],'bytes':size,'sha256':digest.hexdigest(),'anonymous_download_ok':True})
print(json.dumps({'ok':True,'apps':results},indent=2))
