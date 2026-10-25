"""Upgrade a disposable pre-security users table without changing its account."""
import json
import os
import subprocess
import tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
with tempfile.TemporaryDirectory(dir=ROOT/'verification') as directory:
    fixture=Path(directory)/'legacy.sqlite'
    assert fixture.resolve().is_relative_to((ROOT/'verification').resolve())
    env={**os.environ,'SEASON_WEB_SQLITE':str(fixture)}
    code=r'''
    $old=new PDO('sqlite:'.getenv('SEASON_WEB_SQLITE'));
    $old->exec('CREATE TABLE sa1_users(id INTEGER PRIMARY KEY AUTOINCREMENT,name VARCHAR(60) NOT NULL,email VARCHAR(190) NOT NULL UNIQUE,password_hash VARCHAR(255) NOT NULL,created_at BIGINT NOT NULL)');
    $hash=password_hash('Legacy-Local-Password',PASSWORD_DEFAULT);
    $insert=$old->prepare('INSERT INTO sa1_users(name,email,password_hash,created_at) VALUES(?,?,?,?)');
    $insert->execute(['Legacy','legacy@example.test',$hash,1]);
    define('SEASON_BOOTSTRAPPED',true);require getcwd().'/htdocs/private/app.php';
    $current=db();migrate($current);
    $row=sql($current,'SELECT * FROM sa1_users WHERE id=1')->fetch();
    if($row['password_hash']!==$hash||(int)$row['auth_version']!==0)throw new RuntimeException('Legacy account changed');
    $_SESSION['user_id']=1;unset($_SESSION['auth_version']);validate_session($current);
    if(uid()!==1)throw new RuntimeException('Compatible legacy session was lost');
    echo json_encode(['ok'=>true,'checks'=>['existing_password_hash_and_account_preserved','legacy_session_epoch_zero_accepted','schema_upgrade_idempotent']]);
    '''
    response=subprocess.run([r'C:/Users/Eduardo/.config/herd-lite/bin/php.exe','-r',code],cwd=ROOT,env=env,check=True,capture_output=True,text=True)
    result=json.loads(response.stdout)
    (ROOT/'verification/schema-upgrade-check.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))
