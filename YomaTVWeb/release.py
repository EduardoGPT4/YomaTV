"""Immutable release builder and FTPS publisher. Never stores server credentials in releases."""
from __future__ import annotations
import argparse, hashlib, io, json, re, secrets, ssl, sys, zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

ROOT=Path(__file__).resolve().parent
ENTRIES=('index.php','actions.php','mal-callback.php','calendar.php','maintenance.php','catalog-public.php','backup.php','release-health.php','service-worker.php','app-manifest.php')
RELEASE_PATTERN=re.compile(r'[a-z0-9][a-z0-9-]{5,63}\Z')

ROUTER=r'''<?php
declare(strict_types=1);
$allowed=['index.php','actions.php','mal-callback.php','calendar.php','maintenance.php','catalog-public.php','backup.php','release-health.php','service-worker.php','app-manifest.php'];
if(!isset($seasonEntry)||!in_array($seasonEntry,$allowed,true)){http_response_code(404);exit();}
$base=dirname(__DIR__);$pointer=json_decode((string)@file_get_contents(__DIR__.'/current.json'),true);
$id=$pointer['release']??'';
if(!is_string($id)||!preg_match('/^[a-z0-9][a-z0-9-]{5,63}$/D',$id)){http_response_code(503);exit('Publicación no disponible.');}
$folder=$base.'/releases/'.$id;
if(!is_file($folder.'/private/ready.json')||!is_file($folder.'/'.$seasonEntry)){http_response_code(503);exit('Publicación incompleta.');}
define('SEASON_APP_ROOT',$base);define('SEASON_RELEASE_ID',$id);
require $folder.'/'.$seasonEntry;
'''

def valid_id(value):
    if not RELEASE_PATTERN.fullmatch(value):raise ValueError('Invalid release ID')
    return value

def source_files():
    files={}
    for p in (ROOT/'htdocs').rglob('*'):
        if not p.is_file():continue
        name=p.relative_to(ROOT/'htdocs').as_posix();parts=PurePosixPath(name).parts
        if p.name.endswith('.local.php') or parts[0].startswith('__qa') or parts[0]=='releases':continue
        if name in ('private/current.json','private/release-router.php'):continue
        if parts[0]=='feeds' and p.suffix in ('.ics','.tmp') and p.name!='horario.ics':continue
        files[name]=p.read_bytes()
    return files

def build(release_id, files=None, legacy=False):
    release_id=valid_id(release_id);files=dict(source_files() if files is None else files)
    prefix=f'releases/{release_id}/'
    for name,data in list(files.items()):
        if name.endswith(('.js','.html')) or name=='index.php':
            text=data.decode('utf-8-sig')
            # Document URLs remain at the app root; assets point into this immutable release.
            text=re.sub(r'''(["'])(assets/|downloads/|data/offline-catalog\.json)''',lambda m:m[1]+prefix+m[2],text)
            text=text.replace('href="offline.html"',f'href="{prefix}offline.html"')
            if name=='index.php':text=text.replace('href="manifest.webmanifest"',f'href="{prefix}manifest.webmanifest"')
            if name=='assets/offline.js':
                text=text.replace("'catalog-public.php'","'/seasonav1/catalog-public.php'").replace("'"+prefix+"data/offline-catalog.json'","'/seasonav1/"+prefix+"data/offline-catalog.json'")
            if name=='assets/pwa.js':text=text.replace("register('sw.js')","register('service-worker.php')")
            if name=='offline.html':
                # Can be opened as a release file or used as the root navigation fallback.
                text=re.sub(r'(src|href)="'+re.escape(prefix),r'\1="/seasonav1/'+prefix,text)
                text=text.replace('href="./"','href="/seasonav1/"')
            # sw.js gets an explicit asset list instead of the generic string transform.
            if name=='sw.js':continue
            files[name]=text.encode()
    if 'sw.js' in files:
        text=files['sw.js'].decode('utf-8-sig')
        text=text.replace("const CACHE =", "const RELEASE = '"+release_id+"';\nconst CACHE =")
        text=re.sub(r"const CACHE = '[^']+';",f"const CACHE = 'seasonav1-public-{release_id}';",text)
        text=re.sub(r"  '((?:assets/|data/|offline\.html)[^']*)',",lambda m:"  '"+prefix+m[1]+"',",text)
        text=text.replace("new URL('offline.html', ROOT)",f"new URL('{prefix}offline.html', ROOT)")
        text=text.replace("[PUBLIC_INDEX,'data/offline-catalog.json']",f"[PUBLIC_INDEX,'{prefix}data/offline-catalog.json']")
        files['sw.js']=text.encode()
    if 'manifest.webmanifest' in files:
        manifest=json.loads(files['manifest.webmanifest']);manifest.update(id='../../',scope='../../',start_url='../../#discover')
        files['manifest.webmanifest']=json.dumps(manifest,ensure_ascii=False,indent=2).encode()
    # Old stable builds also receive the new root worker entry point.
    files.setdefault('service-worker.php',(ROOT/'htdocs/service-worker.php').read_bytes())
    files.setdefault('release-health.php',(ROOT/'htdocs/release-health.php').read_bytes())
    for name in ['config.local.php','access.local.php']:
        files['private/'+name]=("<?php\nif(!defined('SEASON_BOOTSTRAPPED')){http_response_code(404);exit();}\nreturn require dirname(__DIR__,3).'/private/"+name+"';\n").encode()
    # Direct release PHP URLs cannot bypass the selected API or create a second session scope.
    files['.htaccess']=b'Options -Indexes\nAddType font/woff2 .woff2\n<FilesMatch "\\.php$">\nRequire all denied\n</FilesMatch>\n'
    for name in files:
        parts=PurePosixPath(name).parts
        if name.startswith('/') or '..' in parts:raise ValueError('Unsafe path')
    manifest={'release':release_id,'legacy':legacy,'files':{n:hashlib.sha256(b).hexdigest() for n,b in sorted(files.items())}}
    files['private/ready.json']=json.dumps(manifest,sort_keys=True).encode()
    return files,manifest

