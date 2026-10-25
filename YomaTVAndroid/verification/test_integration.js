'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../app/src/main/assets/native-integration.js'),'utf8');
function environment(origin='https://hk-br035.gt.tc'){
  const clicks=[],posted=[],buttons=[],errors=[],requests=[];
  const transport={querySelector:()=>buttons[0],append:b=>buttons.push(b)};
  const context={Document:class{},location:{origin,pathname:'/seasonav1/'},document:{documentElement:{classList:{add(){}}},hidden:false,querySelector:s=>s==='.watch-transport'?transport:null,querySelectorAll:()=>[],createElement:()=>({dataset:{}}),addEventListener:(event,fn)=>{if(event==='click')clicks.push(fn);}},
    MutationObserver:class{observe(){}},setTimeout,clearTimeout,YomaAndroid:{postMessage:s=>posted.push(JSON.parse(s))},
    state:{user:{id:12,name:'Local fixture'},settings:{language:'SUB'}},playerView:{episode:{id:7},index:0,servers:[{language:'SUB'}]},
    addEventListener:()=>{},api:async(action,input)=>{requests.push({action,input});return{offline_plan:{owner:12,title:'Fixture',slug:'fixture',language:input.language,episodes:[{episode_id:7,number:'2'},{episode_id:8,number:'3'}]}}},toast:message=>errors.push(message)};
  context.window=context;vm.runInNewContext(source,context);return{context,clicks,posted,buttons,errors,requests};
}
(async()=>{
  const foreign=environment('https://foreign.example');assert.equal(foreign.posted.length,0);assert.equal(foreign.clicks.length,0);
  const app=environment();assert.equal(app.posted[0].type,'auth');assert.equal(app.buttons.length,1);
  const button=app.buttons[0];await app.clicks[0]({target:{closest:()=>button},preventDefault(){},stopImmediatePropagation(){}});
  const plan=app.posted.find(p=>p.type==='plan');assert.equal(plan.episodes.length,1);assert.equal(plan.episodes[0].episode_id,7);
  assert.equal(app.requests[0].action,'offline_plan');assert(!app.requests.some(r=>r.action==='player'));
  const race=environment();race.context.api=async()=>{race.context.state.user={id:13};return{offline_plan:{owner:12,episodes:[]}}};
  await race.clicks[0]({target:{closest:()=>race.buttons[0]},preventDefault(){},stopImmediatePropagation(){}});
  assert(!race.posted.some(p=>p.type==='plan'));assert(race.errors.some(e=>e.includes('cuenta')));
  const guest=environment();guest.context.state.user=null;await guest.clicks[0]({target:{closest:()=>guest.buttons[0]},preventDefault(){},stopImmediatePropagation(){}});assert.equal(guest.requests.length,0);
  const anime=environment();anime.context.detailState={episodes:[{id:7}]};anime.buttons[0].dataset.nativeOffline='anime';anime.context.state.settings.language='LAT';anime.context.playerView.servers[0].language='DUB';
  await anime.clicks[0]({target:{closest:()=>anime.buttons[0]},preventDefault(){},stopImmediatePropagation(){}});assert.equal(anime.posted.find(p=>p.type==='plan').language,'LAT');
  const report={ok:true,checks:['origin_restricted','native_action_injected_once','download_plan_does_not_open_playback_session','single_episode_selection_preserved','account_change_cancels_plan','guest_cannot_queue','anime_download_uses_preferences_not_another_animes_player_language']};
  fs.writeFileSync(path.join(__dirname,'native-integration-check.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report));
})().catch(error=>{console.error(error);process.exitCode=1});
