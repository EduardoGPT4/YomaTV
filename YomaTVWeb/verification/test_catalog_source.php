<?php
define('SEASON_BOOTSTRAPPED',true);
require dirname(__DIR__).'/htdocs/private/app.php';
if (!getenv('SEASON_WEB_SQLITE')) exit(1);
$db=db(); $checks=[];
function source_check(bool $ok,string $name): void { global $checks; if(!$ok) throw new RuntimeException($name); $checks[]=$name; }
$db->beginTransaction();
try {
  $html=file_get_contents(__DIR__.'/source-filter-pages/naruto.html');
  catalog_source_detail($db,'naruto',svelte_state($html));
  $row=sql($db,'SELECT * FROM sa1_catalog_source WHERE slug=?',['naruto'])->fetch();
  source_check($row && (int)$row['premiere_year']===2002 && $row['airing_status']==='finished_airing','real_public_detail_year_and_status');
  source_check(in_array('Acción',json_decode($row['genres'],true),true),'real_public_detail_spanish_genres');
  catalog_source_detail($db,'naruto','media:{slug:"different-anime",genres:[{name:"Drama"}],status:2,startDate:"2025-01-01"}');
  source_check(sql($db,'SELECT * FROM sa1_catalog_source WHERE slug=?',['naruto'])->fetch()===$row,'another_animes_detail_cannot_override_source');
  catalog_source_detail($db,'naruto','media:{slug:"naruto",status:2},related:{genres:[{name:"Drama"}],startDate:"2025-01-01"}');
  source_check(sql($db,'SELECT * FROM sa1_catalog_source WHERE slug=?',['naruto'])->fetch()===$row,'related_anime_fields_cannot_fill_missing_root_metadata');
  source_check(catalog_source_genres(['Anthropomorphic','antropomorfico','Antropomórfico'])===['Antropomórfico'],'legacy_labels_and_real_source_slugs_are_canonical');
  $db->rollBack();
} catch(Throwable $error) { $db->rollBack(); throw $error; }
$result=['ok'=>true,'count'=>count($checks),'checks'=>$checks];
file_put_contents(__DIR__.'/catalog-source-check.json',json_encode($result,JSON_PRETTY_PRINT));
echo json_encode($result,JSON_PRETTY_PRINT)."\n";
