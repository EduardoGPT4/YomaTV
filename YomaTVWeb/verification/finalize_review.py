"""Finalize documentation only after this exact source has passed and is live."""
import hashlib,json,re,subprocess,sys,time
from pathlib import Path
import delivery4_evidence as evidence
ROOT=evidence.ROOT;sys.path.insert(0,str(ROOT));import release
identifier='improvements-20261023-1'
status=evidence.external_checks(evidence.read_report('delivery4-status.json'))
deployment=evidence.read_report('delivery4-deployment.json');public=evidence.read_report('delivery4-published-check.json')
assert deployment.get('release')==identifier and public.get('release')==identifier
assert status['published'] and not status['pending']
current=evidence.application_hashes();browser=evidence.read_report('review-browser-check.json')
assert browser.get('ok') and browser.get('application_sha256')==current
assert evidence.read_report('player-layout-check.json').get('ok')
assert all(status.get('source_sha256',{}).get(p)==h for p,h in current.items())
status.update(at=int(time.time()),published_release=identifier,local_browser_checks_ok=True,browser_evidence='review-browser-check.json',brave_verified=False,
    javascript_suites=len(list((ROOT/'verification').glob('test_*.js'))),extra_js_evidence='player-layout-check.json')
(ROOT/'verification/delivery4-status.json').write_text(json.dumps(status,indent=2),encoding='utf8')
p=ROOT/'README.md';text=p.read_text(encoding='utf-8-sig');text=re.sub(r'\*\*Estado del fuente:\*\*[^\n]+','**Estado del fuente:** publicada la implementación de la revisión el 23 de octubre de 2026, versión `'+identifier+'`. Respaldo real de producción y comprobación en Brave conservan el aplazamiento indicado por el propietario.',text,count=1)
note='''

## Revisión implementada · 23 de octubre de 2026

Confirmación de vínculos antes de enviar progreso a MAL, capacidad reservada para servidores y ejecutor central por visitas, mensajes y estados reales de tareas, paginación de cola bajo demanda y fallos persistentes informados por la PC. Reanudación exacta en portada, escenario persistente, búsqueda de capítulo, intro por tramo, escenas privadas y recorrido de saga. Colecciones, bandeja MAL, radio sincronizada con control de conflictos, exportación completa por bloques, modo compartido, guía inicial, actualización PWA diferida, caché con concesión y diagnóstico sin secretos.

Los cambios y sus límites se detallan en [CAMBIOS-REVISION-2026-10-23.md](CAMBIOS-REVISION-2026-10-23.md). El comando actual de comprobación/publicación y la recuperación están en [OPERACION.md](OPERACION.md). La revisión original se conserva como diagnóstico previo.

La fuente publicada pasó 13 suites HTTP con MAL ficticio, 19 suites JavaScript, 13 suites locales y 15 comprobaciones MariaDB. El navegador integrado verificó colección, intro, escenas, búsqueda, 80 % y siguiente con video sintético, reanudación y favoritos musicales persistidos, además de la cancelación y las páginas de una cola ficticia de ochenta capítulos. No se descargaron capítulos reales ni se cambió una cuenta MAL real. Se verificaron la salud pública, archivos de la versión y reversión de código en el alojamiento.

Sin visitas ni un ejecutor externo compatible con InfinityFree, la cola de actualización espera. Las versiones de PC que no informan intentos se indican como tales. Brave y la copia real de producción siguen aplazados; la restauración completa se probó en bases aisladas. El contenedor de pantalla completa se conserva, pero la superficie nativa del navegador integrado no sustituye la prueba en Brave.
'''
if '## Revisión implementada · 23 de octubre de 2026' not in text:text+=note
p.write_text(text,encoding='utf8')
p=ROOT/'MEJORAS.md';text=p.read_text(encoding='utf-8-sig')
if '## Revisión implementada · 23 de octubre de 2026' not in text:text+='\n\n## Revisión implementada · 23 de octubre de 2026\n\nPublicación `'+identifier+'`. Cambios completos en `CAMBIOS-REVISION-2026-10-23.md`; operación y copias en `OPERACION.md`. Conserva los aplazamientos del respaldo real de producción y Brave.\n'
p.write_text(text,encoding='utf8')
p=ROOT/'REVISION-WEB-2026-10-23.md';text=p.read_text(encoding='utf8')
notice='> Actualización posterior: las recomendaciones se implementaron en `improvements-20261023-1`. Consulta [los cambios y límites](CAMBIOS-REVISION-2026-10-23.md). Este documento conserva el diagnóstico previo.\n\n'
if notice not in text:text=text.replace('\n\n','\n\n'+notice,1)
p.write_text(text,encoding='utf8')
subprocess.run([sys.executable,'verification/package_final.py'],cwd=ROOT,check=True)
files,manifest=release.published_files(identifier)
artifact={'ok':True,'release':identifier,'verified_release_files':len(manifest['files']),'source_matches_final_tests':True,
  'source_archive_sha256':hashlib.sha256((ROOT/'artifacts/YomaTVWeb-fuente.zip').read_bytes()).hexdigest(),'published':True,
  'verified_public_files':public['verified_public_files'],'http_suites':status['http_suites'],'javascript_suites':status['javascript_suites'],'mysql_checks':status['mysql_checks'],
  'deferred_by_owner':status['deferred_by_owner'],'implementation':'CAMBIOS-REVISION-2026-10-23.md','screenshot':'verification/review-player-final.jpg'}
(ROOT/'verification/delivery4-artifact-check.json').write_text(json.dumps(artifact,indent=2),encoding='utf8')
print(json.dumps({'ok':True,'published':True,'release':identifier,'pending':status['pending'],'archive_bytes':(ROOT/'artifacts/YomaTVWeb-fuente.zip').stat().st_size}))
