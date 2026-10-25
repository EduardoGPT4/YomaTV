"""Update delivery documentation only after the real activation and public checks pass."""
import hashlib,json,re,time
from pathlib import Path
import delivery4_evidence as evidence

ROOT=Path(__file__).resolve().parents[1]
deployment=evidence.read_report('delivery4-deployment.json')
public=evidence.read_report('delivery4-published-check.json')
rollback=evidence.read_report('delivery4-rollback-check.json')
assert deployment.get('ok') and deployment.get('release')=='watch-room-20261022-1'
assert public.get('ok') and public.get('release')==deployment['release']
assert rollback.get('ok') and rollback.get('final_release')==deployment['release']
current=evidence.application_hashes()
for name in ['delivery4-http-suite.json','mysql-check.json']:
    report=evidence.read_report(name);assert report.get('ok') and report.get('application_sha256')==current
assert public['application_sha256']==current
status=evidence.external_checks(evidence.read_report('delivery4-status.json'))
assert status['published'] and not status['pending']
status['source_sha256']['release.py']=hashlib.sha256((ROOT/'release.py').read_bytes()).hexdigest()
status.update(at=int(time.time()),published_release=deployment['release'],local_browser_checks_ok=True,
    browser_evidence='watch-room-browser-check.json',brave_verified=False,
    deployment_tool_checks=evidence.read_report('release-check.json')['count'])
status.pop('blocker',None)
(ROOT/'verification/delivery4-status.json').write_text(json.dumps(status,indent=2),encoding='utf8')

readme=(ROOT/'README.md').read_text(encoding='utf-8-sig')
readme=re.sub(r'\*\*Estado del fuente:\*\*[^\n]+',
    '**Estado del fuente:** entrega 4 y Sala de anime publicadas el 22 de octubre de 2026, versión `watch-room-20261022-1`. Respaldo de producción y comprobación en Brave aplazados por indicación del propietario.',readme,count=1)
readme=readme.replace('Las entregas 1–3 están publicadas.','Las entregas 1–4 están publicadas.')
readme=readme.replace('## Entrega 4 · infraestructura y seguridad · fuente preparado','## Entrega 4 · infraestructura y seguridad · publicada')
readme=re.sub(r'Esta sección describe el \*\*código local\*\*.*?\n\n### Peticiones',
    'Publicada junto con la Sala de anime. Pasaron 13 suites locales, 17 JavaScript, 11 HTTP y 11 comprobaciones MariaDB 11.4.13, además de la revisión visual local con video sintético. La activación, la reversión a `stable-delivery3`, el regreso a la versión nueva y los archivos públicos se verificaron en InfinityFree. El propietario pidió aplazar el respaldo real y Brave; esas comprobaciones no se presentan como realizadas. La limitación de suscripciones `.ics` externas continúa.\n\n### Peticiones',readme,count=1,flags=re.S)
readme=readme.replace('Se probó activación/reversión usando un sistema de archivos desechable; **falta verificar el comportamiento real de FTPS e InfinityFree**.',
    'La activación/reversión se comprobó primero en un sistema de archivos desechable y después en InfinityFree, verificando la salud al volver a ambas versiones.')
readme=re.sub(r'Antes de activar, el publicador exige.*?\n\nEn este workspace,',
    'Por defecto, antes de activar el publicador exige una copia cifrada verificada de las últimas 24 horas. `tools/remote_backup.py` usa un endpoint temporal con token aleatorio, vencimiento y limpieza. Guarda únicamente copia cifrada y clave local fuera del paquete. En esta publicación el propietario pidió omitir la copia y se usó explícitamente `--skip-database-backup`; el recibo registra `waived_by_owner`. No existe una copia de producción verificada para esta entrega.\n\nEn este workspace,',readme,count=1,flags=re.S)
readme=readme.replace('Está preparada, aún sin ejecutar contra la entrega 4.','Se ejecutó contra `watch-room-20261022-1` y comprobó versión, esquema, catálogo, permisos, archivos públicos, service worker y extensión.')
readme=readme.replace('y **16 JavaScript**.','y **17 JavaScript**.')
readme=readme.replace('Pasaron las diez suites HTTP de `run_delivery1.py`','Pasaron las once suites HTTP de `run_delivery1.py`')
readme=readme.replace('`run_mysql.py` ejecutó diez comprobaciones','`run_mysql.py` ejecutó once comprobaciones')
readme=readme.replace('Respaldo real, FTPS/reversión, comprobación pública y Brave/extensión/PiP siguen abiertos en el plan.',
    'FTPS/reversión y la comprobación pública pasaron; respaldo real y Brave/extensión/PiP quedan aplazados por el propietario. La Sala de anime tiene sus evidencias adicionales debajo.')
