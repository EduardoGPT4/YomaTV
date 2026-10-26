from pathlib import Path
import http.server,urllib.parse
ROOT=Path(__file__).resolve().parents[1]
view=(ROOT/'htdocs/assets/player-view.js').read_text(encoding='utf8')
renderer=view[view.index('function watchServerButtons('):view.index('function playerMalConfirmed(')]
native=(ROOT.parent/'YomaTVAndroid/app/src/main/assets/native-integration.js').read_text(encoding='utf8').split('style.textContent=`',1)[1].split('` + (nativeLayout',1)[0]
native+=(ROOT.parent/'YomaTVAndroid/app/src/main/assets/native-layout.css').read_text(encoding='utf8')
page='''<!doctype html><html lang="es" data-theme="dark"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'''+''.join('<link rel="stylesheet" href="/assets/'+n+'">' for n in ['fonts.css','app.css','features.css','medianoche.css','mobile-app.css'])+'''<style>body{margin:0;padding:16px}main{width:100%;max-width:960px;margin:0 auto}h1{font-size:22px}#result{white-space:pre-wrap;font-size:14px;color:var(--muted)}</style></head><body><main><h1>Servidores de reproducción</h1><section class="watch-servers" aria-label="Servidores de reproducción"><div class="watch-server-groups"></div></section><p id="result"></p></main><script>
const e=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[c]);
'''+renderer+'''
const p={index:2,servers:[{server:'MP4Upload',language:'DUB'},{server:'Voe',language:'SUB'},{server:'MP4Upload',language:'SUB'},{server:'Voe',language:'DUB'}]};
if(location.search.includes('native')){document.documentElement.classList.add('yoma-native');const style=document.createElement('style');style.textContent=NATIVE_STYLE;document.head.append(style)}
function draw(){document.querySelector('.watch-server-groups').innerHTML=watchServerButtons(p);}
draw();document.addEventListener('click',e=>{const b=e.target.closest('[data-watch-server]');if(b){p.index=Number(b.dataset.watchServer);draw();report();}});
function report(){const rows=[...document.querySelectorAll('.watch-server-group')].map(row=>{const r=row.getBoundingClientRect();return {audio:row.querySelector('.watch-server-label').textContent,top:r.top,bottom:r.bottom,buttons:[...row.querySelectorAll('button')].map(b=>{const br=b.getBoundingClientRect();return {label:b.getAttribute('aria-label'),selected:b.getAttribute('aria-pressed'),left:br.left,right:br.right,top:br.top,bottom:br.bottom}})}});document.querySelector('#result').textContent='Seleccionado: '+p.servers[p.index].server+' · '+p.servers[p.index].language;window.layoutReport={width:innerWidth,scrollWidth:document.documentElement.scrollWidth,rows}}
window.addEventListener('load',report);window.addEventListener('resize',report);
</script></body></html>'''
import json
page=page.replace('NATIVE_STYLE',json.dumps(native))
class Handler(http.server.BaseHTTPRequestHandler):
 def do_GET(self):
  path=urllib.parse.urlsplit(self.path).path
  if path=='/matrix':
   data=('<html><body style="margin:0;background:#0e0d14;color:#f4f1ea"><h1 style="font:22px sans-serif;padding:12px">Móvil · 320 y 412 px</h1>'+''.join('<iframe title="Móvil '+str(w)+'" src="/?native" style="width:'+str(w)+'px;height:460px;border:1px solid #493c5d;vertical-align:top;margin:12px"></iframe>' for w in [320,412])+'</body></html>').encode();mime='text/html; charset=utf-8'
  elif path=='/': data=page.encode();mime='text/html; charset=utf-8'
  elif path.startswith('/assets/'):
   file=(ROOT/'htdocs'/path.lstrip('/')).resolve()
   if not file.is_relative_to((ROOT/'htdocs/assets').resolve()) or file.suffix not in {'.css','.woff2'} or not file.is_file():self.send_error(404);return
   data=file.read_bytes();mime='text/css' if file.suffix=='.css' else 'font/woff2'
  else:self.send_error(404);return
  self.send_response(200);self.send_header('Content-Type',mime);self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(data)
 def log_message(self,*_):pass
print('Read-only layout preview on http://127.0.0.1:8102',flush=True)
http.server.ThreadingHTTPServer(('127.0.0.1',8102),Handler).serve_forever()
