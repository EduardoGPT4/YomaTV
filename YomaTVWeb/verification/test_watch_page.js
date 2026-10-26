'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync('htdocs/assets/player-view.js','utf8');
const pending=[],calls=[],timers=new Map(),main={innerHTML:'',dataset:{}},groups={innerHTML:''},dialog={open:false},listeners={};let timerId=0;
const context=vm.createContext({state:{user:{id:1},settings:{}},view:'discover',playerView:null,playerController:null,
  statsPage:null,malLibraryPage:null,location:{hash:'#discover?search=bleach'},TITLES:{discover:'Catálogo',watch:'Reproductor'},
  document:{title:'',querySelector:s=>s==='#main'?main:s==='#dialog'?dialog:s==='.watch-server-groups'?groups:null,addEventListener:(type,fn)=>{listeners[type]=fn;}},
  $:s=>s==='#main'?main:s==='#dialog'?dialog:{replaceChildren(){}},
  window:{addEventListener(){},scrollTo(){}},history:{pushState(_a,_b,route){context.location.hash=route;}},
  api:async(action,data)=>{calls.push([action,data]);return new Promise(resolve=>pending.push(resolve));},
  requireUser:()=>true,captureDetailDraft(){},cancelNextEpisode(){},radio:{pause(){}},
  render(){},sidebarNavigation:{closeMobile(){}},scheduleWatchPump(){},toast(){},
  e:s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[c]),icon:()=>'<svg></svg>',
  setTimeout:(fn,delay)=>{timers.set(++timerId,{fn,delay});return timerId;},clearTimeout:id=>timers.delete(id),
  mountWatchPage:html=>main.innerHTML=html,playerBookmarks:()=>'',sagaWatchOrder:()=>'',pendingPlayerTask:()=>false,pollPlayerTask(){},showPlayerTransition(){},confirmPlayerMal(){},offerPlayerMalConfirmation(){},
  Number,Math,Boolean,String,Promise,console});