def legacy_files():
    with zipfile.ZipFile(ROOT/'artifacts/delivery3-stable.zip') as z:
        return {n[7:]:z.read(n) for n in z.namelist() if n.startswith('htdocs/') and not n.endswith('/')}

def write_local(folder,files):
    for name,data in files.items():
        path=folder/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)

def ftp_read(ftp,path):
    target=io.BytesIO();ftp.retrbinary('RETR '+path,target.write);return target.getvalue()

def lossless_icon(source,received):
    """Only an alternate PNG encoding with identical pixels and color interpretation."""
    from PIL import Image
    if not source.startswith(b'\x89PNG\r\n\x1a\n') or not received.startswith(b'\x89PNG\r\n\x1a\n'):return False
    try:
        with Image.open(io.BytesIO(source)) as a,Image.open(io.BytesIO(received)) as b:
            if a.size!=b.size or max(a.size)>512:return False
            for field in ['icc_profile','gamma','chromaticity','srgb','transparency']:
                if a.info.get(field)!=b.info.get(field):return False
            return a.convert('RGBA').tobytes()==b.convert('RGBA').tobytes()
    except Exception:return False

def finalize_staged_content(expected,read):
    """Re-read every source file and pin final host PNG encodings after other files."""
    ready=json.loads(expected['private/ready.json']);ready.pop('normalization',None)
    content={};normalization={}
    names=sorted(ready['files'],key=lambda n:(bool(re.fullmatch(r'assets/icon-(32|180|192|512)\.png',n)),n))
    for name in names:
        source=expected[name];received=read(name)
        if source!=received:
            if not re.fullmatch(r'assets/icon-(32|180|192|512)\.png',name) or not lossless_icon(source,received):
                raise RuntimeError('Staged file differs from requested source: '+name)
            normalization[name]={'source_sha256':hashlib.sha256(source).hexdigest(),'kind':'lossless_png'}
        content[name]=received;ready['files'][name]=hashlib.sha256(received).hexdigest()
    if normalization:ready['normalization']=normalization
    content['private/ready.json']=json.dumps(ready,sort_keys=True).encode()
    return content,ready

