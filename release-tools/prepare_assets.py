"""Build deterministic public metadata from the actual signed artifacts."""
import hashlib,json,re,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'release-artifacts';OUT.mkdir(exist_ok=True)
android=ROOT/'YomaTVAndroid';pc=ROOT/('YomaTVPC' if (ROOT/'YomaTVPC').exists() else 'SeasonAV1')
av=re.search(r'versionName = "([0-9.]+)"',(android/'app/build.gradle.kts').read_text()).group(1)
wv=re.search(r'VERSION = "([0-9.]+)"',(pc/'seasonav1/brand.py').read_text()).group(1)
tag='v'+av
apps=[]
for platform,version,source,name in [('android',av,android/'app/build/outputs/apk/release/app-release.apk',f'YomaTV-Android-{av}.apk'),('windows',wv,pc/'build/release/YomaTV.exe',f'YomaTV-Windows-{wv}.exe')]:
    data=source.read_bytes()
    if platform=='android' and not data.startswith(b'PK'):raise RuntimeError('APK invalid')
    if platform=='windows' and not data.startswith(b'MZ'):raise RuntimeError('EXE invalid')
    destination=OUT/name;shutil.copyfile(source,destination)
    alias='YomaTV-Android.apk' if platform=='android' else 'YomaTV-Windows.exe';shutil.copyfile(source,OUT/alias)
    apps.append({'platform':platform,'version':version,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'url':f'https://github.com/EduardoGPT4/YomaTV/releases/download/{tag}/{name}'})
manifest={'repository':'EduardoGPT4/YomaTV','tag':tag,'apps':apps}
(OUT/'yomatv-downloads.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
(ROOT/'YomaTVWeb/htdocs/assets/app-releases.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
(OUT/'SHA256SUMS.txt').write_text('\n'.join(a['sha256']+'  '+a['url'].rsplit('/',1)[1] for a in apps)+'\n',encoding='utf8')
print(json.dumps(manifest,indent=2))
