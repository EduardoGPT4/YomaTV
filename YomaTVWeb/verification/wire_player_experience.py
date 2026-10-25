from pathlib import Path
root=Path(__file__).resolve().parents[1]/'htdocs'
def edit(name,old,new):
 p=root/name;s=p.read_text(encoding='utf-8-sig');assert old in s,(name,old[:100]);p.write_text(s.replace(old,new),encoding='utf-8')
edit('assets/player-controller.js','onStatus, onExtension })','onStatus, onExtension, onPosition, onPreference, onEnded, resumePosition = 0, preferences = {} })')
edit('assets/player-controller.js','this.stage = stage;','''this.stage = stage;
      this.onPosition = onPosition || (() => {});
      this.onPreference = onPreference || (() => {});
      this.onEnded = onEnded || (() => {});
      this.preferences = preferences;
      this.resumePosition = Number(resumePosition) || 0;
      this.resumePending = this.resumePosition > 3;
      this.resumeReady = !this.resumePending;
      this.preferencesApplied = false;
      if (this.resumePending) {
        this.resume = document.createElement('div'); this.resume.className='player-resume';
        this.resume.innerHTML=`<strong>Continuar desde ${time(this.resumePosition)}</strong><button type="button" data-resume="continue">Continuar</button><button type="button" data-resume="restart">Desde el inicio</button>`;
        stage.append(this.resume);
        this.resume.addEventListener('click',event=>{
          const action=event.target.closest('[data-resume]')?.dataset.resume;
          if(!action||!this.activated)return;
          this.resumePending=false;this.resumeTarget=action==='continue'?Math.min(this.resumePosition,this.latest.duration):0;
          this.post('seek',this.resumeTarget);this.resume.remove();this.post('play');
        });
      }''')
edit('assets/player-controller.js',"this.onExtension(this.enhanced ? 'ready' : 'update');","this.onExtension(this.enhanced ? 'ready' : 'update', m.payload);\n        this.videoTimer=setTimeout(()=>{if(!this.activated&&!this.closed)this.onStatus('Extensión conectada; el servidor no entrega un video reproducible. Prueba otro servidor.','video');},30000);")
edit('assets/player-controller.js',"const seek = this.bar.querySelector('.video-progress');",'''clearTimeout(this.videoTimer);
      if(!this.preferencesApplied){
        this.preferencesApplied=true;
        if(Number.isFinite(this.preferences.volume))this.post('volume',this.preferences.volume);
        if(this.preferences.muted===true && s.muted!==true)this.post('mute');
        if(this.enhanced && Number.isFinite(this.preferences.rate))this.post('rate',this.preferences.rate);
        if(this.resumePending)this.post('pause');
      }
      if(!this.resumePending && !this.resumeReady && Math.abs(s.position-this.resumeTarget)<2)this.resumeReady=true;
      if(this.resumeReady){this.onPosition(s);if(s.ended===true&&s.position>=s.duration-2&&!this.endedSent){this.endedSent=true;this.onEnded();}}
      const seek = this.bar.querySelector('.video-progress');''')
edit('assets/player-controller.js','if (s.position / s.duration >= 0.8 && !this.thresholdSent)','if (this.resumeReady && s.position / s.duration >= 0.8 && !this.thresholdSent)')
edit('assets/player-controller.js',"if (event.type !== 'change' && t.matches('.video-volume')) this.post('volume', Number(t.value));","if (event.type !== 'change' && t.matches('.video-volume')) {this.post('volume', Number(t.value));this.onPreference({volume:Number(t.value),muted:false});}")
edit('assets/player-controller.js',"if (event.type === 'change' && t.matches('.video-rate') && this.enhanced) this.post('rate', Number(t.value));","if (event.type === 'change' && t.matches('.video-rate') && this.enhanced) {this.post('rate', Number(t.value));this.onPreference({rate:Number(t.value)});}")
edit('assets/player-controller.js',"if (action === 'mute') this.post('mute');","if (action === 'mute') {this.post('mute');this.onPreference({muted:!this.latest.muted});}")
edit('assets/player-controller.js',"this.post('disconnect');","if(this.resumeReady && this.latest.duration>0)this.onPosition(this.latest,true);\n      this.resume?.remove();clearTimeout(this.videoTimer);\n      this.post('disconnect');")
edit('assets/feature-ui.js','playerView.index = 0;','''const pref=playerView.playback?.preferences||{};
  playerView.index=Math.max(0,playerView.servers.findIndex(s=>s.server===pref.server&&s.language===pref.language));''')
edit('assets/feature-ui.js',"error: 'No se pudo guardar · se reintentará'","error: 'No se pudo guardar · se reintentará', rewatched:'Revisionado ✓ · MAL conservado'")
edit('assets/feature-ui.js',"<div class=\"toolbar player-controls\"><select id=\"player-server\"", "${typeof playerExtraControls==='function'?playerExtraControls(p):''}<div class=\"toolbar player-controls\"><select id=\"player-server\"")
edit('assets/feature-ui.js',"episodeNumber: p.episode.number,","episodeNumber: p.episode.number,\n      ...playerExperience(p),")
edit('assets/feature-ui.js','onExtension: (status) => {','onExtension: (status, info) => {\n        playerDiagnostic(\'extension\', status===\'ready\'?`Conectada ${info?.extensionVersion||\'1.1 o posterior\'}`:status);')
edit('assets/feature-ui.js','node.textContent = message;','node.textContent = message;\n          playerDiagnostic([\'saving\',\'synced\',\'pending\',\'blocked\',\'rewatched\'].includes(status)?\'mal\':\'video\',message);')
edit('assets/feature-ui.js','mal_account_id: p.mal_account_id,','mal_account_id: p.mal_account_id,\n          progress_revision:p.playback?.revision,')
edit('assets/feature-ui.js','playerView.index = Number(t.value);','rememberPlayerServer(playerView,Number(t.value));\n      playerView.index = Number(t.value);')
edit('assets/feature-ui.js','<form id="mal-edit-form" data-id="${id}"','<form id="mal-edit-form" data-watched="${Number(m.watched)||0}" data-id="${id}"')
edit('assets/feature-ui.js','Al guardar se actualizará tu lista real de MAL.','Al guardar se actualizará tu lista real de MAL. Si reduces los capítulos vistos, se cancelarán los envíos pendientes y las marcas web superiores. Los reproductores abiertos antes de la corrección tendrán que reabrirse.')
edit('assets/feature-ui.js',"if (f.id === 'mal-edit-form') {","""if (f.id === 'mal-edit-form') {
      if(Number(data.watched)<Number(f.dataset.watched)){
        if(!confirm('¿Corregir el progreso hacia abajo en MAL y en la web? Se cancelarán los envíos pendientes.'))return;
        data.confirmation='CORREGIR';data.reconcile_local=true;
      }""")
edit('assets/feature-ui.js','<button class="button small ghost" data-mal-edit="${a.mal.id}">Editar en MAL</button>','<button class="button small ghost" data-mal-edit="${a.mal.id}">Editar en MAL</button><button class="button small ghost" data-exp="reconcile" data-slug="${e(a.slug)}">Reconciliar progreso</button>')
