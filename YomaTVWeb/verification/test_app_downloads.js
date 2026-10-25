const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const root=path.join(__dirname,'..'),source=fs.readFileSync(path.join(root,'htdocs/assets/app-downloads.js'),'utf8');
const ctx={e:x=>String(x),icon:()=>'',document:{querySelector:()=>null},yomaNative:()=>false,fetch:async()=>{throw Error('offline')},URL,AbortSignal};
vm.createContext(ctx);vm.runInContext(source,ctx);
const metadata=JSON.parse(fs.readFileSync(path.join(root,'htdocs/assets/app-releases.json'),'utf8'));
assert.equal(metadata.apps.length,2);for(const app of metadata.apps)assert(ctx.validAppRelease(app));
const sample=metadata.apps[0];assert(!ctx.validAppRelease({...sample,url:'https://github.com/other/repo/releases/download/v1/file.apk'}));assert(!ctx.validAppRelease({...sample,bytes:-1}));assert(!ctx.validAppRelease({...sample,version:'<script>'}));
ctx.fixture=metadata.apps;vm.runInContext('appReleasePromise=Promise.resolve();appReleases=fixture',ctx);
const html=ctx.appDownloadsView();assert(html.includes('Descargar para Android'));assert(html.includes('Descargar para Windows'));for(const app of metadata.apps){assert(html.includes(app.url));assert(html.includes(app.version));assert(html.includes((app.bytes/1000000).toLocaleString('es-MX',{maximumFractionDigits:1})));}
ctx.yomaNative=()=>true;assert.equal(ctx.appDownloadsView(),'');
const featureSource=fs.readFileSync(path.join(root,'htdocs/assets/feature-ui.js'),'utf8');
for(const match of featureSource.matchAll(/href="(downloads\/[^"<>]+)"/g))assert(fs.existsSync(path.join(root,'htdocs',match[1])),`Missing downloadable file: ${match[1]}`);
console.log(JSON.stringify({ok:true,checks:['published_metadata_has_both_platforms','foreign_repo_rejected','invalid_size_and_version_rejected','actual_version_size_and_url_rendered','native_app_does_not_show_install_prompt']}));
