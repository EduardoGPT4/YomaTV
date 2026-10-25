"""Package current web source without depending on disposable test fixtures."""
import json
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
archive=ROOT/'artifacts/YomaTVWeb-fuente.zip'
archive.parent.mkdir(parents=True,exist_ok=True)
files=[p for p in (ROOT/'htdocs').rglob('*') if p.is_file() and not p.name.endswith('.local.php') and not p.relative_to(ROOT/'htdocs').parts[0].startswith('__qa') and not (p.relative_to(ROOT/'htdocs').parts[0]=='feeds' and p.suffix in ('.ics','.tmp') and p.name!='horario.ics')]
files.extend([ROOT/'README.md',ROOT/'PLAN-4-ENTREGAS.md',ROOT/'MEJORAS.md',ROOT/'release.py',ROOT/'deploy.py',ROOT/'tools/db_backup.php',ROOT/'tools/remote_backup.py',ROOT/'tools/check_publish.py',ROOT/'OPERACION.md'])
review=ROOT/'REVISION-WEB-2026-10-23.md'
if review.is_file():files.append(review)
implementation=ROOT/'CAMBIOS-REVISION-2026-10-23.md'
if implementation.is_file():files.append(implementation)
design=ROOT/'MEDIANOCHE-2026-10-24.md'
if design.is_file():files.append(design)
mobile=ROOT/'MOVIL-2026-10-24.md'
if mobile.is_file():files.append(mobile)
android=ROOT/'ANDROID-2026-10-24.md'
if android.is_file():files.append(android)
yoma=ROOT/'YOMATV-2026-10-25.md'
if yoma.is_file():files.append(yoma)
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as output:
    for file in sorted(files):output.write(file,file.relative_to(ROOT).as_posix())
with zipfile.ZipFile(archive) as output:
    assert len(output.namelist())==len(files)
    assert output.testzip() is None
    assert not any(name.endswith('.local.php') or name.startswith(('verification/','datos/')) for name in output.namelist())
    for file in files:assert output.read(file.relative_to(ROOT).as_posix())==file.read_bytes()
result={'ok':True,'archive_bytes':archive.stat().st_size,'entries':len(files),
        'private_configuration_included':False,'test_fixtures_included':False}
(ROOT/'verification/source-package-check.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
