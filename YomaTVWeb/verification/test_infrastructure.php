<?php
declare(strict_types=1);
define('SEASON_BOOTSTRAPPED',true);
require dirname(__DIR__).'/htdocs/private/app.php';
require dirname(__DIR__).'/htdocs/private/backup.php';
$checks=[];
function must(bool $condition,string $message):void {global $checks;if(!$condition)throw new RuntimeException($message);$checks[]=$message;}
class CountingPDO extends PDO {public int $ddl=0;public function exec(string $statement):int|false {if(preg_match('/^(CREATE|ALTER|DROP)/i',$statement))$this->ddl++;return parent::exec($statement);}}
function fresh():PDO {$d=new CountingPDO('sqlite::memory:');$d->setAttribute(PDO::ATTR_ERRMODE,PDO::ERRMODE_EXCEPTION);$d->setAttribute(PDO::ATTR_DEFAULT_FETCH_MODE,PDO::FETCH_ASSOC);$d->exec('PRAGMA foreign_keys=ON');migrate($d);return $d;}
$db=fresh();
$before=meta($db,'schema_migrated_at');
$db->exec("CREATE TRIGGER protect_schema BEFORE UPDATE ON sa1_meta WHEN OLD.name='schema_migrated_at' BEGIN SELECT RAISE(ABORT,'DDL should not run');END");
$ddl=$db->ddl;migrate($db);must($db->ddl===$ddl&&meta($db,'schema_migrated_at')===$before,'current_schema_skips_ddl_and_backfills');$db->exec('DROP TRIGGER protect_schema');
must(consume_limit($db,'test',2,60,100)&&consume_limit($db,'test',2,60,101)&&!consume_limit($db,'test',2,60,102),'rate_limit_counts_denied_requests_atomically');
must(consume_limit($db,'test',2,60,160),'rate_limit_resets_at_exact_expiry');
$_SERVER['REMOTE_ADDR']='127.0.0.1';
$registered=dispatch_auth($db,'register',['name'=>'Fixture','email'=>'infra@example.test','password'=>'Fixture-Only-Password']);
must(count($registered['recovery_codes'])===10,'registration_returns_ten_one_time_recovery_codes');
must((int)sql($db,'SELECT COUNT(*) FROM sa1_recovery WHERE user_id=? AND used_at IS NULL',[uid()])->fetchColumn()===10,'only_recovery_hashes_stored');
$hashes=json_encode(sql($db,'SELECT * FROM sa1_recovery')->fetchAll());must(!array_filter($registered['recovery_codes'],static fn($code)=>str_contains($hashes,$code)),'plaintext_recovery_codes_absent');
$originalUser=uid();$db->exec("CREATE TRIGGER recovery_failure BEFORE INSERT ON sa1_recovery BEGIN SELECT RAISE(ABORT,'synthetic failure');END");
try{dispatch_auth($db,'register',['name'=>'Failed QA','email'=>'failed@example.test','password'=>'Fixture-Only-Password']);throw new LogicException('Registration should fail');}
catch(RuntimeException $e){must(!$e instanceof LogicException&&uid()===$originalUser&&!sql($db,'SELECT id FROM sa1_users WHERE email=?',['failed@example.test'])->fetchColumn(),'failed_recovery_generation_rolls_back_registration_and_keeps_current_session');}
$db->exec('DROP TRIGGER recovery_failure');
// Minimal public data + a private library that must never enter the facet cache.
$anime=['slug'=>'fixture','source_id'=>1,'title'=>'Fixture','synopsis'=>'','cover'=>'','weekday'=>0,'latest'=>'1','published'=>'','start_date'=>'2026-10-01','season'=>'otoño2026','category'=>'TV Anime','active'=>1,'catalog_complete'=>1,'updated_at'=>time()];
upsert($db,'sa1_anime',array_keys($anime),[$anime],['slug'],['title']);
$facets=catalog_facets($db);$cache=sql($db,'SELECT version,payload FROM sa1_public_cache WHERE cache_key=?',['facets-v1'])->fetch();
must(!str_contains($cache['payload'],'infra@example.test')&&!str_contains($cache['payload'],'recovery'),'public_cache_does_not_contain_personal_data');
$db->exec("UPDATE sa1_anime SET start_date='2025-01-01'");catalog_touch($db,'fixture',['directory_at']);
must(in_array('2025',catalog_facets($db)['years'],true)&&$cache['version']!==sql($db,'SELECT version FROM sa1_public_cache WHERE cache_key=?',['facets-v1'])->fetchColumn(),'public_cache_invalidates_after_public_update');
for($i=0;$i<110;$i++)sql($db,'INSERT INTO sa1_history(user_id,level,message,created_at) VALUES(?,?,?,?)',[uid(),'info','Synthetic event',1]);
sql($db,'INSERT INTO sa1_limits(name,hits,reset_at) VALUES(?,?,?)',['ancient',1,1]);
$removed=retention_cleanup($db,true);
must((int)sql($db,'SELECT COUNT(*) FROM sa1_history WHERE user_id=? AND created_at=1',[uid()])->fetchColumn()===80,'retention_keeps_latest_eighty_history_events');
must(!sql($db,'SELECT name FROM sa1_limits WHERE name=?',['ancient'])->fetchColumn(),'retention_removes_expired_limits');

