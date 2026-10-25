"""Record the verified hosting-cookie correction without claiming a physical Android test."""
import hashlib,json,re,subprocess,sys,time
from pathlib import Path
import delivery4_evidence as evidence

ROOT=evidence.ROOT
sys.path.insert(0,str(ROOT));import release
identifier='brave-icon-20261024-1'
status=evidence.external_checks(evidence.read_report('delivery4-status.json'))
public=evidence.read_report('delivery4-published-check.json')
deployment=evidence.read_report('delivery4-deployment.json')
before=evidence.read_report('brave-install-before.json')
current=evidence.application_hashes()
assert status['published'] and not status['pending']
assert deployment.get('release')==public.get('release')==identifier
assert all(status['source_sha256'].get(p)==sha for p,sha in current.items())
assert before.get('challenge_html') and not before.get('valid_manifest')
after=public['install_credentials_probe']
assert after['ok'] and after['declared_credentials']=='include' and not after['second_host_handshake_performed']
(ROOT/'verification/brave-install-after.json').write_text(json.dumps({'release':identifier,'at':int(time.time()),**after},indent=2),encoding='utf8')
status.update(published_release=identifier,install_manifest_verified=True,physical_android_tested=False,
    native_android_install_verified=False,installation_evidence='brave-install-after.json')
(ROOT/'verification/delivery4-status.json').write_text(json.dumps(status,indent=2),encoding='utf8')
p=ROOT/'README.md';text=p.read_text(encoding='utf-8-sig')
text=re.sub(r'\*\*Estado del fuente:\*\*[^\n]+','**Estado del fuente:** publicada la corrección del manifiesto para instalación en Brave el 24 de octubre de 2026, versión `'+identifier+'`. El resultado del icono en un dispositivo Android físico todavía no está verificado. Respaldo real y comprobación en Brave conservan el aplazamiento indicado por el propietario.',text,count=1)
if '## Cookie del manifiesto · Brave Android' not in text:
    text+='\n\n## Cookie del manifiesto · Brave Android\n\nLa petición del manifiesto sin cookies recibía HTML de la comprobación de InfinityFree, aunque los PNG eran públicos. El enlace ahora declara `crossorigin="use-credentials"`. La verificación pública reproduce la petición indicada por el HTML sin ejecutar una segunda comprobación del hosting: antes obtenía HTML y después obtiene el JSON correcto. Las pruebas generales pasaron; la instalación nativa del icono requiere confirmación en Android real. [Detalles](MOVIL-2026-10-24.md).\n'
p.write_text(text,encoding='utf8')
p=ROOT/'MEJORAS.md';text=p.read_text(encoding='utf-8-sig')
if '## Instalación Brave · cookie del hosting' not in text:
    text+='\n\n## Instalación Brave · cookie del hosting\n\nPublicación `'+identifier+'`. Corregida la omisión de la cookie en la solicitud del manifiesto. Se añadió una verificación que no oculta el bloqueo del hosting resolviendo de nuevo su comprobación. El acceso directo todavía debe comprobarse en Brave Android real.\n'
p.write_text(text,encoding='utf8')
subprocess.run([sys.executable,'verification/package_final.py'],cwd=ROOT,check=True)
_,manifest=release.published_files(identifier)
artifact={'ok':True,'release':identifier,'published':True,'source_matches_final_tests':True,
    'verified_release_files':len(manifest['files']),'verified_public_files':public['verified_public_files'],
    'javascript_suites':status['javascript_suites'],'http_suites':status['http_suites'],'mysql_checks':status['mysql_checks'],
    'install_manifest_verified':True,'physical_android_tested':False,'deferred_by_owner':status['deferred_by_owner'],
    'source_archive_sha256':hashlib.sha256((ROOT/'artifacts/YomaTVWeb-fuente.zip').read_bytes()).hexdigest()}
(ROOT/'verification/delivery4-artifact-check.json').write_text(json.dumps(artifact,indent=2),encoding='utf8')
print(json.dumps({'ok':True,'release':identifier,'published':True,'installation_metadata_verified':True,
    'physical_android_tested':False,'pending':status['pending']}))
