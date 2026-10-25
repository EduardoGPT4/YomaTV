"""HTTP and RBAC regression against the disposable harness only; no live hosting account."""
import json,secrets,sqlite3,urllib.error,urllib.request
import test_web
test_web.BASE='http://127.0.0.1:8096/';DB=test_web.ROOT/'verification/hardening-2026-10-14.sqlite';checks=[]
with urllib.request.urlopen(test_web.BASE+'app-manifest.php',timeout=10) as response:
    assert response.headers.get_content_type()=='application/manifest+json'
    assert response.headers.get('Set-Cookie') is None
    manifest=json.load(response)
    assert manifest['id']==manifest['scope']=='/' and manifest['start_url']=='/#discover'
    assert any(icon['purpose']=='maskable' and icon['sizes']=='512x512' for icon in manifest['icons'])
    for icon in manifest['icons']:
        with urllib.request.urlopen(test_web.BASE.rstrip('/')+icon['src'],timeout=10) as image:
            assert image.read(8)==b'\x89PNG\r\n\x1a\n'
checks.append('public_install_manifest_has_stable_identity_real_icons_and_no_session')
anon=test_web.Client();anon.call('system_health',get=True,expected=401)
member=test_web.Client();registered=member.call('register',name='Infrastructure QA',email='infra-'+secrets.token_hex(6)+'@example.test',password='Infrastructure-QA-2026')
assert len(registered['recovery_codes'])==10
assert member.call('account',get=True)['account']['recovery_remaining']==10
member.call('system_health',get=True,expected=403);checks.append('health_requires_admin_and_registration_offers_ten_codes')
admin=test_web.Client();admin.call('login',email='admin@example.test',password='Admin-Local-Test-8096')
health=admin.call('system_health',get=True)['system_health'];assert health['schema']=='20261023.1' and health['metrics'] and 'password' not in json.dumps(health)
checks.append('admin_health_contains_schema_timings_plans_and_retention_without_secrets')
def backup(client,csrf=True,password='Fixture-Backup-Password-2026'):
    headers={'Content-Type':'application/json'}
    if csrf:headers['X-CSRF-Token']=client.csrf
    request=urllib.request.Request(test_web.BASE+'backup.php',data=json.dumps({'password':password}).encode(),headers=headers)
    try:return client.opener.open(request,timeout=30)
    except urllib.error.HTTPError as e:return e
assert backup(anon).status==401 and backup(member).status==403 and backup(admin,False).status==403
response=backup(admin);assert response.status==200
payload=response.read();assert json.loads(payload.splitlines()[0])['format']=='seasonav1.db-backup/v1'
assert b'admin@example.test' not in payload and b'Infrastructure QA' not in payload
checks.append('encrypted_backup_is_post_csrf_and_admin_protected')
assert backup(admin).status==200 and backup(admin).status==429;checks.append('large_snapshots_are_rate_limited')
with sqlite3.connect(DB) as d:
    assert d.execute('SELECT COUNT(*) FROM sa1_runtime_metrics').fetchone()[0]>0
    assert not d.execute("SELECT payload FROM sa1_public_cache WHERE payload LIKE '%@example.test%'").fetchall()
result={'ok':True,'count':len(checks),'checks':checks,'real_accounts_used':False}
(test_web.ROOT/'verification/infrastructure-http-check.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(result))
