'use strict';
// DOM tree fixture, not a browser substitute. Tests identity, ordering and dirty-control contracts.
const vm=require('node:vm'),fs=require('node:fs'),assert=require('node:assert/strict');
class Node {
  constructor(name,attrs={},nodes=[]){this.nodeName=name.toUpperCase();this.nodeType=name==='#text'?3:1;this.attrs={...attrs};this.childNodes=[];this.dataset={};this.value=attrs.value||'';this.checked='checked' in attrs;for(const n of nodes)this.insertBefore(n,null);}
  get id(){return this.attrs.id||'';}get attributes(){return Object.entries(this.attrs).map(([name,value])=>({name,value}));}
  get firstChild(){return this.childNodes[0]||null;}get nextSibling(){return this.parentNode?.childNodes[this.parentNode.childNodes.indexOf(this)+1]||null;}
  getAttribute(n){return this.attrs[n]??null;}hasAttribute(n){return n in this.attrs;}setAttribute(n,v){this.attrs[n]=v;}removeAttribute(n){delete this.attrs[n];}
  insertBefore(n,before){if(n===before)return n;n.remove();const index=before?this.childNodes.indexOf(before):this.childNodes.length;if(index<0)throw Error('Not a child');this.childNodes.splice(index,0,n);n.parentNode=this;return n;}
  remove(){if(this.parentNode){this.parentNode.childNodes.splice(this.parentNode.childNodes.indexOf(this),1);this.parentNode=null;}}
  replaceWith(n){const parent=this.parentNode;parent.insertBefore(n,this);this.remove();}
  set innerHTML(name){this.childNodes.forEach(n=>n.parentNode=null);this.childNodes=[];for(const n of fixtures[name]())this.insertBefore(n,null);}
}
const text=value=>{const n=new Node('#text');n.nodeValue=value;return n;};
const row=(id,value)=>new Node('article',{'data-ui-key':String(id)},[text(value)]);
const control=value=>new Node('input',{id:'search',value});
const fixtures={first:()=>[control('initial'),row(1,'first'),row(2,'second')],second:()=>[control('server'),row(2,'changed'),row(3,'third'),row(1,'first')],third:()=>[control('saved'),row(3,'third')],large:()=>Array.from({length:2000},(_,i)=>row(i,'item-'+i)),largeUpdate:()=>Array.from({length:2000},(_,i)=>row(i,i===1000?'updated':'item-'+i))};
const events={},document={activeElement:null,addEventListener:(name,fn)=>events[name]=fn,createElement(name){assert.equal(name,'template');return {content:new Node('fragment'),set innerHTML(value){this.content.innerHTML=value;}};}};
const ctx=vm.createContext({document,WeakSet,Map,Set});vm.runInContext(fs.readFileSync('htdocs/assets/dom-renderer.js','utf8')+'\nthis.ui=SeasonUI;',ctx);
const target=new Node('main'),checks=[];
ctx.ui.renderInto(target,'first','1:catalog');const input=target.firstChild,first=target.childNodes[1],second=target.childNodes[2];input.form={};input.value='my draft';input.selectionStart=3;document.activeElement=input;events.input({target:input});
ctx.ui.renderInto(target,'second','1:catalog');assert.equal(target.firstChild,input);assert.equal(input.value,'my draft');assert.equal(input.selectionStart,3);assert.equal(target.childNodes[1],second);assert.equal(target.childNodes[3],first);assert.equal(second.firstChild.nodeValue,'changed');checks.push('focused_control_selection_and_existing_keyed_rows_survive_updates_and_reordering');
document.activeElement=null;ctx.ui.renderInto(target,'third','1:catalog');assert.equal(target.firstChild,input);assert.equal(input.value,'my draft');assert.equal(target.childNodes.length,2);checks.push('unfocused_dirty_draft_survives_and_removed_rows_are_pruned');
events['season-form-saved']({detail:{elements:[input]}});ctx.ui.renderInto(target,'third','1:catalog');assert.equal(input.value,'saved');checks.push('explicit_save_releases_dirty_control_for_server_values');
ctx.ui.renderInto(target,'first','2:catalog');assert.notEqual(target.firstChild,input);assert.equal(target.firstChild.value,'initial');checks.push('account_scope_change_rebuilds_without_leaking_previous_draft');
ctx.ui.renderInto(target,'large','2:queue');const originals=[...target.childNodes];ctx.ui.renderInto(target,'largeUpdate','2:queue');assert(target.childNodes.every((n,i)=>n===originals[i]));assert.equal(target.childNodes[1000].firstChild.nodeValue,'updated');checks.push('two_thousand_queue_rows_keep_identity_when_only_one_status_changes');

ctx.ui.renderInto(target,'first','3:catalog');const query=target.firstChild;query.value='old filter';events.input({target:query});document.activeElement=null;ctx.ui.renderInto(target,'third','3:catalog');assert.equal(query.value,'saved');checks.push('clearing_non_form_filters_does_not_keep_an_obsolete_dirty_value');
const makeSelect=value=>{const n=new Node('select',{id:'quality'},[new Node('option',{id:'option-'+value,value,selected:''},[text(value)])]);delete n.value;Object.defineProperty(n,'value',{get(){return this.childNodes.find(c=>c.hasAttribute('selected'))?.attrs.value||'';},set(v){for(const c of this.childNodes){if(c.attrs.value===v)c.setAttribute('selected','');else c.removeAttribute('selected');}}});return n;};
fixtures.selectOld=()=>[makeSelect('720')];fixtures.selectNew=()=>[makeSelect('1080')];ctx.ui.renderInto(target,'selectOld','4:settings');ctx.ui.renderInto(target,'selectNew','4:settings');assert.equal(target.firstChild.value,'1080');checks.push('new_select_options_keep_value_when_the_fresh_tree_is_consumed');
const result={ok:true,count:checks.length,checks,environment:'DOM tree test fixture; real browser validation pending'};fs.writeFileSync('verification/dom-renderer-check.json',JSON.stringify(result,null,2));console.log(JSON.stringify(result));
