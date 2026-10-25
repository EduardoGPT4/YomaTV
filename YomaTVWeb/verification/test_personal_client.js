'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const store=()=>{const map=new Map();return {map,get length(){return map.size;},getItem:k=>map.get(k)||null,setItem:(k,v)=>map.set(k,String(v)),removeItem:k=>map.delete(k),key:i=>[...map.keys()][i]};};
const calls=[],pending=[],timers=new Map();let clock=0;
const ctx=vm.createContext({console,structuredClone,crypto:require('node:crypto').webcrypto,localStorage:store(),sessionStorage:store(),Map,Set,Date,Number,Math,String,JSON,
  MutationObserver:class{observe(){}},CustomEvent:class{},document:{hidden:false,addEventListener(){},dispatchEvent(){},getElementById:()=>({open:false}),querySelector:()=>null},
  setTimeout:fn=>{timers.set(++clock,fn);return clock;},clearTimeout:id=>timers.delete(id),
  state:{user:{id:1},anime:[]},view:'library',radio:{libraryScope:'1',library:{favorites:['abcdefghijk'],lists:[]}},render(){},toast(){},detailDrafts:new Map(),
  bridge:{forget(){ctx.forgot=true;}},invalidateSettingsSync(){},e:s=>String(s).replaceAll('<','&lt;'),
  api:(action,data)=>{calls.push([action,data]);return new Promise(resolve=>pending.push(resolve));}});
vm.runInContext(fs.readFileSync('htdocs/assets/personal-ui.js','utf8'),ctx);
(async()=>{
  const loading=ctx.loadPersonalUI();pending.shift()({personal:{collections:[],options:{},radio:{favorites:['lmnopqrstuv'],lists:[],revision:'a'.repeat(32)}}});await loading;
  assert.equal(ctx.radio.library.favorites[0],'abcdefghijk');assert(ctx.radio.cloudConflict); // legacy local favorites must not disappear
  assert(calls.some(([action])=>action==='catalog_pulse'));pending.shift()({catalog_worker:{skipped:true}});
  const checks=['legacy_radio_favorites_are_preserved_for_explicit_conflict_merge','first_authenticated_visit_triggers_the_bounded_central_worker'];
  ctx.resetPersonalUI();ctx.state.user.id=2;ctx.radio.libraryScope='2';ctx.radio.library={favorites:[],lists:[]};
  const old=ctx.loadPersonalUI();ctx.resetPersonalUI();ctx.state.user.id=3;ctx.radio.libraryScope='3';ctx.radio.library={favorites:[],lists:[]};
  pending.shift()({personal:{collections:[{key:'private-user-two'}],radio:{favorites:['abcdefghijk'],lists:[],revision:'b'.repeat(32)},options:{}}});await old;
  assert.equal(vm.runInContext('personalData',ctx),null);assert.equal(ctx.radio.library.favorites.length,0);
  checks.push('late_account_load_cannot_install_another_users_collections_or_radio');
  vm.runInContext("personalData={options:{shared:true,forget_pc:true}}",ctx);
  for(const storage of [ctx.localStorage,ctx.sessionStorage]){storage.setItem('seasonav1.draft.3:settings-form::','private');storage.setItem('seasonav1.draft.9:settings-form::','other');storage.setItem('seasonav1.radio.library.3','private');storage.setItem('unrelated.setting','keep');}
  ctx.clearSharedAccountData();assert(ctx.forgot);
  for(const storage of [ctx.localStorage,ctx.sessionStorage]){assert.equal(storage.getItem('seasonav1.draft.3:settings-form::'),null);assert.equal(storage.getItem('seasonav1.radio.library.3'),null);assert.equal(storage.getItem('seasonav1.draft.9:settings-form::'),'other');assert.equal(storage.getItem('unrelated.setting'),'keep');}
  checks.push('shared_computer_cleanup_is_scoped_to_current_user_and_can_forget_pc_pairing');
  const p={episode:{id:6},prefetchStarted:false};ctx.playerView=p;
  const before=calls.length;ctx.maybePrefetchNext(p,{position:84,duration:100});assert.equal(calls.length,before);
  ctx.maybePrefetchNext(p,{position:85,duration:100});ctx.maybePrefetchNext(p,{position:95,duration:100});assert.equal(calls.length,before+1);assert.equal(calls.at(-1)[0],'player_prefetch');
  pending.shift()({prefetch:null});await Promise.resolve();checks.push('next_episode_prefetch_is_one_metadata_request_near_the_end_without_loading_video');
  assert(ctx.sagaWatchOrder({related:{watch_order:[{slug:'naruto',title:'<private>',relation:'prequel',watched:5,total:12}]}}).includes('&lt;private>'));
  checks.push('saga_order_escapes_titles_and_displays_personal_progress');
  const batches=[];ctx.api=async(action,data)=>{assert.equal(action,'download_events');batches.push(data.items);return {};};ctx.bridge.info={device:{id:'a'.repeat(32)}};ctx.state.installation='fixture';
  const statuses=Array.from({length:1000},(_,i)=>({web_id:i+1,status:'pending'}));await ctx.persistDownloadEvents(statuses,3);assert.equal(batches.length,5);assert(batches.every(batch=>batch.length<=200));
  await ctx.persistDownloadEvents(statuses,3);assert.equal(batches.length,5);vm.runInContext('downloadEventAt=0',ctx);statuses[500].status='failed';statuses[500].reason='Sin conexión';await ctx.persistDownloadEvents(statuses,3);assert.equal(batches.length,6);assert.equal(batches.at(-1).length,1);assert.equal(batches.at(-1)[0].id,501);
  ctx.resetPersonalUI();assert.equal(vm.runInContext('downloadEventStates.size',ctx),0);checks.push('1000_pc_jobs_send_bounded_initial_batches_then_only_changed_states_and_clear_on_account_change');
  const result={ok:true,checks};fs.writeFileSync('verification/personal-client-check.json',JSON.stringify(result,null,2));console.log(JSON.stringify(result));
})().catch(error=>{console.error(error);process.exitCode=1;});
