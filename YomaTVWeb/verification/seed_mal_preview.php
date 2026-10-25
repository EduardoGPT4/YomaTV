<?php
// Disposable UI fixture; no real account, tokens or network authorization.
define('SEASON_BOOTSTRAPPED', true);
require dirname(__DIR__) . '/htdocs/private/app.php';
if (!getenv('SEASON_WEB_SQLITE') || !getenv('SEASON_WEB_MAL_TEST_URL')) exit(1);
$db = db();
$user = (int) sql($db, 'SELECT id FROM sa1_users WHERE email=?', ['preview@example.test'])->fetchColumn();
$tokens = ['access_token' => 'mock-access-token', 'refresh_token' => 'mock-refresh-token', 'expires_at' => time() + 3600];
upsert($db, 'sa1_mal_connections', ['user_id', 'mal_user_id', 'mal_name', 'token_cipher', 'expires_at', 'connected_at', 'checked_at', 'needs_auth', 'refresh_lock_until'],
  [['user_id' => $user, 'mal_user_id' => 12345, 'mal_name' => 'LocalMAL_Test', 'token_cipher' => mal_encrypt($tokens, $user), 'expires_at' => $tokens['expires_at'], 'connected_at' => time(), 'checked_at' => time(), 'needs_auth' => 0, 'refresh_lock_until' => 0]],
  ['user_id'], ['mal_user_id', 'mal_name', 'token_cipher', 'expires_at', 'connected_at', 'checked_at', 'needs_auth', 'refresh_lock_until']);
echo "Local UI fixture ready; no real MAL account used.\n";
