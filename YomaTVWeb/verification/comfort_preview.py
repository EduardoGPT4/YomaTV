"""Local visual/regression fixture; no real accounts, playback or provider writes."""
from pathlib import Path
import http.server,json,sqlite3,urllib.parse,hashlib
ROOT=Path(__file__).resolve().parents[1]
def read(name):return (ROOT/'htdocs/assets'/name).read_text(encoding='utf8')
def between(text,start,end):return text[text.index(start):text.index(end)]
app=read('app.js');features=read('feature-ui.js');tools=read('catalog-tools.js')
logic='\n'.join([read('mobile-app.js'),between(app,'function button(','function cards('),between(features,'function malTile(','function catalogPersonalSections('),between(app,'function animeDetailMarkup(','async function queueItems('),between(tools,'function detailDataView(','const RELATION_LABELS'),between(read('bridge-ui.js'),'function cardDownload(','function updateBridgeUI('),between(read('downloads.js'),'function episodeCanPrepare(','function updateDownloadUI('),between(read('experience-ui.js'),'function detailEpisodesView(','function refreshEpisodePage(')])
css='\n'.join(read(name) for name in ['fonts.css','app.css','features.css','medianoche.css','mobile-app.css','comfort.css'])+'\n'+(ROOT.parent/'YomaTVAndroid/app/src/main/assets/native-layout.css').read_text(encoding='utf8')
css=css.replace('url(fonts/','url(/assets/fonts/')
svg=between((ROOT/'htdocs/index.php').read_text(encoding='utf8'),'<svg class="svg-library"','<a class="skip-content"')
covers=[];dbpath=ROOT/'verification/hardening-2026-10-14.sqlite'
if dbpath.is_file():
 db=sqlite3.connect(dbpath);covers=[r[0]for r in db.execute("SELECT cover FROM sa1_anime WHERE cover<>'' LIMIT 3")];db.close()
