'use strict';
const vm=require('node:vm'),fs=require('node:fs'),assert=require('node:assert/strict');
const context={Map,Promise,JSON,Number,Math,Date,setTimeout,clearTimeout,
  document:{addEventListener(){},querySelector(){return null;},querySelectorAll(){return [];}},
  localStorage:{getItem(){return null;},setItem(){}},e:String,icon:n=>n,
  queueFilter:'all',bridge:{connected:true,token:'local',capabilities:['settings'],supports:()=>true},
  state:{user:{id:1},preferences_saved:true,installation:'a'.repeat(32),settings:{workers:1},anime:[],jobs:[]},
  activeJobs(){return context.state.jobs.filter(j=>!['confirmed','cancelled'].includes(j.status));}
};
vm.createContext(context);
vm.runInContext(fs.readFileSync(__dirname+'/../htdocs/assets/bridge-ui.js','utf8')+
  '\nthis.ui={jobView,sendableJobs,applySettingsNow,queryBridgeBatches,setLive(values){liveJobs=new Map(values);}};',context);
(async()=>{
  const jobs=[{id:1,status:'exported'},{id:2,status:'pending'},{id:3,status:'confirmed'}];
  context.state.jobs=jobs;
  context.ui.setLive([[1,{status:'downloading',progress:32}],[2,{status:'failed',reason:'Sin conexión'}]]);
  assert.equal(context.ui.jobView(jobs[0]).progress,32);
  assert.equal(context.ui.jobView(jobs[1]).label,'Sin conexión');
  assert.equal(context.ui.sendableJobs().map(j=>j.id).join(','),'2');
  context.ui.setLive([[1,{status:'completed',progress:100}]]);
  assert.equal(context.ui.jobView(jobs[0]).phase,'verifying');
  assert.equal(context.ui.jobView(jobs[2]).phase,'confirmed');
  context.bridge.connected=false;
  assert.equal(context.ui.jobView(jobs[0]).phase,'queued');
  assert.equal(context.ui.jobView(jobs[2]).phase,'confirmed');
  context.bridge.connected=true;
  let finishFirst;const sent=[];
  context.bridge.settings=async value=>{sent.push(JSON.parse(JSON.stringify(value)));if(sent.length===1)await new Promise(resolve=>finishFirst=resolve);};
  const first=context.ui.applySettingsNow(true);
  context.state.settings.workers=3;
  const next=context.ui.applySettingsNow(true);
  assert.equal(sent.length,1);finishFirst();await Promise.all([first,next]);
  assert.equal(sent.length,2);assert.equal(sent[0].workers,1);assert.equal(sent[1].workers,3);
  const batches=[];context.bridge.status=async (_,ids)=>{batches.push(ids);return {jobs:ids.map(web_id=>({web_id,status:'pending'}))};};
  const large=Array.from({length:4101},(_,i)=>({id:i+1}));const queried=await context.ui.queryBridgeBatches('status',large,1);
  assert.equal(batches.map(ids=>ids.length).join(','),'2000,2000,101');assert.equal(queried.flatMap(batch=>batch.jobs).length,4101);
  context.bridge.status=async ()=>{context.state.user.id=2;return {jobs:[]};};assert.equal(await context.ui.queryBridgeBatches('status',large,1),null);
  const result={ok:true,checks:['progress_and_short_errors','do_not_resubmit_active_downloads','completion_requires_receipt','offline_preserves_confirmed','concurrent_settings_save_keeps_latest','large_partial_queue_queries_use_bounded_batches','account_change_cancels_inflight_status_queries']};
  fs.writeFileSync(__dirname+'/bridge-ui-check.json',JSON.stringify(result,null,2));process.stdout.write(JSON.stringify(result));
})().catch(error=>{process.stderr.write(error.stack);process.exitCode=1;});
