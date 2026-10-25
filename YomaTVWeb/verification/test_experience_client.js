'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const checks=[],events={},timeouts=new Map(),intervals=new Map();let clock=1,now=100000;
const dialog={addEventListener(){},open:true},nodes=new Map();
const ctx=vm.createContext({console,crypto:require('node:crypto').webcrypto,Date:class extends Date{static now(){return now;}},Math,Set,Map,Promise,
  document:{hidden:false,getElementById:id=>id==='dialog'?dialog:nodes.get(id),querySelector:s=>nodes.get(s),querySelectorAll:()=>[],addEventListener:(n,fn)=>events[n]=fn,createElement:()=>({className:'',isConnected:true,setAttribute(){},innerHTML:'',querySelector:s=>s==='button'?{}:{textContent:''},remove(){this.isConnected=false;}})},
  setTimeout:fn=>{timeouts.set(clock,fn);return clock++;},clearTimeout:id=>timeouts.delete(id),setInterval:fn=>{intervals.set(clock,fn);return clock++;},clearInterval:id=>intervals.delete(id),
  state:{user:{id:1}},detailState:{anime:{slug:'long-anime'},episodes:Array.from({length:220},(_,i)=>({id:i+1,number:String(i+1),watched:i<5}))},
  episodeCanPrepare:ep=>ep.id!==10,episodeTiles:eps=>eps.map(ep=>`<b data-episode="${ep.id}"></b>`).join(''),
  maybePrefetchNext(){},e:String,bridge:{},liveJobs:new Map(),toast(){},playerView:null,
  api:async (action,data)=>{ctx.calls.push({action,data});return {position_saved:true};},calls:[],opens:[],openOptions:[],openPlayer:async (id,options)=>{ctx.opens.push(id);ctx.openOptions.push(options);}
});
vm.runInContext(fs.readFileSync('htdocs/assets/experience-ui.js','utf8'),ctx);
vm.runInContext(`episodeSelection().add(1);episodeSelection().add(40);episodeSelection().add(10);`,ctx);
assert.equal(JSON.stringify(vm.runInContext('episodeSelectionIds()',ctx)),JSON.stringify([1,40]));
let html=vm.runInContext('detailEpisodesView(detailState.episodes)',ctx);assert.equal((html.match(/data-episode=/g)||[]).length,36);assert(html.includes('1 / 7'));
vm.runInContext("episodePages.set('1:long-anime',2)",ctx);html=vm.runInContext('detailEpisodesView(detailState.episodes)',ctx);assert(html.includes('data-episode="40"'));assert(!html.includes('data-episode="1"'));assert(html.includes('2 seleccionados'));
ctx.state.user.id=2;assert.equal(vm.runInContext('episodeSelectionIds().length',ctx),0);ctx.state.user.id=1;checks.push('220_chapters_page_36_and_selection_across_pages_excludes_blocked_and_other_users');
vm.runInContext(fs.readFileSync('htdocs/assets/player-experience.js','utf8'),ctx);
const stage={append(node){nodes.set('.player-next',node);}};nodes.set('.video-stage',stage);
ctx.playerView={episode:{id:6,slug:'long-anime'},chapters:[{id:6,number:'6'},{id:7,number:'7'}],playback:{mode:'first',revision:'a'.repeat(32),session_key:'b'.repeat(32),preferences:{autoplay_next:true}}};
const callbacks=vm.runInContext('playerExperience(playerView)',ctx);callbacks.onPosition({position:12.25,duration:30,paused:false});callbacks.onPosition({position:13,duration:30,paused:false});callbacks.onPosition({position:13,duration:30,paused:true});callbacks.onPosition({position:22.5,duration:30,paused:true},true);
assert.equal(ctx.calls.length,3);assert.equal(ctx.calls[0].data.position,12.25);assert.equal(ctx.calls[2].data.sequence,3);checks.push('position_is_throttled_but_pause_and_close_flush_with_monotonic_sequence');
dialog.open=false;ctx.playerView.playback.preferences.autoplay_next=false;callbacks.onEnded();assert.equal(intervals.size,1);ctx.document.hidden=true;
const tick=[...intervals.values()][0];now+=7000;tick();assert.equal(ctx.opens.length,0);now+=1000;tick();assert.equal(ctx.opens[0],7);assert.equal(ctx.opens[1],undefined);assert.equal(ctx.openOptions[0].autoplay,true);assert.equal(intervals.size,0);
ctx.document.hidden=false;callbacks.onEnded();vm.runInContext('cancelNextEpisode()',ctx);assert.equal(intervals.size,0);
callbacks.onEnded();ctx.state.user.id=2;now+=10000;[...intervals.values()][0]();assert.equal(ctx.opens.length,1);assert.equal(intervals.size,0);ctx.state.user.id=1;
dialog.open=true;callbacks.onEnded();assert.equal(intervals.size,0);dialog.open=false;
ctx.playerView.episode.id=7;callbacks.onEnded();assert.equal(intervals.size,0);
checks.push('next_always_on_including_hidden_tabs_uses_elapsed_time_and_requests_playback');
checks.push('countdown_cancels_on_manual_cancel_account_change_dialog_and_last_episode');
const source=fs.readFileSync('htdocs/assets/player-view.js','utf8')+fs.readFileSync('htdocs/assets/player-experience.js','utf8');
assert(!source.includes('player-autonext')&&!source.includes('player-anime-prefs')&&!source.includes('Iniciar revisionado')&&!source.includes('player-diagnostics'));
checks.push('removed_player_options_and_diagnostics_are_not_rendered');
const result={ok:true,count:checks.length,checks};fs.writeFileSync('verification/experience-client-check.json',JSON.stringify(result,null,2));console.log(JSON.stringify(result,null,2));
