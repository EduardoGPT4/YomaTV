"""Combine evidence without reusing HTTP/MySQL passes for changed application files."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def application_hashes():
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted((ROOT / 'htdocs').rglob('*'))
        if p.is_file() and not p.name.endswith('.local.php')
        and not p.relative_to(ROOT / 'htdocs').parts[0].startswith('__qa')
        and not (p.relative_to(ROOT / 'htdocs').parts[0] == 'feeds'
                 and p.suffix in ('.ics', '.tmp') and p.name != 'horario.ics')}


def read_report(name):
    path = ROOT / 'verification' / name
    return json.loads(path.read_text(encoding='utf8')) if path.exists() else {}


def external_checks(result):
    current = application_hashes()
    http = read_report('delivery4-http-suite.json')
    mysql = read_report('mysql-check.json')
    http_ok = bool(http.get('ok') and http.get('application_sha256') == current)
    mysql_ok = bool(mysql.get('ok') and mysql.get('application_sha256') == current)
    receipt = read_report('production-backup-receipt.json')
    backup = (ROOT / receipt.get('file', '')).resolve()
    backup_ok = bool(receipt.get('verified')
        and backup.is_relative_to((ROOT / 'artifacts/private-backups').resolve())
        and backup.is_file() and hashlib.sha256(backup.read_bytes()).hexdigest() == receipt.get('sha256'))
    deployment = read_report('delivery4-deployment.json')
    public = read_report('delivery4-published-check.json')
    activated = bool(deployment.get('ok') and deployment.get('health', {}).get('ok'))
    public_ok = bool(activated and public.get('ok') and public.get('release') == deployment.get('release') and public.get('application_sha256')==current)
    published = public_ok
    rollback=read_report('delivery4-rollback-check.json')
    rollback_ok=bool(rollback.get('ok') and rollback.get('final_release')==deployment.get('release'))
    deferred=read_report('deferred-checks.json').get('checks',[])
    result.update(http_checks_ok=http_ok,
        http_suites=len(http.get('tests', [])) if http_ok else 0,
        mysql_checks_ok=mysql_ok, mysql_checks=len(mysql.get('checks', [])) if mysql_ok else 0,
        database_test_version=mysql.get('database_version') if mysql_ok else None,
        production_backup_verified=backup_ok, published=published,release_activated=activated,ftps_rollback_verified=rollback_ok,
        production_public_checks_ok=public_ok,
        production_database_changed=activated, real_mal_changes=False, real_anime_downloads=0)
    result['pending'] = []
    if not http_ok: result['pending'].append('HTTP integration suites for current source')
    if not mysql_ok: result['pending'].append('MariaDB/MySQL execution and plans for current source')
    if not backup_ok and 'production_database_backup' not in deferred: result['pending'].append('Production encrypted snapshot')
    if not activated: result['pending'].append('FTPS activation')
    if not rollback_ok: result['pending'].append('FTPS rollback verification')
    if not public_ok: result['pending'].append('Production HTTP and immutable-file verification')
    # Browser access is independent of the HTTP and CLI regression harnesses.
    if 'real_brave_verification' not in deferred: result['pending'].append('Real Brave extension, local-network permission, playback and PiP')
    result['deferred_by_owner']=deferred
    return result


if __name__ == '__main__':
    result = external_checks(read_report('delivery4-status.json'))
    (ROOT / 'verification/delivery4-status.json').write_text(json.dumps(result, indent=2), encoding='utf8')
    print(json.dumps({k: v for k, v in result.items() if k != 'source_sha256'}, indent=2))
