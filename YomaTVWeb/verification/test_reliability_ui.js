'use strict';
const fs = require('node:fs'), vm = require('node:vm'), assert = require('node:assert/strict');
const root = __dirname + '/../htdocs/assets/';
const read = name => fs.readFileSync(root + name, 'utf8');
const checks = [];
const storage = new Map(), badge = { hidden:true, dataset:{} }, dialog = {open:false,addEventListener(){},showModal(){this.open=true;}};
let form = null, body = {innerHTML:''}, modalCalls = 0;
const context = {
  console, Map, Set, WeakMap, Promise, JSON, Number, Math, Date, TextEncoder, Blob, URLSearchParams,
  location:{hash:'#queue'}, window:{addEventListener(){}},
  document:{hidden:false,activeElement:null,addEventListener(){},querySelectorAll(){return [];},
    querySelector(selector){return selector==='#dialog'?dialog:selector==='#dialog-body'?body:selector==='#detail-form'?form:selector==='[data-player-watch-badge]'?badge:null;}},
  localStorage:{getItem:key=>storage.get(key)||null,setItem:(key,value)=>storage.set(key,value),removeItem:key=>storage.delete(key)},
  setInterval(){return 0;},clearInterval(){},setTimeout(){return 0;},clearTimeout(){},queueMicrotask(){},
  state:{user:{id:1},csrf:'test',preferences_saved:true,installation:'test',settings:{workers:1,language:'SUB'},anime:[],jobs:[]},
  resultsBusy:false,resultUser:2,resultSignature:'',resultsTimer:0,
  view:'mal',queueFilter:'all',search:'',detailState:null,render(){context.renders++;},renders:0,
  radio:{pause(){}}, e:String,icon:name=>name,button:()=>'',title:()=>'',empty:()=>'',searchBox:()=>'',connectionPanel:()=>'',
  activeJobs(){return context.state.jobs.filter(j=>['pending','exported'].includes(j.status));},
  bridge:{token:'new-token',connected:true,capabilities:['settings'],supports:()=>true,ping:async()=>{},settings:async()=>{}},
  FormData:class {constructor(source){this.source=source;} *[Symbol.iterator](){for(const name of ['status','score','notes'])yield [name,this.source.elements[name].value];}}
};
vm.createContext(context);
const app = read('app.js');
vm.runInContext(app.slice(app.indexOf('let detailSequence'), app.indexOf('let resultsTimer')) +
  app.slice(app.indexOf('function modal('),app.indexOf('function requireUser')) +
  '\nthis.helpers={dialogTicket,dialogCurrent,captureDetailDraft,restoreDetailDraft,close(){dialogSequenceForTest();}};function dialogSequenceForTest(){detailSequence++;}',context);
// Intercept actual modal after exercising its capture behavior below.
vm.runInContext(read('feature-ui.js') + read('player-view.js') + read('bridge-ui.js') + read('downloads.js') + read('library-transfer.js') +
  '\nthis.ui={loadMalLibrary,editMal,matchMal,updatePlayerWatchBadge,applySettingsNow,syncResults,invalidateSettingsSync,settingsKey,settingsStamp,groupedJobs,groupCount,downloadQueueView,ensureQueueHistory,libraryImportChunks,setQueue(slug){queueAnime=slug;},setFilters(value){Object.assign(malFilters,value);},page(){return malLibraryPage;},getSettingsApplied(){return settingsApplied;}};',context);
