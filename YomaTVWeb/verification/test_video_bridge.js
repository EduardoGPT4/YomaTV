'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
class El{
 constructor(){this.events={};this.classList={add(){},remove(){}};this.controls=true;}
 addEventListener(k,fn){this.events[k]=fn;}removeEventListener(k){delete this.events[k];}
 append(x){} getAttribute(k){return this[k]??null;}removeAttribute(k){delete this[k];}setAttribute(k,v){this[k]=v;}remove(){this.removed=true;}
}
const video=new El();Object.assign(video,{currentTime:20,duration:120,paused:true,volume:1,muted:false,playbackRate:1,currentSrc:'https://cdn.mp4upload.com/video.mp4',buffered:{length:2,start:i=>[0,80][i],end:i=>[40,100][i]}});
let plays=0,pauses=0,pipCalls=0,ad=false;
video.play=async()=>{plays++;video.paused=false;};video.pause=()=>{pauses++;video.paused=true;};video.requestPictureInPicture=async()=>{pipCalls++;document.pictureInPictureElement=video;};
const events=[],window={addEventListener(){},removeEventListener(){}};
const document={documentElement:new El(),head:new El(),body:new El(),pictureInPictureEnabled:true,addEventListener(){},removeEventListener(){},createElement:()=>new El(),querySelector:s=>s.startsWith('video#')?video:(ad?new El():null),exitPictureInPicture:async()=>{document.pictureInPictureElement=null;}};
const ctx=vm.createContext({window,document,Date,Number,Promise,setTimeout:()=>1,clearTimeout(){},MutationObserver:class{observe(){}disconnect(){}}});
vm.runInContext(fs.readFileSync('browser-extension/YomaTV-Brave/video-bridge.js','utf8'),ctx);
const bridge=new ctx.YomaTVVideoBridge({send:m=>events.push(m),sourceAllowed:s=>s.startsWith('https://cdn.mp4upload.com/')}),nonce='a'.repeat(32),checks=[];
const command=(type,value)=>bridge.command({type,value,nonce});
(async()=>{
 await command('connect');assert.equal(events.find(x=>x.type==='ready').payload.controlsVersion,2);let state=events.at(-1).payload;assert.equal(state.buffered.length,2);assert.equal(state.buffered[1][0],80);checks.push('ready_announces_new_controls_and_native_buffer_ranges');
 await command('activate');assert.equal(video.controls,false);assert(bridge.pip);assert.equal(bridge.pip.hidden,false);
 await bridge.pip.events.click({preventDefault(){},stopImmediatePropagation(){}});await Promise.resolve();assert.equal(pipCalls,1);checks.push('pip_is_requested_by_button_in_video_document_without_runtime_roundtrip');
 await command('rate',1.5);assert.equal(video.playbackRate,1.5);await command('rate',5);assert.equal(video.playbackRate,1.5);assert.equal(events.at(-1).payload.playbackRate,1.5);checks.push('native_playback_speed_is_bounded_and_reported');
 const key=(key,extra={})=>bridge.keyboard({key,target:{closest:()=>null},preventDefault(){},stopImmediatePropagation(){},...extra});
 key('ArrowRight');assert.equal(video.currentTime,30);key('ArrowLeft');assert.equal(video.currentTime,20);key('m');assert.equal(video.muted,true);key(' ');await Promise.resolve();assert.equal(plays,1);key('k');assert.equal(pauses,1);key('f');assert.equal(events.at(-1).type,'key');checks.push('iframe_keys_control_media_and_relay_fullscreen_without_videojs_double_handling');
 key('ArrowRight',{target:{closest:()=>({})}});key('ArrowRight',{ctrlKey:true});assert.equal(video.currentTime,20);key('m',{repeat:true});assert.equal(video.muted,true);checks.push('iframe_hotkeys_leave_fields_browser_shortcuts_and_repeats_alone');
 ad=true;bridge.state(true);key('ArrowRight');assert.equal(video.currentTime,20);assert.equal(bridge.pip.hidden,true);assert.equal(events.at(-1).type,'state');assert.equal(events.at(-1).payload.ad,true);checks.push('advertisements_do_not_expose_controls_or_handle_shortcuts');ad=false;
 await command('disconnect');assert.equal(video.controls,true);assert.equal(bridge.pip,null);bridge.destroy();checks.push('disconnect_restores_provider_controls_and_removes_injected_button');
 const result={ok:true,count:checks.length,checks};fs.writeFileSync('verification/video-bridge-check.json',JSON.stringify(result,null,2));console.log(JSON.stringify(result,null,2));
})().catch(e=>{console.error(e);process.exitCode=1;});
