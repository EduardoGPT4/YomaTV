<?php
// Entirely in-memory. The scraper is a stub and never opens the network.
define('SEASON_BOOTSTRAPPED',true);
require dirname(__DIR__) . '/htdocs/private/db.php';
class ScraperError extends RuntimeException {}
class WebError extends RuntimeException {}
$fixed = false; $visited = [];
function sync_anime(PDO $db, string $slug): int {
  global $fixed,$visited;
  $visited[] = $slug;
  if ($slug==='broken' && !$fixed) throw new ScraperError('Synthetic changed HTML');
  return 12;
}
function admin_member(PDO $db): int { return 1; }
function rate(PDO $db, string $key, int $max, int $seconds): void {}
function home_data(PDO $db): array { return []; }
require dirname(__DIR__) . '/htdocs/private/maintenance.php';
$db = new PDO('sqlite::memory:');
$db->setAttribute(PDO::ATTR_DEFAULT_FETCH_MODE,PDO::FETCH_ASSOC);
$db->setAttribute(PDO::ATTR_ERRMODE,PDO::ERRMODE_EXCEPTION);
$db->exec('CREATE TABLE sa1_meta(name TEXT PRIMARY KEY,value TEXT NOT NULL)');
function check(bool $condition,string $name): void {
  if (!$condition) throw new RuntimeException($name);
  echo "Passed: $name\n";
}
set_meta($db,'maintenance_pending','["broken","healthy"]');
$first=maintenance_step($db);
check($first['failed_slug']==='broken' && json_decode(meta($db,'maintenance_pending'),true)===['healthy','broken'],'failed_item_rotates_behind_other_anime');
$second=maintenance_step($db);
check($second['updated_slug']==='healthy' && $visited===['broken','healthy'],'healthy_anime_updates_without_waiting_for_failed_one');
check(maintenance_step($db)['skipped']===true && count($visited)===2,'backoff_prevents_repeated_network_attempts');
check(meta($db,'maintenance_success','0')==='0','unfinished_batch_is_not_reported_as_complete');
$lastWait=0;
for($attempt=2;$attempt<=5;$attempt++) {
  $failures=json_decode(meta($db,'maintenance_failures'),true);
  $lastWait=$failures['broken']['next_retry'];
  $failures['broken']['next_retry']=0;
  set_meta($db,'maintenance_failures',json_encode($failures));
  maintenance_step($db);
}
check(json_decode(meta($db,'maintenance_pending'),true)===[] && isset(json_decode(meta($db,'maintenance_quarantine'),true)['broken']),'permanent_failure_quarantined_after_five_attempts');
dispatch_maintenance($db,'maintenance_retry_failed',[]);
$fixed=true;maintenance_step($db);
check((int)meta($db,'maintenance_success','0')>0 && json_decode(meta($db,'maintenance_quarantine'),true)===[],'admin_retry_recovers_quarantined_item_and_marks_completion');
