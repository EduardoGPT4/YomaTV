<?php
// Simulate an old schema exclusively in memory. No provider requests are made.
define('SEASON_BOOTSTRAPPED',true);
require dirname(__DIR__) . '/htdocs/private/app.php';
$db=new PDO('sqlite::memory:');
$db->setAttribute(PDO::ATTR_ERRMODE,PDO::ERRMODE_EXCEPTION);
$db->setAttribute(PDO::ATTR_DEFAULT_FETCH_MODE,PDO::FETCH_ASSOC);
$db->exec('PRAGMA foreign_keys=ON');
migrate($db);seed_data($db);
$slug=(string)$db->query('SELECT slug FROM sa1_anime LIMIT 1')->fetchColumn();
foreach([1,2] as $id) {
  sql($db,'INSERT INTO sa1_users(id,name,email,password_hash,created_at,auth_version) VALUES(?,?,?,?,?,?)',[$id,'Legacy QA','legacy'.$id.'@example.test','unchanged-legacy-hash',1,0]);
  sql($db,"INSERT INTO sa1_watch_sync(user_id,slug,mal_id,target,generation,state,updated_at) VALUES(?,?,?,?,?,'pending',?)",[$id,$slug,20,8,'legacy-generation',1]);
}
sql($db,'INSERT INTO sa1_mal_connections(user_id,mal_user_id,mal_name,token_cipher,expires_at,connected_at,checked_at) VALUES(?,?,?,?,?,?,?)',[1,12345,'LegacyMAL','synthetic-legacy-cipher',time()+3600,1,1]);
$db->exec('ALTER TABLE sa1_watch_sync DROP COLUMN mal_account_id');
set_meta($db,'reliability_schema','0');set_meta($db,'schema_version','legacy');
migrate($db);
$owned=sql($db,'SELECT mal_account_id,state,target FROM sa1_watch_sync WHERE user_id=1')->fetch();
if((int)$owned['mal_account_id']!==12345 || $owned['state']!=='pending' || (int)$owned['target']!==8)throw new RuntimeException('Existing connected owner was not preserved');
$unknown=sql($db,'SELECT mal_account_id,state,error_kind,target FROM sa1_watch_sync WHERE user_id=2')->fetch();
if((int)$unknown['mal_account_id']!==0 || $unknown['state']!=='blocked' || $unknown['error_kind']!=='identity_unknown' || (int)$unknown['target']!==8)throw new RuntimeException('Unowned legacy marks could migrate to a new account');
$_SESSION['user_id']=2;
$db->beginTransaction();mal_bind_identity($db,54321);$db->commit();
if(sql($db,'SELECT error_kind FROM sa1_watch_sync WHERE user_id=2')->fetchColumn()!=='identity_unknown')throw new RuntimeException('Unknown old outbox was reactivated');
migrate($db);
if((int)$db->query('SELECT COUNT(*) FROM sa1_users WHERE password_hash=\'unchanged-legacy-hash\'')->fetchColumn()!==2)throw new RuntimeException('Legacy account changed');
echo json_encode(['ok'=>true,'checks'=>['legacy_connected_outbox_attributed_to_existing_account','legacy_disconnected_unknown_owner_blocked_without_data_loss','first_new_connection_does_not_reactivate_unknown_legacy_marks','upgrade_idempotent_accounts_unchanged']]);
