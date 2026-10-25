"""Create disposable same-origin video fixtures. These files must never be deployed."""
from pathlib import Path
import os,subprocess,json,urllib.request,sqlite3
ROOT=Path(__file__).resolve().parent.parent
qa=ROOT/'htdocs/__qa_player';qa.mkdir(exist_ok=True)
ffmpeg=ROOT.parent/'.venv/Lib/site-packages/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe'
subprocess.run([str(ffmpeg),'-hide_banner','-loglevel','error','-f','lavfi','-i','testsrc2=size=640x360:rate=12','-t','30','-c:v','libx264','-preset','ultrafast','-pix_fmt','yuv420p','-movflags','+faststart','-y',str(qa/'sample.mp4')],check=True)
(qa/'video.php').write_text("""<?php
$file=__DIR__.'/sample.mp4';$size=filesize($file);$start=0;$end=$size-1;
header('Content-Type: video/mp4');header('Accept-Ranges: bytes');
if(isset($_SERVER['HTTP_RANGE'])&&preg_match('/^bytes=(\\d+)-(\\d*)$/',$_SERVER['HTTP_RANGE'],$m)){
$start=(int)$m[1];$end=$m[2]!==''?min((int)$m[2],$end):$end;
if($start>$end||$start>=$size){http_response_code(416);header('Content-Range: bytes */'.$size);exit;}
http_response_code(206);header("Content-Range: bytes $start-$end/$size");}
$length=$end-$start+1;header('Content-Length: '.$length);$f=fopen($file,'rb');fseek($f,$start);
while($length>0&&!feof($f)){ $chunk=fread($f,min(65536,$length));echo $chunk;$length-=strlen($chunk); }fclose($f);
""",encoding='utf8')
(qa/'video-bridge.js').write_bytes((ROOT/'browser-extension/YomaTV-Brave/video-bridge.js').read_bytes())
(qa/'frame.html').write_text('''<!doctype html><html><head><meta charset="utf-8"><style>html,body{margin:0;background:#080d14;height:100%;overflow:hidden}video{width:100%;height:100%;object-fit:contain}</style></head><body><video id="player" src="video.php" preload="auto" controls playsinline></video><script src="video-bridge.js"></script><script src="frame.js"></script></body></html>''',encoding='utf8')
(qa/'frame.js').write_text('''const bridge=new YomaTVVideoBridge({send:message=>parent.postMessage({namespace:'seasonav1.fixture/v1',...message},location.origin),sourceAllowed:src=>new URL(src).origin===location.origin});window.addEventListener('message',e=>{if(e.source===parent&&e.origin===location.origin&&e.data?.namespace==='seasonav1.player.command/v1')bridge.command(e.data);});''',encoding='utf8')
(qa/'relay.js').write_text('''let nonce=null;window.addEventListener('message',e=>{const m=e.data,f=document.querySelector('iframe[data-season-player]');if(!f||e.origin!==location.origin)return;if(e.source===window&&m?.namespace==='seasonav1.player.command/v1'){if(m.type==='connect')nonce=m.nonce;f.contentWindow.postMessage(m,location.origin);}else if(e.source===f.contentWindow&&m?.namespace==='seasonav1.fixture/v1'&&m.nonce===nonce){window.postMessage({...m,namespace:'seasonav1.player.reply/v1'},location.origin);}});''',encoding='utf8')
env={**os.environ,'SEASON_WEB_SQLITE':str(ROOT/'verification/hardening-2026-10-14.sqlite'),'SEASON_WEB_MAL_TEST_URL':'http://127.0.0.1:8097'}
subprocess.run([r'C:/Users/Eduardo/.config/herd-lite/bin/php.exe','verification/seed_feature_preview.php'],cwd=ROOT,env=env,check=True)
with sqlite3.connect(env['SEASON_WEB_SQLITE']) as d:
    uid=d.execute("SELECT id FROM sa1_users WHERE email='preview@example.test'").fetchone()[0]
    d.execute('DELETE FROM sa1_watch_sync WHERE user_id=?',(uid,))
    d.execute("DELETE FROM sa1_watched WHERE user_id=? AND episode_id IN(SELECT id FROM sa1_episodes WHERE slug='naruto')",(uid,))
urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:8097/control',data=json.dumps({'mode':'normal','updates':{'20':{'status':'watching','score':8,'num_episodes_watched':5}},'deleted':[],'patch_calls':[]}).encode(),headers={'Content-Type':'application/json'})).close()
print('Synthetic 30-second video and isolated MAL preview ready. No external video downloaded.')
