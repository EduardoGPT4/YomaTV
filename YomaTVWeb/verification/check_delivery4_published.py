"""Anonymous checks after activation; never changes accounts, queues or MAL lists."""
import argparse
import hashlib
import http.cookiejar
import io
import json
import re
import secrets
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path
from delivery4_evidence import application_hashes
from probe_install_manifest import probe as probe_install_manifest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import release

BASE = 'https://hk-br035.gt.tc/seasonav1/'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--release', required=True)
    identifier = release.valid_id(parser.parse_args().release)
    files, manifest = release.published_files(identifier)
    checks = []
    nonce = secrets.token_hex(8)
    client = release.PublicClient()
    class PublicResponse(io.BytesIO):
        def __init__(self,status,data):
            super().__init__(data);self.status=status

    def request(path=''):
        separator = '&' if '?' in path else '?'
        status,data,_=client.get(path+separator+'verification='+nonce)
        return PublicResponse(status,data)

    def read(path='', status=200):
        with request(path) as response:
            if response.status != status:
                raise RuntimeError(f'Unexpected HTTP status for {path}: {response.status}')
            return response.read()

    page = read().decode('utf8')
    health = json.loads(read('release-health.php'))
    assert health.get('ok') and health.get('release') == identifier
    assert health.get('schema') == '20261023.1'
    checks.append('active_release_and_mysql_schema_match')
    prefix = f'releases/{identifier}/'
    for name in ['transport.js', 'dom-renderer.js', 'player-view.js', 'health-ui.js']:
        assert prefix + 'assets/' + name + '?v=' in page, name
    assert 'Saltar al contenido' in page
    checks.append('html_loads_immutable_delivery4_modules')

    def api(action, status=200, **params):
        data = json.loads(read('actions.php?' + urllib.parse.urlencode({'action': action, **params}), status))
        def private_keys(value):
            if isinstance(value, dict):
                if set(value) & {'token_cipher', 'client_secret', 'access_token', 'refresh_token'}:
                    return True
                return any(private_keys(item) for item in value.values())
            return isinstance(value, list) and any(private_keys(item) for item in value)
        assert not private_keys(data), action
        return data

    state = api('state')['data']
    assert state['user'] is None and not state['jobs']
    checks.append('anonymous_state_has_no_account_or_queue')
    catalog = api('catalog')['catalog']
    assert catalog['all_total'] >= 4485
    checks.append('complete_catalog_survives_migration')
    for action, params in [('system_health', {}), ('presence', {'slug': 'naruto'})]:
        assert not api(action, 401, **params)['ok']
    for action in ['player', 'queue_preview', 'player_save', 'player_servers', 'mal_link_batch', 'progress_reconcile']:
        assert not api(action, 405)['ok']
    read('backup.php', 405)
    checks.append('admin_player_backup_and_mutation_guards_enforced')

    public = [name for name in manifest['files'] if name.startswith(('assets/', 'downloads/'))
              or name in ['manifest.webmanifest', 'offline.html']]
    for name in public:
        assert read(prefix + name) == files[name], name
        time.sleep(.08)
    checks.append('all_immutable_client_files_match_verified_bytes')
    assert read('service-worker.php') == files['sw.js']
    assert json.loads(files['manifest.webmanifest'])['scope'] == '../../'
    checks.append('root_worker_and_manifest_scope_match_release')
    status,metadata,headers=client.get('app-manifest.php?verification='+nonce)
    assert status==200 and 'application/manifest+json' in headers
    install=json.loads(metadata)
    assert install['id']==install['scope']=='/seasonav1/' and install['start_url']=='/seasonav1/#discover'
    assert any(i['purpose']=='maskable' for i in install['icons'])
    assert all(i['src'].startswith('/seasonav1/'+prefix+'assets/icon-') for i in install['icons'])
    assert 'href="app-manifest.php" crossorigin="use-credentials"' in page and 'apple-touch-icon' in page
    checks.append('public_install_manifest_mime_identity_maskable_and_apple_icons_are_current')
    install_probe=probe_install_manifest(page,client)
    assert install_probe['ok'],install_probe
    checks.append('manifest_loads_using_html_declared_credentials_without_a_second_host_handshake')
    bell=re.search(r'<button id="notifications-toggle"[^>]+>',page)
    assert bell and 'data-action="notifications_toggle"' in bell[0] and 'data-view=' not in bell[0]
    assert prefix+'assets/notification-panel.js?v=' in page and 'id="notification-panel"' in page
    checks.append('notification_bell_opens_accessible_panel_instead_of_changing_route')
    with zipfile.ZipFile(io.BytesIO(files['downloads/YomaTV-Brave.zip'])) as archive:
        extension = json.loads(archive.read('manifest.json'))
        assert extension['version'] == '1.2.0' and extension['permissions'] == ['storage']
    checks.append('extension_package_keeps_expected_version_and_permissions')
    for path in ['private/config.local.php', 'private/current.json',
                 prefix + 'index.php', prefix + 'private/ready.json']:
        with request(path) as response:
            assert response.status in [403, 404], path
    checks.append('private_configuration_pointer_manifest_and_release_php_are_blocked')

    result = {'ok': True, 'at': int(time.time()), 'release': identifier,
        'schema': health['schema'], 'count': len(checks), 'checks': checks,
        'verified_public_files': len(public), 'catalog_titles': catalog['all_total'],
        'install_credentials_probe':install_probe,
        'manifest_sha256': hashlib.sha256(files['private/ready.json']).hexdigest(),
        'application_sha256':application_hashes(),
        'anonymous_only': True, 'real_mal_changes': False, 'real_video_downloads': 0}
    (ROOT / 'verification/delivery4-published-check.json').write_text(json.dumps(result, indent=2), encoding='utf8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