def ftp_write(ftp,path,data,allow_lossless_icon=False):
    parent=PurePosixPath(path).parent.as_posix()
    directories=getattr(ftp,'_season_directories',set())
    if parent!='.' and parent not in directories:
        original=ftp.pwd()
        for part in parent.split('/'):
            try:ftp.cwd(part)
            except Exception:ftp.mkd(part);ftp.cwd(part)
        ftp.cwd(original)
        directories.add(parent);ftp._season_directories=directories
    ftp.storbinary('STOR '+path,io.BytesIO(data))
    received=ftp_read(ftp,path)
    if received!=data:
        if not (allow_lossless_icon and re.fullmatch(r'icon-(32|180|192|512)\.png',PurePosixPath(path).name) and lossless_icon(data,received)):
            raise RuntimeError('FTPS verification failed: '+path)
    return received

def verified_content(manifest_bytes,expected,read):
    manifest=json.loads(manifest_bytes);original=json.loads(expected['private/ready.json'])
    if manifest['release']!=original['release'] or set(manifest['files'])!=set(original['files']):raise RuntimeError('Published manifest does not match this source')
    files={}
    for name,digest in manifest['files'].items():
        data=read(name)
        if hashlib.sha256(data).hexdigest()!=digest:raise RuntimeError('Local published checksum mismatch: '+name)
        if data!=expected[name]:
            normalization=manifest.get('normalization',{}).get(name,{})
            if normalization.get('source_sha256')!=original['files'][name] or not re.fullmatch(r'assets/icon-(32|180|192|512)\.png',name) or not lossless_icon(expected[name],data):raise RuntimeError('Published file changed beyond lossless icon encoding: '+name)
        files[name]=data
    files['private/ready.json']=manifest_bytes
    return files,manifest

def published_files(identifier):
    """The staged artifact pins the host's lossless PNG encoding, never its PHP or JS."""
    expected,original=build(identifier)
    folder=ROOT/'artifacts/releases'/identifier
    manifest_path=folder/'private/ready.json'
    if not manifest_path.is_file():return expected,original
    return verified_content(manifest_path.read_bytes(),expected,lambda name:(folder/name).read_bytes())

def switch(ftp,release_id,previous):
    release_id=valid_id(release_id)
    ready=json.loads(ftp_read(ftp,f'releases/{release_id}/private/ready.json'))
    if ready['release']!=release_id:raise RuntimeError('Incomplete release')
    temp='private/current-'+secrets.token_hex(8)+'.json'
    value=json.dumps({'release':release_id,'previous':previous,'at':datetime.now(timezone.utc).isoformat()}).encode()
    ftp_write(ftp,temp,value)
    try:
        # RNFR/RNTO must replace in one operation. Never delete the active pointer first.
        ftp.rename(temp,'private/current.json')
    except (OSError,EOFError):
        # A lost reply cannot tell us whether rename committed; reconnect and inspect.
        raise
    except Exception:
        try:ftp.delete(temp)
        except Exception:pass
        raise RuntimeError('The server did not permit an atomic pointer replacement; active release kept.') from None
    if ftp_read(ftp,'private/current.json')!=value:raise RuntimeError('Release pointer verification failed')

