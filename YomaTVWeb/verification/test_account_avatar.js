'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const slots=[{innerHTML:''}],listeners={},tasks=[],pending=[];let calls=0;
const context=vm.createContext({state:{user:{id:1,name:'Haru'}},document:{querySelectorAll:()=>slots,addEventListener:(name,fn)=>listeners[name]=fn},URL,Date,Set,
  queueMicrotask:fn=>tasks.push(fn),e:s=>String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;'),
  api:()=>{calls++;return new Promise(resolve=>pending.push(resolve));}});
vm.runInContext(fs.readFileSync('htdocs/assets/account-avatar.js','utf8'),context);
const avatar=context.YomaAvatar,photo='https://cdn.myanimelist.net/images/userimages/123.jpg?t=1';
const status=(picture=photo,next=Date.now()/1000+86400)=>({configured:true,connected:true,profile:{id:123,name:'MAL_Haru',picture,avatar_next_refresh:next}});
const accept=(mal,action='home',ticket=avatar.ticket())=>avatar.accept({mal},ticket,action);
(async()=>{
  assert(!avatar.html('Haru').includes('<img'));accept(status());assert.equal(avatar.url(),photo);
  assert(avatar.html('Haru').includes('referrerpolicy="no-referrer"'));assert(slots[0].innerHTML.includes(photo.replaceAll('&','&amp;')));
  for(const bad of ['javascript:alert(1)','https://evil.example/x.jpg','https://cdn.myanimelist.net@evil.example/x','http://cdn.myanimelist.net/x','https://cdn.myanimelist.net:8443/x']){
    avatar.reset();accept(status(bad));assert(!avatar.html('Haru').includes('<img'));
  }
  avatar.reset();accept(status());let removed=false;
  listeners.error({target:{tagName:'IMG',parentElement:{hasAttribute:()=>true},getAttribute:()=>photo,remove:()=>removed=true}});
  assert(removed);assert.equal(avatar.url(),'');assert(avatar.html('Haru').includes('>H</span>'));
  avatar.reset();tasks.length=0;accept(status(photo,0));const refreshing=tasks.pop()();assert.equal(calls,1);
  accept(status(photo,0));await tasks.pop()();assert.equal(calls,1);
  const old=avatar.ticket();accept({connected:false,profile:null},'mal_disconnect');accept(status(), 'mal_avatar',old);
  assert.equal(avatar.url(),'');pending.shift()({});await refreshing;
  avatar.reset();context.state.user={id:2,name:'Nueva'};accept(status('',0));const second=tasks.pop()();assert.equal(calls,2);pending.shift()({});await second;
  const otherTicket=avatar.ticket();avatar.reset();context.state.user={id:3,name:'Tercera'};accept(status(),'mal_avatar',otherTicket);assert.equal(avatar.status(),null);
  context.state.user={id:0,name:''};assert(!avatar.html('').includes('<img'));
  const result={ok:true,checks:['connected_profile_photo_is_used_in_all_avatar_slots','remote_urls_are_restricted_to_mal_cdn','broken_image_and_guest_keep_initial','one_background_refresh_per_interval','disconnect_and_account_changes_reject_late_images']};
  fs.writeFileSync('verification/account-avatar-client-check.json',JSON.stringify(result,null,2));console.log(JSON.stringify(result));
})().catch(error=>{console.error(error);process.exitCode=1;});
