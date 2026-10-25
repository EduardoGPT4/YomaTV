"""Disposable portable MariaDB, loopback only, hidden child process, no Windows service."""
import concurrent.futures,json,os,secrets,socket,subprocess,tempfile,time
from pathlib import Path
from delivery4_evidence import application_hashes
ROOT=Path(__file__).resolve().parent.parent;PHP=r'C:/Users/Eduardo/.config/herd-lite/bin/php.exe'
BIN=ROOT/'verification/tools/mariadb-11.4.13-winx64/bin';flags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0
if not BIN.exists():raise RuntimeError('Run verification/download_mariadb.py first')
source_before=application_hashes()
def executable(*names):
    for name in names:
        if (BIN/name).is_file():return str(BIN/name)
    raise RuntimeError('Official MariaDB executable not found')
def php(code,env):
    r=subprocess.run([PHP,'-r',code],cwd=ROOT,env=env,capture_output=True,text=True,timeout=180,creationflags=flags)
    if r.returncode:raise RuntimeError((r.stdout+r.stderr)[-3000:])
    return r.stdout
with socket.socket() as probe:probe.bind(('127.0.0.1',33316))
with tempfile.TemporaryDirectory(dir=ROOT/'verification') as folder:
    folder=Path(folder);assert folder.resolve().is_relative_to((ROOT/'verification').resolve())
    data=folder/'database';password=secrets.token_urlsafe(32);name='seasonav1_test_'+secrets.token_hex(8);restore='seasonav1_test_'+secrets.token_hex(8)
    env={**os.environ,'SEASON_WEB_TEST_MYSQL_PASSWORD':password,'SEASON_TEST_DB':name,'SEASON_TEST_RESTORE':restore,'SEASON_WEB_TEST_MYSQL_DSN':f'mysql:host=127.0.0.1;port=33316;dbname={name};charset=utf8mb4','SEASON_WEB_TEST_RESTORE_DSN':f'mysql:host=127.0.0.1;port=33316;dbname={restore};charset=utf8mb4'}
    env.pop('SEASON_WEB_SQLITE',None)
    installed=subprocess.run([executable('mariadb-install-db.exe','mysql_install_db.exe'),'--datadir='+str(data),'--password='+password,'--port=33316','--silent'],cwd=BIN,env=env,capture_output=True,text=True,timeout=120,creationflags=flags)
    if installed.returncode:raise RuntimeError('Portable MariaDB initialization failed')
    with (folder/'server.log').open('w',encoding='utf8') as log:
        child=subprocess.Popen([executable('mariadbd.exe','mysqld.exe'),'--defaults-file='+str(data/'my.ini'),'--bind-address=127.0.0.1','--port=33316','--skip-name-resolve','--console'],cwd=BIN,env=env,stdout=log,stderr=log,creationflags=flags)
        try:
            deadline=time.monotonic()+30
            while True:
                try:
                    with socket.create_connection(('127.0.0.1',33316),timeout=1):break
                except OSError:
                    if time.monotonic()>deadline or child.poll() is not None:raise RuntimeError('Portable MariaDB did not start')
                    time.sleep(.2)
            init=r'''$db=new PDO('mysql:host=127.0.0.1;port=33316','root',getenv('SEASON_WEB_TEST_MYSQL_PASSWORD'));foreach(['SEASON_TEST_DB','SEASON_TEST_RESTORE'] as $key){$name=getenv($key);if(!preg_match('/^seasonav1_test_[a-f0-9]+$/D',$name))exit(1);$db->exec('CREATE DATABASE '.$name.' CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci');}'''
            php(init,env)
            output=php(r'''try{require 'verification/test_mysql.php';}catch(Throwable $e){fwrite(STDERR,get_class($e).': '.$e->getMessage());exit(1);}''',env);result=json.loads(output)
            worker=r'''define('SEASON_BOOTSTRAPPED',true);require 'htdocs/private/db.php';$db=new PDO(getenv('SEASON_WEB_TEST_MYSQL_DSN'),'root',getenv('SEASON_WEB_TEST_MYSQL_PASSWORD'));$db->setAttribute(PDO::ATTR_ERRMODE,PDO::ERRMODE_EXCEPTION);$db->setAttribute(PDO::ATTR_DEFAULT_FETCH_MODE,PDO::FETCH_ASSOC);echo consume_limit($db,'mysql-concurrent',7,60)?'1':'0';'''
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:values=list(pool.map(lambda _:php(worker,env),range(32)))
            assert values.count('1')==7;result['checks'].append('mysql_thirty_two_concurrent_writers_admit_exactly_seven')
            assert source_before==application_hashes(),'Source changed during MariaDB verification'
            result['application_sha256']=source_before
            (ROOT/'verification/mysql-check.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(result))
        finally:
            if child.poll() is None:
                try:php(r'''$db=new PDO('mysql:host=127.0.0.1;port=33316','root',getenv('SEASON_WEB_TEST_MYSQL_PASSWORD'));$db->exec('SHUTDOWN');''',env)
                except Exception:pass
                try:child.wait(timeout=15)
                except subprocess.TimeoutExpired:child.terminate();child.wait(timeout=10)
