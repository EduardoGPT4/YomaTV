'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync('htdocs/assets/feature-ui.js','utf8'),requests=[],errors=[];
const context=vm.createContext({console,Number,Date,URL,Promise,
 state:{user:{id:7}},view:'notifications',window:{},
 api(action){return new Promise(resolve=>requests.push({action,resolve}));},
 document:{addEventListener(){}},e:v=>String(v),icon:()=>'',button:()=>'',empty:()=>'',title:()=>'',dateText:()=>'',
 render(){},renderFeaturePage(){},toast:message=>errors.push(message),updateFeatureHeader(){},scheduleWatchPump(){},
});
const run=code=>vm.runInContext(code,context);
run(`let noticesPage=null,noticesUpTo=0,noticesHasMore=false,noticesLoading=false,noticeSequence=0,featureSequence=0,featureHome=null;`);
run(source.slice(source.indexOf('function acceptFeatureResult('),source.indexOf('function scheduleWatchPump(')));
run(source.slice(source.indexOf('function notificationsView('),source.indexOf('function adminPanel(')));
run(fs.readFileSync('htdocs/assets/catalog-tools.js','utf8'));
const settle=()=>new Promise(resolve=>setImmediate(resolve));
const checks=[];
(async()=>{
 run('notificationsView();notificationsView()');assert.equal(requests.length,1);
 requests.shift().resolve({notifications:[{id:5,slug:'test',episode_count:3,number:4,first_number:2,unread:3}],notifications_up_to:5});await settle();
 assert.equal(run('noticesPage[0].id'),5);assert.equal(run('noticesUpTo'),5);assert.deepEqual(errors,[]);
 checks.push('grouped_notifications_load_once_and_render_without_reference_errors');
 run(`featureHome={user_id:7,revision:1,notifications:1,notifications_revision:5};acceptFeatureResult({home:{user_id:7,revision:2,notifications:1,notifications_revision:6}})`);
 assert.equal(run('noticesPage'),null);run('notificationsView()');
 run('state.user.id=8;featureSequence++;noticeSequence++;noticesLoading=false');
 requests.shift().resolve({notifications:[{id:6,slug:'private-user-7'}],notifications_up_to:6});await settle();
 assert.equal(run('noticesPage'),null);assert.deepEqual(errors,[]);
 checks.push('new_chapter_invalidates_group_even_when_unread_anime_count_is_unchanged');
 checks.push('late_notification_response_cannot_cross_account_boundaries');
 run(`state.user.id=7;savedFilterView()`);const old=requests.shift();
 run(`state.user.id=8;savedFilterView()`);const next=requests.shift();
 next.resolve({saved_filters:[{id:20,name:'Cuenta 8',filters:{}}]});await settle();
 old.resolve({saved_filters:[{id:10,name:'Privado 7',filters:{}}]});await settle();
 assert.equal(run('savedFilterRows[0].id'),20);
 checks.push('late_saved_search_response_does_not_replace_another_accounts_searches');
 let html='';context.modal=value=>html=value;run('calendarDialog(null,false)');
 assert(html.includes('calendar.php?scope=followed')&&!html.includes('webcal:')&&!html.includes('data-action="calendar_create"'));
 checks.push('blocked_host_offers_filtered_export_without_false_subscription_button');
 assert.deepEqual(errors,[]);
 const result={ok:true,count:checks.length,checks,network:'simulated'};
 fs.writeFileSync('verification/catalog-ui-check.json',JSON.stringify(result,null,2));console.log(JSON.stringify(result,null,2));
})().catch(error=>{console.error(error);process.exitCode=1;});
