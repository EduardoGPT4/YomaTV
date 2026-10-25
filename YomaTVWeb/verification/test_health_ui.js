'use strict';
const vm=require('node:vm'),fs=require('node:fs'),assert=require('node:assert/strict');
const events={},pending=[],downloads=[],requests=[],checks=[];let markup='',resets=0;
const health={release:'fixture',schema:'20261018.4',database:'sqlite',metrics:[{action:'catalog',requests:20,failures:0,average_ms:12,max_ms:30,queries_per_request:25}],pending:[],errors:[],freshness:{total:4485,genres:{checked:4485,oldest:1,newest:2}},plans:{},retention:{},backup:{}};
const ctx=vm.createContext({console,Number,Object,Date,JSON,Blob,
  state:{user:{id:1,is_admin:true},csrf:'fixture'},view:'settings',
  document:{addEventListener:(n,fn)=>events[n]=fn,createElement:()=>({click(){downloads.push(this.download);}})},
  e:String,button:(_,text)=>`<button>${text}</button>`,dateText:v=>String(v||'Sin comprobar'),
  api:()=>new Promise(resolve=>pending.push(resolve)),render(){markup=run('systemHealthPanel()');},toast(){},
  SeasonTransport:{epoch:0,request:(url,options,settings)=>{requests.push({url,options,settings});return new Promise(resolve=>pending.push(resolve));}},
  URL:{createObjectURL:()=> 'blob:fixture',revokeObjectURL(){}},setTimeout:fn=>fn(),
});
const run=code=>vm.runInContext(code,ctx);run(fs.readFileSync('htdocs/assets/health-ui.js','utf8'));
const button={disabled:false},click={target:{closest:()=>button},preventDefault(){}};
(async()=>{
  assert(run('systemHealthPanel()').includes('Salud y mantenimiento'));ctx.state.user.is_admin=false;assert.equal(run('systemHealthPanel()'),'');ctx.state.user.is_admin=true;checks.push('health_controls_are_hidden_for_non_admin_accounts');
  const loading=events.click(click);assert(button.disabled);pending.shift()({system_health:health});await loading;assert(!button.disabled);assert(markup.includes('Actualizar diagnóstico')&&!markup.includes('Comprobando…'));assert(markup.includes('4485')&&markup.includes('Géneros'));checks.push('health_refresh_restores_action_label_and_renders_data_age_and_metrics');
  const stale=events.click(click);ctx.state.user={id:2,is_admin:true};pending.shift()({system_health:{...health,release:'private-old-admin'}});await stale;assert(!run('systemHealthPanel()').includes('private-old-admin'));checks.push('late_health_response_does_not_cross_accounts');
  ctx.state.user={id:1,is_admin:true};const submit={disabled:false},error={textContent:''},form={id:'backup-form',elements:{password:{value:'Fixture-Only-Backup-Password'}},querySelector:s=>s==='button'?submit:error,reset(){resets++;}};
  const downloading=events.submit({target:form,preventDefault(){}});assert(submit.disabled);const request=requests.at(-1);assert.equal(request.url,'backup.php');assert.equal(request.settings.format,'blob');assert.equal(request.settings.timeout,120000);assert(!request.url.includes('Password'));pending.shift()({response:{ok:true},result:new Blob(['ciphertext'])});await downloading;assert.equal(downloads.length,1);assert.equal(resets,1);assert(!submit.disabled);checks.push('encrypted_backup_uses_post_body_shared_transport_and_resets_form_on_success');
  const cancelled=events.submit({target:form,preventDefault(){}});ctx.state.user={id:2,is_admin:false};ctx.SeasonTransport.epoch++;pending.shift()({response:{ok:true},result:new Blob(['old-account'])});await cancelled;assert.equal(downloads.length,1);checks.push('account_change_prevents_stale_backup_download');
  const result={ok:true,count:checks.length,checks};fs.writeFileSync('verification/health-ui-check.json',JSON.stringify(result,null,2));console.log(JSON.stringify(result));
})().catch(e=>{console.error(e);process.exitCode=1;});
