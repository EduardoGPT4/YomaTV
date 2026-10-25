<?php
define('SEASON_BOOTSTRAPPED',true);
require dirname(__DIR__).'/htdocs/private/app.php';
if(getenv('SEASON_WEB_SQLITE')!==':memory:')throw new RuntimeException('Use an in-memory fixture.');
$db=db();$checks=[];
function verify_data(bool $ok,string $name): void {global $checks;if(!$ok)throw new RuntimeException($name);$checks[]=$name;}
$state=svelte_state(file_get_contents(__DIR__.'/source-filter-pages/naruto.html'));
catalog_source_detail($db,'naruto',$state);
$dates=catalog_freshness($db,'naruto');
verify_data($dates['genres_at']>0 && $dates['airing_at']>0 && $dates['episodes_at']===0,'metadata_success_does_not_mark_episode_list_checked');
catalog_relations_import($db,'naruto',file_get_contents(__DIR__.'/source-filter-pages/naruto.html'),$state);
$r=sql($db,'SELECT * FROM sa1_relations WHERE slug=? AND target=?',['naruto','naruto-shippuuden'])->fetch();
verify_data($r && $r['relation']==='sequel' && $r['state']==='pending' && $r['reviewed_by']===null,'source_relation_label_is_preserved_and_requires_review');
catalog_relations_import($db,'naruto',file_get_contents(__DIR__.'/source-filter-pages/naruto.html'),$state);
verify_data((int)sql($db,'SELECT COUNT(*) FROM sa1_relations WHERE slug=?',['naruto'])->fetchColumn()===2,'repeated_source_relation_refresh_does_not_duplicate_candidates');
verify_data(catalog_relations($db,'naruto')===[],'unreviewed_relations_are_not_public');
sql($db,"UPDATE sa1_relations SET state='approved' WHERE slug='naruto' AND target='naruto-shippuuden'");
verify_data(count(catalog_relations($db,'naruto'))===1,'only_reviewed_relations_are_public');
$directory=sync_directory_html($db,file_get_contents(__DIR__.'/source-filter-pages/directory.html'),1);
verify_data($directory['count']===20 && $directory['total']>=1000,'real_source_directory_parser_accepts_cached_public_html');
$empty='<script>kit.start(app,{data:{results:[],pagination:{currentPage:1,totalPages:0,totalRecords:0}}})</script>';
verify_data(sync_directory_html($db,$empty,1)['count']===0,'empty_year_partition_is_valid');
try{sync_directory_html($db,'<script>kit.start(app,{data:{results:[],pagination:{currentPage:2,totalPages:3,totalRecords:60}}})</script>',1);throw new RuntimeException('wrong page accepted');}
catch(ScraperError $error){$checks[]='changed_or_wrong_source_page_is_rejected';}
$source=sql($db,'SELECT * FROM sa1_catalog_source WHERE slug=?',['naruto'])->fetch();
catalog_source_detail($db,'naruto','media:{slug:"different",genres:[],status:2,startDate:"2026-01-01"}');
verify_data(sql($db,'SELECT * FROM sa1_catalog_source WHERE slug=?',['naruto'])->fetch()===$source,'related_title_metadata_cannot_overwrite_root');
sql($db,'INSERT INTO sa1_users(name,email,password_hash,created_at) VALUES(?,?,?,?)',['QA','gap@example.test','unused',time()]);
$owner=(int)$db->lastInsertId();
sql($db,"INSERT INTO sa1_follow(user_id,slug,status,notes) VALUES(?,?,'watching','')",[$owner,'naruto']);
sql($db,'INSERT INTO sa1_notice_baseline(slug,number_value) VALUES(?,?)',['naruto',1]);
notify_new_episode($db,'naruto','4');notify_episode_gap($db,'naruto','4',[1,2,3,4]);
verify_data((int)sql($db,'SELECT COUNT(*) FROM sa1_notifications WHERE user_id=?',[$owner])->fetchColumn()===3,'missed_intermediate_episodes_survive_schedule_latest_update_without_duplicates');
verify_data(!sql($db,'SELECT slug FROM sa1_notice_baseline WHERE slug=?',['naruto'])->fetchColumn(),'gap_baseline_is_cleared_only_after_successful_detail');
catalog_touch($db,'naruto',['directory_at'],time()+86400);
sql($db,'UPDATE sa1_anime SET title=? WHERE slug=?',['Newer title from verified directory','naruto']);
sql($db,'UPDATE sa1_catalog_source SET genres=?,updated_at=? WHERE slug=?',['["New verified metadata"]',time()+86400,'naruto']);
set_meta($db,'catalog_source_version','force-snapshot-upgrade');seed_catalog_source($db);
verify_data(sql($db,'SELECT title FROM sa1_anime WHERE slug=?',['naruto'])->fetchColumn()==='Newer title from verified directory' && sql($db,'SELECT genres FROM sa1_catalog_source WHERE slug=?',['naruto'])->fetchColumn()==='["New verified metadata"]','older_published_snapshot_cannot_overwrite_more_recent_verified_data');
$revoked=['user_id'=>$owner,'feed_key'=>bin2hex(random_bytes(32)),'scope'=>'all','updated_at'=>0];
calendar_write($db,$revoked);
verify_data(!is_file(calendar_feed_path($revoked['feed_key'])),'stale_worker_cannot_recreate_a_revoked_calendar_url');
$coverage=catalog_coverage($db);
verify_data($coverage['directory']['oldest']===(int)meta($db,'directory_seed_updated') && $coverage['directory']['newest']>time(),'directory_coverage_keeps_real_per_title_dates_instead_of_cycle_start');
$result=['ok'=>true,'count'=>count($checks),'checks'=>$checks,'network_requests'=>0];
file_put_contents(__DIR__.'/catalog-data-check.json',json_encode($result,JSON_PRETTY_PRINT));echo json_encode($result,JSON_PRETTY_PRINT)."\n";
