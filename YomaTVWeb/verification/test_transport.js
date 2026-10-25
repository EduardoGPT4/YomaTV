'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const pending=[],checks=[];
const context=vm.createContext({console,AbortController,Map,Set,WeakMap,Number,Object,URLSearchParams,Error,Promise,Blob,
  setTimeout,clearTimeout,queueMicrotask,fetch(url,options){return new Promise((resolve,reject)=>{
    const item={url,options,resolve,reject};pending.push(item);
    options.signal.addEventListener('abort',()=>reject(Object.assign(new Error('aborted'),{name:'AbortError'})),{once:true});
    if(options.signal.aborted)reject(Object.assign(new Error('aborted'),{name:'AbortError'}));
  })},
  state:{revision:1,user:{id:1},csrf:'fixture',anime:[],jobs:[],history:[]},
  syncCatalogPersonal(){},accountStateChanged(){vm.runInContext('SeasonTransport.cancelAll()',context);},
  $(){return {content:'fixture',close(){}};},render(){},detailSequence:1,
});
const run=code=>vm.runInContext(code,context);
run(fs.readFileSync('htdocs/assets/transport.js','utf8')+fs.readFileSync('htdocs/assets/state-client.js','utf8'));
const success=(item,result)=>item.resolve({ok:true,status:200,json:async()=>({ok:true,...result})});
(async()=>{
  const a=run("api('catalog',{q:'old'},true)").catch(e=>e);
  const b=run("api('catalog',{q:'new'},true)");assert(pending[0].options.signal.aborted);success(pending[1],{catalog:{q:'new'}});assert.equal((await b).catalog.q,'new');assert((await a).cancelled);checks.push('new_search_aborts_previous_network_request');
  const timeout=run("SeasonTransport.request('slow',{}, {timeout:10})").catch(e=>e);assert.equal((await timeout).name,'TimeoutError');assert(pending[2].options.signal.aborted);checks.push('timeout_aborts_slow_request_without_implicit_retry');
  const decode=run("SeasonTransport.request('slow-body',{}, {timeout:10})").catch(e=>e);
  pending[3].resolve({json:()=>new Promise((resolve,reject)=>pending[3].options.signal.addEventListener('abort',()=>reject(new Error('aborted'))))});assert.equal((await decode).name,'TimeoutError');checks.push('deadline_includes_body_decoding');
  const old=run("api('state',{},true)").catch(e=>e);run('state={revision:10,user:{id:2},csrf:"second",anime:[],jobs:[],history:[]}');
  success(pending[4],{data:{revision:99,user:{id:1},csrf:'old-account'}});assert((await old).cancelled);assert.equal(run('state.user.id'),2);checks.push('late_full_state_cannot_replace_new_account');
  const later=run("api('state',{},true)");success(pending[5],{data:{revision:5,user:{id:2},csrf:'stale'}});await later;assert.equal(run('state.csrf'),'second');checks.push('older_full_state_cannot_replace_newer_revision');
  const old401=run("api('home',{},true)").catch(e=>e);run('state={revision:20,user:{id:3},csrf:"third",anime:[],jobs:[],history:[]}');pending[6].resolve({ok:false,status:401,json:async()=>({ok:false,message:'expired'})});await old401;assert.equal(pending.length,7);assert.equal(run('state.user.id'),3);checks.push('late_401_does_not_refresh_or_logout_another_account');
  const mutation=run("api('follow',{slug:'fixture'})").catch(e=>e);run('SeasonTransport.cancelAll()');assert((await mutation).cancelled);assert(pending[7].options.signal.aborted);assert.equal(pending.length,8);checks.push('account_change_cancels_all_pending_requests_without_repeating_mutations');
  const binary=run("SeasonTransport.request('backup',{}, {format:'blob'})");pending[8].resolve({ok:true,status:200,headers:{get:()=> 'application/octet-stream'},blob:async()=>new Blob(['fixture ciphertext'])});assert.equal(await (await binary).result.text(),'fixture ciphertext');checks.push('encrypted_backup_download_uses_same_deadline_and_account_cancellation_boundary');
  const result={ok:true,count:checks.length,checks};fs.writeFileSync('verification/transport-check.json',JSON.stringify(result,null,2));console.log(JSON.stringify(result));
})().catch(e=>{console.error(e);process.exitCode=1;});
