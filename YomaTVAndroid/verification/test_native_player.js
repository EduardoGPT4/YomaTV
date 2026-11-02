'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../../YomaTVWeb/htdocs/assets/player-template.js'),'utf8');
const context={window:{YomaNativeOnline:true},e:v=>String(v??''),icon:()=>'<svg></svg>',SeasonMobilePlayback:{isMobile:()=>true},
  watchServerButtons:()=>'',watchServerNotice:()=>'',watchChapters:()=>'',watchRelated:()=>'',playerBookmarks:()=>''};
vm.createContext(context);vm.runInContext(source,context);
const p={episode:{id:7,title:'Fixture',number:'2'},servers:[{server:'MP4Upload',language:'DUB',url:'https://www.mp4upload.com/embed-fixture.html'}],index:0,chapters:[{id:7}],mal:{connected:true,linked:true,confirmed:true},anime:{cover:'https://example.com/cover.jpg'}};
let html=context.watchPageTemplate(p);assert(html.includes('data-native-online'));assert(!html.includes('<iframe'));assert(html.includes('80 %'));assert(!html.includes('data-watch="fullscreen"'));
context.window.YomaNativeOnline=false;html=context.watchPageTemplate(p);assert(html.includes('<iframe'));assert(!html.includes('data-native-online'));
context.window.YomaNativeOnline=true;p.servers[0].server='Voe';html=context.watchPageTemplate(p);assert(html.includes('<iframe'));assert(!html.includes('data-native-online'));
const report={ok:true,checks:['new_apk_opens_mp4upload_without_duplicate_iframe','online_mal_threshold_explained','old_apk_keeps_working','other_servers_preserve_existing_fallback']};
fs.writeFileSync(path.join(__dirname,'native-player-template-check.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report));