for($u=0;$u<4;$u++){
  sql($db,'INSERT INTO sa1_users(name,email,password_hash,created_at) VALUES(?,?,?,?)',['Retention','retention'.$u.'@example.test','fixture',1]);$owner=(int)$db->lastInsertId();
  for($i=0;$i<($u===3?110:80);$i++)sql($db,'INSERT INTO sa1_history(user_id,level,message,created_at) VALUES(?,?,?,?)',[$owner,'info','Protected small histories must not block later cleanup',1]);
}
retention_cleanup($db,true);must((int)sql($db,'SELECT COUNT(*) FROM sa1_history WHERE user_id=?',[$owner])->fetchColumn()===80,'protected_small_histories_cannot_starve_other_users_retention');
observation_start('fixture');sql($db,'SELECT 1');observation_finish($db,new RuntimeException('Do not store this token'));
$health=system_health($db);must(count($health['metrics'])===1&&!str_contains(json_encode($health),'Do not store this token'),'health_aggregates_timings_without_error_payload');
sql($db,'INSERT INTO sa1_users(id,name,email,password_hash,created_at) VALUES(?,?,?,?,?)',[42,'Deleted sequence fixture','deleted@example.test','fixture',1]);sql($db,'DELETE FROM sa1_users WHERE id=?',[42]);
$stream=tmpfile();$password='Fixture-Backup-Password-2026';$written=backup_write($db,$stream,$password);$dest=fresh();$restored=backup_restore($dest,$stream,$password);
must($written['rows']===$restored['rows']&&(int)$dest->query('SELECT COUNT(*) FROM sa1_users')->fetchColumn()===(int)$db->query('SELECT COUNT(*) FROM sa1_users')->fetchColumn(),'encrypted_backup_restores_all_tables_in_fk_order');
sql($dest,'INSERT INTO sa1_users(name,email,password_hash,created_at) VALUES(?,?,?,?)',['After restore','after@example.test','fixture',1]);must((int)$dest->lastInsertId()>42,'restore_preserves_sequence_gaps_and_does_not_reuse_deleted_account_ids');
try{backup_restore($dest,$stream,$password);throw new LogicException('Overwrite was accepted');}catch(RuntimeException $e){must(!$e instanceof LogicException,'restore_rejects_nonempty_destination');}
rewind($stream);$encoded=stream_get_contents($stream);must(!str_contains($encoded,'infra@example.test')&&!str_contains($encoded,'Synthetic event'),'backup_has_no_plaintext_account_data');
foreach(['wrong-key','truncated','tampered'] as $failure){
  $bad=tmpfile();$data=$failure==='truncated'?substr($encoded,0,-200):$encoded;
  if($failure==='tampered'){$lines=explode("\n",$data);$record=json_decode($lines[2],true);$cipher=base64_decode($record['c']);$cipher[0]=chr(ord($cipher[0])^1);$record['c']=base64_encode($cipher);$lines[2]=json_encode($record);$data=implode("\n",$lines);}
  fwrite($bad,$data);$empty=fresh();
  try{backup_restore($empty,$bad,$failure==='wrong-key'?'Incorrect-Password-2026':$password);throw new LogicException('Invalid backup was accepted');}
  catch(RuntimeException $e){must(!$e instanceof LogicException&&(int)$empty->query('SELECT COUNT(*) FROM sa1_users')->fetchColumn()===0,'restore_rejects_'.$failure.'_without_partial_data');}
  fclose($bad);
}
fclose($stream);
session_write_close();


// Reserve at most ninety background requests while keeping the total at 120.
$db->exec("DELETE FROM sa1_limits WHERE name LIKE 'scraper-%'");
for($i=0;$i<90;$i++){sql($db,'DELETE FROM sa1_limits WHERE name=?',['scraper-spacing']);reserve_scraper_budget($db,0,false);}
sql($db,'DELETE FROM sa1_limits WHERE name=?',['scraper-spacing']);
try{reserve_scraper_budget($db,0,false);throw new LogicException('maintenance exceeded reserve');}catch(WebError $e){must($e->status===429,'maintenance_cannot_spend_thirty_reserved_interactive_requests');}
for($i=0;$i<30;$i++){sql($db,'DELETE FROM sa1_limits WHERE name=?',['scraper-spacing']);reserve_scraper_budget($db,0,true);}
sql($db,'DELETE FROM sa1_limits WHERE name=?',['scraper-spacing']);
try{reserve_scraper_budget($db,0,true);throw new LogicException('total exceeded');}catch(WebError $e){must($e->status===429,'interactive_reserve_preserves_the_global_120_limit');}
$cached=public_cache($db,'lease-fixture',fn()=>['safe'=>'public']);
sql($db,'UPDATE sa1_public_cache SET version=? WHERE cache_key=?',['old','lease-fixture']);
set_meta($db,'cache-lock:lease-fixture',(string)(time()+20));
must(public_cache($db,'lease-fixture',fn()=>throw new LogicException('second producer'))===$cached,'warm_cache_serves_stale_public_data_while_another_producer_holds_lease');

echo json_encode(['ok'=>true,'count'=>count($checks),'checks'=>$checks],JSON_PRETTY_PRINT|JSON_UNESCAPED_UNICODE);
