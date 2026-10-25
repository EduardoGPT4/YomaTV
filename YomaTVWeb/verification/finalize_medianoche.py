"""Finalize the design handoff only after this exact source is verified and live."""
import hashlib,json,re,subprocess,sys,time
from pathlib import Path
import delivery4_evidence as evidence
ROOT=evidence.ROOT
sys.path.insert(0,str(ROOT));import release
identifier='medianoche-20261024-1'
status=evidence.external_checks(evidence.read_report('delivery4-status.json'))
deployment=evidence.read_report('delivery4-deployment.json')
public=evidence.read_report('delivery4-published-check.json')
browser=evidence.read_report('medianoche-browser-check.json')
current=evidence.application_hashes()
assert deployment.get('release')==identifier and public.get('release')==identifier
assert status['published'] and not status['pending']
assert browser.get('ok') and browser.get('application_sha256')==current
assert all(status['source_sha256'].get(p)==sha for p,sha in current.items())
status.update(at=int(time.time()),published_release=identifier,local_browser_checks_ok=True,
              browser_evidence='medianoche-browser-check.json',brave_verified=False)
(ROOT/'verification/delivery4-status.json').write_text(json.dumps(status,indent=2),encoding='utf8')
p=ROOT/'README.md';text=p.read_text(encoding='utf-8-sig')
text=re.sub(r'\*\*Estado del fuente:\*\*[^\n]+','**Estado del fuente:** publicado el diseño Medianoche el 24 de octubre de 2026, versión `'+identifier+'`. Respaldo real de producción y comprobación en Brave conservan el aplazamiento indicado por el propietario.',text,count=1)
note='''

## Diseño Medianoche · 24 de octubre de 2026

Navegación superior y móvil inferior, tipografía editorial con fuentes locales, paleta tinta/papel/bermellón, catálogo de pósters ampliados, fichas con progreso real y un sistema visual coherente para todos los apartados. [Cambios y alcance](MEDIANOCHE-2026-10-24.md).

La versión pasó 13 suites locales, 20 JavaScript, 13 HTTP y 15 comprobaciones MariaDB. La revisión visual recorrió diez apartados en escritorio y móvil, y comprobó también 320 px, 768 px, tema claro, foco y controles sobre video sintético. Se verificaron la versión pública, sus archivos y la reversión de código. No se alteró una cuenta MAL real ni se descargaron capítulos reales.
'''
if '## Diseño Medianoche · 24 de octubre de 2026' not in text:text+=note
p.write_text(text,encoding='utf8')
p=ROOT/'MEJORAS.md';text=p.read_text(encoding='utf-8-sig')
if '## Medianoche · 24 de octubre de 2026' not in text:
    text+='\n\n## Medianoche · 24 de octubre de 2026\n\nPublicación `'+identifier+'`. Diseño completo y fuentes locales; detalles en [MEDIANOCHE-2026-10-24.md](MEDIANOCHE-2026-10-24.md). Las funciones y los datos existentes se conservan.\n'
p.write_text(text,encoding='utf8')
subprocess.run([sys.executable,'verification/package_final.py'],cwd=ROOT,check=True)
files,manifest=release.published_files(identifier)
artifact={'ok':True,'release':identifier,'verified_release_files':len(manifest['files']),
  'source_matches_final_tests':True,'source_archive_sha256':hashlib.sha256((ROOT/'artifacts/YomaTVWeb-fuente.zip').read_bytes()).hexdigest(),
  'published':True,'verified_public_files':public['verified_public_files'],'http_suites':status['http_suites'],
  'javascript_suites':status['javascript_suites'],'mysql_checks':status['mysql_checks'],'deferred_by_owner':status['deferred_by_owner'],
  'implementation':'MEDIANOCHE-2026-10-24.md','screenshot':'verification/medianoche-home-desktop.jpg'}
(ROOT/'verification/delivery4-artifact-check.json').write_text(json.dumps(artifact,indent=2),encoding='utf8')
print(json.dumps({'ok':True,'published':True,'release':identifier,'pending':status['pending'],
                  'archive_bytes':(ROOT/'artifacts/YomaTVWeb-fuente.zip').stat().st_size}))
