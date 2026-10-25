"""Record the player quota fix only after its real release and checks have passed."""
import hashlib,json,re,subprocess,sys,time
import delivery4_evidence as evidence
ROOT=evidence.ROOT
deployment=evidence.read_report('delivery4-deployment.json')
public=evidence.read_report('delivery4-published-check.json')
rollback=evidence.read_report('delivery4-rollback-check.json')
release='watch-room-20261022-2'
assert deployment.get('ok') and deployment['release']==release
assert public.get('ok') and public['release']==release
assert rollback.get('ok') and rollback['final_release']==release
current=evidence.application_hashes()
for name in ['delivery4-http-suite.json','mysql-check.json','delivery4-published-check.json']:
    report=evidence.read_report(name)
    assert report.get('ok') and report.get('application_sha256')==current,name
status=evidence.external_checks(evidence.read_report('delivery4-status.json'))
assert status['published'] and not status['pending']
status.update(at=int(time.time()),published_release=release,
    player_quota_regression_verified=True,brave_verified=False)
# The visual preview belongs to the preceding page release; do not claim a new browser run.
status['previous_browser_evidence']='watch-room-browser-check.json'
status['local_browser_checks_ok']=False
status.pop('browser_evidence',None)
(ROOT/'verification/delivery4-status.json').write_text(json.dumps(status,indent=2),encoding='utf8')

readme=(ROOT/'README.md').read_text(encoding='utf-8-sig')
readme=re.sub(r'\*\*Estado del fuente:\*\*[^\n]+',
    '**Estado del fuente:** entrega 4 y Sala de anime publicadas el 22 de octubre de 2026; corrección del límite del reproductor publicada en `'+release+'`. Respaldo de producción y comprobación en Brave aplazados por indicación del propietario.',readme,count=1)
note='''

## Corrección del límite del reproductor · 22 de octubre de 2026

Abrir un capítulo ya no ejecuta el scraper: devuelve los servidores guardados y la sesión de reproducción. La consulta de servidores se hace por separado mediante `player_servers` (POST, CSRF y administrador). Si no hay servidores y los datos caducaron, la página la solicita automáticamente; un límite del scraper devuelve el estado de espera y su próxima hora permitida, sin sustituir la página por un error. Solo hay un temporizador, cancelado al cambiar de capítulo, salir o cambiar de cuenta. Los servidores ya disponibles pueden reproducirse durante la espera; actualizar sus datos conserva el iframe y la sesión activa. Los usuarios normales disponen de «Solicitar servidores», que reutiliza la cola central y sus permisos/cuotas. El mantenimiento automático de la pestaña se pausa mientras se ve un capítulo.

Las regresiones HTTP simulan el cupo global agotado con caché y sin caché, comprueban el formato seguro de los enlaces, los permisos y que actualizar servidores no renueve la sesión de reproducción. Las pruebas JavaScript comprueban el temporizador cancelable, que no se sustituya el video activo y que una cuenta normal solicite trabajo central. Pasaron las once suites HTTP, diecisiete JavaScript, trece locales y once comprobaciones MariaDB; la publicación y los archivos públicos se verificaron por HTTPS. Las pruebas usaron cuentas locales y MAL ficticio, sin descargar capítulos reales. No se repitió la revisión visual en Brave.
'''
if '## Corrección del límite del reproductor' not in readme:readme+=note
(ROOT/'README.md').write_text(readme,encoding='utf8')
for name in ['MEJORAS.md','PLAN-4-ENTREGAS.md']:
    p=ROOT/name;text=p.read_text(encoding='utf-8-sig')
    if '## Corrección del límite del reproductor' not in text:
        text+='\n\n## Corrección del límite del reproductor\n\nPublicada en `'+release+'`: la página sirve su caché sin hacer scraping. La actualización separada respeta el tiempo de espera, conserva la reproducción y ofrece solicitudes centrales a cuentas normales. Regresiones de cupo agotado y reintento comprobadas; respaldo de producción y Brave conservan el aplazamiento indicado por el propietario.\n'
    p.write_text(text,encoding='utf8')
subprocess.run([sys.executable,'verification/package_final.py'],cwd=ROOT,check=True)
sys.path.insert(0,str(ROOT))
import release as publisher
files,manifest=publisher.published_files(release)
artifact={'ok':True,'release':release,'verified_release_files':len(manifest['files']),
    'source_matches_final_tests':True,'source_archive_sha256':hashlib.sha256((ROOT/'artifacts/YomaTVWeb-fuente.zip').read_bytes()).hexdigest(),
    'published':True,'verified_public_files':public['verified_public_files'],
    'normalized_lossless_icons':sorted(manifest.get('normalization',{})),
    'http_suites':status['http_suites'],'javascript_suites':status['javascript_suites'],
    'mysql_checks':status['mysql_checks'],'deferred_by_owner':status['deferred_by_owner']}
(ROOT/'verification/delivery4-artifact-check.json').write_text(json.dumps(artifact,indent=2),encoding='utf8')
print(json.dumps({'ok':True,'published':True,'release':release,'pending':status['pending']}))
