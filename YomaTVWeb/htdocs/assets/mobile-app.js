'use strict';
// Mobile presentation shares the existing actions, data and account protections.
function yomaNative(){return document.documentElement.classList.contains('yoma-native');}
function yomaHomeHero(featured){
  const a=featured[0]||catalogState?.items?.[0];
  return `<nav class="yoma-home-tabs" aria-label="Descubrir"><button class="selected" data-yoma-home="all">Para ti</button><button data-yoma-home="airing">En emisión</button><button data-yoma-home="movies">Películas</button><a class="icon-button" href="#catalog-results" aria-label="Buscar anime">${icon('search')}</a></nav>${a?`<section class="yoma-featured"><img src="${e(a.cover)}" alt="" decoding="async"><div class="yoma-featured-shade"></div><span class="yoma-featured-label">DESTACADO DEL HORARIO</span><div class="yoma-featured-copy"><h1>${e(a.title)}</h1><p>${e(a.category||'Anime')}${a.latest?' · '+e(a.latest)+' episodios disponibles':''}</p><div class="toolbar"><button class="button primary" data-open="${e(a.slug)}">${icon('play')}Ver capítulos</button><button class="button ghost" data-action="${a.status==='none'?'follow':'unfollow'}" data-slug="${e(a.slug)}">${icon(a.status==='none'?'plus':'check')}${a.status==='none'?'Mi lista':'En mi lista'}</button></div></div></section>`:''}`;
}
function yomaTodaySection(){
  const today=(new Date().getDay()+6)%7+1,rows=state.anime.filter(a=>a.active&&a.weekday===today);
  return `<section class="personal-section yoma-today"><div class="section-heading"><h2>Estrenos de hoy <span class="yoma-count">${rows.length}</span></h2><button class="text-button" data-view="schedule">Ver todos →</button></div>${rows.length?`<div class="yoma-horizontal">${rows.slice(0,12).map(a=>card(a)).join('')}</div>`:'<p class="muted">Hoy no hay títulos anunciados en el horario actual.</p>'}</section>`;
}
function yomaScheduleView(rows){
  return `<section class="yoma-season"><header><h1>Temporada</h1><p>Descubre lo que se estrena</p></header><div class="yoma-season-pill">${icon('calendar')}<strong>${e(state.season)}</strong><button class="text-button" data-action="calendar_open" aria-label="Abrir calendario">Ver calendario →</button></div><div class="yoma-schedule-tools"><span>Horario actual</span><a class="text-button" href="calendar.php">Exportar .ics ↗</a>${state.user?.is_admin?button('sync','Actualizar','refresh','','small ghost'):''}</div><div class="day-tabs" role="group" aria-label="Día del horario">${[0,1,2,3,4,5,6,7].map(d=>`<button class="day-tab ${day===d?'active':''}" data-day="${d}" aria-pressed="${day===d}">${d?['Lun','Mar','Mié','Jue','Vie','Sáb','Dom'][d-1]:'Todos'}</button>`).join('')}</div>${searchBox()}<div class="section-heading"><h2>${day?'Estrenos del '+DAYS[day-1].toLocaleLowerCase():'Esta semana'}</h2><span>${rows.length} títulos</span></div><div class="yoma-season-grid">${rows.map(a=>`<article class="yoma-release"><a data-open="${e(a.slug)}" href="#anime-${e(a.slug)}"><div class="yoma-release-cover"><img src="${e(a.cover)}" loading="lazy" alt=""><span>Ep. ${e(a.latest||'—')}</span></div><h3>${e(a.title)}</h3></a><p>${e(DAYS[a.weekday-1])}${a.latest?' · Episodio '+e(a.latest):''}</p><span data-card-download="${e(a.slug)}">${cardDownload(a)}</span></article>`).join('')||'<p class="muted">No hay estrenos para este día o búsqueda.</p>'}</div><p class="muted yoma-schedule-note">Las fechas y capítulos proceden del horario actual de AnimeAV1. No se anuncian horas ni temporadas futuras sin confirmar.</p></section>`;
}
document.addEventListener('click',event=>{
  const node=event.target.closest('[data-yoma-home]');if(!node)return;
  const mode=node.dataset.yomaHome;
  Object.assign(catalogFilters,{...CATALOG_DEFAULTS,include_genres:[],exclude_genres:[],category:mode==='movies'?'Película':'',airing:mode==='airing'?'currently_airing':''});
  catalogWriteRoute();render();loadCatalog();
  if(mode!=='all')document.querySelector('#catalog-filters')?.scrollIntoView({behavior:'smooth',block:'start'});
});
