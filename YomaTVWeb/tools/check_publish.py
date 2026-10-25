"""One repeatable entry point. Providers are mocked; publication is opt-in."""
import argparse,json,os,re,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'verification'))
from delivery4_evidence import application_hashes,external_checks,read_report
HTTP=['test_personal_http.py','test_review_findings.py','test_watch_page.py','test_infrastructure_http.py','test_experience.py','test_features.py','test_watch_auto.py','test_reliability_http.py','test_hardening.py','test_mal.py','test_schema_upgrade.py','test_catalog_filters.py','test_catalog_updates.py']
def run(args,label,timeout=1800):
    print(label,flush=True);log=ROOT/'verification'/('current-'+label+'.log')
    with log.open('w',encoding='utf8') as out:
        result=subprocess.run([sys.executable,*args],cwd=ROOT,env={**os.environ,'PYTHONUTF8':'1'},stdout=out,stderr=out,timeout=timeout)
    if result.returncode:raise RuntimeError(f'{label} failed; see {log}')
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--publish');parser.add_argument('--use-current-tests',action='store_true');parser.add_argument('--defer-production-backup',action='store_true');parser.add_argument('--snapshot',action='store_true')
    args=parser.parse_args()
    if args.defer_production_backup and not args.publish:parser.error('--defer-production-backup requires --publish')
    if args.publish and not re.fullmatch('[a-z0-9][a-z0-9-]{2,63}',args.publish):parser.error('Invalid release ID')
    if args.snapshot:run(['tools/remote_backup.py'],'encrypted-snapshot',600)
    hashes=application_hashes()
    if not args.use_current_tests:
        run(['verification/run_delivery4_final.py'],'local-regressions')
        run(['verification/run_delivery1.py',*HTTP],'http-regressions')
        run(['verification/run_mysql.py'],'mysql-regressions')
    status=external_checks(read_report('delivery4-status.json'))
    if not all(read_report('delivery4-status.json').get('source_sha256',{}).get(path)==sha for path,sha in hashes.items()):raise RuntimeError('Local PHP/JS checks belong to another source version')
    if not all(status.get(k) for k in ['local_checks_ok','http_checks_ok','mysql_checks_ok']):raise RuntimeError('Missing passing checks for the current source')
    if hashes!=application_hashes():raise RuntimeError('Source changed during verification')
    if args.publish:
        import importlib.util
        spec=importlib.util.spec_from_file_location('season_release',ROOT/'release.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        previous=module.check_health()['release']
        command=['release.py','--publish',args.publish]+(['--skip-database-backup'] if args.defer_production_backup else [])
        run(command,'publish',1800)
        run(['verification/check_watch_retry_rollback.py','--release',args.publish,'--previous',previous],'rollback-check',900)
        run(['verification/check_delivery4_published.py','--release',args.publish],'public-verification',900)
        status=external_checks(status)
        if not status['published']:raise RuntimeError('Publication did not pass verification')
    run(['verification/package_final.py'],'source-package')
    report={'ok':True,'at':int(time.time()),'release':args.publish,'published':bool(args.publish),'application_sha256':hashes,'http_suites':len(HTTP),'deferred_by_owner':status.get('deferred_by_owner',[])}
    (ROOT/'verification/current-workflow.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps({k:v for k,v in report.items() if k!='application_sha256'}))
if __name__=='__main__':main()
