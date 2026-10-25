'use strict';
const vm=require('node:vm'),fs=require('node:fs'),assert=require('node:assert/strict');
const store=new Map(),requests=[],token='A'.repeat(43),plan={format:'seasonav1.web-plan/v1',items:[{web_id:1}]};
let fail=false;
const context={localStorage:{getItem:k=>store.get(k),setItem:(k,v)=>store.set(k,v),removeItem:k=>store.delete(k)},AbortController,URLSearchParams,setTimeout,clearTimeout,TypeError,
  fetch:async(url,options)=>{requests.push({url,options});if(fail)throw new TypeError('offline');return {ok:true,json:async()=>({ok:true,app:'YomaTV',protocol:'seasonav1.bridge/v1',capabilities:['settings','live_status','filtered_results'],jobs:[],receipts:[],signature:'empty'})};}};
vm.createContext(context);vm.runInContext(fs.readFileSync(__dirname+'/../htdocs/assets/bridge.js','utf8')+'\nthis.client=new SeasonBridge();',context);
(async()=>{
  const client=context.client,files=[];
  let result=await client.deliver(plan,p=>files.push(p));assert.equal(result.direct,false);assert.equal(requests.length,0);assert.equal(files.length,1);
  await client.pair(token);assert.equal(store.get(client.key),token);
  result=await client.deliver(plan,p=>files.push(p));assert.equal(result.direct,true);assert.equal(files.length,1);
  assert.equal(requests.at(-1).url,'http://127.0.0.1:47653/queue');assert.equal(requests.at(-1).options.headers.Authorization,'Bearer '+token);
  assert.equal(requests.at(-1).options.credentials,'omit');assert.equal(requests.at(-1).options.body,JSON.stringify(plan));
  await client.ping();assert(client.supports('settings'));assert(client.supports('live_status'));
  await client.settings({workers:2});assert.equal(requests.at(-1).url,'http://127.0.0.1:47653/settings');
  assert.equal(requests.at(-1).options.body,JSON.stringify({format:'seasonav1.web-settings/v1',preferences:{workers:2}}));
  await client.status('a'.repeat(32),[1,2]);assert.equal(requests.at(-1).url,'http://127.0.0.1:47653/status?installation='+'a'.repeat(32)+'&ids=1%2C2');
  await client.results('a'.repeat(32),[1,2]);assert(requests.at(-1).url.endsWith('&ids=1%2C2'));
  fail=true;result=await client.deliver(plan,p=>files.push(p));assert.equal(result.direct,false);assert.equal(files.length,2);
  client.forget();assert.equal(store.size,0);assert.equal(client.token,'');
  const resultData={ok:true,checks:['unpaired_json_fallback','pairing_persisted_only_in_browser','direct_queue_without_file','offline_json_fallback','forget_connection','settings_without_queue','live_status_scoped_ids','filtered_results']};
  fs.writeFileSync(__dirname+'/bridge-client-check.json',JSON.stringify(resultData,null,2));process.stdout.write(JSON.stringify(resultData));
})().catch(e=>{process.stderr.write(e.stack);process.exitCode=1;});