def publish(release_id=None,rollback=False,status=False,skip_database_backup=False):
    # Existing authorized credential provider; never print or package its values.
    sys.path.insert(0,str(ROOT.parent.parent/'Expedition-7'))
    from deploy import InfinityFTP,credentials
    config=credentials()
    if config['username']!='if0_43115975' or config['database']!='if0_43115975_anime':raise RuntimeError('The local credentials do not match this authorized hosting account')
    with InfinityFTP(context=ssl.create_default_context(),timeout=60) as ftp:
        ftp.connect('ftpupload.net',21);ftp.login(config['username'],config['password']);ftp.prot_p();ftp.cwd('/htdocs/seasonav1')
        def reconnect():
            ftp.close();ftp.connect('ftpupload.net',21);ftp.login(config['username'],config['password']);ftp.prot_p();ftp.cwd('/htdocs/seasonav1');ftp._season_directories=set()
        def stage_reader(identifier):
            count=0
            def read(name):
                nonlocal count
                if count and count%20==0:reconnect()
                count+=1
                return ftp_read(ftp,f'releases/{identifier}/{name}')
            return read
        try:current=json.loads(ftp_read(ftp,'private/current.json'))
        except Exception as error:
            if not str(error).startswith('550'):raise
            current=None
        if status:print(json.dumps(current or {'release':'legacy-root'}));return
        if release_id and current and current.get('release')==release_id:
            expected,_=build(release_id)
            content,_=verified_content(ftp_read(ftp,f'releases/{release_id}/private/ready.json'),expected,stage_reader(release_id))
            health=check_health()
            if not health.get('ok') or health.get('release')!=release_id:raise RuntimeError('Active release did not pass health verification')
            write_local(ROOT/'artifacts/releases'/release_id,content)
            result={'ok':True,'release':release_id,'previous':current.get('previous'),'files':len(content),'health':health,'database_backup':'waived_by_owner' if skip_database_backup else 'already_active'}
            (ROOT/'verification/delivery4-deployment.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(result));return
        if rollback:
            if not current or not current.get('previous'):raise RuntimeError('No previous release registered')
            target=valid_id(current['previous']);switch(ftp,target,current['release'])
            try:
                health=check_health()
                if not health.get('ok') or health.get('release')!=target:raise RuntimeError('Rollback target did not pass health verification')
            except Exception:
                switch(ftp,current['release'],target)
                raise RuntimeError('Rollback health failed; the prior active pointer was restored') from None
            print('Rolled back to '+target);return
        import time
        receipt_path=ROOT/'verification/production-backup-receipt.json'
        receipt=json.loads(receipt_path.read_text(encoding='utf8')) if receipt_path.exists() else {}
        backup=(ROOT/receipt.get('file','')).resolve()
        if not skip_database_backup and (not receipt.get('verified') or int(receipt.get('at',0))<time.time()-86400 or not backup.is_relative_to((ROOT/'artifacts/private-backups').resolve()) or not backup.is_file() or hashlib.file_digest(backup.open('rb'),'sha256').hexdigest()!=receipt.get('sha256')):
            raise RuntimeError('Create and verify an encrypted database snapshot first: python tools/remote_backup.py')
        files,manifest=build(release_id)
        stages=[(release_id,files)]
        if current is None:
            old_id='stable-delivery3';old_files,_=build(old_id,legacy_files(),legacy=True);stages.insert(0,(old_id,old_files))
        for identifier,content in stages:
            requested=dict(content)
            # An interrupted stage is reusable only when every byte matches this source.
            try:existing=ftp_read(ftp,f'releases/{identifier}/private/ready.json')
            except Exception as error:
                if not str(error).startswith('550'):raise
            else:
                complete,_=verified_content(existing,content,stage_reader(identifier))
                content.clear();content.update(complete);write_local(ROOT/'artifacts/releases'/identifier,content)
                print('Verified staged release '+identifier,flush=True);continue
            ready=json.loads(content['private/ready.json']);normalization={}
            completed=0
            for name,data in sorted(content.items()):
                if name=='private/ready.json':continue
                icon=bool(re.fullmatch(r'assets/icon-(32|180|192|512)\.png',name))
                try:existing_file=ftp_read(ftp,f'releases/{identifier}/{name}')
                except Exception as error:
                    if not str(error).startswith('550'):raise
                    existing_file=None
                actual=existing_file if existing_file==data or icon and existing_file is not None and lossless_icon(data,existing_file) else ftp_write(ftp,f'releases/{identifier}/{name}',data,allow_lossless_icon=icon)
                if actual!=data:
                    normalization[name]={'source_sha256':hashlib.sha256(data).hexdigest(),'kind':'lossless_png'}
                    content[name]=actual;ready['files'][name]=hashlib.sha256(actual).hexdigest()
                completed+=1
                if completed%10==0:print(f'Staged {identifier}: {completed}/{len(content)-1} files',flush=True)
                if completed%20==0:reconnect()
            # The host can recompress an icon asynchronously after STOR. Read all
            # files against the requested source, with icons last, before pinning hashes.
            complete,ready=finalize_staged_content(requested,stage_reader(identifier))
            content.clear();content.update(complete)
            ftp_write(ftp,f'releases/{identifier}/private/ready.json',content['private/ready.json'])
            for name in ready.get('normalization',{}):
                if hashlib.sha256(ftp_read(ftp,f'releases/{identifier}/{name}')).hexdigest()!=ready['files'][name]:
                    raise RuntimeError('Staged icon changed after finalization: '+name)
            write_local(ROOT/'artifacts/releases'/identifier,content)
            reconnect()
        ftp_write(ftp,'private/release-router.php',ROUTER.encode())
        if current is None:
            switch(ftp,'stable-delivery3',None)
            current={'release':'stable-delivery3'}
        for entry in ENTRIES:
            wrapper=("<?php\n$seasonEntry='"+entry+"';require __DIR__.'/private/release-router.php';\n").encode()
            ftp_write(ftp,entry,wrapper)
        switch(ftp,release_id,current['release'])
        # Health verification is done through the same anonymous first-party gate as normal visitors.
        try:
            health=check_health()
            if health.get('release')!=release_id or not health.get('ok'):raise RuntimeError('New release health check failed')
        except Exception:
            switch(ftp,current['release'],release_id)
            if not check_health().get('ok'):raise RuntimeError('Activation and rollback health checks failed') from None
            raise RuntimeError('Activation failed; previous release restored') from None
    result={'ok':True,'release':release_id,'previous':current['release'],'files':len(files),'health':health,'database_backup':'waived_by_owner' if skip_database_backup else 'verified'}
    (ROOT/'verification/delivery4-deployment.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    print(json.dumps(result))

class PublicClient:
    """Read the host's public pages, including its ordinary first-party cookie handshake."""
    def __init__(self):
        import http.cookiejar,urllib.request
        self.opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        self.cookie=''
    def get(self,path):
        import urllib.request,urllib.error,urllib.parse,subprocess
        if path.startswith(('/', 'http')) or '..' in path.split('/'):raise ValueError('Only relative app paths are allowed')
        for attempt in range(3):
            headers={'User-Agent':'Mozilla/5.0 YomaTV release verification'}
            if self.cookie:headers['Cookie']='__test='+self.cookie
            request=urllib.request.Request('https://hk-br035.gt.tc/seasonav1/'+path,headers=headers)
            try:response=self.opener.open(request,timeout=40)
            except urllib.error.HTTPError as error:response=error
            with response:
                data=response.read();status=response.status;content_type=response.headers.get('Content-Type','')
            if 'text/html' not in content_type or b'aes.js' not in data or b'toNumbers(' not in data:return status,data,content_type
            challenge=re.findall(r'toNumbers\("([a-f0-9]+)"\)',data.decode('utf8',errors='replace'))
            if len(challenge)!=3:raise RuntimeError('Unexpected public host cookie handshake')
            code='$v=json_decode(stream_get_contents(STDIN),true);echo bin2hex(openssl_decrypt(hex2bin($v[2]),"aes-128-cbc",hex2bin($v[0]),OPENSSL_RAW_DATA|OPENSSL_ZERO_PADDING,hex2bin($v[1])));'
            self.cookie=subprocess.run([r'C:/Users/Eduardo/.config/herd-lite/bin/php.exe','-r',code],input=json.dumps(challenge),text=True,capture_output=True,check=True).stdout.strip()
            if not re.fullmatch('[a-f0-9]{32}',self.cookie):raise RuntimeError('Unexpected public host cookie')
            if not re.search(r'(?:[?&])i=',path):path+=('&' if '?' in path else '?')+'i=1'
        raise RuntimeError('The public host cookie handshake did not complete')

def check_health():
    status,data,_=PublicClient().get('release-health.php?v='+secrets.token_hex(6))
    if status!=200:raise RuntimeError('Release health returned HTTP '+str(status))
    return json.loads(data)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--build');parser.add_argument('--publish');parser.add_argument('--rollback',action='store_true');parser.add_argument('--status',action='store_true');parser.add_argument('--skip-database-backup',action='store_true',help='Use only when the owner explicitly defers the database backup')
    args=parser.parse_args()
    if args.skip_database_backup and not args.publish:parser.error('--skip-database-backup requires --publish')
    if args.build:
        files,manifest=build(args.build);folder=ROOT/'artifacts/releases'/args.build
        if folder.exists():raise RuntimeError('Release build already exists')
        write_local(folder,files);print(json.dumps({'release':args.build,'files':len(files),'folder':str(folder)}))
    elif args.publish or args.rollback or args.status:
        import ftplib,time
        for attempt in range(4):
            try:
                publish(args.publish,args.rollback,args.status,args.skip_database_backup);break
            except (OSError,EOFError,ftplib.error_temp) as error:
                if args.rollback or args.status or attempt==3:raise
                print('FTPS connection interrupted; resuming verified staging (attempt '+str(attempt+2)+')',flush=True)
                time.sleep([2,5,10][attempt])
    else:parser.error('Choose --build ID, --publish ID, --rollback or --status')
if __name__=='__main__':main()
