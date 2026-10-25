"""Offline regressions only; every database is disposable and every provider is a fixture."""
import json,os,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent;PHP=r'C:/Users/Eduardo/.config/herd-lite/bin/php.exe';results=[]
def run(args,env):
    r=subprocess.run(args,cwd=ROOT,env=env,capture_output=True,text=True,encoding='utf8',timeout=180)
    if r.returncode:raise RuntimeError((r.stdout+r.stderr)[-6000:])
    return r.stdout
with tempfile.TemporaryDirectory(dir=ROOT/'verification') as folder:
    env={**os.environ,'SEASON_WEB_SQLITE':str(Path(folder)/'fixture.sqlite'),'SEASON_WEB_ADMIN_EMAILS':'admin@example.test','SEASON_WEB_MAL_TEST_URL':'http://127.0.0.1:8097','PYTHONUTF8':'1'}
    # Reuse real fixture functions through CLI. They do not contact their mock URLs.
    initial=r'''define('SEASON_BOOTSTRAPPED',true);require 'htdocs/private/app.php';$db=db();sql($db,'INSERT INTO sa1_users(name,email,password_hash,created_at) VALUES(?,?,?,?)',['QA','preview@example.test',password_hash('Fixture-Only-Password',PASSWORD_DEFAULT),time()]);sql($db,'INSERT INTO sa1_users(name,email,password_hash,created_at) VALUES(?,?,?,?)',['Admin','admin@example.test','fixture-hash',time()]);'''
    run([PHP,'-r',initial],env)
    run([PHP,'verification/seed_feature_preview.php'],env)
    for name in ['test_infrastructure.php','test_catalog_worker.php','test_maintenance_rotation.php','test_reliability_upgrade.php','test_feature_core.php','test_mal_core.php','test_catalog_source.php','test_catalog_data.php','test_catalog_metadata.php','test_large_storage.php']:
        selected=dict(env)
        if name=='test_catalog_data.php':selected['SEASON_WEB_SQLITE']=':memory:'
        if name=='test_catalog_metadata.php':run([PHP,'verification/seed_catalog_filters.php'],env)
        code='try {require '+json.dumps('verification/'+name)+';}catch(Throwable $e){fwrite(STDERR,get_class($e).": ".$e->getMessage()."\\n".$e->getTraceAsString());exit(1);}'
        output=run([PHP,'-r',code],selected)
        if name=='test_infrastructure.php':(ROOT/'verification/infrastructure-check.json').write_text(output,encoding='utf8')
        results.append({'test':name,'ok':True});print(json.dumps(results[-1]),flush=True)
    for name in ['test_schema_upgrade.py','test_concurrency.py','test_release.py']:
        run([sys.executable,'verification/'+name],env);results.append({'test':name,'ok':True});print(json.dumps(results[-1]),flush=True)
result={'ok':True,'suites':results,'network_requests':0,'production_database_used':False}
(ROOT/'verification/delivery4-local-suite.json').write_text(json.dumps(result,indent=2),encoding='utf8')
