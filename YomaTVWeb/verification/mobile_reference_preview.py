from pathlib import Path
import http.server,json,sqlite3,urllib.parse
ROOT=Path(__file__).resolve().parents[1]
rows=[]
fixture=ROOT/'verification/hardening-2026-10-14.sqlite'
if fixture.is_file():
 with sqlite3.connect(fixture) as db:
  rows=[dict(zip(['slug','title','cover','category'],r))for r in db.execute("SELECT slug,title,cover,category FROM sa1_anime WHERE cover<>'' LIMIT 6")]
 db.close()
if not rows:rows=[dict(slug='demo',title='Historia de prueba',cover='/assets/icon-192.png',category='TV Anime')]
fixtures=[dict(rows[i%len(rows)],active=True,latest=3,weekday=i%7+1,status='following',airing_status='currently_airing') for i in range(28)]
mobile=(ROOT/'htdocs/assets/mobile-app.js').read_text(encoding='utf8')
features=(ROOT/'htdocs/assets/feature-ui.js').read_text(encoding='utf8')
parts=features[features.index('function malTile('):features.index('function detailDownloadCounts(')]+features[features.index('function catalogPersonalSections('):features.index('function malLibraryView(')]
css='\n'.join((ROOT/'htdocs/assets'/f).read_text(encoding='utf8') for f in ['fonts.css','app.css','features.css','medianoche.css','mobile-app.css'])+'\n'+(ROOT.parent/'YomaTVAndroid/app/src/main/assets/native-layout.css').read_text(encoding='utf8')
css=css.replace('url(fonts/','url(/assets/fonts/')
base='''<!doctype html><html class="yoma-native" lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>CSS</style></head><body><header class="site-header"><div class="header-inner"><a class="brand"><img src="/assets/icon-192.png"><span>Yoma<span class="brand-accent">TV</span></span></a><div class="header-utilities"><button class="icon-button notification-button">♧</button><button class="account-button"><span class="avatar">H</span><span>Mi cuenta</span></button></div></div></header><main id="main"></main><script>
const state={user:{id:1},season:'otoño2026',anime:FIXTURES};let day=0,search='',view='schedule',catalogState=null;const catalogFilters={category:'',airing:''};const DAYS=['Lunes','Martes','Miércoles','Jueves','Viernes','Sábado','Domingo'];
const MAL_STATUSES={watching:'Viendo',plan_to_watch:'Por ver'};const malRefreshBusy=false;
const e=v=>String(v??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;');
const icon=n=>'<svg viewBox="0 0 24 24"><path d="'+({search:'M15 15 21 21M17 10a7 7 0 1 1-14 0 7 7 0 0 1 14 0',play:'M7 4 20 12 7 20Z',check:'m4 12 5 5 11-11',plus:'M12 4v16M4 12h16'}[n]||'M4 12h16')+'"/></svg>';
const searchBox=()=>'<label class="search-box">'+icon('search')+'<input id="search" placeholder="Buscar anime..."></label>';
const lookupAnime=slug=>state.anime.find(a=>a.slug===slug),positionText=s=>Math.floor(s/60)+':00',api=async()=>({catalog:{items:[],total:0}}),card=()=>'';
const featureHome={continue:[{...state.anime[0],number:2,position:300,duration:1400,episode_id:1}],total:3,watching_count:3,planned_count:0,unmatched:0,watching:state.anime.slice(0,3).map((a,i)=>({...a,mal_id:i+1,watched:i+2,num_episodes:12,status:'watching',score:8})),planned:[]};
MOBILE
PARTS
function render(){document.querySelector('#main').innerHTML=location.search.includes('home')?yomaHomeHero(state.anime)+catalogPersonalSections():yomaScheduleView()};render();
</script></body></html>'''.replace('CSS',css).replace('FIXTURES',json.dumps(fixtures)).replace('MOBILE',mobile).replace('PARTS',parts)
class Handler(http.server.BaseHTTPRequestHandler):
 def do_GET(self):
  path=urllib.parse.urlsplit(self.path).path
  if path=='/':data=b'<html><body style="background:#0e0d14"><iframe src="/frame?home" style="width:412px;height:850px;border:1px solid #393449"></iframe><iframe src="/frame?schedule" style="width:412px;height:850px;border:1px solid #393449"></iframe></body></html>';mime='text/html; charset=utf-8'
  elif path=='/frame':data=base.encode();mime='text/html; charset=utf-8'
  elif path.startswith('/assets/'):
   file=(ROOT/'htdocs'/path.lstrip('/')).resolve()
   if not file.is_relative_to((ROOT/'htdocs/assets').resolve())or file.suffix not in {'.woff2','.png'}or not file.is_file():self.send_error(404);return
   data=file.read_bytes();mime='image/png'if file.suffix=='.png'else'font/woff2'
  else:self.send_error(404);return
  self.send_response(200);self.send_header('Content-Type',mime);self.end_headers();self.wfile.write(data)
 def log_message(self,*_):pass
print('Read-only mobile preview http://127.0.0.1:8102',flush=True)
http.server.ThreadingHTTPServer(('127.0.0.1',8102),Handler).serve_forever()
