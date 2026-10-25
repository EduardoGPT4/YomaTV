"""Isolated PHP processes, real session-file locking and real SQLite writers; no sockets."""
import concurrent.futures,json,os,secrets,subprocess,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent;PHP=r'C:/Users/Eduardo/.config/herd-lite/bin/php.exe';checks=[]
flags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0
def call(code,env):
    response=subprocess.run([PHP,'-r',code],cwd=ROOT,env=env,capture_output=True,text=True,timeout=30,creationflags=flags)
    if response.returncode:raise RuntimeError(response.stderr or response.stdout)
    return response.stdout
with tempfile.TemporaryDirectory(dir=ROOT/'verification') as folder:
    folder=Path(folder);env={**os.environ,'SEASON_CONCURRENCY_FILE':str(folder/'rates.sqlite'),'SEASON_SESSION_DIR':str(folder),'SEASON_SESSION_ID':secrets.token_hex(16),'SEASON_SESSION_MARKER':str(folder/'released')}
    init=r'''define('SEASON_BOOTSTRAPPED',true);require 'htdocs/private/db.php';$db=new PDO('sqlite:'.getenv('SEASON_CONCURRENCY_FILE'));$db->exec('CREATE TABLE sa1_limits(name VARCHAR(190) PRIMARY KEY,hits INTEGER NOT NULL,reset_at BIGINT NOT NULL)');'''
    call(init,env)
    worker=r'''define('SEASON_BOOTSTRAPPED',true);require 'htdocs/private/db.php';$db=new PDO('sqlite:'.getenv('SEASON_CONCURRENCY_FILE'));$db->setAttribute(PDO::ATTR_ERRMODE,PDO::ERRMODE_EXCEPTION);$db->setAttribute(PDO::ATTR_DEFAULT_FETCH_MODE,PDO::FETCH_ASSOC);$db->exec('PRAGMA busy_timeout=10000');echo consume_limit($db,'shared-account',7,60)?'1':'0';'''
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:results=list(pool.map(lambda _:call(worker,env),range(32)))
    assert results.count('1')==7 and results.count('0')==25,results;checks.append('thirty_two_concurrent_real_writers_admit_exactly_seven_requests')
    count=call(r'''$d=new PDO('sqlite:'.getenv('SEASON_CONCURRENCY_FILE'));echo $d->query('SELECT hits FROM sa1_limits')->fetchColumn();''',env)
    assert int(count)==32;checks.append('concurrent_denied_attempts_are_not_lost')
    setup=r'''session_save_path(getenv('SEASON_SESSION_DIR'));session_id(getenv('SEASON_SESSION_ID'));define('SEASON_BOOTSTRAPPED',true);require 'htdocs/private/app.php';'''
    slow=setup+r'''$_SESSION['user_id']=123;$_SESSION['auth_version']=0;release_remote_session();file_put_contents(getenv('SEASON_SESSION_MARKER'),'ready');usleep(1500000);echo json_encode(['actor'=>uid(),'closed'=>session_status()!==PHP_SESSION_ACTIVE]);'''
    process=subprocess.Popen([PHP,'-r',slow],cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,creationflags=flags)
    try:
        deadline=time.monotonic()+10
        while not (folder/'released').exists():
            if process.poll() is not None:raise RuntimeError(process.communicate())
            if time.monotonic()>deadline:raise TimeoutError('Session marker unavailable')
            time.sleep(.02)
        started=time.monotonic();fast=call(setup+r'''$old=uid();$_SESSION['user_id']=222;echo $old;session_write_close();''',env);elapsed=time.monotonic()-started
        assert fast=='123' and elapsed<1 and process.poll() is None,(fast,elapsed)
        checks.append('second_session_request_finishes_while_first_request_is_in_remote_io')
        output,error=process.communicate(timeout=10);assert process.returncode==0,(output,error)
        assert json.loads(output)=={'actor':123,'closed':True};checks.append('released_request_keeps_original_actor_after_concurrent_session_change')
    finally:
        if process.poll() is None:process.terminate();process.wait(timeout=5)
result={'ok':True,'count':len(checks),'checks':checks,'network_requests':0}
(ROOT/'verification/concurrency-check.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(result))
