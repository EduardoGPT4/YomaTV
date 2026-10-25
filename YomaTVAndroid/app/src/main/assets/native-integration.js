(() => {
  'use strict';
  if (window.__seasonNative || !window.YomaAndroid || location.origin !== 'https://hk-br035.gt.tc' || !location.pathname.startsWith('/seasonav1/')) return;
  window.__seasonNative = true;document.documentElement.classList.add('yoma-native');
  const post = data => YomaAndroid.postMessage(JSON.stringify(data));
  let previousAuth = '', previousRoute = '', timer;
  if(document.head){
    const style=document.createElement('style');style.id='season-android-navigation';
    style.textContent='.mobile-navigation{display:none!important}.footer{padding-bottom:24px!important}';
    document.head.append(style);
  }
  let suspended = false, nativeRendered=false;
  const hidden=Object.getOwnPropertyDescriptor(Document.prototype,'hidden');
  if(hidden?.get)Object.defineProperty(document,'hidden',{configurable:true,get:()=>suspended||hidden.get.call(document)});

  window.addEventListener('season-native-suspend', () => {
    if (suspended) return;
    suspended = true;
    if (typeof radio !== 'undefined') radio.pause();
    if(typeof playerController!=='undefined'&&playerController)playerController.post('pause');
    document.dispatchEvent(new Event('visibilitychange'));
  });
  window.addEventListener('season-native-resume', () => {
    if (!suspended) return;
    suspended = false;
    previousAuth='';document.dispatchEvent(new Event('visibilitychange'));update();
  });
  function update() {
    if (suspended || typeof state === 'undefined' || !state) return;
    if(!nativeRendered&&typeof render==='function'){nativeRendered=true;render();}
    const auth = JSON.stringify({type:'auth',owner:Number(state.user?.id)||0,name:String(state.user?.name||''),mal:Boolean(state.mal?.connected)});
    if (auth !== previousAuth) { previousAuth = auth; YomaAndroid.postMessage(auth); }
    const route=location.hash||'#discover';if(route!==previousRoute){previousRoute=route;post({type:'navigation',route});}
    const transport = document.querySelector('.watch-actions')||document.querySelector('.watch-transport');
    if (transport && !transport.querySelector('[data-native-offline]')) {
      const b = document.createElement('button'); b.type='button'; b.className='button primary'; b.dataset.nativeOffline='episode'; b.textContent='↓ Descargar'; transport.append(b);
    }
    const episodes = document.querySelector('#dialog .episodes-header');
    if (episodes && !episodes.querySelector('[data-native-offline]')) {
      const b = document.createElement('button'); b.type='button'; b.className='button small primary'; b.dataset.nativeOffline='anime'; b.textContent='↓ Capítulos para llevar'; episodes.append(b);
    }
  }
  new MutationObserver(() => { clearTimeout(timer); timer = setTimeout(update, 300); }).observe(document.documentElement, {childList:true,subtree:true});
  window.addEventListener('pageshow', () => { previousAuth=''; update(); });
  window.addEventListener('hashchange',update);
  document.addEventListener('visibilitychange', () => { if (!document.hidden) { previousAuth=''; update(); } });
  document.addEventListener('click', async event => {
    const b = event.target.closest('[data-native-offline]'); if (!b || b.disabled) return;
    event.preventDefault(); event.stopImmediatePropagation(); b.disabled = true;
    const owner = Number(state?.user?.id)||0;
    try {
      if (!owner) throw new Error('Inicia sesión antes de guardar capítulos en el celular.');
      let id;
      if (b.dataset.nativeOffline === 'episode') id = playerView?.episode?.id;
      else id = detailState?.episodes?.[0]?.id;
      if (!id && b.dataset.nativeOffline === 'anime') id = detailState?.anime?.episodes?.[0]?.id;
      if (!id) {
        const node = document.querySelector('#dialog [data-play]'); id = Number(node?.dataset.play);
      }
      if (!id) throw new Error('Actualiza el listado del anime antes de descargar.');
      const selectedLanguage = b.dataset.nativeOffline === 'episode' ? playerView?.servers?.[playerView.index]?.language : null;
      const language = String(selectedLanguage || state.settings?.language || 'SUB').toUpperCase();
      const result = await api('offline_plan', {episode_id:Number(id),language}), plan = result.offline_plan;
      if (Number(state?.user?.id) !== owner || Number(plan.owner) !== owner) throw new Error('La cuenta cambió; vuelve a elegir los capítulos.');
      if (b.dataset.nativeOffline === 'episode') plan.episodes = plan.episodes.filter(ep=>Number(ep.episode_id)===Number(id));
      post({...plan,type:'plan'});
    } catch (error) { if (typeof toast === 'function') toast(error.message,true); }
    finally { b.disabled = false; }
  }, true);
  update();
})();
