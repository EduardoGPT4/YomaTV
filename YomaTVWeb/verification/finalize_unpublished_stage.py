"""Repair final icon hashes of a never-finalized, non-active stage only."""
import json,ssl,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));import release
identifier=release.valid_id(sys.argv[1]);expected,_=release.build(identifier)
if (ROOT/'artifacts/releases'/identifier/'private/ready.json').exists():raise RuntimeError('Refusing to change a locally finalized release')
sys.path.insert(0,str(ROOT.parent.parent/'Expedition-7'))
from deploy import InfinityFTP,credentials
config=credentials()
assert config['username']=='if0_43115975' and config['database']=='if0_43115975_anime'
with InfinityFTP(context=ssl.create_default_context(),timeout=60) as ftp:
    def connect():
        ftp.connect('ftpupload.net',21);ftp.login(config['username'],config['password']);ftp.prot_p();ftp.cwd('/htdocs/seasonav1')
    connect()
    def inactive():
        pointer=json.loads(release.ftp_read(ftp,'private/current.json'))
        if identifier in [pointer.get('release'),pointer.get('previous')]:raise RuntimeError('Refusing to repair a current or previous active release')
    inactive();count=0
    def read(name):
        global count
        if count and count%20==0:ftp.close();connect();inactive()
        count+=1
        return release.ftp_read(ftp,'releases/'+identifier+'/'+name)
    content,manifest=release.finalize_staged_content(expected,read)
    inactive()
    release.ftp_write(ftp,'releases/'+identifier+'/private/ready.json',content['private/ready.json'])
    for name in manifest.get('normalization',{}):
        if release.ftp_read(ftp,'releases/'+identifier+'/'+name)!=content[name]:raise RuntimeError('Host icon changed again')
    release.write_local(ROOT/'artifacts/releases'/identifier,content)
print(json.dumps({'ok':True,'unpublished_stage':identifier,'verified_files':len(manifest['files']),'only_pixel_identical_png_encodings_allowed':True}))
