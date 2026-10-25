"""Check private server configuration and source ZIP without printing any secret."""
import base64
import importlib.util
import io
import json
import re
import ssl
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
spec=importlib.util.spec_from_file_location('season_deploy',ROOT/'deploy.py')
deployment=importlib.util.module_from_spec(spec);spec.loader.exec_module(deployment)

def main():
    config=deployment.credentials()
    with deployment.InfinityFTP(context=ssl.create_default_context(),timeout=60) as ftp:
        ftp.connect('ftpupload.net',21);ftp.login(config['username'],config['password']);ftp.prot_p()
        ftp.cwd('/htdocs/seasonav1/private');private=io.BytesIO()
        ftp.retrbinary('RETR config.local.php',private.write);ftp.quit()
    data=private.getvalue();text=data.decode('utf-8-sig')
    block=text.split('/* SEASONAV1_MAL_CONFIG_START */',1)[1].split('/* SEASONAV1_MAL_CONFIG_END */',1)[0]
    values={name:re.search("'"+name+"'\\s*=>\\s*'([^']+)'",block)[1] for name in ['client_id','client_secret','encryption_key']}
    assert len(values['client_id'])==32 and len(values['client_secret'])==64
    assert len(base64.b64decode(values['encryption_key'],validate=True))==32
    result=subprocess.run([r'C:/Users/Eduardo/.config/herd-lite/bin/php.exe','-l'],input=data,capture_output=True)
    assert result.returncode==0
    archive=ROOT/'artifacts/YomaTVWeb-fuente.zip'
    with zipfile.ZipFile(archive) as source:
        assert source.testzip() is None
        for name in source.namelist():
            assert not name.endswith('.local.php')
            contents=source.read(name)
            assert all(value.encode() not in contents for value in values.values())
    for file in (ROOT/'htdocs').rglob('*'):
        if file.is_file():assert all(value.encode() not in file.read_bytes() for value in values.values())
    record={'ok':True,'server_configuration_syntax_valid':True,'token_encryption_key_valid':True,
      'real_credentials_in_local_htdocs':False,'real_credentials_in_source_zip':False,
      'server_private_configuration_backed_up_locally':False}
    (ROOT/'verification/mal-secrets-check.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
    print(json.dumps(record,indent=2))

if __name__=='__main__':
    try:main()
    except Exception:
        print('Private configuration/source audit failed. No credentials were printed.',file=sys.stderr)
        sys.exit(1)
