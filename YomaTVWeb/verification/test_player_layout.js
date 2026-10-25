'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
function node(name){return {name,isConnected:true,children:[],childNodes:[],dataset:{},remove(){this.isConnected=false;},replaceChildren(...children){this.childNodes=children;},replaceWith(other){this.replacement=other;},append(child){this.children.push(child);}};}
const stage=node('fullscreen-stage'),oldHeader=node('old-header'),oldAside=node('old-aside'),oldControls=node('old-controls');
const content=node('old-content');content.children=[stage,oldControls];
const old=node('root');old.querySelector=s=>({'.video-stage':stage,'.watch-heading':oldHeader,'.watch-content':content,'.watch-playlist':oldAside})[s];
const newStage=node('new-stage'),newFrame=node('episode-two-frame'),newControls=node('new-controls'),newHeader=node('new-heading'),newAside=node('new-aside'),nextContent=node('new-content');newStage.childNodes=[newFrame];nextContent.children=[newStage,newControls];
const next=node('new-root');next.dataset.episode='2';next.querySelector=s=>({'.video-stage':newStage,'.watch-heading':newHeader,'.watch-content':nextContent,'.watch-playlist':newAside})[s];
let inserted='',hasOld=true;
const main={querySelector:()=>hasOld?old:null,set innerHTML(html){assert(!hasOld,'A mounted player was destroyed');inserted=html;}};
const ctx=vm.createContext({document:{getElementById:()=>main,createElement:()=>({content:{querySelector:()=>next},set innerHTML(value){this.markup=value;}})}});
vm.runInContext(fs.readFileSync('htdocs/assets/player-layout.js','utf8'),ctx);
ctx.mountWatchPage('<section>episode two</section>');
assert.equal(stage.isConnected,true);assert.equal(old.isConnected,true);assert.equal(old.dataset.episode,'2');assert.equal(stage.childNodes[0],newFrame);assert.equal(oldHeader.replacement,newHeader);assert.equal(oldAside.replacement,newAside);assert.equal(oldControls.isConnected,false);assert(!content.children.includes(newStage));
hasOld=false;ctx.mountWatchPage('<section>first episode</section>');assert.equal(inserted,'<section>first episode</section>');
const result={ok:true,checks:['episode_change_keeps_fullscreen_stage_and_ancestors_connected','only_frame_controls_and_side_content_are_replaced','first_entry_mounts_normally']};fs.writeFileSync('verification/player-layout-check.json',JSON.stringify(result,null,2));console.log(JSON.stringify(result));
