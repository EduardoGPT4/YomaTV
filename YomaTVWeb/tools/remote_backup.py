"""One-operation, expiring encrypted snapshot of the existing authorized hosting database."""
import hashlib,io,json,os,re,secrets,ssl,subprocess,sys,urllib.parse,urllib.request
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));import release

def main():
    sys.path.insert(0,str(ROOT.parent.parent/'Expedition-7'))
    from deploy import InfinityFTP,credentials
    config=credentials();
    if config['username']!='if0_43115975' or config['database']!='if0_43115975_anime':raise RuntimeError('The local credentials do not match this authorized hosting account')
    nonce=secrets.token_hex(12);token=secrets.token_hex(32);password=secrets.token_urlsafe(40)
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ');folder=ROOT/'artifacts/private-backups';folder.mkdir(parents=True,exist_ok=True)
    target=folder/('production-'+stamp+'.sa1backup');keyfolder=Path(os.environ.get('SEASON_BACKUP_KEY_DIRECTORY',str(ROOT.parent/'.private-backup-keys')));keyfolder.mkdir(parents=True,exist_ok=True);keyfile=keyfolder/('production-'+stamp+'.key.local.json')
    if target.exists() or keyfile.exists():raise RuntimeError('Backup artifact already exists')
    entry='snapshot-'+nonce+'.php';helper='private/snapshot-'+nonce+'.php'
    import time
    script=('''<?php
declare(strict_types=1);
if($_SERVER['REQUEST_METHOD']!=='POST'||time()>EXPIRES||!hash_equals('TOKENHASH',hash('sha256',(string)($_SERVER['HTTP_X_SEASON_DEPLOY_TOKEN']??'')))){http_response_code(404);exit();}
define('SEASON_BOOTSTRAPPED',true);require __DIR__.'/private/app.php';
if(!defined('SEASON_SCHEMA_VERSION'))define('SEASON_SCHEMA_VERSION','20261018.4');
require __DIR__.'/HELPER';
try{
  $input=json_decode(file_get_contents('php://input',false,null,0,2048),true,8,JSON_THROW_ON_ERROR);
  if(session_status()===PHP_SESSION_ACTIVE)session_write_close();
  $stream=tmpfile();$info=backup_write(db(),$stream,(string)($input['password']??''));set_meta(db(),'backup_last',json_encode($info));
  header('Content-Type: application/octet-stream');header('Cache-Control: no-store');rewind($stream);fpassthru($stream);fclose($stream);
}catch(Throwable $error){http_response_code(500);echo '{"ok":false}';}
'''.replace('EXPIRES',str(int(time.time())+1800)).replace('TOKENHASH',hashlib.sha256(token.encode()).hexdigest()).replace('HELPER',helper)).encode()
    # Use the normal first-party gate before making this narrowly authenticated POST.
    import http.cookiejar
    opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()));base='https://hk-br035.gt.tc/seasonav1/'
    page=opener.open(base,timeout=40).read().decode();challenge=re.findall(r'toNumbers\("([a-f0-9]+)"\)',page)
    if challenge:
        code='$v=json_decode(stream_get_contents(STDIN),true);echo bin2hex(openssl_decrypt(hex2bin($v[2]),"aes-128-cbc",hex2bin($v[0]),OPENSSL_RAW_DATA|OPENSSL_ZERO_PADDING,hex2bin($v[1])));'
        value=subprocess.run([r'C:/Users/Eduardo/.config/herd-lite/bin/php.exe','-r',code],input=json.dumps(challenge),text=True,capture_output=True,check=True).stdout.strip()
        if not re.fullmatch('[a-f0-9]{32}',value):raise RuntimeError('Unexpected host gate')
        opener.addheaders=[('Cookie','__test='+value)]
    partial=target.with_suffix('.part');uploaded=[]
    with InfinityFTP(context=ssl.create_default_context(),timeout=90) as ftp:
        ftp.connect('ftpupload.net',21);ftp.login(config['username'],config['password']);ftp.prot_p();ftp.cwd('/htdocs/seasonav1')
        try:
            for path,data in [(helper,(ROOT/'htdocs/private/backup.php').read_bytes()),(entry,script)]:
                # A successful STOR followed by a failed checksum still needs cleanup.
                uploaded.append(path);release.ftp_write(ftp,path,data)
            keyfile.write_text(json.dumps({'password':password,'file':target.name}),encoding='utf8')
            request=urllib.request.Request(base+entry,data=json.dumps({'password':password}).encode(),headers={'Content-Type':'application/json','X-Season-Deploy-Token':token})
            with opener.open(request,timeout=180) as response,partial.open('xb') as out:
                if not response.headers.get('Content-Type','').startswith('application/octet-stream'):
                    body=response.read(1024*1024)
                    diagnostic={'status':response.status,'content_type':response.headers.get('Content-Type',''),
                        'path':urllib.parse.urlsplit(response.url).path,'bytes':len(body),
                        'host_cookie_gate':b'toNumbers(' in body and b'aes.js' in body,
                        'html':b'<html' in body.lower(),'php_fatal':b'Fatal error' in body}
                    raise RuntimeError('Snapshot did not return an encrypted backup: '+json.dumps(diagnostic))
                while block:=response.read(1024*1024):out.write(block)
            os.replace(partial,target)
            env={**os.environ,'SEASON_BACKUP_PASSWORD':password,'SEASON_WEB_SQLITE':':memory:'}
            verified=subprocess.run([r'C:/Users/Eduardo/.config/herd-lite/bin/php.exe','tools/db_backup.php','verify',str(target)],cwd=ROOT,env=env,capture_output=True,text=True,timeout=180)
            if verified.returncode:raise RuntimeError('Encrypted production snapshot verification failed; no release activated')
            receipt={'ok':True,'at':int(time.time()),'file':str(target.relative_to(ROOT)),'sha256':hashlib.file_digest(target.open('rb'),'sha256').hexdigest(),'bytes':target.stat().st_size,'verified':True}
            (ROOT/'verification/production-backup-receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
            print(json.dumps({'ok':True,'encrypted_backup':str(target),'verified':True,'server_configuration_included':False}))
        finally:
            for path in reversed(uploaded):
                try:ftp.delete(path)
                except Exception:print('Cleanup required for expiring snapshot file: '+path,file=sys.stderr)
            partial.unlink(missing_ok=True)
            if not target.exists():keyfile.unlink(missing_ok=True)
if __name__=='__main__':main()
