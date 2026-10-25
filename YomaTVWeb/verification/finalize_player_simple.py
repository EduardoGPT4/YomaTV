"""Finish documentation and package only after the simplified player is live."""
import hashlib,json,re,subprocess,sys,time
from pathlib import Path
import delivery4_evidence as evidence
ROOT=evidence.ROOT;sys.path.insert(0,str(ROOT));import release
identifier='player-simple-20261023-1'
status=evidence.external_checks(evidence.read_report('delivery4-status.json'))
deployment=evidence.read_report('delivery4-deployment.json');public=evidence.read_report('delivery4-published-check.json')
assert deployment.get('release')==identifier and public.get('release')==identifier
assert status['published'] and not status['pending']
assert evidence.read_report('player-simple-browser-check.json').get('ok')
assert evidence.read_report('project-review-findings.json').get('ok')
status.update(at=int(time.time()),published_release=identifier,local_browser_checks_ok=True,
    browser_evidence='player-simple-browser-check.json',brave_verified=False,
    deployment_tool_checks=evidence.read_report('release-check.json')['count'])
status['source_sha256']['release.py']=hashlib.sha256((ROOT/'release.py').read_bytes()).hexdigest()
(ROOT/'verification/delivery4-status.json').write_text(json.dumps(status,indent=2),encoding='utf8')
p=ROOT/'README.md';text=p.read_text(encoding='utf-8-sig')
text=re.sub(r'\*\*Estado del fuente:\*\*[^\n]+',
    '**Estado del fuente:** publicada la simplificación del reproductor el 23 de octubre de 2026, versión `'+identifier+'`. Respaldo de producción y comprobación en Brave conservan el aplazamiento indicado por el propietario.',text,count=1)
note='''

## Reproductor simplificado · 23 de octubre de 2026

El siguiente capítulo queda siempre activado, con aviso de ocho segundos y cancelación para esa ocasión. También funciona en pestañas ocultas cuando el navegador permite ejecutar el temporizador. Se retiraron las casillas de siguiente automático y preferencias por anime, el botón de iniciar revisionado y todo el panel de diagnóstico. Volumen, velocidad, servidor e idioma se guardan globalmente. Las preferencias antiguas desactivadas se normalizan a la nueva política; se conservan los datos de revisionados anteriores y se puede volver al seguimiento de MAL desde la ficha.

El siguiente episodio pide reproducción al recibir datos válidos del video. La elección de reanudar una posición guardada se conserva. Funciona con la señal de final de MP4Upload y la extensión; los otros servidores y las políticas de autoplay del navegador mantienen sus limitaciones. Las consultas nuevas de servidores también respetan el idioma y servidor preferidos. Se muestran avisos breves para errores de posición y sesiones reemplazadas.

Pasaron doce suites HTTP (dos hallazgos de revisión reproducidos con MAL ficticio), diecisiete JavaScript, trece suites locales y once comprobaciones MariaDB. En el navegador integrado se comprobó con video sintético el final del capítulo 6, el aviso de ocho segundos, el paso al 7 y su reproducción sin otro clic. No se modificó una lista MAL real ni se descargaron capítulos reales. El publicador finaliza los hashes de iconos después de verificar los archivos de código, comprobando que la recompresión diferida del alojamiento conserve píxeles y colores.

La revisión completa y las recomendaciones pendientes están en [REVISION-WEB-2026-10-23.md](REVISION-WEB-2026-10-23.md). Se distingue lo aplicado de lo recomendado.
'''
if '## Reproductor simplificado · 23 de octubre de 2026' not in text:text+=note
p.write_text(text,encoding='utf8')
p=ROOT/'MEJORAS.md';text=p.read_text(encoding='utf-8-sig')
if '## Reproductor simplificado · 23 de octubre de 2026' not in text:
    text+='\n\n## Reproductor simplificado · 23 de octubre de 2026\n\nSiguiente capítulo siempre activado, controles opcionales y diagnóstico retirados, preferencias globales y aviso breve de cuenta atrás. Prueba visual y de reproducción con video sintético; publicación `'+identifier+'` verificada. La revisión completa y sus recomendaciones pendientes están en `REVISION-WEB-2026-10-23.md`.\n'
p.write_text(text,encoding='utf8')
subprocess.run([sys.executable,'verification/package_final.py'],cwd=ROOT,check=True)
files,manifest=release.published_files(identifier)
artifact={'ok':True,'release':identifier,'verified_release_files':len(manifest['files']),
    'source_matches_final_tests':True,'source_archive_sha256':hashlib.sha256((ROOT/'artifacts/YomaTVWeb-fuente.zip').read_bytes()).hexdigest(),
    'published':True,'verified_public_files':public['verified_public_files'],
    'http_suites':status['http_suites'],'javascript_suites':status['javascript_suites'],'mysql_checks':status['mysql_checks'],
    'deferred_by_owner':status['deferred_by_owner'],'review':'REVISION-WEB-2026-10-23.md'}
(ROOT/'verification/delivery4-artifact-check.json').write_text(json.dumps(artifact,indent=2),encoding='utf8')
print(json.dumps({'ok':True,'published':True,'release':identifier,'pending':status['pending'],'review':artifact['review']}))
