'use strict';
const vm=require('node:vm'),fs=require('node:fs'),assert=require('node:assert/strict');
const context={Map,Number,Math,location:{hash:'#queue'},window:{addEventListener(){}},
 document:{addEventListener(){},querySelector(){return null;},querySelectorAll(){return [];}},
 localStorage:{getItem(){return null;}},e:String,icon:n=>`[${n}]`,
 button:(action,label,ic,attrs='')=>`<button data-action="${action}" ${attrs}>${label}</button>`,
 title:(...parts)=>parts.join(''),empty:(...parts)=>parts.join(''),searchBox:()=>'',connectionPanel:()=>'',
 filePresenceMarkup:()=>'',queueMicrotask:()=>{},api:async(action,{slug,page,phase})=>{assert.equal(action,'queue_page');const jobs=context.state.jobs.filter(j=>j.slug===slug&&(phase==='all'||j.status===phase)).sort((a,b)=>Number(a.number)-Number(b.number));const pages=Math.max(1,Math.ceil(jobs.length/36));page=Math.max(1,Math.min(page,pages));return {queue_page:{slug,page,pages,total:jobs.length,items:jobs.slice((page-1)*36,page*36),events:[]}};},
 bridge:{connected:true},state:{user:{id:1},settings:{language:'SUB'},jobs:[]},
 queueFilter:'all',search:'',detailState:null,view:'queue',activeJobs(){return context.state.jobs.filter(j=>!['confirmed','cancelled'].includes(j.status));}
};
vm.createContext(context);
vm.runInContext(fs.readFileSync(__dirname+'/../htdocs/assets/bridge-ui.js','utf8')+
 fs.readFileSync(__dirname+'/../htdocs/assets/downloads.js','utf8')+
 '\nthis.d={groupedJobs,groupCount,groupState,groupMatches,downloadQueueView,queueChapters,episodeCanPrepare,episodeTiles,episodeDownload,updateDownloadUI,loadQueuePage,invalidateQueuePages,setPage(n){queuePage=n;},setLive(values){liveJobs=new Map(values);}};',context);
(async()=>{
const checks=[],d=context.d;
context.state.jobs=Array.from({length:220},(_,i)=>({id:220-i,episode_id:220-i,slug:'naruto',title:'Naruto',cover:'cover',number:String(220-i),language:'SUB',server:'MP4Upload',height:1080,status:i>=210?'confirmed':'pending'}));
let group=d.groupedJobs()[0];assert.equal(d.groupedJobs().length,1);assert.equal(group.jobs.map(j=>Number(j.number)).join(','),Array.from({length:220},(_,i)=>i+1).join(','));
assert.equal((d.downloadQueueView().match(/data-queue-open=/g)||[]).length,1);assert.equal(d.groupCount(group),'10 / 220 descargados');checks.push('220_episodes_one_anime_row_numeric_order_and_count');
await d.loadQueuePage('naruto',1);let html=d.queueChapters(group);assert.equal((html.match(/data-queue-chapter=/g)||[]).length,36);assert.ok(html.includes('EP 1</strong>')&&html.includes('EP 36</strong>')&&html.includes('Página 1 de 7'));
d.setPage(2);await d.loadQueuePage('naruto',2);html=d.queueChapters(group);assert.ok(html.includes('EP 37</strong>')&&!html.includes('EP 1</strong>'));d.setPage(7);await d.loadQueuePage('naruto',7);assert.equal((d.queueChapters(group).match(/data-queue-chapter=/g)||[]).length,4);checks.push('chapter_pagination_first_next_and_last');
context.queueFilter='confirmed';await d.loadQueuePage('naruto',7,'confirmed');html=d.queueChapters(group);assert.equal((html.match(/data-queue-chapter=/g)||[]).length,10);assert.ok(html.includes('Página 1 de 1'));context.queueFilter='failed';assert.equal(d.groupMatches(group),false);context.queueFilter='all';context.search='NARUTO';assert.equal(d.groupMatches(group),true);context.search='otra';assert.equal(d.groupMatches(group),false);checks.push('status_filter_search_and_page_clamp');
assert.equal(d.episodeCanPrepare({id:1}),false);assert.equal(d.episodeCanPrepare({id:50}),false);
html=d.episodeTiles([{id:1,number:1,watched:false}]);assert.ok(html.includes('downloaded')&&html.includes('disabled')&&html.includes('Descargado')&&html.includes('Marcar visto'));checks.push('confirmed_and_queued_blocked_without_marking_watched');
context.state.jobs=[];assert.equal(d.episodeCanPrepare({id:999,download_job_id:500,status:'',download_status:'confirmed'}),false);assert.equal(d.episodeDownload({id:999,download_job_id:500,download_status:'confirmed'}).phase,'confirmed');checks.push('older_confirmed_job_from_detail_blocks_duplicates');
context.state.jobs=[{id:1,episode_id:1,language:'SUB',status:'exported'},{id:2,episode_id:2,language:'SUB',status:'pending'},{id:3,episode_id:3,language:'SUB',status:'confirmed'}];
d.setLive([[1,{status:'completed',progress:100}],[2,{status:'failed'}]]);
assert.equal(d.episodeCanPrepare({id:1}),false);assert.equal(d.episodeCanPrepare({id:2}),true);assert.equal(d.episodeCanPrepare({id:3}),false);assert.equal([1,2,3,4].filter(id=>d.episodeCanPrepare({id})).join(','),'2,4');checks.push('prepare_all_excludes_active_confirmed_and_verifying_allows_retry');
context.state.settings.language='DUB';assert.equal(d.episodeCanPrepare({id:3}),true);checks.push('download_status_scoped_to_language');
context.state.settings.language='SUB';context.state.jobs=[{id:3,episode_id:3,language:'SUB',status:'confirmed',slug:'naruto',number:'3',title:'Naruto'}];context.detailState={anime:{catalog_complete:true},episodes:[{id:3,number:'3'}]};
const input={checked:true,disabled:false,parentElement:{lastChild:{textContent:''}}},badge={},classes=new Set();
const tile={classList:{toggle(name,on){if(on)classes.add(name);else classes.delete(name);}},querySelector(selector){return selector==='.episode-select'?input:badge;}};
const all={},selected={};context.document.querySelector=selector=>selector==='#dialog'?{open:true}:selector.startsWith('[data-download-episode=')?tile:selector==='[data-action="queue_all"]'?all:selector==='[data-action="queue_selected"]'?selected:null;
d.updateDownloadUI();assert.equal(input.disabled,true);assert.equal(input.checked,false);assert.equal(all.disabled,true);assert.equal(selected.disabled,true);assert.equal(classes.has('downloaded'),true);assert.ok(badge.innerHTML.includes('Descargado'));checks.push('live_confirmation_unchecks_and_disables_selection_without_reopening');
d.invalidateQueuePages({jobs:[{slug:'naruto'}]});assert(d.queueChapters(group).includes('Cargando capítulos'));checks.push('queue_mutations_invalidate_cached_pages_instead_of_showing_old_status');
const result={ok:true,checks};fs.writeFileSync(__dirname+'/downloads-client-check.json',JSON.stringify(result,null,2));process.stdout.write(JSON.stringify(result,null,2));

})().catch(error=>{console.error(error);process.exitCode=1;});
