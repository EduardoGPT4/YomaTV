'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const source=fs.readFileSync('htdocs/assets/player-controller.js','utf8');
const checks=[];
class Element {
  constructor(selector=''){this.selector=selector;this.values={};this.listeners={};this.style={setProperty(){}};this.classList={values:new Set(),add(v){this.values.add(v);},remove(v){this.values.delete(v);}};this.children={};this.isConnected=true;}
  addEventListener(name,fn){this.listeners[name]=fn;}removeEventListener(name){delete this.listeners[name];}
  append(child){this.child=child;}querySelector(s){return this.children[s] ||= new Element(s);}
  setAttribute(k,v){this.values[k]=v;}contains(){return false;}closest(){return this;}remove(){this.isConnected=false;}matches(s){return s===this.selector;}
}
function setup(result={state:'synced',message:'Visto en web y MAL'},options={}){
  const commands=[],marks=[],statuses=[],timers=new Map();let nextTimer=1;
  const window={addEventListener(){},removeEventListener(){},postMessage:m=>commands.push(m)};
  const document={createElement:()=>new Element(),addEventListener(){},removeEventListener(){},activeElement:null,fullscreenElement:null};
  const context=vm.createContext({window,document,location:{origin:'https://hk-br035.gt.tc'},crypto:crypto.webcrypto,MutationObserver:class{observe(){}disconnect(){}},setTimeout:fn=>{const id=nextTimer++;timers.set(id,fn);return id;},clearTimeout:id=>timers.delete(id),Promise,Date,URL});
  vm.runInContext(source,context);
  const stage=new Element(),iframe=new Element();iframe.src='https://www.mp4upload.com/embed-abcde12345.html';
  const c=new context.YomaTVPlayerController({stage,iframe,episodeNumber:'6',onThreshold:async data=>{marks.push(data);return result;},onStatus:(...args)=>statuses.push(args),...options});
  const emit=(type,payload={},extra={})=>c.message({source:window,origin:'https://hk-br035.gt.tc',data:{namespace:'seasonav1.player.reply/v1',nonce:c.nonce,type,payload},...extra});
  const media=(position,duration=1380,extra={})=>emit('state',{position,duration,paused:true,volume:1,muted:false,videoReady:true,ad:false,error:false,...extra});
  return {c,commands,marks,statuses,timers,emit,media,stage,window,document};
}
(async()=>{
  let x=setup();for(const fn of [...x.timers.values()])fn();assert.equal(x.marks.length,0);x.c.destroy();checks.push('time_passing_without_video_position_never_marks_watched');
  x=setup();x.emit('ready');x.media(1103.9);assert.equal(x.marks.length,0);x.media(1104);await Promise.resolve();assert.equal(x.marks.length,1);assert.equal(x.marks[0].position,1104);x.media(1200);assert.equal(x.marks.length,1);x.c.destroy();checks.push('80_percent_of_23_minutes_triggers_once_at_18_24');
  x=setup();x.emit('ready');x.media(0);x.media(1200);assert.equal(x.marks.length,1);x.c.destroy();checks.push('seeking_directly_to_minute_20_counts_even_while_paused');
  x=setup();x.emit('state',{position:1200,duration:1380,paused:true,videoReady:true},{origin:'https://evil.invalid'});x.emit('state',{position:1200,duration:1380,paused:true,videoReady:true},{source:{}});x.emit('state',{position:1200,duration:1380,paused:true,videoReady:true},{data:{namespace:'seasonav1.player.reply/v1',type:'state',nonce:'a'.repeat(32)}});assert.equal(x.marks.length,0);x.c.destroy();checks.push('foreign_origin_frame_and_old_channel_messages_are_ignored');
  x=setup();x.emit('ready');x.media(1200,1380,{ad:true});x.media(1200,1380,{error:true});x.media(1200,NaN);assert.equal(x.marks.length,0);x.c.destroy();checks.push('advertisements_errors_and_invalid_duration_cannot_mark_an_episode');
  x=setup();x.emit('ready');x.media(60);const seek=x.c.bar.querySelector('.video-progress');seek.value='900';x.c.handleInput({target:seek});assert.equal(x.commands.at(-1).type,'seek');assert.equal(x.commands.at(-1).value,1242);assert.equal(x.marks.length,0);x.media(1242);assert.equal(x.marks.length,1);x.c.destroy();checks.push('seek_control_waits_for_confirmed_media_position_before_marking');
  x=setup();x.emit('ready');x.media(20,1380,{paused:false});const hide=x.timers.get(x.c.hideTimer);hide();assert(x.stage.classList.values.has('video-controls-hidden'));x.media(21,1380,{paused:false});assert(x.stage.classList.values.has('video-controls-hidden'));x.emit('pointer');assert(!x.stage.classList.values.has('video-controls-hidden'));x.c.destroy();checks.push('controls_stay_hidden_during_timeupdates_and_show_on_pointer_movement');
  x=setup();x.emit('ready');x.c.destroy();x.media(1200);assert.equal(x.marks.length,0);assert.equal(x.commands.at(-1).type,'disconnect');checks.push('closing_player_disconnects_and_ignores_late_progress');
  x=setup();x.emit('ready',{controlsVersion:2});x.media(60);let prevented=0;
  const key=(key,extra={})=>x.c.handleKey({key,target:{closest:()=>null},preventDefault(){prevented++;},...extra});
  key('ArrowRight');assert.equal(x.commands.at(-1).value,70);key(' ');assert.equal(x.commands.at(-1).type,'play');key('m');assert.equal(x.commands.at(-1).type,'mute');
  const count=x.commands.length;key(' ',{target:{closest:()=>({})}});key('m',{ctrlKey:true});key(' ',{repeat:true});assert.equal(x.commands.length,count);assert.equal(prevented,4);x.c.destroy();checks.push('keyboard_controls_seek_pause_mute_and_respect_form_fields_modifiers_and_repeat');
  x=setup();x.emit('ready',{controlsVersion:2});x.media(100,150);x.c.handleClick({target:{closest:()=>({dataset:{video:'intro'}})}});assert.equal(x.commands.at(-1).value,150);assert.equal(x.marks.length,0);x.c.destroy();checks.push('skip_intro_adds_85_seconds_clamped_to_duration_and_waits_for_media_confirmation');
  x=setup();x.emit('ready',{controlsVersion:2});const rate=x.c.bar.querySelector('.video-rate');assert.equal(rate.hidden,false);rate.value='1.5';x.c.handleInput({type:'change',target:rate});assert.equal(x.commands.at(-1).type,'rate');assert.equal(x.commands.at(-1).value,1.5);x.media(12,100,{playbackRate:1.25});assert.equal(rate.value,'1.25');x.c.destroy();checks.push('speed_control_sends_rate_and_reflects_actual_playback_rate');
  x=setup();x.emit('ready');assert.equal(x.c.bar.querySelector('.video-rate').hidden,true);x.c.destroy();checks.push('old_extension_keeps_basic_controls_without_showing_unsupported_speed');
  x=setup();x.emit('ready',{controlsVersion:2});x.media(20,100,{buffered:[[0,40],[65,85],[-1,99],[80,50],[0,Infinity]]});const bg=x.c.bar.querySelector('.video-buffered').style.background;assert(bg.includes('40%')&&bg.includes('65%')&&bg.includes('85%'));assert(!bg.includes('Infinity')&&!bg.includes('-1%'));assert.equal(x.c.bar.querySelector('.video-played').style.width,'20%');x.c.destroy();checks.push('disjoint_buffered_ranges_and_played_position_are_separate_and_validated');
  x=setup();x.media(0,1380);x.c.bar.querySelector('.video-progress').getBoundingClientRect=()=>({left:100,width:1000});x.c.previewTime({clientX:600});const tip=x.c.bar.querySelector('.video-seek-preview');assert.equal(tip.textContent,'11:30');assert.equal(tip.hidden,false);x.c.previewTime({clientX:2000});assert.equal(tip.textContent,'23:00');x.c.hidePreview();assert.equal(tip.hidden,true);x.c.destroy();checks.push('seek_hover_previews_time_without_seeking_or_marking_watched');
  x=setup();assert.equal(x.c.notice.hidden,true);x.emit('ready');x.media(1104);await new Promise(resolve=>setImmediate(resolve));assert.equal(x.c.notice.hidden,false);assert.equal(x.c.notice.querySelector('.player-sync-toast-text').textContent,'Capítulo 6 actualizado en MyAnimeList');assert.equal(x.c.notice.values['aria-live'],'polite');const timer=x.c.noticeTimer;x.c.notifySynced();assert.equal(x.c.noticeTimer,timer);x.timers.get(timer)();x.timers.get(x.c.noticeExitTimer)();assert.equal(x.c.notice.hidden,true);x.c.notifySynced();assert.equal(x.c.notice.hidden,true);x.c.destroy();checks.push('confirmed_mal_update_announces_chapter_once_and_dismisses_automatically');
  for(const status of ['pending','blocked','error']){x=setup({state:status,message:'Sin confirmar'});x.emit('ready');x.media(1104);await new Promise(resolve=>setImmediate(resolve));assert.equal(x.c.notice.hidden,true);x.c.destroy();}checks.push('pending_blocked_and_failed_updates_never_claim_mal_success');
  x=setup();x.emit('ready');x.media(1104);x.c.destroy();await new Promise(resolve=>setImmediate(resolve));assert.equal(x.c.syncNoticeShown,false);assert.equal(x.c.notice.isConnected,false);x=setup();x.emit('ready');x.media(1104);await new Promise(resolve=>setImmediate(resolve));const noticeTimer=x.c.noticeTimer;x.c.destroy();assert(!x.timers.has(noticeTimer));assert.equal(x.c.notice.isConnected,false);checks.push('closing_or_switching_player_cancels_notices_and_late_confirmations');
  const saved=[],prefs=[];let ended=0;
  x=setup(undefined,{resumePosition:1200,preferences:{volume:0.35,rate:1.5},onPosition:(s,force)=>saved.push([s.position,force]),onPreference:v=>prefs.push(v),onEnded:()=>ended++});
  x.emit('ready',{controlsVersion:2});x.media(0);assert.equal(saved.length,0);assert.equal(x.marks.length,0);assert(x.commands.some(m=>m.type==='pause'));assert(x.commands.some(m=>m.type==='volume'&&m.value===0.35));
  x.c.resume.listeners.click({target:{closest:()=>({dataset:{resume:'continue'}})}});assert(x.commands.some(m=>m.type==='seek'&&m.value===1200));x.media(0);assert.equal(saved.length,0);x.media(1200);assert.equal(saved[0][0],1200);assert.equal(x.marks.length,1);
  x.media(1380,1380,{ended:true});x.media(1380,1380,{ended:true});assert.equal(ended,1);x.c.destroy();assert.equal(saved.at(-1)[1],true);checks.push('resume_waits_for_user_choice_and_confirmed_seek_persists_exact_position_and_ended_once');
  x=setup(undefined,{resumePosition:1200,onPosition:s=>saved.push([s.position])});x.emit('ready');x.media(1200);assert.equal(x.marks.length,0);x.c.resume.listeners.click({target:{closest:()=>({dataset:{resume:'restart'}})}});x.media(0);assert(x.c.resumeReady);assert.equal(x.marks.length,0);x.c.destroy();checks.push('start_again_does_not_mark_saved_80_percent_position');
  x=setup(undefined,{autoplay:true});x.emit('ready',{controlsVersion:2});x.media(0);x.media(1);assert.equal(x.commands.filter(m=>m.type==='play').length,1);assert.equal(x.marks.length,0);x.c.destroy();
  x=setup(undefined,{autoplay:true,resumePosition:1200});x.emit('ready');x.media(0);assert.equal(x.commands.filter(m=>m.type==='play').length,0);assert(x.c.resumePending);x.c.destroy();
  checks.push('automatic_next_requests_play_once_when_video_is_ready_and_preserves_resume_choice');
  let repeats=0;x=setup(undefined,{onEnded:()=>repeats++});x.emit('ready');x.media(1380,1380,{ended:true});x.media(1380,1380,{ended:true});assert.equal(repeats,1);x.media(1200);x.media(1380,1380,{ended:true});assert.equal(repeats,2);x.c.destroy();
  checks.push('replaying_after_cancelling_next_can_trigger_automatic_next_again');
  x=setup(undefined,{intro:{start:60,end:145}});x.emit('ready',{controlsVersion:2});x.media(70);x.c.handleClick({target:{closest:()=>({dataset:{video:'intro'}})}});assert.equal(x.commands.at(-1).value,145);assert.equal(x.marks.length,0);x.c.destroy();checks.push('per_anime_intro_seeks_to_saved_endpoint_instead_of_adding_85_seconds');
  const mobileSaved=[];let mobileEnded=0;
  x=setup(undefined,{nativeControls:true,resumePosition:1200,preferences:{volume:0.2,rate:1.5,muted:true},onPosition:s=>mobileSaved.push(s.position),onEnded:()=>mobileEnded++});
  assert(!x.c.resume);x.emit('ready',{controlsVersion:2});x.media(0);assert.equal(mobileSaved.length,0);assert.equal(x.c.bar.hidden,true);
  assert(!x.commands.some(m=>['activate','volume','mute','rate','pause','seek'].includes(m.type)));
  const mobileCount=x.commands.length;x.c.handleKey({key:' ',preventDefault(){throw Error('Native keys intercepted');}});x.c.handleClick({target:{closest:()=>({dataset:{video:'toggle'}})}});assert.equal(x.commands.length,mobileCount);
  x.media(1104);assert.equal(x.marks.length,1);assert.equal(mobileSaved[0],1104);assert.equal(x.c.bar.hidden,true);x.media(1380,1380,{ended:true});assert.equal(mobileEnded,1);x.c.destroy();
  checks.push('mobile_keeps_original_controls_and_preferences_while_retaining_verified_progress_when_telemetry_exists');
  x=setup(undefined,{nativeControls:true});for(const fn of [...x.timers.values()])fn();assert(!x.statuses.some(s=>/Instala|recarga la extensión/.test(s[0])));assert.equal(x.c.bar.hidden,true);assert.equal(x.marks.length,0);x.c.destroy();
  checks.push('mobile_without_extension_never_shows_desktop_controls_or_promises_automatic_progress');
  const result={ok:true,count:checks.length,checks};fs.writeFileSync('verification/player-controller-check.json',JSON.stringify(result,null,2));console.log(JSON.stringify(result,null,2));
})().catch(e=>{console.error(e);process.exitCode=1;});
