<?php
// CLI only. No password in command arguments, shell history or standard output.
declare(strict_types=1);
if(PHP_SAPI!=='cli'){http_response_code(404);exit();}
define('SEASON_BOOTSTRAPPED',true);
require dirname(__DIR__).'/htdocs/private/app.php';
require dirname(__DIR__).'/htdocs/private/backup.php';
try{
  $operation=$argv[1]??'';$path=$argv[2]??'';
  $password=(string)getenv('SEASON_BACKUP_PASSWORD');
  if(!in_array($operation,['backup','verify','restore'],true)||!$path)throw new RuntimeException('Uso: php tools/db_backup.php backup|verify|restore archivo.sa1backup. Clave en SEASON_BACKUP_PASSWORD. Restaurar exige una base vacía.');
  if($operation==='verify'){
    $stream=fopen($path,'rb');if(!$stream)throw new RuntimeException('No se pudo abrir el respaldo.');
    $result=backup_read($stream,$password,static function(){});
  }elseif($operation==='backup'){
    $stream=fopen($path,'xb');if(!$stream)throw new RuntimeException('El archivo ya existe o no puede crearse.');
    $result=backup_write(db(),$stream,$password);
  }else{
    // Create schema without seeding a catalog into an intentionally empty target.
    $sqlite=getenv('SEASON_WEB_SQLITE');$config=__DIR__.'/../htdocs/private/config.local.php';
    if($sqlite){$target=new PDO('sqlite:'.$sqlite);$target->exec('PRAGMA foreign_keys=ON');}
    else{$c=require $config;$target=new PDO('mysql:host='.$c['host'].';port='.(int)$c['port'].';dbname='.$c['database'].';charset=utf8mb4',$c['username'],$c['password']);}
    $target->setAttribute(PDO::ATTR_ERRMODE,PDO::ERRMODE_EXCEPTION);$target->setAttribute(PDO::ATTR_DEFAULT_FETCH_MODE,PDO::FETCH_ASSOC);
    migrate($target);$stream=fopen($path,'rb');if(!$stream)throw new RuntimeException('No se pudo abrir el respaldo.');
    $result=backup_restore($target,$stream,$password);
  }
  fclose($stream);echo json_encode(['ok'=>true,'operation'=>$operation,'result'=>$result]).PHP_EOL;
}catch(Throwable $error){fwrite(STDERR,'No se pudo completar la operación: '.$error->getMessage().PHP_EOL);exit(1);}