vm.runInContext(fs.readFileSync('htdocs/assets/player-shelves.js','utf8'),context);
vm.runInContext(fs.readFileSync('htdocs/assets/player-template.js','utf8'),context);
vm.runInContext(source,context);
function player(id){return {index:0,episode:{id,number:String(id),slug:'naruto',title:'Naruto'},anime:{},servers:[{server:'Voe',language:'SUB',url:'https://voe.sx/e/abcde'}],playback:{revision:'revision',preferences:{}},mal_account_id:12,mal:{connected:true,linked:true,confirmed:true,watched:0},chapters:Array.from({length:220},(_,i)=>({id:i+1,number:String(i+1),watched:false})),warning:'Servidor externo'};}
(async()=>{
  const first=context.openPlayer(3),second=context.openPlayer(4);
  pending[1]({player:player(4)});await second;pending[0]({player:player(3)});await first;
  assert.equal(context.playerView.episode.id,4);assert.equal(context.location.hash,'#watch/4');
  assert(main.innerHTML.includes('watch-layout')&&main.innerHTML.includes('data-watch="mark"'));
  assert(!main.innerHTML.includes('<dialog'));assert.equal((main.innerHTML.match(/data-watch-episode=/g)||[]).length,60);
  assert(main.innerHTML.includes('aria-current="page"'));const checks=['last_episode_request_wins_and_page_has_bounded_chapter_navigation'];
  assert(main.innerHTML.includes('watch-related-saga-tab'));
  assert(context.watchRelated(context.playerView).includes('aria-selected="true">De esta saga'));
  context.playerView.relatedTab='genres';assert(context.watchRelated(context.playerView).includes('aria-selected="true">Por géneros'));
  checks.push('related_shelf_defaults_to_saga_and_has_a_genre_tab');
  const mark=context.markPlayerManually();assert.equal(calls.at(-1)[0],'watch_manual');
  assert.equal(calls.at(-1)[1].progress_revision,'revision');assert(!('position' in calls.at(-1)[1]));
  pending[2]({watch_sync:{state:'pending',target:4,message:'Pendiente'}});await mark;
  assert.equal(context.playerMalConfirmed(context.playerView),false);
  const retry=context.markPlayerManually();pending[3]({watch_sync:{state:'synced',target:4,message:'Confirmado'}});await retry;
  assert(context.playerMalConfirmed(context.playerView));const count=calls.length;await context.markPlayerManually();assert.equal(calls.length,count);
  checks.push('manual_eye_uses_identity_and_revision_and_only_disables_after_confirmed_mal_progress');
  const third=context.openPlayer(5);context.view='discover';context.leavePlayerPage();pending[4]({player:player(5)});await third;
  assert.equal(context.playerView,null);checks.push('leaving_page_invalidates_late_player_response');
  context.view='watch';context.playerView=player(6);const old=context.playerView;
  const late=context.markPlayerManually();context.playerView=player(7);pending[5]({watch_sync:{state:'synced',target:6,message:'Confirmado'}});await late;
  assert.equal(context.playerView.mal.watched,0);assert.equal(old.mal.watched,0);
  checks.push('late_manual_confirmation_cannot_mark_the_new_episode');
  context.view='watch';context.playerView=player(10);const cold=context.playerView;cold.servers=[];cold.server_refresh={state:'stale',can_refresh:true};
  const refresh=context.refreshPlayerServers();assert.equal(calls.at(-1)[0],'player_servers');
  pending.at(-1)({player_servers:{servers:[],server_refresh:{state:'waiting',can_refresh:true,retry_at:Date.now()/1000+30,message:'Espera de actualización'}}});await refresh;
  assert.equal(context.playerView,cold);assert.equal(timers.size,1);assert(context.watchServerNotice(cold).includes('Próximo intento:'));
  const timer=[...timers.values()][0];assert(timer.delay>=29000);context.leavePlayerPage();assert.equal(timers.size,0);
  context.view='watch';context.playerView=player(11);const playing=context.playerView;playing.server_refresh={state:'stale',can_refresh:true};
  const controller={destroy(){throw new Error('Refreshing servers interrupted playback');}};context.playerController=controller;
  const savedHtml=main.innerHTML,oldUrl=playing.servers[0].url,update=context.refreshPlayerServers();
  pending.at(-1)({player_servers:{servers:[{server:'MP4Upload',language:'SUB',url:'https://www.mp4upload.com/embed-new123.html'}],server_refresh:{state:'fresh',can_refresh:true}}});await update;
  assert.equal(context.playerController,controller);assert.equal(main.innerHTML,savedHtml);assert.equal(playing.servers[playing.index].url,oldUrl);
  assert(groups.innerHTML.includes('watch-server-group')&&groups.innerHTML.includes('MP4Upload'));
  context.playerController=null;
  checks.push('quota_refresh_uses_one_cancellable_timer_and_never_replaces_the_active_video');
  context.playerView=player(12);const member=context.playerView;member.server_refresh={state:'stale',can_refresh:false};
  const request=context.refreshPlayerServers();assert.equal(calls.at(-1)[0],'catalog_request');pending.at(-1)({task:{state:'pending'},message:'Solicitud registrada'});await request;
  assert(context.watchServerNotice(member).includes('disabled'));assert.equal(timers.size,0);
  checks.push('members_request_central_updates_without_launching_scraping');
  const preferred=player(13);preferred.playback.preferences={server:'MP4Upload',language:'LAT'};
  preferred.servers=[{server:'Voe',language:'SUB',url:'https://voe.sx/e/abcde'},{server:'MP4Upload',language:'LAT',url:'https://www.mp4upload.com/embed-abcde.html'}];
  context.selectPlayerServer(preferred);assert.equal(preferred.servers[preferred.index].language,'LAT');assert.equal(preferred.servers[preferred.index].server,'MP4Upload');
  checks.push('newly_loaded_servers_follow_saved_language_and_server_preferences');
  context.view='watch';context.playerView=player(14);const alreadyFresh=context.playerView;alreadyFresh.servers=[];alreadyFresh.server_refresh={state:'stale',can_refresh:false};
  const freshRequest=context.refreshPlayerServers();pending.at(-1)({task:{state:'done'},message:'Los datos ya están actualizados.'});await new Promise(resolve=>setImmediate(resolve));
  assert.equal(calls.at(-1)[0],'player_cached_servers');pending.at(-1)({player_servers:{servers:[{server:'Voe',language:'SUB',url:'https://voe.sx/e/fresh123'}],server_refresh:{state:'fresh',can_refresh:false}}});await freshRequest;
  assert.equal(context.playerView,alreadyFresh);assert.equal(alreadyFresh.servers[0].url,'https://voe.sx/e/fresh123');assert(main.innerHTML.includes('fresh123'));
  checks.push('already_completed_member_server_request_mounts_cached_servers_without_reopening_session');
  context.SeasonMobilePlayback={isMobile:()=>true};
  const mobilePlayer=player(15);mobilePlayer.servers[0].server='MP4Upload';
  const mobileMarkup=context.watchPageTemplate(mobilePlayer);
  assert(mobileMarkup.includes('mobile-native-player')&&mobileMarkup.includes('data-watch="fullscreen"'));
  assert(mobileMarkup.includes('allow-orientation-lock')&&mobileMarkup.includes('Controles originales de MP4Upload'));
  assert(!mobileMarkup.includes('data-personal="intro"')&&!mobileMarkup.includes('data-personal="bookmark"'));
  context.SeasonMobilePlayback.isMobile=()=>false;
  const desktopMarkup=context.watchPageTemplate(player(15));assert(!desktopMarkup.includes('mobile-native-player'));assert(desktopMarkup.includes('data-personal="intro"'));
  checks.push('mobile_renders_provider_controls_fullscreen_and_honest_mal_copy_without_desktop_only_actions');
  const grouped=player(16);grouped.index=2;
  grouped.servers=[{server:'MP4Upload',language:'DUB'},{server:'Voe',language:'SUB'},{server:'MP4Upload',language:'SUB'},{server:'Voe',language:'DUB'},{server:'Voe',language:'LAT'}];
  const before=JSON.stringify(grouped.servers),rows=context.watchServerButtons(grouped).match(/<section class="watch-server-group"[\s\S]*?<\/section>/g);
  assert.equal(rows.length,3);assert(rows[0].includes('>SUB</span>'));assert(rows[1].includes('>LAT</span>'));assert(rows[2].includes('>DUB</span>'));
  assert(rows[0].includes('data-watch-server="1"')&&rows[0].includes('data-watch-server="2" aria-label="MP4Upload · SUB" aria-pressed="true"'));
  assert(rows[2].includes('data-watch-server="0"')&&rows[2].includes('data-watch-server="3"'));
  assert(!rows.join('').includes('<small>'));assert.equal(JSON.stringify(grouped.servers),before);
  assert.equal((rows.join('').match(/aria-pressed="true"/g)||[]).length,1);
  assert.equal((rows.join('').match(/data-watch-server=/g)||[]).length,grouped.servers.length);
  context.view='watch';context.playerView=grouped;let remembered=null,renders=0;
  context.rememberPlayerServer=(_p,index)=>remembered=index;context.renderPlayer=()=>renders++;
  await listeners.click({target:{closest:()=>({dataset:{watchServer:'0'}})},preventDefault(){},stopImmediatePropagation(){}});
  assert.equal(grouped.index,0);assert.equal(grouped.servers[grouped.index].language,'DUB');assert.equal(remembered,0);assert.equal(renders,1);
  assert.equal(context.watchServerButtons({servers:[],index:0}),'<span class="muted">Sin servidores guardados</span>');
  const escaped=context.watchServerButtons({servers:[{server:'<img onerror=x>',language:'<script>'}],index:0});assert(!escaped.includes('<img')&&!escaped.includes('<script>'));
  assert.equal((context.watchServerButtons(player(17)).match(/watch-server-group"/g)||[]).length,1);
  checks.push('audio_rows_preserve_server_indices_selection_and_click_target_with_no_duplicate_buttons_or_empty_rows');
  const result={ok:true,checks};fs.writeFileSync('verification/watch-page-ui-check.json',JSON.stringify(result,null,2));console.log(JSON.stringify(result));
})().catch(error=>{console.error(error);process.exitCode=1;});
