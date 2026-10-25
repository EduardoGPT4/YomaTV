"""Read one public MAL record; never uses user tokens or prints configuration."""
import importlib.util
import io
import json
import re
import ssl
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
def main():
    spec=importlib.util.spec_from_file_location('season_deploy',ROOT/'deploy.py')
    deployment=importlib.util.module_from_spec(spec);spec.loader.exec_module(deployment)
    config=deployment.credentials()
    with deployment.InfinityFTP(context=ssl.create_default_context(),timeout=30) as ftp:
        ftp.connect('ftpupload.net',21);ftp.login(config['username'],config['password']);ftp.prot_p()
        ftp.cwd('/htdocs/seasonav1/private');private=io.BytesIO()
        ftp.retrbinary('RETR config.local.php',private.write);ftp.quit()
    block=private.getvalue().decode('utf-8-sig').split('/* SEASONAV1_MAL_CONFIG_START */',1)[1].split('/* SEASONAV1_MAL_CONFIG_END */',1)[0]
    client_id=re.search("'client_id'\\s*=>\\s*'([^']+)'",block)[1]
    fields=['alternative_titles','media_type','start_date','status','num_episodes','genres','mean','studios']
    url='https://api.myanimelist.net/v2/anime/20?'+urllib.parse.urlencode({'fields':','.join(fields)})
    request=urllib.request.Request(url,headers={'X-MAL-CLIENT-ID':client_id,'Accept':'application/json','User-Agent':'YomaTVWeb/1.0 (public metadata check)'})
    with urllib.request.urlopen(request,timeout=25) as response:
        data=json.load(response)
    assert data['id']==20 and all(field in data for field in fields)
    assert isinstance(data['genres'],list) and isinstance(data['studios'],list) and isinstance(data['mean'],(int,float))
    result={'ok':True,'public_record_id':20,'fields_present':fields,'personal_tokens_used':False,'remote_list_changes':False}
    (ROOT/'verification/mal-public-fields-check.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    print(json.dumps(result,indent=2))
if __name__=='__main__':
    try: main()
    except Exception:
        print('No se pudo verificar la ficha pública de MAL; no se imprimieron credenciales.',file=sys.stderr)
        sys.exit(1)
