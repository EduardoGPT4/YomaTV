<?php
// Deterministic in-memory worker. Network functions are stubs; no user DB is opened.
define('SEASON_BOOTSTRAPPED',true);
require dirname(__DIR__).'/htdocs/private/db.php';
class ScraperError extends RuntimeException {}
class WebError extends RuntimeException {public function __construct(string $message,public int $status=422){parent::__construct($message);}}
function admin_member(PDO $db): int {return 1;}
function calendar_refresh_feeds(PDO $db): void {}
function record_scraper_failure(PDO $db,string $message): void {set_meta($db,'test_error',$message);}
$visited=[];$broken=true;$pageTotal=3;
function sync_anime(PDO $db,string $slug): int {
  global $visited,$broken;$visited[]=$slug;
  if($slug==='broken'&&$broken)throw new ScraperError('Synthetic missing HTML');
  if($slug==='limited')throw new WebError('Synthetic source budget exhausted',429);
  catalog_touch($db,$slug,['episodes_at']);return 2;
}
function episode_mirrors(PDO $db,array $ep): array {return [];}
function sync_directory_partition(PDO $db,int $low,int $high,int $page): array {
  global $pageTotal;return ['total'=>$high-$low>200?1000:$pageTotal,'pages'=>2,'page'=>$page,'count'=>2];
}
function sync_directory_page(PDO $db,int $page): array {return ['total'=>20,'pages'=>1,'page'=>$page,'count'=>20];}
require dirname(__DIR__).'/htdocs/private/catalog-updates.php';
$db=new PDO('sqlite::memory:');$db->setAttribute(PDO::ATTR_DEFAULT_FETCH_MODE,PDO::FETCH_ASSOC);
$db->exec('CREATE TABLE sa1_meta(name TEXT PRIMARY KEY,value TEXT NOT NULL)');
$db->exec('CREATE TABLE sa1_anime(slug TEXT PRIMARY KEY,active INTEGER NOT NULL DEFAULT 0)');
$db->exec('CREATE TABLE sa1_catalog_freshness(slug TEXT PRIMARY KEY,episodes_at INTEGER DEFAULT 0,genres_at INTEGER DEFAULT 0,airing_at INTEGER DEFAULT 0,directory_at INTEGER DEFAULT 0,relations_at INTEGER DEFAULT 0)');
$db->exec('CREATE TABLE sa1_catalog_tasks(task_key TEXT PRIMARY KEY,kind TEXT,target TEXT,payload TEXT,state TEXT,priority INTEGER,attempts INTEGER,next_retry INTEGER,lock_until INTEGER,error TEXT,created_at INTEGER,updated_at INTEGER)');
$checks=[];
function verify(bool $ok,string $name): void {global $checks;if(!$ok)throw new RuntimeException($name);$checks[]=$name;}
catalog_prepare_cycle($db);verify(catalog_jobs_status($db)['pending']===2,'incremental_cycle_is_started_once');
catalog_prepare_cycle($db);verify(catalog_jobs_status($db)['pending']===2,'repeated_visits_do_not_duplicate_cycle');
sql($db,"UPDATE sa1_catalog_tasks SET state='done' WHERE kind='latest'");
catalog_jobs_step($db);verify(catalog_jobs_status($db)['pending']===2,'source_cap_splits_into_year_partitions');
catalog_jobs_step($db);verify((int)sql($db,"SELECT COUNT(*) FROM sa1_catalog_tasks WHERE target LIKE '%:2' AND state='pending'")->fetchColumn()===1,'partition_pagination_schedules_next_page');
// A count change on the final page must not falsely mark a cycle complete.
sql($db,"UPDATE sa1_catalog_tasks SET state='done' WHERE target NOT LIKE '%:2'");$pageTotal=4;
$changed=catalog_jobs_step($db);verify(!empty($changed['restarted']) && catalog_jobs_status($db)['pending']===1,'changed_final_page_restarts_affected_partition_without_false_completion');
sql($db,"UPDATE sa1_catalog_tasks SET state='done'");
foreach(['broken','healthy','limited'] as $slug){sql($db,'INSERT INTO sa1_anime(slug) VALUES(?)',[$slug]);catalog_touch($db,$slug,['episodes_at']);}
catalog_enqueue($db,'detail','broken',[],20);catalog_enqueue($db,'detail','healthy',[],10);
$first=catalog_jobs_step($db);verify(($first['failed_slug']??'')==='broken','failure_is_retained_with_backoff');
$second=catalog_jobs_step($db);verify(($second['updated_slug']??'')==='healthy','failure_does_not_block_other_anime');
$status=catalog_task_status($db,'detail','broken');verify($status['attempts']==1 && $status['next_retry']>time(),'backoff_is_progressive_and_persisted');
// Exhausting a shared hourly budget must not consume a title's retry attempts.
catalog_enqueue($db,'detail','limited',[],30);$limited=catalog_jobs_step($db);
verify($limited['skipped'] && catalog_task_status($db,'detail','limited')['attempts']==0,'rate_limits_defer_without_quarantining_healthy_titles');
set_meta($db,'catalog_job_lock',(string)(time()+30));$before=count($visited);catalog_jobs_step($db);
verify(count($visited)===$before,'global_lease_prevents_concurrent_fetches');set_meta($db,'catalog_job_lock','0');
sql($db,"UPDATE sa1_catalog_tasks SET state='done'");catalog_enqueue($db,'detail','healthy',[],10);
sql($db,"UPDATE sa1_catalog_tasks SET state='running',lock_until=? WHERE target='healthy'",[time()-1]);
$recovered=catalog_jobs_step($db);verify(($recovered['updated_slug']??'')==='healthy','interrupted_job_recovers_after_lease_expiry');
$result=['ok'=>true,'count'=>count($checks),'checks'=>$checks,'network_requests'=>0];
file_put_contents(__DIR__.'/catalog-worker-check.json',json_encode($result,JSON_PRETTY_PRINT));echo json_encode($result,JSON_PRETTY_PRINT)."\n";
