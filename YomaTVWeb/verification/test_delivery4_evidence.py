"""Do not report stale HTTP/MySQL passes, and remove a partial snapshot upload."""
import importlib.util
import json
import sys
import tempfile
import types
from pathlib import Path
from unittest.mock import patch

import delivery4_evidence as evidence

ROOT = Path(__file__).resolve().parents[1]
checks = []
with tempfile.TemporaryDirectory(dir=ROOT / 'verification') as folder:
    root = Path(folder)
    (root / 'htdocs/private').mkdir(parents=True)
    (root / 'verification').mkdir()
    (root / 'htdocs/assets').mkdir()
    script = root / 'htdocs/assets/app.js'
    script.write_text('verified application', encoding='utf8')
    with patch.object(evidence, 'ROOT', root):
        hashes = evidence.application_hashes()
        http = {'ok': True, 'tests': [{'ok': True}], 'application_sha256': hashes}
        mysql = {'ok': True, 'checks': ['restored'], 'application_sha256': hashes,
                 'database_version': 'fixture'}
        (root / 'verification/delivery4-http-suite.json').write_text(json.dumps(http))
        (root / 'verification/mysql-check.json').write_text(json.dumps(mysql))
        result = evidence.external_checks({})
        assert result['http_checks_ok'] and result['mysql_checks_ok']
        assert not result['published'] and not result['production_backup_verified']
        (root / 'verification/delivery4-deployment.json').write_text(json.dumps({'ok':True,'release':'fixture-2','health':{'ok':True}}))
        rollback_file=root / 'verification/delivery4-rollback-check.json'
        rollback_file.write_text(json.dumps({'ok':True,'final_release':'fixture-1'}))
        assert not evidence.external_checks({})['ftps_rollback_verified']
        rollback_file.write_text(json.dumps({'ok':True,'final_release':'fixture-2'}))
        assert evidence.external_checks({})['ftps_rollback_verified']
        checks.append('rollback_evidence_must_match_the_current_deployed_release')
        script.write_text('changed application', encoding='utf8')
        result = evidence.external_checks({})
        assert not result['http_checks_ok'] and not result['mysql_checks_ok']
        checks.append('source_changes_invalidate_http_and_mysql_evidence')

    spec = importlib.util.spec_from_file_location('snapshot_under_test', ROOT / 'tools/remote_backup.py')
    snapshot = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(snapshot)
    (root / 'htdocs/private/backup.php').write_bytes(b'<?php // disposable test helper')
    deleted = []
    uploaded = []

    class FakeFTP:
        def __init__(self, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def connect(self, *args): pass
        def login(self, *args): pass
        def prot_p(self): pass
        def cwd(self, *args): pass
        def delete(self, path): deleted.append(path)

    class FakePage:
        def read(self): return b'normal first-party page'

    class FakeOpener:
        def open(self, *args, **kwargs): return FakePage()

    def incomplete_upload(ftp, path, data):
        uploaded.append(path)
        raise RuntimeError('FTPS verification failed after STOR')

    provider = types.SimpleNamespace(InfinityFTP=FakeFTP,
        credentials=lambda: {'username': 'if0_43115975', 'database': 'if0_43115975_anime',
                              'password': 'disposable-fixture-only'})
    with patch.object(snapshot, 'ROOT', root), patch.dict(sys.modules, {'deploy': provider}), \
         patch.object(snapshot.urllib.request, 'build_opener', return_value=FakeOpener()), \
         patch.object(snapshot.release, 'ftp_write', side_effect=incomplete_upload):
        try:
            snapshot.main()
            raise AssertionError('Partial upload should fail')
        except RuntimeError as error:
            assert str(error) == 'FTPS verification failed after STOR'
    assert len(uploaded) == 1 and deleted == uploaded
    assert not list((root / 'artifacts/private-backups').glob('*'))
    checks.append('snapshot_helper_is_removed_if_upload_verification_fails')

result = {'ok': True, 'checks': checks, 'network_requests': 0}
(ROOT / 'verification/delivery4-evidence-check.json').write_text(json.dumps(result, indent=2), encoding='utf8')
print(json.dumps(result))
