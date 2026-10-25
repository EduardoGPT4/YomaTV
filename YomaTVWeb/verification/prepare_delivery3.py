"""Validate deployable sources and compare them with delivery 2's source archive."""
import json,zipfile,difflib,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PHP=r'C:/Users/Eduardo/.config/herd-lite/bin/php.exe'
NODE=r'C:/Users/Eduardo/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe'
files=[p for p in (ROOT/'htdocs').rglob('*') if p.is_file() and not p.name.endswith('.local.php') and not p.relative_to(ROOT/'htdocs').parts[0].startswith('__qa') and not (p.relative_to(ROOT/'htdocs').parts[0]=='feeds' and p.suffix in ('.ics','.tmp') and p.name!='horario.ics')]
syntax=0
for p in files:
    if p.suffix not in ('.php','.js'):continue
    r=subprocess.run([PHP,'-l',str(p)] if p.suffix=='.php' else [NODE,'--check',str(p)],capture_output=True,text=True)
    assert r.returncode==0,(p.name,r.stderr);syntax+=1
with zipfile.ZipFile(ROOT/'artifacts/YomaTVWeb-fuente.zip') as archive:
    changed=[];diff=[]
    for p in sorted(files):
        name=p.relative_to(ROOT).as_posix();old=archive.read(name) if name in archive.namelist() else b'';new=p.read_bytes()
        if old==new:continue
        changed.append(p.relative_to(ROOT/'htdocs').as_posix())
        if p.suffix in ('.php','.js','.css'):diff.extend(difflib.unified_diff(old.decode('utf-8-sig').splitlines(True),new.decode('utf-8-sig').splitlines(True),fromfile='old/'+name,tofile='new/'+name))
(ROOT/'verification/delivery3-files.json').write_text(json.dumps(changed,indent=2),encoding='utf8')
(ROOT/'verification/delivery3-source.diff').write_text(''.join(diff),encoding='utf8')
(ROOT/'verification/delivery3-syntax-check.json').write_text(json.dumps({'ok':True,'files':syntax}),encoding='utf8')
print(json.dumps({'ok':True,'syntax_files':syntax,'changed_files':len(changed)}))
