"""No network: build integrity, immutable URL routing and real filesystem pointer flips."""
import hashlib,io,json,os,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent;sys.path.insert(0,str(ROOT));import release
checks=[]
files,manifest=release.build('qa-delivery4-first')
assert all(hashlib.sha256(files[n]).hexdigest()==digest for n,digest in manifest['files'].items())
assert all(not (name.endswith('.local.php') and b'return require' not in data) for name,data in files.items())
assert b'client_secret' not in files['private/config.local.php'];checks.append('all_release_hashes_exact_and_only_guarded_configuration_proxies')
index=files['index.php'].decode();assert 'releases/qa-delivery4-first/assets/transport.js' in index
assert "__DIR__.'/assets/transport.js'" in index # filemtime must still use the filesystem path
assert b"register('service-worker.php')" in files['assets/pwa.js'];checks.append('immutable_assets_with_stable_root_api_and_worker')
sw=files['sw.js'].decode();assert "'releases/qa-delivery4-first/offline.html'" in sw
assert "new URL('releases/qa-delivery4-first/offline.html', ROOT)" in sw
assert b"'/seasonav1/catalog-public.php'" in files['assets/offline.js']
assert json.loads(files['manifest.webmanifest'])['scope']=='../../';checks.append('offline_catalog_and_manifest_resolve_from_release_and_root_fallback')
assert 'href="app-manifest.php" crossorigin="use-credentials"' in index and 'app-manifest.php' in release.ENTRIES and 'app-manifest.php' in release.ROUTER
import subprocess
with tempfile.TemporaryDirectory(dir=ROOT/'verification') as folder:
    for release_id in ['qa-manifest-first','qa-manifest-second']:
        bundle,_=release.build(release_id);release.write_local(Path(folder)/release_id,bundle)
        entry=(Path(folder)/release_id/'app-manifest.php').as_posix()
        code="define('SEASON_RELEASE_ID', '"+release_id+"'); $_SERVER['SCRIPT_NAME']='/seasonav1/app-manifest.php'; require '"+entry+"';"
        result=subprocess.run([r'C:/Users/Eduardo/.config/herd-lite/bin/php.exe','-r',code],capture_output=True,text=True,encoding='utf8',check=True)
        install=json.loads(result.stdout)
        assert install['id']==install['scope']=='/seasonav1/' and install['start_url']=='/seasonav1/#discover'
        assert all(i['src'].startswith('/seasonav1/releases/'+release_id+'/assets/icon-') for i in install['icons'])
checks.append('stable_manifest_identity_survives_release_switches_and_points_to_current_immutable_icons')
assert b'Require all denied' in files['.htaccess'];assert "file_get_contents(__DIR__.'/current.json')" in release.ROUTER;checks.append('direct_php_release_access_blocked_and_pointer_not_opcache_cached')

class LocalFTP:
    def __init__(self,root,refuse=False):self.root=Path(root);self.path=self.root;self.refuse=refuse
    def cwd(self,path):
        p=Path(path) if Path(path).is_absolute() else self.path/path
        if not p.is_dir():raise FileNotFoundError(p)
        self.path=p
    def pwd(self):return str(self.path)
    def mkd(self,path):(self.path/path).mkdir()
    def storbinary(self,command,stream):(self.path/command[5:]).write_bytes(stream.read())
    def retrbinary(self,command,write):write((self.path/command[5:]).read_bytes())
    def rename(self,source,target):
        if self.refuse:raise RuntimeError('Atomic overwrite denied')
        os.replace(self.path/source,self.path/target)
    def delete(self,path):(self.path/path).unlink()
