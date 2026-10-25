"""Build the smallest restricted MV3 extension ZIP, without credentials."""
from pathlib import Path
import zipfile,json
ROOT=Path(__file__).resolve().parent.parent
source=ROOT/'browser-extension/YomaTV-Brave'
manifest=json.loads((source/'manifest.json').read_text())
assert manifest['manifest_version']==3 and manifest['permissions']==['storage']
assert 'host_permissions' not in manifest and 'externally_connectable' not in manifest
matches=[m for entry in manifest['content_scripts'] for m in entry['matches']]
assert matches==['https://hk-br035.gt.tc/seasonav1/*','https://www.mp4upload.com/embed-*.html*','https://mp4upload.com/embed-*.html*']
names={'manifest.json','worker.js','parent.js','video-bridge.js','provider.js','LEEME.txt','icon-32.png','icon-192.png'}
assert {p.name for p in source.iterdir() if p.is_file()}==names
out=ROOT/'htdocs/downloads/YomaTV-Brave.zip';out.parent.mkdir(exist_ok=True)
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for name in sorted(names):z.write(source/name,name)
with zipfile.ZipFile(out) as z:
    assert z.testzip() is None and set(z.namelist())==names
    assert all(z.read(name)==(source/name).read_bytes() for name in names)
result={'ok':True,'bytes':out.stat().st_size,'files':len(names),'only_storage_permission':True,'only_seasonav1_and_mp4upload':True,'credentials_included':False}
(ROOT/'verification/brave-package-check.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))