rows=[dict(slug='anime-'+str(i),title=t,cover=covers[i%len(covers)]if covers else'/assets/icon-192.png',category='TV Anime',active=True,weekday=(__import__('datetime').datetime.now().weekday()+1),latest=9-i,episodes=9-i,catalog_complete=True,status='following'if i<2 else'none',favorite=False,next_airing=1793030000,mal=dict(status='watching',watched=8))for i,t in enumerate(['Bleach: Sennen Kessen-hen - Kashin-tan','Doumo, Suki na Hito ni Horegusuri wo Irai sareta Majo desu.','Mahou Shoujo Ikusei Keikaku'])]
base='''<!doctype html><html class="yoma-native" lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>CSS</style></head><body>SVG<header class="site-header"><div class="header-inner"><a class="brand"><img src="/assets/icon-192.png"><span>Yoma<span class="brand-accent">TV</span></span></a></div></header><main id="main"></main><dialog id="dialog" class="dialog anime-dialog"><button class="dialog-close icon-button" onclick="this.parentElement.close()">×</button><div id="dialog-body"></div></dialog><pre id="test-result"></pre><script>
const state={user:{id:7,is_admin:false},season:'otoño2026',anime:ROWS};let day=0,search='',view='discover',catalogState=null;const catalogFilters={category:'',airing:''};const DAYS=['Lunes','Martes','Miércoles','Jueves','Viernes','Sábado','Domingo'],MAL_STATUSES={watching:'Viendo'};
const e=v=>String(v??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;'),icon=n=>'<svg aria-hidden="true"><use href="#i-'+n+'"/></svg>';
const latestJob=()=>null,lookupAnime=slug=>state.anime.find(a=>a.slug===slug),episodeDownload=()=>({phase:'available',label:'Disponible'}),episodeSelection=()=>new Set(),episodeSelectionIds=()=>[],episodePages=new Map(),detailRelationsView=()=>'',sourceMalPanel=()=>'<p>Tu progreso se comparte con MyAnimeList.</p>',api=async()=>({catalog:{items:[],total:0}}),searchBox=()=>'',render=()=>{};
LOGIC
const anime={...state.anime[0],title:'Yuusha-kei ni Shosu: Choubatsu Yuusha 9004-tai Keimu Kiroku',season:'invierno2026',synopsis:'Una historia de aventura y fantasía. '.repeat(30),genres:['Acción','Aventura','Fantasía','Drama'],studios:['Studio KAI'],mal_mean:8.11};
const detailState={anime,episodes:Array.from({length:12},(_,i)=>({id:i+1,number:i+1,watched:i<3})),freshness:{episodes_at:1793000000,servers_checked:12,episodes_known:12},relations:[]};
const form='<form id="detail-form" class="detail-form"><select name="status" class="select-input" aria-label="Estado en mi biblioteca"><option>Viendo</option><option>Por ver</option></select><textarea class="form-input" name="notes"></textarea></form>';
const choiceForm='<form id="choice-form"><label class="field">Estado en MAL<select id="status-test" name="status" class="select-input" aria-label="Estado en MAL"><option value="">Todos los estados</option><option value="watching" selected>Viendo</option><option value="completed">Completado</option><option value="hold">En pausa</option><option disabled value="disabled">No disponible</option><option value="planned">Por ver</option></select></label><label class="field">Género<select id="genre-test" class="select-input" aria-label="Género">'+['Acción','Aventura','Comedia','Drama','Fantasía','Misterio','Romance','Deportes','<img src=x onerror=alert(1)>','Terror'].map((t,i)=>'<option value="'+i+'">'+e(t)+'</option>').join('')+'</select></label><button type="button" id="nested-test">Probar en otra ventana</button><p class="muted">Opciones de prueba; no se guarda ningún cambio real.</p></form>';
const mode=new URLSearchParams(location.search).get('view')||'home';
if(mode==='detail'){document.querySelector('#dialog-body').innerHTML=animeDetailMarkup(anime,detailState.episodes,detailState.episodes[3],form);document.querySelector('#dialog').showModal();}
else if(mode==='choices'){document.querySelector('#main').innerHTML=choiceForm;document.querySelector('#nested-test').onclick=()=>{document.querySelector('#dialog-body').innerHTML=choiceForm.replaceAll('-test','-nested');document.querySelector('#dialog').showModal();};}
else document.querySelector('#main').innerHTML='<section class="personal-section"><div class="card-grid personal-cards">'+state.anime.map((a,i)=>malTile({...a,mal_id:i+1,watched:3,num_episodes:12})).join('')+'</div></section>'+yomaTodaySection();
</script><script src="/assets/choice-sheet.js"></script><script src="/checks.js"></script></body></html>'''.replace('CSS',css).replace('SVG',svg).replace('ROWS',json.dumps(rows).replace('</','<\\/')).replace('LOGIC',logic)
index='''<html><body style="background:#0e0d14;color:#eee;font:16px sans-serif"><button id="run">Ejecutar pruebas de diseño y selectores</button><button onclick="document.querySelectorAll('iframe')[1].hidden=true">Vista compacta</button><pre id="results" style="max-height:110px;overflow:auto"></pre><div style="display:flex;gap:12px;align-items:start">'''+''.join(f'<iframe title="{view}" src="/frame?view={view}" style="flex:none;width:360px;height:820px;border:1px solid #393449"></iframe>'for view in ['home','detail&web=1','detail','choices'])+'''</div><script>document.querySelector('#run').onclick=async()=>{try{const frames=[...document.querySelectorAll('iframe')],checks=[];for(const width of[320,360,412,768,1280])for(const frame of frames.slice(0,-1)){frame.style.width=width+'px';await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));checks.push(...await frame.contentWindow.geometryChecks());}frames.slice(0,-1).forEach(f=>f.style.width='360px');checks.push(...await frames.at(-1).contentWindow.choiceChecks());const report={ok:true,checks,synthetic_data:true};document.querySelector('#results').textContent=JSON.stringify(report,null,2);await fetch('/result',{method:'POST',body:JSON.stringify(report)});}catch(error){document.querySelector('#results').textContent='FAIL: '+error.stack;}};</script></body></html>'''
class Handler(http.server.BaseHTTPRequestHandler):
 def do_GET(self):
  url=urllib.parse.urlsplit(self.path);path=url.path
  if path=='/':data=index.encode();mime='text/html; charset=utf-8'
  elif path=='/frame':
   content=base
   if urllib.parse.parse_qs(url.query).get('web'):content=content.replace('class="yoma-native"','')
   data=content.encode();mime='text/html; charset=utf-8'
  elif path=='/checks.js':data=(ROOT/'verification/comfort_browser_checks.js').read_bytes();mime='text/javascript'
  elif path.startswith('/assets/'):
   file=(ROOT/'htdocs'/path.lstrip('/')).resolve()
   if not file.is_relative_to((ROOT/'htdocs/assets').resolve())or file.suffix not in {'.woff2','.png','.js'}or not file.is_file():self.send_error(404);return
   data=file.read_bytes();mime={'.png':'image/png','.js':'text/javascript','.woff2':'font/woff2'}[file.suffix]
  else:self.send_error(404);return
  self.send_response(200);self.send_header('Content-Type',mime);self.end_headers();self.wfile.write(data)
 def do_POST(self):
  if self.path!='/result':self.send_error(404);return
  length=int(self.headers.get('Content-Length','0'))
  if not 0<length<40000:self.send_error(400);return
  report=json.loads(self.rfile.read(length));assert report.get('synthetic_data')is True
  report['source_sha256']={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest()for name in ['htdocs/assets/choice-sheet.js','htdocs/assets/comfort.css','htdocs/assets/app.js','htdocs/assets/feature-ui.js','htdocs/assets/catalog-tools.js']}
  (ROOT/'verification/comfort-browser-check.json').write_text(json.dumps(report,indent=2),encoding='utf8');self.send_response(204);self.end_headers()
 def log_message(self,*_):pass
print('Read-only fixture http://127.0.0.1:8103',flush=True)
http.server.ThreadingHTTPServer(('127.0.0.1',8103),Handler).serve_forever()
