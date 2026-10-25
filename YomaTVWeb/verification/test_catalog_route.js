'use strict';
const vm=require('node:vm'), fs=require('node:fs'), assert=require('node:assert/strict');
const events={},windowEvents={},timers=new Map(),requests=[],historyEntries=[];
let nextTimer=0;
const location={hash:'#discover',pathname:'/seasonav1/',search:'?i=1'};
const context=vm.createContext({
  URLSearchParams,location,console,Map,Set,
  history:{pushState(_a,_b,url){historyEntries.push(url);location.hash=url.slice(url.indexOf('#'));},replaceState(_a,_b,url){location.hash=url.slice(url.indexOf('#'));}},
  document:{activeElement:null,querySelector(){return null;},getElementById(){return null;},addEventListener(n,f){events[n]=f;}},
  window:{addEventListener(n,f){windowEvents[n]=f;}},
  setTimeout(f){timers.set(++nextTimer,f);return nextTimer;},clearTimeout(id){timers.delete(id);},
  state:{user:{id:7},anime:[]},view:'discover',render(){},dateText(){return '';},
  api(_action,filters){return new Promise(resolve=>requests.push({filters,resolve}));},
});
vm.runInContext(fs.readFileSync('htdocs/assets/catalog.js','utf8'),context);
const run=code=>vm.runInContext(code,context);
const clone=code=>JSON.parse(JSON.stringify(run(code)));
const checks=[];
const result=page=>({catalog:{page,pages:8,items:[],total:80,all_total:4485}});
(async()=>{
  run(`Object.assign(catalogFilters,{search:'Ángel + café',letter:'A',library:'none',download:'unprepared',season:'otoño2026',genre_mode:'any',include_genres:['Action','Comedy'],exclude_genres:['Ecchi'],page:3})`);
  const expected=clone('catalogFilters');
  run('catalogWriteRoute()');
  assert.deepEqual(clone('catalogReadRoute(location.hash)'),expected);
  assert.ok(historyEntries[0].startsWith('/seasonav1/?i=1#discover?'));
  checks.push('shareable_unicode_array_filters_preserve_host_query');
  const bad=clone(`catalogReadRoute('#discover?order=evil&library=invalid&page=NaN&language=ES&letter=AA&include_genres=bad')`);
  assert.equal(bad.order,'recent');assert.equal(bad.page,1);assert.deepEqual(bad.include_genres,[]);assert.equal(bad.library,'');assert.equal(bad.language,'');assert.equal(bad.letter,'');
  checks.push('invalid_url_values_are_normalized');
  run(`Object.assign(catalogFilters,CATALOG_DEFAULTS,{include_genres:[],exclude_genres:[]})`);
  const old=run('loadCatalog()');
  events.input({target:{id:'catalog-search',value:'latest'}});
  requests.shift().resolve(result(1));await old;
  assert.equal(run('catalogState'),null);
  const fn=[...timers.values()].pop();fn();
  assert.equal(requests[0].filters.search,'latest');
  requests.shift().resolve(result(2));await new Promise(resolve=>setImmediate(resolve));
  assert.equal(run('catalogState.page'),2);
  assert.ok(location.hash.includes('search=latest'));
  checks.push('old_responses_cannot_replace_new_search_during_debounce');
  location.hash='#discover?library=planned&page=4&include_genres=%5B%22Action%22%5D';
  windowEvents.popstate();
  assert.equal(run('catalogFilters.library'),'planned');assert.equal(run('catalogFilters.page'),4);
  assert.deepEqual(clone('catalogFilters.include_genres'),['Action']);
  requests.shift().resolve(result(4));await new Promise(resolve=>setImmediate(resolve));
  checks.push('back_forward_restores_every_filter_and_page');
  const remove=run(`catalogAction('catalog_remove',{dataset:{key:'include_genres',value:'Action'}})`);
  assert.deepEqual(clone('catalogFilters.include_genres'),[]);assert.equal(run('catalogFilters.library'),'planned');assert.equal(run('catalogFilters.page'),1);
  requests.shift().resolve(result(1));await remove;
  checks.push('remove_one_chip_keeps_other_filters_and_resets_page');
  const pending=run('loadCatalog()');run('catalogPersonalChanged()');
  requests.shift().resolve(result(7));await pending;
  assert.equal(run('catalogState.page'),1);
  checks.push('personal_updates_invalidate_old_filtered_responses');
  const clear=run(`catalogAction('catalog_clear',{})`);requests.shift().resolve(result(1));await clear;
  assert.deepEqual(clone('catalogFilters'),clone('CATALOG_DEFAULTS'));assert.equal(location.hash,'#discover');
  checks.push('clear_removes_all_active_filters_from_url');
  const output={ok:true,count:checks.length,checks};
  fs.writeFileSync('verification/catalog-route-check.json',JSON.stringify(output,null,2));console.log(JSON.stringify(output,null,2));
})().catch(error=>{console.error(error);process.exitCode=1;});