(ROOT/'README.md').write_text(readme,encoding='utf8')

plan=(ROOT/'PLAN-4-ENTREGAS.md').read_text(encoding='utf-8-sig')
plan=re.sub(r'\*\*Código implementado; validación local, HTTP y MariaDB terminada; publicación pendiente\.\*\*.*?\n\n- \[x\] Migraciones',
    '**Publicada y verificada el 22 de octubre de 2026.** Trece suites locales, diecisiete JavaScript, once HTTP y once comprobaciones con MariaDB 11.4.13. Publicación por FTPS, hashes de los archivos públicos, esquema real, activación, reversión y regreso a `watch-room-20261022-1` comprobados. La revisión visual local usó video sintético y MAL ficticio. El propietario aplazó el respaldo de producción y Brave; la copia real no se obtuvo.\n\n- [x] Migraciones',plan,count=1,flags=re.S)
plan=plan.replace('- [ ] Activar la publicación atómica y comprobar FTPS/reversión en el alojamiento. Publicador, hashes, versiones inmutables y reversión local implementados y probados.',
    '- [x] Activar la publicación atómica y comprobar FTPS/reversión en el alojamiento. Versiones inmutables, manifiestos, reversión a la entrega 3 y regreso a la versión nueva comprobados por HTTPS.')
plan=plan.replace('La copia de producción sigue pendiente antes de publicar.','La copia de producción se aplazó por indicación del propietario; no se presenta como realizada.')
plan=plan.replace('diez suites HTTP y diez comprobaciones MariaDB ejecutadas con éxito.','once suites HTTP y once comprobaciones MariaDB ejecutadas con éxito.')
plan=plan.replace('- [ ] Verificación real en Brave de extensión, permisos locales, reproducción y PiP: la revisión automática impidió consultar el navegador.',
    '- [ ] Verificación real en Brave de extensión, permisos locales, reproducción y PiP: aplazada por el propietario el 22 de octubre. La nueva página se revisó en el navegador integrado, sin atribuirlo a Brave.')
(ROOT/'PLAN-4-ENTREGAS.md').write_text(plan,encoding='utf8')

improvements=(ROOT/'MEJORAS.md').read_text(encoding='utf-8-sig')
improvements=improvements.replace('La entrega 3 está publicada. La entrega 4 está implementada y pasó las comprobaciones locales, HTTP y MariaDB. El respaldo real, FTPS y Brave siguen pendientes por el fallo de la revisión automática. El plan distingue las casillas terminadas de estos pendientes.',
    'Las cuatro entregas están publicadas, junto con la Sala de anime. La activación, reversión, MySQL y archivos públicos se verificaron en InfinityFree. El respaldo real y Brave están aplazados por el propietario.')
improvements=improvements.replace('La entrega 4 está preparada localmente y aún no publicada;','La entrega 4 está publicada;')
improvements=improvements.replace('## Entrega 4 · fuente preparado, sin publicar','## Entrega 4 · publicada el 22 de octubre de 2026')
improvements=re.sub(r'Pasaron 13 suites locales, 16 JavaScript, diez suites HTTP.*?README.md detalla comandos, evidencias y límites\.',
    'Pasaron 13 suites locales, 17 JavaScript, once suites HTTP y once comprobaciones MariaDB. Se verificaron la activación y la reversión real por FTPS/HTTPS. No se creó una copia de producción; se aplazó por indicación del propietario, junto con Brave. Las pruebas de MAL usaron un proveedor ficticio y no descargaron capítulos reales. README.md detalla comandos, evidencias y límites.',improvements,count=1,flags=re.S)
improvements+='\n\n## Sala de anime\n\nPágina completa con video amplio, navegación, servidores por idioma, capítulos a la derecha y marcas de visto. El ojo permite marcar directamente en MAL sin esperar al 80 %, con confirmación y reintentos persistentes. Debajo de los capítulos, «De esta saga» aparece seleccionada y combina relaciones aprobadas con títulos parecidos identificados como sugerencias; «Por géneros» usa el catálogo público completo de AnimeAV1. En móvil las secciones se apilan sin desbordamiento.\n'
(ROOT/'MEJORAS.md').write_text(improvements,encoding='utf8')
print(json.dumps({'ok':True,'published':status['published'],'release':deployment['release'],'pending':status['pending'],'deferred_by_owner':status['deferred_by_owner']}))
