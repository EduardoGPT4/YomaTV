"""Finalize this mobile update only after current tests and publication pass."""
import hashlib,json,re,subprocess,sys,time
from pathlib import Path
import delivery4_evidence as evidence

ROOT=evidence.ROOT
sys.path.insert(0,str(ROOT))
import release

identifier='mobile-20261024-1'
status=evidence.external_checks(evidence.read_report('delivery4-status.json'))
deployment=evidence.read_report('delivery4-deployment.json')
public=evidence.read_report('delivery4-published-check.json')
current=evidence.application_hashes()
assert deployment.get('release')==identifier and public.get('release')==identifier
assert status['published'] and not status['pending']
assert all(status['source_sha256'].get(p)==sha for p,sha in current.items())
assert evidence.read_report('mobile-player-check.json').get('ok')
assert evidence.read_report('player-controller-check.json').get('ok')
assert evidence.read_report('notification-panel-check.json').get('ok')
assert (ROOT/'verification/mobile-player-final.jpg').is_file()
browser={
    'ok':True,'at':int(time.time()),'release':identifier,
    'method':'IAB responsive preview with a synthetic video; test-only mobile-mode selector. Orientation API behavior covered by VM tests.',
    'sizes_checked':[320,390,768,1440],
    'notifications':{'bell_keeps_watch_route':True,'scrollable_dropdown':True,'mark_all_verified_in_fixture':True,
                     'sizes_checked':[320,390,1440],'screenshot':'verification/notification-panel-desktop.jpg'},
    'mobile':{'native_video_controls':True,'provider_controls_overridden':False,'custom_bar_hidden':True,
              'desktop_extension_help_hidden':True,'horizontal_overflow':False},
    'desktop':{'custom_bar_visible':True,'provider_controls_overridden':True,'console_errors':[]},
    'orientation_api_checks':evidence.read_report('mobile-player-check.json')['count'],
    'physical_phone_tested':False,'home_screen_installation_tested':False,'brave_tested':False,
    'screenshot':'verification/mobile-player-final.jpg',
    'ui_source_sha256':{p:current[p] for p in ['htdocs/index.php','htdocs/assets/player-template.js',
        'htdocs/assets/player-controller.js','htdocs/assets/player-view.js','htdocs/assets/medianoche.css',
        'htdocs/assets/notification-panel.js','htdocs/assets/feature-ui.js']},
}
(ROOT/'verification/mobile-browser-check.json').write_text(json.dumps(browser,indent=2),encoding='utf8')
status.update(at=int(time.time()),published_release=identifier,local_browser_checks_ok=True,
              browser_evidence='mobile-browser-check.json',brave_verified=False,
              physical_phone_tested=False)
(ROOT/'verification/delivery4-status.json').write_text(json.dumps(status,indent=2),encoding='utf8')
p=ROOT/'README.md';text=p.read_text(encoding='utf-8-sig')
text=re.sub(r'\*\*Estado del fuente:\*\*[^\n]+',
    '**Estado del fuente:** publicados los ajustes móviles el 24 de octubre de 2026, versión `'+identifier+'`. Respaldo real de producción y comprobación en Brave conservan el aplazamiento indicado por el propietario.',text,count=1)
if '## Ajustes móviles · 24 de octubre de 2026' not in text:
    text+='\n\n## Ajustes móviles · 24 de octubre de 2026\n\nIconos de instalación para Android y Apple, manifiesto estable y reproducción móvil con los controles originales de MP4Upload. La pantalla completa solicita orientación horizontal y la libera al salir, cuando el sistema lo permite. La campana abre un panel de notificaciones sobre la vista actual, con estados, desplazamiento y marcado como leídas. [Alcance y límites de la comprobación](MOVIL-2026-10-24.md).\n\nPasaron 13 suites locales, 22 JavaScript, 13 HTTP y 15 comprobaciones MariaDB, además de la verificación de la publicación. La interfaz se revisó con video sintético en el navegador integrado; no se comprobó la rotación física ni la instalación en un teléfono real.\n'
p.write_text(text,encoding='utf8')
p=ROOT/'MEJORAS.md';text=p.read_text(encoding='utf-8-sig')
if '## Móvil · 24 de octubre de 2026' not in text:
    text+='\n\n## Móvil · 24 de octubre de 2026\n\nPublicación `'+identifier+'`: logo para accesos a inicio, controles originales de MP4Upload en teléfonos y solicitud de bloqueo horizontal durante la pantalla completa. [Detalles](MOVIL-2026-10-24.md).\n'
p.write_text(text,encoding='utf8')
subprocess.run([sys.executable,'verification/package_final.py'],cwd=ROOT,check=True)
files,manifest=release.published_files(identifier)
artifact={'ok':True,'release':identifier,'verified_release_files':len(manifest['files']),
    'source_matches_final_tests':True,'source_archive_sha256':hashlib.sha256((ROOT/'artifacts/YomaTVWeb-fuente.zip').read_bytes()).hexdigest(),
    'published':True,'verified_public_files':public['verified_public_files'],'http_suites':status['http_suites'],
    'javascript_suites':status['javascript_suites'],'mysql_checks':status['mysql_checks'],
    'deferred_by_owner':status['deferred_by_owner'],'implementation':'MOVIL-2026-10-24.md',
    'screenshot':'verification/mobile-player-final.jpg','physical_phone_tested':False}
(ROOT/'verification/delivery4-artifact-check.json').write_text(json.dumps(artifact,indent=2),encoding='utf8')
print(json.dumps({'ok':True,'published':True,'release':identifier,'pending':status['pending'],
    'archive_bytes':(ROOT/'artifacts/YomaTVWeb-fuente.zip').stat().st_size}))
