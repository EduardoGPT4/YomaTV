'use strict';
const assert=(condition,message)=>{if(!condition)throw Error(message);};
const settle=()=>new Promise(resolve=>setTimeout(resolve,40));
async function geometryChecks(){
  await document.fonts.ready;const checks=[],width=document.documentElement.clientWidth;
  if(document.querySelector('.yoma-today')){
    for(const card of document.querySelectorAll('.yoma-today .anime-card')){
      const r=card.getBoundingClientRect(),b=card.querySelector('.card-download .button').getBoundingClientRect();
      assert(b.left>=r.left-1&&b.right<=r.right+1,'Prepare outside card at '+width);
      assert(getComputedStyle(card.querySelector('.format-badge')).display==='none','Format overlaps favorite');
      const favorite=card.querySelector('.card-favorite').getBoundingClientRect(),follow=card.querySelector('.card-follow').getBoundingClientRect();assert(follow.right<=favorite.left+1,'Favorite/follow overlap at '+width);
    }
    for(const meta of document.querySelectorAll('.personal-cards .mal-full-meta'))assert(getComputedStyle(meta).display==='none','APK style reveals duplicate MAL text');
    checks.push('home_cards_fit_and_keep_distinct_actions_'+width);
  }else{
    const dialog=document.querySelector('#dialog'),cover=document.querySelector('.detail-cover').getBoundingClientRect(),episodes=document.querySelector('.episodes-header').getBoundingClientRect();
    assert(cover.height<=(width<=680?133:256),'Cover too large '+width);
    assert(episodes.top-dialog.getBoundingClientRect().top<800,'Episodes require excessive scroll '+width);
    assert(!document.querySelector('.detail-synopsis').open,'Synopsis initially expanded');
    const picker=document.querySelector('.episode-picker');assert(!picker.open,'Batch tools initially expanded');picker.open=true;const label=picker.querySelector('label').getBoundingClientRect(),input=picker.querySelector('input').getBoundingClientRect();assert(input.width>label.width-3&&input.left>=label.left-1&&input.right<=label.right+1,'Range field outside its label');picker.open=false;
    assert(document.querySelector('.detail-info').getBoundingClientRect().right<=dialog.getBoundingClientRect().right,'Title outside dialog');
    checks.push('compact_detail_keeps_episodes_near_top_'+width);
  }return checks;
}
async function choiceChecks(){
  const checks=[],source=document.querySelector('#status-test');let changes=0,inputs=0;source.addEventListener('change',()=>changes++);source.addEventListener('input',()=>inputs++);
  const open=node=>node.dispatchEvent(new MouseEvent('click',{bubbles:true,cancelable:true}));
  const option=text=>[...document.querySelectorAll('.choice-option')].find(b=>b.textContent.includes(text));
  open(source);assert(document.querySelector('.choice-sheet').open,'Choice did not open');assert(option('Viendo').getAttribute('aria-selected')==='true','Wrong initial selection');assert(option('No disponible').disabled,'Disabled option enabled');
  option('Completado').click();await settle();assert(source.value==='completed'&&changes===1&&inputs===1,'Choice did not preserve change handlers');assert(new FormData(source.form).get('status')==='completed','Form value lost');assert(document.activeElement===source,'Focus not restored');checks.push('choice_uses_existing_form_and_fires_one_input_change');
  open(source);option('Completado').click();await settle();assert(changes===1,'Same choice emitted extra change');checks.push('same_choice_does_not_repeat_actions');
  open(source);document.activeElement.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true,cancelable:true}));await settle();assert(!document.querySelector('.choice-sheet').open&&source.value==='completed','Escape changed selection');checks.push('escape_preserves_value_and_returns_focus');
  source.dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowDown',bubbles:true,cancelable:true}));assert(document.querySelector('.choice-sheet').open,'Keyboard did not open choices');document.dispatchEvent(new Event('season-account-reset'));await settle();assert(!document.querySelector('.choice-sheet').open,'Account reset left private choice open');checks.push('keyboard_and_account_reset_close_safely');
  open(document.querySelector('#genre-test'));const search=document.querySelector('.choice-sheet input');assert(!search.hidden,'Long list lacks search');search.value='accion';search.dispatchEvent(new Event('input',{bubbles:true}));assert(document.querySelectorAll('.choice-option').length===1&&option('Acción'),'Accent search failed');search.value='img';search.dispatchEvent(new Event('input',{bubbles:true}));assert(document.querySelector('.choice-option').textContent.includes('<img')&&!document.querySelector('.choice-option img'),'Option text parsed as HTML');window.dispatchEvent(new Event('season-native-suspend'));await settle();checks.push('long_choices_search_accents_and_escape_untrusted_labels');
  document.querySelector('#nested-test').click();const parent=document.querySelector('#dialog'),nested=document.querySelector('#status-nested');open(nested);assert(parent.open&&document.querySelector('.choice-sheet').open,'Nested choice failed');option('Por ver').click();await settle();assert(parent.open&&nested.value==='planned','Choice closed the parent dialog');parent.close();await settle();checks.push('choices_work_inside_existing_anime_and_form_dialogs');
  open(source);source.remove();await settle();assert(!document.querySelector('.choice-sheet').open,'Removed source kept orphan popup');checks.push('replaced_filter_cannot_apply_a_stale_value');
  return checks;
}
