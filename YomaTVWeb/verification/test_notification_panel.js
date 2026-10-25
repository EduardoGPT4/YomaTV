'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync('htdocs/assets/notification-panel.js','utf8');
function setup(){
  const events={},windowEvents={},requests=[],errors=[];
  const element=()=>({hidden:false,disabled:false,style:{},attrs:{},innerHTML:'',setAttribute(k,v){this.attrs[k]=v;},focus(){this.focused=true;},contains(target){return target===this;},replaceChildren(){this.innerHTML='';}});
  const bell=element(),panel=element(),content=element(),read=element();
  panel.hidden=true;panel.contains=t=>t===panel||t.inPanel===true;
  panel.querySelector=s=>s==='[data-notice-content]'?content:read;
  bell.getBoundingClientRect=()=>({right:330,bottom:74});
  const context={console,Number,Math,String,Date,Promise,window:{innerWidth:390,innerHeight:844,addEventListener:(n,f)=>windowEvents[n]=f},
    document:{getElementById:id=>id==='notifications-toggle'?bell:panel,addEventListener:(n,f)=>events[n]=f},
    state:{user:{id:7}},featureHome:{notifications:2,notifications_revision:50},noticesPage:[{id:1}],
    sidebarNavigation:{closeMobile(){}},e:s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[c]),dateText:()=> '24 oct, 12:00',toast:message=>errors.push(message),
    api:(action,data,get)=>new Promise((resolve,reject)=>requests.push({action,data,get,resolve,reject})),
    location:{hash:'#watch/182'},playerController:{identity:'playing'},render(){throw Error('Notification panel remounted the page');}};
  vm.runInNewContext(source,context);
  const click=action=>events.click({target:{inPanel:true,closest:s=>s==='[data-notice-action]'?{dataset:{noticeAction:action}}:null},preventDefault(){},stopImmediatePropagation(){}});
  return {context,api:context.SeasonNotifications,bell,panel,content,read,events,windowEvents,requests,errors,click};
}
const settle=()=>new Promise(resolve=>setImmediate(resolve));
const notice=(id=50)=>({id,slug:'naruto-'+id,title:'Naruto '+id,cover:'https://example.test/poster.jpg',episode_count:1,first_number:6,number:6,unread:1,created_at:1792800000});
const result=rows=>({notifications:rows,notifications_up_to:50});
(async()=>{
  const checks=[];let x=setup();const controller=x.context.playerController;x.api.toggle();
  assert(!x.panel.hidden);assert.equal(x.bell.attrs['aria-expanded'],'true');assert.equal(x.context.location.hash,'#watch/182');assert.equal(x.context.playerController,controller);assert.equal(x.requests[0].action,'notifications');assert.equal(x.panel.style.width,'366px');assert.equal(x.panel.style.left,'12px');
  x.api.toggle();x.api.toggle();assert.equal(x.requests.length,1);x.requests.shift().resolve(result([notice()]));await settle();assert(x.content.innerHTML.includes('Naruto 50'));assert.equal(x.read.disabled,false);
  checks.push('bell_opens_bounded_dropdown_without_navigation_or_remounting_active_player_and_deduplicates_requests');
  x.events.keydown({key:'Escape',preventDefault(){}});assert(x.panel.hidden&&x.bell.focused);x.api.toggle();assert.equal(x.requests.length,0);
  x.events.pointerdown({target:{}});assert(x.panel.hidden);x.api.toggle();x.events.focusin({target:{}});assert(x.panel.hidden);
  checks.push('escape_outside_pointer_and_focus_close_panel_and_escape_returns_focus_to_bell');
  x.context.featureHome.notifications_revision=51;x.api.sync();assert.equal(x.requests.length,0);x.api.toggle();assert.equal(x.requests.length,1);
  x.requests.shift().resolve(result(Array.from({length:25},(_,i)=>notice(50-i))));await settle();assert.equal((x.content.innerHTML.match(/data-open=/g)||[]).length,20);
  checks.push('new_revision_refreshes_when_open_without_polling_closed_panel_and_recent_list_is_bounded');
  x.click('read');assert.equal(x.read.disabled,true);const mark=x.requests.shift();assert.equal(mark.action,'notifications_read');assert.equal(mark.data.up_to,50);
  x.context.featureHome.notifications=0;mark.resolve({});await settle();assert.equal(x.context.noticesPage,null);const reload=x.requests.shift();assert.equal(reload.action,'notifications');reload.resolve(result([{...notice(),unread:0}]));await settle();assert.equal(x.read.disabled,true);assert(x.content.innerHTML.includes('aria-label="Leída"'));
  checks.push('mark_all_uses_loaded_snapshot_updates_badge_data_and_reloads_without_navigation');
  x.api.close();x.context.featureHome.notifications_revision=52;x.api.toggle();const old=x.requests.shift();x.context.state.user={id:8};x.context.featureHome={notifications:1,notifications_revision:100};x.api.sync();assert(x.panel.hidden);assert.equal(x.content.innerHTML,'');
  old.resolve(result([{...notice(),title:'Private account seven'}]));await settle();assert(!x.content.innerHTML.includes('Private account seven'));x.api.toggle();const fresh=x.requests.shift();fresh.resolve(result([{...notice(100),title:'<img onerror=alert(1)>'}]));await settle();assert(x.content.innerHTML.includes('&lt;img onerror=alert(1)&gt;'));
  checks.push('account_switch_clears_private_rows_ignores_late_response_and_escapes_notification_text');
  x=setup();x.api.toggle();x.requests.shift().reject(Error('Sin conexión'));await settle();assert(x.content.innerHTML.includes('Volver a intentar'));assert.equal(x.read.disabled,true);x.api.sync();assert.equal(x.requests.length,0);x.click('retry');x.requests.shift().resolve(result([]));await settle();assert(x.content.innerHTML.includes('Estás al día'));
  checks.push('network_failure_has_explicit_retry_without_request_loop_and_empty_state_is_honest');
  x=setup();x.context.state.user=null;x.context.featureHome=null;x.api.toggle();assert(x.content.innerHTML.includes('Iniciar sesión'));assert.equal(x.requests.length,0);assert(x.read.disabled);
  checks.push('anonymous_dropdown_offers_login_without_private_api_request');
  const report={ok:true,count:checks.length,checks};fs.writeFileSync('verification/notification-panel-check.json',JSON.stringify(report,null,2));console.log(JSON.stringify(report));
})().catch(e=>{console.error(e);process.exitCode=1;});
