"""Publish only the prepared YomaTV installers. Git credentials stay in memory."""
from pathlib import Path
import hashlib,json,os,subprocess,urllib.request,urllib.error,urllib.parse
ROOT=Path(__file__).resolve().parents[1];REPO='EduardoGPT4/YomaTV'
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None
opener=urllib.request.build_opener(NoRedirect())

def credential():
    token=os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
    if token:return token
    r=subprocess.run(['git','credential','fill'],input='protocol=https\nhost=github.com\nusername=EduardoGPT4\n\n',capture_output=True,text=True,check=True,env={**os.environ,'GIT_TERMINAL_PROMPT':'0','GCM_INTERACTIVE':'never'})
    values=dict(line.split('=',1)for line in r.stdout.splitlines()if '='in line)
    if values.get('username','').lower()!='eduardogpt4' or not values.get('password'):raise RuntimeError('Sign into GitHub with Git Credential Manager first.')
    return values['password']

def request(url,token,method='GET',data=None,binary=False):
    assert url.startswith('https://api.github.com/repos/'+REPO+'/')or url.startswith('https://uploads.github.com/repos/'+REPO+'/')
    body=data if binary else json.dumps(data).encode()if data is not None else None
    req=urllib.request.Request(url,data=body,method=method,headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json','Content-Type':'application/octet-stream'if binary else'application/json','User-Agent':'YomaTV-release'})
    try:
        with opener.open(req,timeout=180)as response:
            payload=response.read();return json.loads(payload)if payload else{}
    except urllib.error.HTTPError as e:raise RuntimeError('GitHub HTTP '+str(e.code))from None

def main():
    folder=ROOT/'release-artifacts';metadata=json.loads((folder/'yomatv-downloads.json').read_text());tag=metadata['tag']
    assert metadata['repository']==REPO and tag=='v'+metadata['apps'][0]['version']
    names=['yomatv-downloads.json','SHA256SUMS.txt','YomaTV-Android.apk','YomaTV-Windows.exe']+[a['url'].rsplit('/',1)[1]for a in metadata['apps']]
    for a in metadata['apps']:
        data=(folder/a['url'].rsplit('/',1)[1]).read_bytes();assert len(data)==a['bytes']and hashlib.sha256(data).hexdigest()==a['sha256']
    token=credential();base='https://api.github.com/repos/'+REPO
    releases=request(base+'/releases?per_page=30',token)
    previous=next((r for r in releases if r['tag_name']==tag),None)
    if previous and not previous['draft']:raise RuntimeError('This version is already public. Bump the version; installers are immutable.')
    release=previous or request(base+'/releases',token,'POST',{'tag_name':tag,'target_commitish':os.environ.get('GITHUB_SHA','main'),'name':'YomaTV '+tag,'draft':True,'body':'YomaTV Android y Windows. Incluye nueva interfaz móvil, navegación que conserva su estado, nuevo icono y descargas sin Google Drive. Tamaños y SHA-256 en yomatv-downloads.json.'})
    identifier=release['id'];existing={a['name']:a for a in release['assets']}
    for name in names:
        data=(folder/name).read_bytes();sha='sha256:'+hashlib.sha256(data).hexdigest()
        asset=existing.get(name)
        if asset:
            if asset.get('digest')!=sha:raise RuntimeError('Existing draft asset differs or has no verified digest: '+name)
        else:
            upload='https://uploads.github.com/repos/'+REPO+'/releases/'+str(identifier)+'/assets?name='+urllib.parse.quote(name)
            asset=request(upload,token,'POST',data,True)
        assert asset['size']==len(data)
        if asset.get('digest'):assert asset['digest']==sha
        print('Verified upload: '+name+' ('+str(len(data))+' bytes)',flush=True)
    release=request(base+'/releases/'+str(identifier),token,'PATCH',{'draft':False,'prerelease':False,'make_latest':'true'})
    (folder/'publication-receipt.json').write_text(json.dumps({'ok':True,'url':release['html_url'],'release_id':identifier,'tag':tag,'apps':metadata['apps']},indent=2),encoding='utf8')
    print('Published: '+release['html_url'],flush=True)
if __name__=='__main__':main()
