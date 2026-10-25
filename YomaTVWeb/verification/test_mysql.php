<?php
declare(strict_types=1);
if(!preg_match('/^mysql:host=127\.0\.0\.1;port=33316;dbname=seasonav1_test_[a-f0-9]+;charset=utf8mb4$/D',(string)getenv('SEASON_WEB_TEST_MYSQL_DSN')))exit(1);
define('SEASON_BOOTSTRAPPED',true);require dirname(__DIR__).'/htdocs/private/app.php';require dirname(__DIR__).'/htdocs/private/backup.php';
$db=db();$checks=[];
function mysql_check(bool $condition,string $name):void {global $checks;if(!$condition)throw new RuntimeException($name);$checks[]=$name;}
$before=meta($db,'schema_migrated_at');migrate($db);mysql_check(meta($db,'schema_migrated_at')===$before,'mysql_schema_version_is_idempotent');
$registered=dispatch_auth($db,'register',['name'=>'MySQL QA','email'=>'mysql@example.test','password'=>'MySQL-Fixture-Only-2026']);mysql_check(count($registered['recovery_codes'])===10,'mysql_registration_and_recovery_codes');
mysql_check(consume_limit($db,'mysql-exact',1,60)&&!consume_limit($db,'mysql-exact',1,60),'mysql_atomic_limit_exact_boundary');
$db->beginTransaction();
try{
  $rows=[];
  for($i=1;$i<=5200;$i++)$rows[]=['slug'=>'naruto','number'=>(string)$i,'number_value'=>$i,'url'=>'https://animeav1.com/media/naruto/'.$i];
  upsert($db,'sa1_episodes',array_keys($rows[0]),$rows,['slug','number'],['url']);
  $jobs=[];foreach(sql($db,'SELECT id FROM sa1_episodes WHERE slug=? ORDER BY number_value',['naruto'])->fetchAll() as $i=>$ep)$jobs[]=['user_id'=>uid(),'episode_id'=>$ep['id'],'language'=>'SUB','server'=>'MP4Upload','height'=>1080,'status'=>$i<2600?'pending':'confirmed','added_at'=>time()];
  upsert($db,'sa1_jobs',array_keys($jobs[0]),$jobs,['user_id','episode_id','language'],['status']);
  for($i=0;$i<200;$i++)log_event($db,uid(),'Synthetic database event');
  $db->commit();
}catch(Throwable $e){$db->rollBack();throw $e;}
$state=state($db);mysql_check(count(array_filter($state['jobs'],static fn($j)=>$j['status']==='pending'))===80,'mysql_large_queue_initial_projection_is_bounded');
$personal=personal_store($db,'collection',str_repeat('a',16),['name'=>'Friends','slugs'=>['naruto']]);
$radio=personal_store($db,'radio','library',['favorites'=>['abcdefghijk'],'lists'=>[]],'');
try{personal_store($db,'radio','library',['favorites'=>[],'lists'=>[]],'');throw new LogicException('stale accepted');}catch(WebError $error){mysql_check($error->status===409,'mysql_radio_compare_and_swap_rejects_stale_device');}
$page=dispatch_personal($db,'queue_page',['slug'=>'naruto','page'=>2])['queue_page'];mysql_check(count($page['items'])===36&&(float)$page['items'][0]['number']===37.0,'mysql_lazy_numeric_queue_page');
$job=(int)$page['items'][0]['id'];dispatch_personal($db,'download_events',['installation'=>meta($db,'installation'),'device_id'=>str_repeat('b',32),'items'=>[['id'=>$job,'state'=>'failed','attempts'=>2,'error_kind'=>'connection']]]);
mysql_check(dispatch_personal($db,'queue_page',['slug'=>'naruto','phase'=>'failed'])['queue_page']['total']===1,'mysql_persistent_failure_filter_keeps_verified_state_separate');
personal_store($db,'intro','naruto',['start'=>15,'end'=>100]);
mysql_check((float)personal_export($db)['intro'][0]['data']['end']===100.0,'mysql_personal_export_includes_playback_tools');
$cold=catalog($db,[]);$warm=catalog($db,['year'=>'2002']);mysql_check($cold['all_total']>=4485&&is_array($warm['genres']),'mysql_catalog_facets_and_cache_preserve_full_catalog');
$recommendations=player_recommendations($db,find_anime($db,'naruto'));mysql_check(count($recommendations['genres'])>0&&count($recommendations['saga'])>0,'mysql_player_recommendations_use_public_genres_and_names');
$plans=query_plans($db);foreach(['history','expired_limits'] as $name)mysql_check((bool)array_filter($plans[$name],static fn($p)=>!empty($p['key'])),'mysql_index_plan_'.$name);
sql($db,'INSERT INTO sa1_users(id,name,email,password_hash,created_at) VALUES(?,?,?,?,?)',[42,'Deleted QA','deleted-mysql@example.test','fixture',1]);sql($db,'DELETE FROM sa1_users WHERE id=?',[42]);
$stream=tmpfile();$password='MySQL-Backup-Fixture-2026';$written=backup_write($db,$stream,$password);
$restoreDsn=(string)getenv('SEASON_WEB_TEST_RESTORE_DSN');if(!preg_match('/^mysql:host=127\.0\.0\.1;port=33316;dbname=seasonav1_test_[a-f0-9]+;charset=utf8mb4$/D',$restoreDsn))exit(1);
$target=new PDO($restoreDsn,'root',(string)getenv('SEASON_WEB_TEST_MYSQL_PASSWORD'));$target->setAttribute(PDO::ATTR_ERRMODE,PDO::ERRMODE_EXCEPTION);$target->setAttribute(PDO::ATTR_DEFAULT_FETCH_MODE,PDO::FETCH_ASSOC);migrate($target);
$restored=backup_restore($target,$stream,$password);fclose($stream);mysql_check($restored['rows']===$written['rows']&&(int)$target->query('SELECT COUNT(*) FROM sa1_jobs')->fetchColumn()===count($jobs),'mysql_encrypted_snapshot_restores_with_foreign_keys');
sql($target,'INSERT INTO sa1_users(name,email,password_hash,created_at) VALUES(?,?,?,?)',['Restored QA','restored-mysql@example.test','fixture',1]);mysql_check((int)$target->lastInsertId()>42,'mysql_restore_preserves_auto_increment_gaps');
echo json_encode(['ok'=>true,'checks'=>$checks,'database_version'=>$db->query('SELECT VERSION()')->fetchColumn(),'plans'=>$plans],JSON_PRETTY_PRINT);