with tempfile.TemporaryDirectory(dir=ROOT/'verification') as folder:
    ftp=LocalFTP(folder)
    for name in ['qa-delivery4-first','qa-delivery4-second']:
        bundle,_=release.build(name);release.write_local(Path(folder)/'releases'/name,bundle)
    (Path(folder)/'private').mkdir()
    release.switch(ftp,'qa-delivery4-first',None)
    release.switch(ftp,'qa-delivery4-second','qa-delivery4-first')
    pointer=json.loads((Path(folder)/'private/current.json').read_bytes());assert pointer['release']=='qa-delivery4-second'
    release.switch(ftp,pointer['previous'],pointer['release']);assert json.loads((Path(folder)/'private/current.json').read_bytes())['release']=='qa-delivery4-first'
    checks.append('activation_and_rollback_use_atomic_filesystem_replacement')
    ftp.refuse=True;before=(Path(folder)/'private/current.json').read_bytes()
    try:release.switch(ftp,'qa-delivery4-second','qa-delivery4-first');raise AssertionError('Must refuse non-atomic publication')
    except RuntimeError:pass
    assert (Path(folder)/'private/current.json').read_bytes()==before;checks.append('unsupported_atomic_replace_leaves_previous_release_untouched')
    for bad in ['../../secret','x','a'*65,'UpperCase']:
        try:release.build(bad);raise AssertionError('Unsafe release ID accepted')
        except ValueError:pass
    checks.append('release_ids_cannot_traverse_directories')
from PIL import Image
def png(color,level):
    target=io.BytesIO();Image.new('RGBA',(32,32),color).save(target,format='PNG',compress_level=level);return target.getvalue()
original=png((45,66,80,200),0);compressed=png((45,66,80,200),9);altered=png((46,66,80,200),9)
assert original!=compressed and release.lossless_icon(original,compressed)
assert not release.lossless_icon(original,altered)
with tempfile.TemporaryDirectory(dir=ROOT/'verification') as folder:
    class EncodedFTP(LocalFTP):
        def storbinary(self,command,stream):
            stream.read();(self.path/command[5:]).write_bytes(compressed)
    ftp=EncodedFTP(folder)
    try:release.ftp_write(ftp,'icon-32.png',original);raise AssertionError('Strict file check accepted changed bytes')
    except RuntimeError:pass
    assert release.ftp_write(ftp,'icon-32.png',original,allow_lossless_icon=True)==compressed
    try:release.ftp_write(ftp,'application.js',original,allow_lossless_icon=True);raise AssertionError('PNG exception accepted a script')
    except RuntimeError:pass
checks.append('host_png_reencoding_requires_identical_pixels_and_never_applies_to_scripts')
expected={'assets/icon-32.png':original,'application.js':b'verified script'}
ready={'release':'qa-resume-1','files':{name:hashlib.sha256(data).hexdigest() for name,data in expected.items()}}
expected['private/ready.json']=json.dumps(ready).encode()
encoded=dict(expected);encoded['assets/icon-32.png']=compressed
ready['files']['assets/icon-32.png']=hashlib.sha256(compressed).hexdigest()
ready['normalization']={'assets/icon-32.png':{'source_sha256':hashlib.sha256(original).hexdigest(),'kind':'lossless_png'}}
content,_=release.verified_content(json.dumps(ready).encode(),expected,lambda name:encoded[name])
assert content['assets/icon-32.png']==compressed
encoded['application.js']=b'another script';ready['files']['application.js']=hashlib.sha256(encoded['application.js']).hexdigest()
try:release.verified_content(json.dumps(ready).encode(),expected,lambda name:encoded[name]);raise AssertionError('Different source reused an immutable release')
except RuntimeError:pass
checks.append('resuming_ready_stage_rechecks_all_files_against_the_requested_source')
final,final_ready=release.finalize_staged_content(expected,lambda name:compressed if name=='assets/icon-32.png' else expected[name])
assert final['assets/icon-32.png']==compressed and final_ready['files']['assets/icon-32.png']==hashlib.sha256(compressed).hexdigest()
release.verified_content(final['private/ready.json'],expected,lambda name:final[name])
for bad_name in ['application.js','assets/icon-32.png']:
    def modified(name):return (b'changed script' if name=='application.js' else altered) if name==bad_name else expected[name]
    try:release.finalize_staged_content(expected,modified);raise AssertionError('Finalization accepted modified source or pixels')
    except RuntimeError:pass
checks.append('delayed_png_reencoding_is_pinned_after_uploads_without_accepting_changed_scripts_or_pixels')
result={'ok':True,'count':len(checks),'checks':checks,'network_requests':0}
(ROOT/'verification/release-check.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(result))
