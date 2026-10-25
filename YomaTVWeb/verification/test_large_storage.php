<?php
declare(strict_types=1);
define('SEASON_BOOTSTRAPPED',true);
require dirname(__DIR__).'/htdocs/private/app.php';
$db=new PDO('sqlite::memory:');$db->setAttribute(PDO::ATTR_ERRMODE,PDO::ERRMODE_EXCEPTION);$db->setAttribute(PDO::ATTR_DEFAULT_FETCH_MODE,PDO::FETCH_ASSOC);$db->exec('PRAGMA foreign_keys=ON');migrate($db);seed_data($db);
sql($db,'INSERT INTO sa1_users(name,email,password_hash,created_at) VALUES(?,?,?,?)',['Large QA','large@example.test','fixture-hash',time()]);$_SESSION['user_id']=(int)$db->lastInsertId();$_SESSION['auth_version']=0;
$db->beginTransaction();$eps=[];
for($i=1;$i<=5200;$i++)$eps[]=['slug'=>'naruto','number'=>(string)$i,'number_value'=>$i,'url'=>'https://animeav1.com/media/naruto/'.$i];
upsert($db,'sa1_episodes',array_keys($eps[0]),$eps,['slug','number'],['url']);
$jobs=[];foreach(sql($db,'SELECT id FROM sa1_episodes WHERE slug=? ORDER BY number_value',['naruto'])->fetchAll() as $i=>$ep)$jobs[]=['user_id'=>uid(),'episode_id'=>$ep['id'],'language'=>'SUB','server'=>'MP4Upload','height'=>1080,'status'=>$i<2600?'pending':'confirmed','added_at'=>time()];
upsert($db,'sa1_jobs',array_keys($jobs[0]),$jobs,['user_id','episode_id','language'],['status']);
$follows=[];foreach(sql($db,'SELECT slug FROM sa1_anime LIMIT 3000')->fetchAll() as $row)$follows[]=['user_id'=>uid(),'slug'=>$row['slug'],'status'=>'watching','notes'=>'Synthetic library note'];
upsert($db,'sa1_follow',array_keys($follows[0]),$follows,['user_id','slug'],['status','notes']);$db->commit();
$checks=[];function large_check(bool $ok,string $name):void {global $checks;if(!$ok)throw new RuntimeException($name);$checks[]=$name;}
$state=state($db);
large_check(count(array_filter($state['jobs'],static fn($job)=>$job['status']==='pending'))===80,'active_queue_initial_projection_is_bounded');
large_check(count($state['jobs'])<=160,'completed_history_is_bounded_to_recent_eighty');
large_check(count(array_filter($state['anime'],static fn($anime)=>$anime['status']==='watching'))===3000,'three_thousand_library_entries_are_preserved');
$cursor=0;$ids=[];do{$page=queue_history($db,['slug'=>'naruto','before'=>$cursor])['queue_history'];large_check(count($page['items'])<=200,'history_page_is_bounded');foreach($page['items'] as $row)$ids[]=(int)$row['id'];$cursor=$page['next_before'];}while($cursor);
large_check(count($ids)===count($jobs)&&count(array_unique($ids))===count($jobs),'cursor_history_recovers_all_jobs_once');
large_check($state['queue_totals']['total']===count($jobs),'all_5200_jobs_are_counted_without_truncation');
observation_start('catalog');$cold=catalog($db,[]);$coldCount=$GLOBALS['season_observation']['queries'];unset($GLOBALS['season_observation']);
observation_start('catalog');$warm=catalog($db,[]);$warmCount=$GLOBALS['season_observation']['queries'];unset($GLOBALS['season_observation']);
large_check($warm['all_total']===$cold['all_total']&&$warmCount<$coldCount,'versioned_facets_reduce_repeated_queries_without_losing_titles');
$plans=query_plans($db);large_check(str_contains(json_encode($plans['history']),'sa1_history_user_id'),'history_index_is_used_in_sqlite_query_plan');
$result=['ok'=>true,'checks'=>$checks,'library'=>3000,'jobs'=>count($jobs),'cold_queries'=>$coldCount,'warm_queries'=>$warmCount,'plans'=>$plans,'engine'=>'SQLite fixture; MySQL measurement pending'];
file_put_contents(__DIR__.'/large-storage-check.json',json_encode($result,JSON_PRETTY_PRINT));echo json_encode($result,JSON_PRETTY_PRINT);
