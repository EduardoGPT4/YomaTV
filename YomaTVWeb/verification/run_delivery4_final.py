"""Final non-network check. Records current source hashes and explicitly pending validation."""
import hashlib,json,os,subprocess,sys
from pathlib import Path
from delivery4_evidence import external_checks
ROOT=Path(__file__).resolve().parent.parent
PHP=r'C:/Users/Eduardo/.config/herd-lite/bin/php.exe'
NODE=r'C:/Users/Eduardo/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe'
env={**os.environ,'PYTHONUTF8':'1'}
def sources():
    paths=[p for p in (ROOT/'htdocs').rglob('*') if p.is_file() and not p.name.endswith('.local.php') and not p.relative_to(ROOT/'htdocs').parts[0].startswith('__qa')]
    paths += [ROOT/'release.py',ROOT/'deploy.py',ROOT/'tools/db_backup.php',ROOT/'tools/remote_backup.py',ROOT/'tools/check_publish.py']
    return {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}
def run(args):
    r=subprocess.run(args,cwd=ROOT,env=env,capture_output=True,text=True,encoding='utf8',timeout=240)
    if r.returncode:raise RuntimeError((r.stdout+r.stderr)[-5000:])
    return r.stdout
before=sources()
output=run([sys.executable,'verification/run_delivery4_local.py'])
(ROOT/'verification/delivery4-local-run.log').write_text(output,encoding='utf8')
php_suites=json.loads((ROOT/'verification/delivery4-local-suite.json').read_text(encoding='utf8'))['suites']
print('Local PHP/storage suites: '+str(len(php_suites)),flush=True)
js=[]
for p in sorted((ROOT/'verification').glob('test_*.js')):
    run([NODE,str(p)]);js.append(p.name)
print('JavaScript suites: '+str(len(js)),flush=True)
php_files=[p for p in (ROOT/'htdocs').rglob('*.php') if not p.name.endswith('.local.php') and not p.relative_to(ROOT/'htdocs').parts[0].startswith('__qa')]+[ROOT/'tools/db_backup.php']
for p in php_files:run([PHP,'-l',str(p)])
for p in (ROOT/'htdocs/assets').glob('*.js'):run([NODE,'--check',str(p)])
run([sys.executable,'-m','py_compile','release.py','deploy.py','tools/remote_backup.py','tools/check_publish.py','verification/run_mysql.py','verification/download_mariadb.py','verification/test_infrastructure_http.py'])
assert before==sources(),'Source changed during verification; rerun the affected checks'
result=external_checks({'local_checks_ok':True,'php_storage_suites':len(php_suites),'javascript_suites':len(js),'php_syntax_files':len(php_files),
    'source_sha256':before})
(ROOT/'verification/delivery4-status.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in result.items() if k!='source_sha256'}),flush=True)
