'use strict';
const vm=require('node:vm'),fs=require('node:fs'),assert=require('node:assert/strict');
const elements=new Map(),listeners=new Map(),players=[];
for(const id of ['#radio-dock','#dialog','#radio-track-title','#radio-track-anime','#radio-youtube-link','#radio-status'])elements.set(id,{hidden:true,open:false,textContent:'',innerHTML:'',replaceChildren(){this.innerHTML='';}});
const context={window:{},location:{origin:'https://hk-br035.gt.tc'},localStorage:{getItem:()=>null,setItem:()=>{}},CustomEvent:class{constructor(type){this.type=type;}},setTimeout,clearTimeout,queueMicrotask:()=>{},loadPersonalUI:async()=>{},
 document:{hidden:false,body:{classList:{add(){},remove(){}}},getElementById:id=>elements.get('#'+id),querySelector:id=>elements.get(id),addEventListener:(type,cb)=>listeners.set(type,cb),dispatchEvent(){}},
 YT:{Player:class{constructor(id,config){this.config=config;this.loaded=[];players.push(this);}loadVideoById(id){this.loaded.push(id);}playVideo(){this.played=true;}pauseVideo(){this.paused=true;}setVolume(v){this.volume=v;}destroy(){this.destroyed=true;}}}};
context.window.YT=context.YT;vm.createContext(context);vm.runInContext(fs.readFileSync(__dirname+'/../htdocs/assets/radio.js','utf8')+'\nthis.radio=new AnimeRadio();',context);
(async()=>{
 const r=context.radio;r.setTracks({tracks:[{id:'a',type:'OP',title:'Opening',anime:'Anime',artist:'Artist',url:'https://www.youtube.com/watch?v=a'},{id:'b',type:'ED',title:'Ending',anime:'Anime',artist:'Artist',url:'https://www.youtube.com/watch?v=b'}]});
 assert.equal(r.enabled,false);assert.equal(players.length,0);
 await r.start();const p=players[0];r.next();assert.equal(players.length,1);assert.equal(p.loaded.length,0);
 p.config.events.onReady({target:p});assert.equal(p.loaded.at(-1),'b');assert.equal(p.volume,50);
 p.config.events.onStateChange({data:0});assert.equal(p.loaded.at(-1),'a');
 context.document.hidden=true;listeners.get('visibilitychange')();assert.equal(p.paused,true);
 r.next(1,true);assert.equal(p.loaded.at(-1),'a');context.document.hidden=false;
 r.setVolume(200);assert.equal(p.volume,100);
 elements.get('#dialog').open=true;r.play();assert.notEqual(p.played,true);elements.get('#dialog').open=false;
 r.minimize();assert.equal(r.minimized,true);assert.equal(p.paused,true);const loaded=p.loaded.length;r.next(1,true);assert.equal(p.loaded.length,loaded);
 p.config.events.onStateChange({data:1});assert.equal(r.playing,false);assert.equal(p.paused,true);
 r.play();assert.equal(r.minimized,false);assert.equal(p.played,true);
 r.off();assert.equal(p.destroyed,true);assert.equal(elements.get('#radio-dock').hidden,true);assert.equal(r.enabled,false);
 p.config.events.onReady({target:p});assert.equal(r.enabled,false);
 vm.runInContext(fs.readFileSync(__dirname+'/../htdocs/assets/radio-library.js','utf8'),context);
 r.setLibraryScope(1);r.library.favorites=['a'];r.collection='favorites';assert.equal(r.playlist().length,1);r.collection='all';r.library.lists=[{id:'c'.repeat(16),name:'Test',ids:['b']}];r.collection='c'.repeat(16);assert.equal(r.playlist()[0].t.id,'b');
 r.collection='missing';await r.start();assert.equal(r.enabled,false);r.setLibraryScope(2);assert.equal(r.library.favorites.length,0);assert.equal(r.library.lists.length,0);
 r.collection='all';await r.start();const p2=players.at(-1);p2.config.events.onReady({target:p2});
 p2.config.events.onError({data:100});p2.config.events.onError({data:101});p2.config.events.onError({data:150});assert.equal(r.playing,false);assert.equal(p2.paused,true);assert(r.message.includes('varios videos'));r.off();
 const result={ok:true,checks:['off_by_default_without_youtube','track_change_before_player_ready','advance_when_ended','pause_when_page_hidden','no_hidden_autoplay','clamped_volume','modal_blocks_play','minimize_pauses_and_blocks_background_play','expand_resumes_after_user_action','off_destroys_player','stale_callback_does_not_restart','favorites_and_named_lists_filter_real_tracks_and_empty_lists_do_not_autoplay','radio_library_is_scoped_to_account','unavailable_videos_stop_after_three_errors_and_off_cancels_retry']};
 fs.writeFileSync(__dirname+'/radio-client-check.json',JSON.stringify(result,null,2));process.stdout.write(JSON.stringify(result));
})().catch(error=>{process.stderr.write(error.stack);process.exitCode=1;});
