<?php
define('SEASON_BOOTSTRAPPED',true);
require dirname(__DIR__).'/htdocs/private/app.php';
if (!getenv('SEASON_WEB_SQLITE')) exit(1);
$db=db(); $checks=[];
function check_metadata(bool $value,string $name): void {global $checks;if(!$value)throw new RuntimeException($name);$checks[]=$name;}
$db->beginTransaction();
try {
  $node=['id'=>990099,'title'=>'Álgebra QA','media_type'=>'tv','start_date'=>'2002-10-03','genres'=>[['name'=>'Wrong genre']],'status'=>'finished_airing'];
  mal_node($db,$node);
  $map=sql($db,'SELECT mal_id FROM sa1_catalog_mal WHERE slug=?',['qa-filter-00'])->fetch();
  check_metadata($map && $map['mal_id']===null,'two_compatible_mal_ids_block_public_auto_match');
  mal_node($db,array_merge($node,['id'=>900000]));
  check_metadata(sql($db,'SELECT mal_id FROM sa1_catalog_mal WHERE slug=?',['qa-filter-00'])->fetch()['mal_id']===null,'ambiguous_match_is_not_restored_by_response_order');
  mal_node($db,['id'=>990098,'title'=>'Filtro QA 08','media_type'=>'movie','genres'=>[['name'=>'Action']]]);
  check_metadata(!sql($db,'SELECT mal_id FROM sa1_catalog_mal WHERE slug=?',['qa-filter-08'])->fetch(),'incompatible_format_cannot_fill_metadata');
  mal_node($db,['id'=>990097,'title'=>'Filtro QA 09','media_type'=>'tv'],false);
  check_metadata(!sql($db,'SELECT mal_id FROM sa1_catalog_mal WHERE slug=?',['qa-filter-09'])->fetch(),'xml_record_cannot_publish_public_metadata');
  $db->rollBack();
} catch(Throwable $error) {$db->rollBack();throw $error;}
$result=['ok'=>true,'count'=>count($checks),'checks'=>$checks];
file_put_contents(__DIR__.'/catalog-metadata-check.json',json_encode($result,JSON_PRETTY_PRINT));
echo json_encode($result,JSON_PRETTY_PRINT)."\n";