const pending = [];
context.api = (action,data) => new Promise(resolve=>pending.push({action,data:{...data},resolve}));
const tick = () => new Promise(resolve=>setImmediate(resolve));
(async()=>{
  context.ui.setFilters({search:'nar'});
  const first=context.ui.loadMalLibrary();
  context.ui.setFilters({search:'naruto'});
  const second=context.ui.loadMalLibrary();
  pending[1].resolve({mal_library:{query:'naruto'}});await second;
  pending[0].resolve({mal_library:{query:'nar'}});await first;
  assert.equal(context.ui.page().query,'naruto');
  context.ui.setFilters({search:'one'});const third=context.ui.loadMalLibrary();
  context.ui.setFilters({search:'one piece'});pending[2].resolve({mal_library:{query:'one'}});await third;
  assert.equal(context.ui.page().query,'naruto');
  checks.push('latest_mal_search_wins_and_changed_debounced_query_cannot_be_replaced');

  context.modal=()=>{modalCalls++;};
  let edit=context.ui.editMal(20);context.helpers.close();
  pending[3].resolve({mal_entry:{title:'Naruto',score:5,watched:1}});await edit;
  assert.equal(modalCalls,0);
  edit=context.ui.editMal(20);const match=context.ui.matchMal(21);pending[4].resolve({mal_entry:{title:'Naruto'}});await edit;
  assert.equal(modalCalls,0);context.view='queue';pending[5].resolve({mal_anime:{title:'Other'},matches:[]});await match;
  assert.equal(modalCalls,0);
  checks.push('closed_replaced_or_navigated_dialog_ignores_late_mal_responses');

  context.ui.updatePlayerWatchBadge('saving');context.ui.updatePlayerWatchBadge('error');
  assert.equal(badge.dataset.state,'error');assert.ok(!badge.textContent.includes('Guardando'));
  checks.push('failed_scrobble_never_keeps_saving_badge');

  form={dataset:{slug:'naruto',user:'1'},elements:{status:{value:'paused'},score:{value:'9'},notes:{value:'Unsaved private note'},excluded:{checked:true,type:'checkbox'},namedItem(name){return this[name];}}};
  context.helpers.captureDetailDraft();
  for(const name of ['status','score','notes'])form.elements[name].value='';form.elements.excluded.checked=false;
  context.helpers.restoreDetailDraft('naruto');
  assert.equal(form.elements.notes.value,'Unsaved private note');assert.equal(form.elements.status.value,'paused');assert.equal(form.elements.excluded.checked,true);
  context.state.user.id=2;form.elements.notes.value='Another account';context.helpers.restoreDetailDraft('naruto');assert.equal(form.elements.notes.value,'Another account');
  context.state.user.id=1;form=null;
  checks.push('detail_draft_keeps_notes_status_score_exclusion_and_is_scoped_to_user');

  let sent=0;context.bridge.settings=async()=>{sent++;};
  storage.set(context.ui.settingsKey(),context.ui.settingsStamp());
  assert.equal((await context.ui.applySettingsNow()).applied,true);assert.equal(sent,0);
  context.ui.invalidateSettingsSync();
  assert.equal((await context.ui.applySettingsNow()).applied,true);assert.equal(sent,1);
  let finish;context.bridge.settings=async()=>{sent++;await new Promise(resolve=>finish=resolve);};
  const old=context.ui.applySettingsNow(true);context.ui.invalidateSettingsSync();context.bridge.token='another-device';finish();
  assert.equal((await old).applied,false);assert.equal(context.ui.getSettingsApplied(),'');
  storage.set(context.ui.settingsKey(),context.ui.settingsStamp());
  sent=0;context.bridge.settings=async()=>{sent++;};
  await context.ui.syncResults();assert.equal(sent,1);
  checks.push('new_pairing_resends_settings_and_old_device_cannot_confirm_them');

  context.state.jobs=[{id:1,episode_id:1,status:'pending',slug:'naruto',number:'1',language:'SUB',title:'Naruto'}];
  context.state.queue_summary=[{slug:'naruto',title:'Naruto',cover:'',total:4001,queued:2001,confirmed:2000,cancelled:0,languages:['SUB','DUB']}];
  context.state.queue_totals={total:4001,confirmed:2000};context.view='queue';
  assert.equal(context.ui.groupCount(context.ui.groupedJobs()[0]),'2000 / 4001 descargados');
  assert.ok(context.ui.downloadQueueView().includes('4001 capítulos'));
  context.ui.setQueue('naruto');
  let pages=0;
  context.api=async(action,data)=>{assert.equal(action,'queue_history');pages++;return {queue_history:{next_before:pages===1?50:0}};};
  await Promise.all([context.ui.ensureQueueHistory('naruto'),context.ui.ensureQueueHistory('naruto')]);
  assert.equal(pages,2);
  checks.push('complete_group_counts_and_bounded_history_pages_without_duplicate_loads');

  const entry=index=>({slug:'anime-'+index,status:'planned',favorite:false,excluded:false,score:8,notes:'😀'.repeat(2000)});
  const backup={format:'seasonav1.library/v1',entries:Array.from({length:1600},(_,i)=>entry(i)),watched:[]};
  assert.ok(new TextEncoder().encode(JSON.stringify(backup)).length>12*1024*1024);
  const chunks=context.ui.libraryImportChunks(backup);
  assert.ok(chunks.length>12);assert.equal(chunks.flatMap(part=>part.entries).length,1600);
  assert.ok(chunks.every(part=>new TextEncoder().encode(JSON.stringify(part)).length<=1024*1024));
  assert.throws(()=>context.ui.libraryImportChunks({...backup,entries:[entry(1),{...entry(2),score:11}]}),/inválidos/);
  checks.push('large_utf8_backup_splits_below_request_limit_and_validates_before_first_write');

  const result={ok:true,count:checks.length,checks,network:'simulated'};
  fs.writeFileSync(__dirname+'/reliability-ui-check.json',JSON.stringify(result,null,2));
  process.stdout.write(JSON.stringify(result,null,2));
})().catch(error=>{process.stderr.write(error.stack);process.exitCode=1;});
