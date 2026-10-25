"""Create disposable cached catalog/account fixtures; never reads the user's desktop DB."""
import os
import subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
fixture=ROOT/'verification/hardening-2026-10-14.sqlite'
assert fixture.resolve().is_relative_to((ROOT/'verification').resolve())
env={**os.environ,'SEASON_WEB_SQLITE':str(fixture),'SEASON_WEB_ADMIN_EMAILS':'admin@example.test'}
code=r'''
define('SEASON_BOOTSTRAPPED',true);
require getcwd().'/htdocs/private/app.php';
$db=db();
foreach([['Administrador QA','admin@example.test','Admin-Local-Test-8096'],['Perfil de prueba','preview@example.test','Preview-Local-Test-8096']] as $user){
    if(!sql($db,'SELECT id FROM sa1_users WHERE email=?',[$user[1]])->fetchColumn())
        sql($db,'INSERT INTO sa1_users(name,email,password_hash,created_at) VALUES(?,?,?,?)',[$user[0],$user[1],password_hash($user[2],PASSWORD_DEFAULT),time()]);
}
foreach(['naruto'=>220,'bleach'=>2000] as $slug=>$count){
    $rows=[];
    for($n=1;$n<=$count;$n++)$rows[]=['slug'=>$slug,'number'=>(string)$n,'number_value'=>$n,'url'=>'https://animeav1.com/media/'.$slug.'/'.$n];
    upsert($db,'sa1_episodes',['slug','number','number_value','url'],$rows,['slug','number'],['url']);
    sql($db,'UPDATE sa1_anime SET catalog_complete=1,latest=?,start_date=?,season=? WHERE slug=?',[(string)$count,'2002-10-03','otoño2002',$slug]);
}
echo "Disposable accounts and cached episode fixtures ready. No videos downloaded.\n";
'''
subprocess.run([r'C:/Users/Eduardo/.config/herd-lite/bin/php.exe','-r',code],cwd=ROOT,env=env,check=True)
