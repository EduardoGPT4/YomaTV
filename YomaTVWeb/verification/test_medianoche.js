'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const checks=[];
const appearance=fs.readFileSync('htdocs/assets/theme.js','utf8');
let saved=JSON.stringify({theme:'light',accent:'mint',density:'compact'}),writes=0;
const root={dataset:{}};
const context=vm.createContext({document:{documentElement:root},localStorage:{getItem:()=>saved,setItem:(k,v)=>{saved=v;writes++;}},matchMedia:()=>({matches:false,addEventListener(){}})});
vm.runInContext(appearance,context);
assert.equal(root.dataset.theme,'light');assert.equal(root.dataset.accent,'vermilion');assert.equal(root.dataset.density,'normal');
vm.runInContext("setAppearance('theme','dark');setAppearance('density','compact');setAppearance('accent','mint')",context);
assert.equal(root.dataset.theme,'dark');assert.equal(root.dataset.accent,'vermilion');assert.equal(root.dataset.density,'compact');assert.equal(writes,2);
checks.push('legacy_accent_cannot_recolor_semantic_states_and_existing_theme_is_preserved');
const fresh=vm.createContext({document:{documentElement:root},localStorage:{getItem:()=>saved},matchMedia:()=>({matches:false,addEventListener(){}})});
vm.runInContext(appearance,fresh);assert.equal(root.dataset.density,'compact');
checks.push('new_density_preference_survives_reload');

let focused=null;const listeners={},menuListeners={},attrs={};
const opener={isConnected:true,focus(){focused=this;doc.activeElement=this;}};
const first={hidden:false,getClientRects:()=>[1],focus(){focused=this;doc.activeElement=this;}},last={...first};
const menu={hidden:true,contains:n=>n===first||n===last,querySelector:()=>first,querySelectorAll:()=>[first,last]};
const toggle={...opener,setAttribute:(k,v)=>attrs[k]=v};
const backdrop={hidden:true};
const doc={activeElement:opener,documentElement:{classList:{add(){},remove(){}}},getElementById:id=>({'sidebar':menu,'sidebar-toggle':toggle,'sidebar-backdrop':backdrop}[id]),addEventListener:(k,v)=>{(listeners[k]??=[]).push(v);}};
const navigation=vm.createContext({document:doc});vm.runInContext(fs.readFileSync('htdocs/assets/sidebar.js','utf8'),navigation);
vm.runInContext('sidebarNavigation.toggle()',navigation);assert(!menu.hidden&&!backdrop.hidden);assert.equal(attrs['aria-expanded'],'true');assert.equal(focused,first);
doc.activeElement=last;let prevented=false;listeners.keydown[0]({key:'Tab',preventDefault(){prevented=true;}});assert(prevented&&focused===first);
listeners.keydown[0]({key:'Escape',preventDefault(){}});assert(menu.hidden&&backdrop.hidden);assert.equal(attrs['aria-expanded'],'false');assert.equal(focused,opener);
checks.push('overflow_menu_traps_keyboard_focus_and_escape_returns_to_its_opener');
vm.runInContext('sidebarNavigation.toggle()',navigation);
first.closest=selector=>selector==='button,a'?first:null;
listeners.click[0]({target:first});assert(menu.hidden);
checks.push('navigation_and_help_close_menu_before_opening_another_surface');

const source=fs.readFileSync('htdocs/assets/feature-ui.js','utf8');
const detail=vm.createContext({state:{user:{id:1}},lookupAnime:()=>null,episodeDownload:ep=>({phase:ep.phase}),e:v=>String(v).replaceAll('<','&lt;'),MAL_STATUSES:{watching:'Viendo'},button:()=>''});
vm.runInContext(source.slice(source.indexOf('function detailDownloadCounts('),source.indexOf('function catalogMetadataInfo(')),detail);
const html=vm.runInContext("detailProgressCards({slug:'test',mal:{id:5,status:'watching',watched:3}},[{watched:true,phase:'confirmed'},{watched:true,phase:'queued'},{watched:false,phase:'downloading'},{watched:false,phase:'cancelled'}])",detail);
assert(html.includes('2 <small>de 4 vistos'));assert(html.includes('>1</span> <small data-detail-download-label>guardado'));assert(html.includes('<h3>En tu PC</h3>'));assert(html.includes('2 en cola'));assert(html.includes('3 vistos en MAL'));
assert(html.includes('aria-valuenow="2"')&&html.includes('data-mal-edit="5"'));
checks.push('detail_summaries_derive_watched_downloaded_and_queued_counts_without_inventing_mal_progress');

const rgb=hex=>hex.match(/../g).map(c=>Number.parseInt(c,16)/255).map(c=>c<=.04045?c/12.92:((c+.055)/1.055)**2.4);
const luminance=hex=>rgb(hex).reduce((sum,v,i)=>sum+v*[.2126,.7152,.0722][i],0);
const contrast=(a,b)=>{let x=luminance(a),y=luminance(b);return (Math.max(x,y)+.05)/(Math.min(x,y)+.05);};
for(const palette of [
 {surface:'201D2B',text:'F4F1EA',muted:'A9A3BC',ok:'7FE3C0',gold:'F2C46D',info:'B9A8FF',accent:'FF6A55',ink:'1A0B09'},
 {surface:'EBE6E0',text:'211B29',muted:'655B70',ok:'18634C',gold:'805318',info:'65509B',accent:'A82B1C',ink:'FFFAF1'}]){
 for(const key of ['text','muted','ok','gold','info'])assert(contrast(palette[key],palette.surface)>=4.5,`${key} contrast`);
 assert(contrast(palette.accent,palette.ink)>=4.5);
}
checks.push('dark_and_light_text_statuses_and_primary_action_meet_45_contrast');
const result={ok:true,count:checks.length,checks};fs.writeFileSync('verification/medianoche-client-check.json',JSON.stringify(result,null,2));console.log(JSON.stringify(result,null,2));
