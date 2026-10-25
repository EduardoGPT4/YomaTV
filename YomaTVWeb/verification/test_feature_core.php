<?php
define('SEASON_BOOTSTRAPPED',true);
require dirname(__DIR__).'/htdocs/private/app.php';
function verify(bool $ok,string $name): void {if(!$ok)throw new RuntimeException($name);echo "Passed: $name\n";}
$db=db();$_SESSION['user_id']=(int)sql($db,'SELECT id FROM sa1_users WHERE email=?',['preview@example.test'])->fetchColumn();
verify(title_key('Pokémon: CAFÉ')===title_key('pokemon cafe'),'accent_case_punctuation_normalization');
verify(title_key('東京2026')!==title_key('2026'),'cjk_titles_do_not_collapse_to_year');
verify(!compatible_match(['start_date'=>'2002-01-01','category'=>'TV Anime'],['start_date'=>'2004-01-01','media_type'=>'tv']),'different_year_is_not_automatic');
verify(!compatible_match(['start_date'=>'','category'=>'OVA'],['start_date'=>'','media_type'=>'tv']),'different_format_is_not_automatic');
$m=sql($db,'SELECT * FROM sa1_mal_anime WHERE mal_id=20')->fetch();
if($m){$index=['naruto'=>[['slug'=>'naruto','title'=>'Naruto','start_date'=>'2002-10-03','category'=>'TV Anime'],['slug'=>'second-naruto','title'=>'Naruto','start_date'=>'2002-10-03','category'=>'TV Anime']]];
  sql($db,'DELETE FROM sa1_mal_links WHERE user_id=? AND mal_id=20',[uid()]);mal_try_match($db,$m,$index);
  verify(!sql($db,'SELECT slug FROM sa1_mal_links WHERE user_id=? AND mal_id=20',[uid()])->fetchColumn(),'ambiguous_exact_titles_require_selection');
  mal_try_match($db,$m,mal_catalog_index($db));
}
$next=next_airing(['active'=>1,'published'=>'2026-10-01T12:00:00-06:00']);verify($next===null,'overdue_estimate_is_unknown_instead_of_inventing_another_week');
verify(next_airing(['active'=>0,'published'=>'2026-10-01T12:00:00-06:00'])===null,'inactive_anime_has_no_estimated_next_event');
$number='99991';sql($db,'DELETE FROM sa1_notifications WHERE user_id=? AND slug=? AND number=?',[uid(),'naruto',$number]);
notify_new_episode($db,'naruto',$number);notify_new_episode($db,'naruto',$number);
verify((int)sql($db,'SELECT COUNT(*) FROM sa1_notifications WHERE user_id=? AND slug=? AND number=?',[uid(),'naruto',$number])->fetchColumn()===1,'new_episode_notifications_deduplicate');
sql($db,'DELETE FROM sa1_notifications WHERE slug=? AND number=?',['naruto',$number]);
$_SESSION['user_id']=(int)sql($db,'SELECT id FROM sa1_users WHERE email=?',['admin@example.test'])->fetchColumn();
set_meta($db,'catalog_job_lock',(string)(time()+60));
set_meta($db,'maintenance_next_due',(string)(time()+43200));set_meta($db,'maintenance_pending','[]');
verify(maintenance_run($db)['skipped'],'fresh_schedule_respects_existing_catalog_lease_without_scraping');
verify(!external_maintenance_enabled(),'external_cron_disabled_without_compatible_host_configuration');
set_meta($db,'maintenance_pending','["naruto"]');set_meta($db,'maintenance_step_retry',(string)(time()+900));
verify(maintenance_run($db)['skipped'],'scraper_retry_cooldown_does_not_scrape');
set_meta($db,'maintenance_pending','[]');set_meta($db,'maintenance_step_retry','0');
record_scraper_failure($db,'Aviso de estructura cambiado para QA');verify(maintenance_status($db)['error']==='Aviso de estructura cambiado para QA','scraper_failure_visible_in_admin_status');
set_meta($db,'scraper_error','');
