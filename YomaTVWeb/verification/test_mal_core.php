<?php
// Run only against the disposable local fixture, never deploy this file.
define('SEASON_BOOTSTRAPPED', true);
require dirname(__DIR__) . '/htdocs/private/app.php';
function check(bool $condition, string $name): void {
  if (!$condition) throw new RuntimeException('Failed: ' . $name);
  echo "Passed: $name\n";
}
$db = db();
$user = (int) sql($db, 'SELECT id FROM sa1_users WHERE email=?', ['preview@example.test'])->fetchColumn();
$_SESSION['user_id'] = $user;
$_SESSION['auth_version'] = 0;
$tokens = ['access_token' => 'mock-access-token', 'refresh_token' => 'mock-refresh-token', 'expires_at' => time() + 3600];
$cipher = mal_encrypt($tokens, $user);
check(mal_decrypt($cipher, $user) === $tokens, 'authenticated_encryption_roundtrip');
$legacyKey=base64_decode(mal_require_config()['encryption_key'],true);
$legacyIv=random_bytes(12);$legacyTag='';
$legacyData=openssl_encrypt(json_encode($tokens,JSON_THROW_ON_ERROR),'aes-256-gcm',$legacyKey,OPENSSL_RAW_DATA,$legacyIv,$legacyTag,'SeasonAV1-MAL:'.$user);
$legacyCipher=base64_encode($legacyIv.$legacyTag.$legacyData);
check(mal_decrypt($legacyCipher,$user)===$tokens,'pre_yomatv_connection_remains_readable_after_rebrand');
foreach([$user+10000,$user] as $index=>$id){
  $bad=$index?substr($legacyCipher,0,-8).'AAAAAAAA':$legacyCipher;
  try{mal_decrypt($bad,$id);check(false,'reject_legacy_cipher');}
  catch(WebError $error){check($error->status===409,$index?'legacy_tampering_rejected':'legacy_cipher_bound_to_its_original_user');}
}
foreach ([$user + 10000, $user] as $index => $id) {
  $bad = $index === 1 ? substr($cipher, 0, -8) . 'AAAAAAAA' : $cipher;
  try { mal_decrypt($bad, $id); check(false, 'reject_cipher'); }
  catch (WebError $error) { check($error->status === 409, $index ? 'tampered_cipher_rejected' : 'cipher_bound_to_user'); }
}
mal_begin($db);$state = $_SESSION['mal_oauth']['state'];
$_SESSION['mal_oauth']['issued_at'] = time() - 601;
try { mal_complete($db, ['state' => $state, 'code' => 'expired']); check(false, 'expired'); }
catch (WebError $error) { check($error->status === 403 && !isset($_SESSION['mal_oauth']), 'expired_state_consumed'); }
mal_begin($db);$state = $_SESSION['mal_oauth']['state'];
$_SESSION['mal_oauth']['session_hash'] = str_repeat('a', 64);
try { mal_complete($db, ['state' => $state, 'code' => 'foreign']); check(false, 'session'); }
catch (WebError $error) { check($error->status === 403, 'state_bound_to_browser_session'); }
mal_begin($db);$state = $_SESSION['mal_oauth']['state'];
try { mal_complete($db, ['state' => $state, 'code' => "header\r\ninjection"]); check(false, 'code'); }
catch (WebError $error) { check($error->status === 422, 'malformed_code_rejected'); }
foreach (['token_type' => 'Basic', 'expires_in' => -1, 'access_token' => "bad\r\nheader"] as $key => $value) {
  $response = ['token_type' => 'Bearer', 'expires_in' => 3600, 'access_token' => 'valid-test-token', 'refresh_token' => 'valid-refresh-token'];
  $response[$key] = $value;
  try { mal_tokens($response); check(false, 'tokens'); }
  catch (MalRemoteError $error) { check(true, 'malformed_token_' . $key); }
}
mal_begin($db);$state = $_SESSION['mal_oauth']['state'];
$_SESSION['mal_oauth']['user_id'] = $user + 10000;
try { mal_complete($db, ['state' => $state, 'code' => 'foreign']); check(false, 'user'); }
catch (WebError $error) { check($error->status === 403, 'state_bound_to_account'); }
