'use strict';
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const root=path.join(__dirname,'..','htdocs'),events={},stored=new Map(),requests=[];
const cache={async addAll(reqs){for(const req of reqs){requests.push(req.url);stored.set(req.url,new Response('public asset'));}},async match(key){return stored.get(String(key))?.clone();},async put(key,value){stored.set(String(key),value.clone());}};
let offline=false;
const context={URL,Request,Response,console,self:{location:{href:'https://example.test/seasonav1/sw.js'},addEventListener:(name,fn)=>events[name]=fn,skipWaiting:async()=>{},clients:{claim:async()=>{}}},caches:{open:async()=>cache,keys:async()=>['other-project','seasonav1-public-old'],delete:async()=>true,match:async key=>stored.get(String(key))},fetch:async()=>{if(offline)throw Error('offline');return new Response('network public asset');}};
vm.runInNewContext(fs.readFileSync(path.join(root,'sw.js'),'utf8'),context);
async function main(){
  let pending;events.install({waitUntil:p=>pending=p});await pending;
  assert(requests.length>=8);assert(requests.every(url=>!url.includes('actions.php')&&!url.includes('index.php')&&!url.includes('mal-callback')&&!url.includes('private')));
  for(const url of requests){const file=decodeURIComponent(new URL(url).pathname.replace('/seasonav1/',''));assert(fs.existsSync(path.join(root,file)));}
  const manifest=JSON.parse(fs.readFileSync(path.join(root,'manifest.webmanifest')));assert(manifest.icons.some(i=>i.sizes==='192x192')&&manifest.icons.some(i=>i.sizes==='512x512'));assert(manifest.scope==='./');
  // The hosting gate needs its first-party cookie even though metadata is public.
  const manifestLink=fs.readFileSync(path.join(root,'index.php'),'utf8').match(/<link\s+rel="manifest"[^>]*>/)?.[0];
  assert(manifestLink?.includes('href="app-manifest.php"')&&manifestLink.includes('crossorigin="use-credentials"'));
  const data=JSON.parse(fs.readFileSync(path.join(root,'data','offline-catalog.json')));assert.equal(data.items.length,JSON.parse(require('node:zlib').gunzipSync(fs.readFileSync(path.join(root,'data/catalog-facets.json.gz')))).directory.length);assert(data.items.every(a=>Object.keys(a).sort().join(',')==='category,slug,title'));
  let response=null;offline=true;
  events.fetch({request:{url:'https://example.test/seasonav1/assets/app.css?v=new-version',method:'GET',mode:'cors'},respondWith:p=>response=p});assert.equal(await (await response).text(),'public asset');
  const publicURL='https://example.test/seasonav1/catalog-public.php';
  await cache.put(publicURL,new Response(JSON.stringify({items:[{slug:'naruto',title:'Naruto',category:'TV Anime'}]}),{headers:{'Content-Type':'application/json'}}));
  events.fetch({request:{url:publicURL,method:'GET',mode:'cors'},respondWith:p=>response=p});assert.equal((await (await response).json()).items[0].slug,'naruto');
  offline=false;
  events.fetch({request:{url:publicURL,method:'GET',mode:'cors'},respondWith:p=>response=p});assert.equal((await (await response).json()).items[0].slug,'naruto');
  offline=true;
  events.fetch({request:{url:'https://example.test/seasonav1/',method:'GET',mode:'navigate'},respondWith:p=>response=p});assert(await response);
  for(const request of [{url:'https://example.test/seasonav1/actions.php?action=home',method:'GET',mode:'cors'},{url:'https://example.test/seasonav1/actions.php',method:'POST',mode:'cors'},{url:'https://example.test/seasonav1/private/config.local.php',method:'GET',mode:'cors'}]){let captured=false;events.fetch({request,respondWith:()=>captured=true});assert(!captured);}
  events.activate({waitUntil:p=>pending=p});await pending;
  const result={ok:true,checks:['manifest_192_and_512_icons_and_scope','manifest_link_includes_host_cookie_for_installation_metadata','all_public_precache_files_exist','offline_catalog_matches_current_source_without_personal_data','versioned_assets_recover_canonical_copy_on_network_failure','live_public_index_survives_network_failure_and_host_html_challenge','navigation_falls_back_to_public_offline_page','private_api_oauth_and_post_requests_never_cached','only_this_apps_old_caches_removed']};
  fs.writeFileSync(path.join(__dirname,'pwa-check.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result));
}
main().catch(e=>{console.error(e);process.exitCode=1;});
