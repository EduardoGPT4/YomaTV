'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const handlers=[],tasks=[],requests=[],pending=[];
const context=vm.createContext({state:{user:{id:7},season:'otoño2026',anime:Array.from({length:7},(_,i)=>({active:true,weekday:i+1,title:'Anime '+i,slug:'anime-'+i,latest:3,airing_status:'currently_airing',cover:'https://cdn.animeav1.com/a.jpg'}))},
  search:'',day:0,view:'schedule',catalogState:null,catalogFilters:{category:'',airing:''},
  document:{documentElement:{classList:{contains:()=>true}},addEventListener:(type,fn)=>{if(type==='click')handlers.push(fn);},querySelector:()=>null},
  DAYS:['Lunes','Martes','Miércoles','Jueves','Viernes','Sábado','Domingo'],
  e:v=>String(v??'').replaceAll('<','&lt;'),icon:()=>'<svg></svg>',searchBox:()=>'<label class="search-box"><input id="search"></label>',
  queueMicrotask:fn=>tasks.push(fn),render(){},api:(action,filters)=>{requests.push({action,filters});return new Promise(resolve=>pending.push(resolve));},
  Math,Date,Number,String,Promise,console});
vm.runInContext(fs.readFileSync('htdocs/assets/mobile-app.js','utf8'),context);
(async()=>{
  const first=context.yomaScheduleView();assert.equal((first.match(/class="day-tab /g)||[]).length,7);assert(first.includes('Otoño 2026'));assert(first.includes('Estrenos de hoy'));assert(!first.includes('18:30'));
  vm.runInContext("yomaSeasonMode='upcoming'",context);
  const fetch=context.yomaLoadSeason();assert.equal(requests[0].action,'catalog');assert.equal(requests[0].filters.airing,'not_yet_aired');assert.equal(requests[0].filters.season,'otoño2026');
  pending.shift()({catalog:{total:1,items:[{slug:'public-upcoming',title:'Título del catálogo completo',category:'TV Anime',start_date:'2026-12-01',cover:''}]}});await fetch;
  const upcoming=context.yomaScheduleView();assert(upcoming.includes('Título del catálogo completo'));assert(upcoming.includes('2026-12-01'));assert(!upcoming.includes('class="day-tab '));
  const shift={dataset:{yomaSeasonShift:'1'}};
  handlers[0]({target:{closest:s=>s==='[data-yoma-season-shift]'?shift:null},preventDefault(){}});
  assert.equal(vm.runInContext('yomaSeason',context),'invierno2027');
  const stale=context.yomaLoadSeason();context.state.user={id:8};pending.shift()({catalog:{items:[{title:'Old personal state'}]}});await stale;
  assert(!context.yomaScheduleView().includes('Old personal state'));
  const home=context.yomaHomeHero(context.state.anime,true);assert(home.includes('DESTACADO DE LA SEMANA'));assert(home.includes('Ver ahora'));
  assert(!context.yomaHomeHero(context.state.anime,false).includes('yoma-featured'));
  const result={ok:true,checks:['weekly_schedule_keeps_real_days_without_invented_airtimes','upcoming_uses_full_public_catalog_with_season_filter','quarter_navigation_handles_year_boundary','late_catalog_result_cannot_cross_accounts','home_feed_uses_compact_hero_only_when_unfiltered']};
  fs.writeFileSync('verification/mobile-layout-check.json',JSON.stringify(result,null,2));console.log(JSON.stringify(result));
})().catch(error=>{console.error(error);process.exitCode=1;});
