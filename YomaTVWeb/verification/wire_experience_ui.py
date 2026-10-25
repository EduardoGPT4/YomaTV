from pathlib import Path
root=Path(__file__).resolve().parents[1]/'htdocs'
def edit(name,old,new):
 p=root/name;s=p.read_text(encoding='utf-8-sig');assert old in s,(name,old[:80]);p.write_text(s.replace(old,new),encoding='utf8')
edit('assets/app.js','<div class="episodes-grid">${episodeTiles(eps)}</div>','${detailEpisodesView(eps)}')
edit('assets/app.js',"const r = await api('queue', { slugs, mode, episode_ids: ids });","if(mode==='all'||mode==='selected'){ids=await previewQueue(slugs,mode,ids);if(!ids.length)return;mode='selected';}\n  const r = await api('queue', { slugs, mode, episode_ids: ids });")
edit('assets/app.js',"const ids = [\n        ...document.querySelectorAll('.episode-select:checked:not(:disabled)'),\n      ].map((x) => Number(x.value));","const ids = episodeSelectionIds();")
edit('assets/downloads.js','${allowed ? \'\' : \'disabled\'}>${done','${allowed ? \'\' : \'disabled\'} ${typeof episodeSelection===\'function\'&&episodeSelection().has(Number(ep.id))&&allowed?\'checked\':\'\'}>${done')
edit('assets/downloads.js',"selected.disabled = !document.querySelector(\n        '.episode-select:checked:not(:disabled)'\n      );","selected.disabled = typeof episodeSelectionIds==='function'?episodeSelectionIds().length===0:!document.querySelector('.episode-select:checked:not(:disabled)');\n    const count=document.querySelector('[data-selection-count]');if(count&&typeof episodeSelectionIds==='function')count.textContent=`${episodeSelectionIds().length} seleccionados`;")
edit('assets/downloads.js','<div class="filter-bar">${queueFilterSelect()}<span class="muted">Capítulos en orden numérico','${queueGroupControls(group)}<div class="filter-bar">${queueFilterSelect()}<span class="muted">Capítulos en orden numérico')
edit('assets/downloads.js','${jobStatus(job)}</div>${[','${jobStatus(job)}</div>${typeof filePresenceMarkup===\'function\'?filePresenceMarkup(job):\'\'}${[')
edit('assets/bridge.js','this.capabilities = Array.isArray(result.capabilities)','this.info=result;\n    this.capabilities = Array.isArray(result.capabilities)')
edit('assets/bridge.js','  forget() {','''  control(installation,ids,action,extra={}) {
    return this.request('/control',{format:'seasonav1.web-control/v1',installation,ids,action,...extra});
  }
  files(installation,ids) {return this.request('/files',{installation,ids});}
  forget() {
    this.info=null;''')
edit('assets/feature-ui.js',"${button('mal_refresh_all', 'Actualizar MAL'",'<button class="button ghost" data-exp="batch">Revisar coincidencias</button>${button(\'mal_refresh_all\', \'Actualizar MAL\'')
edit('index.php','  <script src="assets/catalog-tools.js', '''  <script src="assets/player-experience.js?v=<?= filemtime(__DIR__ . '/assets/player-experience.js') ?>" defer></script>
  <script src="assets/experience-ui.js?v=<?= filemtime(__DIR__ . '/assets/experience-ui.js') ?>" defer></script>
  <script src="assets/accessibility.js?v=<?= filemtime(__DIR__ . '/assets/accessibility.js') ?>" defer></script>
  <script src="assets/radio-library.js?v=<?= filemtime(__DIR__ . '/assets/radio-library.js') ?>" defer></script>
  <script src="assets/catalog-tools.js''')
edit('index.php','<div class="app-shell">','<a class="skip-content" href="#main">Saltar al contenido</a>\n<div class="app-shell">')
edit('index.php','<aside class="sidebar" id="sidebar">','<aside class="sidebar" id="sidebar"><button class="button ghost mobile-sidebar-close" data-action="menu" type="button">Cerrar menú</button>')
edit('sw.js',"20261017-catalog-v4","20261018-experience-v5")
edit('sw.js',"  'assets/player-controller.js',","  'assets/player-controller.js',\n  'assets/player-experience.js',\n  'assets/experience-ui.js',\n  'assets/accessibility.js',\n  'assets/radio-library.js',")
edit('assets/theme.js',"theme: 'dark', accent: 'mint'","theme: 'dark', accent: 'mint', density:'compact'")
edit('assets/theme.js',"if (['mint', 'blue', 'rose', 'violet'].includes(saved.accent))","if(['compact','normal'].includes(saved.density))themePreferences.density=saved.density;\n  if (['mint', 'blue', 'rose', 'violet'].includes(saved.accent))")
edit('assets/theme.js','document.documentElement.dataset.accent = themePreferences.accent;','document.documentElement.dataset.accent = themePreferences.accent;\n  document.documentElement.dataset.density=themePreferences.density;')
edit('assets/theme.js',"(key === 'theme' &&", "!['theme','accent','density'].includes(key) ||\n    (key==='density'&&!['compact','normal'].includes(value)) ||\n    (key === 'theme' &&")
edit('assets/feature-ui.js','<h2 class="panel-title">Apariencia</h2>','<h2 class="panel-title">Apariencia</h2><label>Densidad<select class="select-input" id="appearance-density"><option value="compact" ${themePreferences.density===\'compact\'?\'selected\':\'\'}>Compacta</option><option value="normal" ${themePreferences.density===\'normal\'?\'selected\':\'\'}>Normal</option></select></label>')
edit('private/experience.php',"$rows[]=['user_id'=>uid(),'job_id'=>$item['web_id']", "if($item['present']===null&&($item['known']??null)!==false)continue;\n      $rows[]=['user_id'=>uid(),'job_id'=>$item['web_id']")
# Serialize cancellation with the existing MAL lock; never tombstone a title for a rewatch.
p=root/'private/experience.php';s=p.read_text(encoding='utf8');start=s.index('  $row=sql($db,\'SELECT lock_until',s.index('function mal_cancel_progress'))
s=s[:start]+'''  $db->beginTransaction();
  try {
    $lock=$db->getAttribute(PDO::ATTR_DRIVER_NAME)==='mysql'?' FOR UPDATE':'';
    $row=sql($db,'SELECT lock_until FROM sa1_watch_sync WHERE user_id=? AND slug=?'.$lock,[uid(),$slug])->fetch();
    if($row && (int)$row['lock_until']>time())throw new WebError('Hay una actualización de MAL en curso. Intenta de nuevo al terminar.',409);
    sql($db,"UPDATE sa1_watch_sync SET state='blocked',error_kind='corrected',generation=?,lock_until=0 WHERE user_id=? AND slug=?",[bin2hex(random_bytes(16)),uid(),$slug]);
    $db->commit();
  }catch(Throwable $error){if($db->inTransaction())$db->rollBack();throw $error;}
}
''';p.write_text(s,encoding='utf8')
