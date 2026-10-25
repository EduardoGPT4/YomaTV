<?php
define('SEASON_BOOTSTRAPPED',true);
require dirname(__DIR__).'/htdocs/private/app.php';
if(!getenv('SEASON_WEB_SQLITE')||!getenv('SEASON_WEB_MAL_TEST_URL'))exit(1);
$db=db();$_SESSION['user_id']=(int)sql($db,'SELECT id FROM sa1_users WHERE email=?',['preview@example.test'])->fetchColumn();$_SESSION['auth_version']=0;
$tokens=['access_token'=>'mock-access-token','refresh_token'=>'mock-refresh-token','expires_at'=>time()+3600];
upsert($db,'sa1_mal_connections',['user_id','mal_user_id','mal_name','token_cipher','expires_at','connected_at','checked_at','needs_auth','refresh_lock_until'],
  [['user_id'=>uid(),'mal_user_id'=>12345,'mal_name'=>'LocalMAL_Test','token_cipher'=>mal_encrypt($tokens,uid()),'expires_at'=>$tokens['expires_at'],'connected_at'=>time(),'checked_at'=>time(),'needs_auth'=>0,'refresh_lock_until'=>0]],['user_id'],['token_cipher','expires_at','checked_at','needs_auth','refresh_lock_until']);
sql($db,'DELETE FROM sa1_mal_list WHERE user_id=?',[uid()]);$index=mal_catalog_index($db);
foreach([[20,'Naruto','watching',5,8,'2002-10-03',220],[21,'One Piece','plan_to_watch',0,0,'1999-10-20',0],[269,'Bleach','watching',3,7,'2004-10-05',366]] as $a){
  $m=mal_cache_list($db,['id'=>$a[0],'title'=>$a[1],'media_type'=>'tv','start_date'=>$a[5],'num_episodes'=>$a[6],'genres'=>[['name'=>'Action']],'average_episode_duration'=>1440,'status'=>$a[0]===21?'currently_airing':'finished_airing'],
    ['status'=>$a[2],'num_episodes_watched'=>$a[3],'score'=>$a[4]],'api','ui');mal_try_match($db,$m,$index);
}
upsert($db,'sa1_mal_sync',['user_id','run_id','next_offset','updated_at','finished_at'],[['user_id'=>uid(),'run_id'=>'ui','next_offset'=>0,'updated_at'=>time(),'finished_at'=>time()]],['user_id'],['run_id','next_offset','updated_at','finished_at']);
foreach(sql($db,"SELECT id FROM sa1_episodes WHERE slug='naruto' AND number='6'")->fetchAll() as $ep)sql($db,'UPDATE sa1_episodes SET mirrors=?,mirrors_at=? WHERE id=?',[json_encode([['server'=>'MP4Upload','language'=>'SUB','url'=>'https://www.mp4upload.com/embed-abcd12345678.html']]),time(),$ep['id']]);
echo "Preview MAL data seeded locally; no real MAL or video requests.\n";
