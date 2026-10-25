'use strict';
let appReleases=null,appReleasePromise=null;
const APP_REPOSITORY='EduardoGPT4/YomaTV';
function validAppRelease(row){
  return row&&['android','windows'].includes(row.platform)&&typeof row.version==='string'&&/^[0-9.]{3,30}$/.test(row.version)&&Number.isSafeInteger(row.bytes)&&row.bytes>0&&row.bytes<300000000&&typeof row.url==='string'&&row.url.startsWith('https://github.com/'+APP_REPOSITORY+'/releases/download/')&&/^[a-zA-Z0-9._\/-]+$/.test(row.url.slice('https://github.com/'.length));
}
function appDownloadsView(){
  if(typeof yomaNative==='function'&&yomaNative())return '';
  if(!appReleasePromise)appReleasePromise=loadAppReleases();
  const rows=(appReleases||[]).filter(validAppRelease);
  return `<section class="app-download-section" aria-labelledby="app-download-heading"><div><p class="eyebrow">YOMATV CONTIGO</p><h2 id="app-download-heading">Tus historias, en tu dispositivo.</h2><p>Android para guardar y ver sin conexión. Windows para descargar, organizar y automatizar tu biblioteca.</p></div><div class="app-download-options">${['android','windows'].map(platform=>{const r=rows.find(x=>x.platform===platform);return `<article><span class="app-platform">${platform==='android'?'Android · APK':'Windows · EXE'}</span><h3>${platform==='android'?'Anime para llevar':'Tu biblioteca en la PC'}</h3><p>${platform==='android'?'Android 8 o posterior · Reanudación · Solo Wi-Fi':'Descargador portátil · Cola web · Temporada opcional'}</p>${r?`<a class="button ${platform==='android'?'primary':'ghost'}" href="${e(r.url)}" data-app-download="${platform}" rel="noopener">${icon('download')}Descargar para ${platform==='android'?'Android':'Windows'}</a><small>Versión ${e(r.version)} · ${(r.bytes/1000000).toLocaleString('es-MX',{maximumFractionDigits:1})} MB</small>`:'<span class="muted" role="status">Consultando la versión publicada…</span>'}</article>`;}).join('')}</div><a class="text-button" href="https://github.com/${APP_REPOSITORY}/releases" target="_blank" rel="noopener noreferrer">Versiones y notas de cambios ↗</a></section>`;
}
async function loadAppReleases(){
  async function apply(rows){if(!Array.isArray(rows)||rows.filter(validAppRelease).length!==2)return;appReleases=rows;const section=document.querySelector('.app-download-section');if(section)section.outerHTML=appDownloadsView();}
  try{
    // Bundled, verified metadata remains usable when GitHub's API is rate limited.
    const script=document.querySelector('script[src*="assets/app-downloads.js"]');
    const r=await fetch(new URL('app-releases.json',script?.src||new URL('assets/app-downloads.js',location.href)),{credentials:'omit',cache:'no-cache'});
    if(r.ok)await apply((await r.json()).apps);
  }catch{}
  try{
    const r=await fetch('https://api.github.com/repos/'+APP_REPOSITORY+'/releases/latest',{credentials:'omit',headers:{Accept:'application/vnd.github+json'},signal:AbortSignal.timeout(8000)});if(!r.ok)return;
    const release=await r.json(),rows=[];if(release.draft||release.prerelease)return;
    for(const [platform,pattern]of [['android',/^YomaTV-Android-([0-9.]+)\.apk$/],['windows',/^YomaTV-Windows-([0-9.]+)\.exe$/]]){
      const a=release.assets?.find(a=>pattern.test(a.name));if(a)rows.push({platform,version:a.name.match(pattern)[1],bytes:a.size,url:a.browser_download_url});
    }
    await apply(rows);
  }catch{}
}
