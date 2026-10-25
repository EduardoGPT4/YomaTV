<?php
// Deterministic, disposable records in the local SQLite fixture only.
define('SEASON_BOOTSTRAPPED',true);
require dirname(__DIR__).'/htdocs/private/app.php';
if (!getenv('SEASON_WEB_SQLITE')) exit(1);
$db=db();
$_SESSION['user_id']=(int)sql($db,'SELECT id FROM sa1_users WHERE email=?',['preview@example.test'])->fetchColumn();
$owner=uid(); $other=(int)sql($db,'SELECT id FROM sa1_users WHERE email=?',['admin@example.test'])->fetchColumn();
$statuses=['watching','planned','completed','paused','dropped','watching','planned'];
$qaMalNodes=[];
set_meta($db,'directory_updated',(string)(time()+100));
set_meta($db,'maintenance_next_due',(string)(time()+86400));
set_meta($db,'maintenance_pending','[]');
for($n=0;$n<40;$n++) {
  $slug='qa-filter-'.str_pad((string)$n,2,'0',STR_PAD_LEFT);
  $title=$n===0?'Álgebra QA':($n===1?'86 Temporada QA':'Filtro QA '.str_pad((string)$n,2,'0',STR_PAD_LEFT));
  $date=$n===0?'2002-10-03':($n===1?'2024-07-01':($n===2?'2026-10-01':''));
  $row=['slug'=>$slug,'source_id'=>900000+$n,'title'=>$title,'synopsis'=>'Ficha ficticia para validar filtros.','cover'=>'https://cdn.animeav1.com/cover/20.jpg','weekday'=>1,'latest'=>'2','published'=>'','start_date'=>$date,'season'=>'','category'=>'QA TV','active'=>0,'catalog_complete'=>1,'updated_at'=>time()+$n];
  upsert($db,'sa1_anime',array_keys($row),[$row],['slug'],array_keys(array_diff_key($row,['slug'=>1])));
  $count=$n===8?30:($n===9?40:2);
  for($i=1;$i<=$count;$i++) upsert($db,'sa1_episodes',['slug','number','number_value','url'],[['slug'=>$slug,'number'=>(string)$i,'number_value'=>$i,'url'=>'https://animeav1.com/media/'.$slug.'/'.$i]],['slug','number'],['url']);
  $status=$statuses[$n] ?? ($n>=10?'watching':null);
  if($status) upsert($db,'sa1_follow',['user_id','slug','status','favorite','excluded','score','notes'],[['user_id'=>$owner,'slug'=>$slug,'status'=>$status,'favorite'=>(int)($n===5),'excluded'=>0,'score'=>$n===0?10:($n===5?9:3),'notes'=>'Solo mi cuenta']],['user_id','slug'],['status','favorite','score','notes']);
  $ep=(int)sql($db,"SELECT id FROM sa1_episodes WHERE slug=? AND number='1'",[$slug])->fetchColumn();
  if($n<5) {
    $state=['confirmed','pending','exported','cancelled','confirmed'][$n];
    upsert($db,'sa1_jobs',['user_id','episode_id','language','server','height','status','added_at'],[['user_id'=>$n===4?$other:$owner,'episode_id'=>$ep,'language'=>'SUB','server'=>'MP4Upload','height'=>1080,'status'=>$state,'added_at'=>time()]],['user_id','episode_id','language'],['status']);
  }
  if($n<3) {
    $mirrors=[['server'=>'MP4Upload','language'=>['SUB','LAT','DUB'][$n],'url'=>'https://www.mp4upload.com/embed-abcd12345678.html']];
    sql($db,'UPDATE sa1_episodes SET mirrors=?,mirrors_at=? WHERE id=?',[json_encode($mirrors),time(),$ep]);
    catalog_index_languages($db,$ep,$mirrors);
  }
  if(in_array($n,[0,1,2,4,5,6,7],true)) {
    $genres=[0=>['Action','Comedy'],1=>['Action','Ecchi'],2=>['Comedy'],4=>['Action','Comedy','Ecchi'],5=>['Action','Comedy'],6=>['Action'],7=>['Comedy','Ecchi']][$n];
    $qaMalNodes[]=['id'=>900000+$n,'title'=>$title,'media_type'=>'tv','start_date'=>$date?:'2024-04-01','status'=>'finished_airing','genres'=>array_map(fn($g)=>['name'=>$g],$genres),'mean'=>9.1,'studios'=>[['name'=>'Estudio de prueba']],'num_episodes'=>100];
    $source=['slug'=>$slug,'genres'=>json_encode(catalog_source_genres($genres),JSON_UNESCAPED_UNICODE),'premiere_year'=>(int)substr($date?:'2024-04-01',0,4),'airing_status'=>'finished_airing','updated_at'=>time()];
    upsert($db,'sa1_catalog_source',array_keys($source),[$source],['slug'],['genres','premiere_year','airing_status','updated_at']);
  }
}

foreach ($qaMalNodes as $node) mal_node($db,$node);
foreach (['a','b','c'] as $i=>$key) {
  $slug='qa-source-'.$key;
  $row=['slug'=>$slug,'source_id'=>990000+$i,'title'=>'Origen QA '.$key,'synopsis'=>'Sin datos en la lista de MAL.','cover'=>'https://cdn.animeav1.com/covers/20.jpg','weekday'=>0,'latest'=>'','published'=>'','start_date'=>null,'season'=>'','category'=>'QA Source','active'=>0,'catalog_complete'=>0,'updated_at'=>time()];
  upsert($db,'sa1_anime',array_keys($row),[$row],['slug'],['title']);
  $source=['slug'=>$slug,'genres'=>json_encode([['Acción','Comedia'],['Acción'],[]][$i],JSON_UNESCAPED_UNICODE),'premiere_year'=>[1998,2025,2006][$i],'airing_status'=>['finished_airing','currently_airing','not_yet_aired'][$i],'updated_at'=>time()];
  upsert($db,'sa1_catalog_source',array_keys($source),[$source],['slug'],['genres','premiere_year','airing_status','updated_at']);
}
// A deliberately different personal link must not override source filters.
mal_node($db,['id'=>990099,'title'=>'Título de otro registro privado','media_type'=>'tv','start_date'=>'2020-01-01','status'=>'currently_airing','genres'=>[['name'=>'Romance']]]);
upsert($db,'sa1_mal_links',['user_id','slug','mal_id','confirmed'],[['user_id'=>$owner,'slug'=>'qa-source-a','mal_id'=>990099,'confirmed'=>1]],['user_id','slug'],['mal_id','confirmed']);
upsert($db,'sa1_follow',['user_id','slug','status','favorite','excluded','score','notes'],[['user_id'=>$owner,'slug'=>'qa-source-a','status'=>'watching','favorite'=>0,'excluded'=>0,'score'=>0,'notes'=>'']],['user_id','slug'],['status']);
echo "Local filter fixtures ready; no external requests.\n";
