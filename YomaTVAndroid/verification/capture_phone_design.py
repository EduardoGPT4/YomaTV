"""Capture only the foreground YomaTV app for owner-assisted physical design QA."""
from pathlib import Path
import argparse,json,os,subprocess,xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--serial',required=True)
parser.add_argument('--name',choices=['home','player','player-bottom','more','more-bottom','schedule','downloads','labels-before','labels-after','settings','forms'],required=True)
args=parser.parse_args()
adb=Path(os.environ.get('ANDROID_HOME',str(Path.home()/'AppData/Local/Android/Sdk')))/'platform-tools/adb.exe'
def command(*parts):
    return subprocess.run([str(adb),'-s',args.serial,*parts],capture_output=True,check=True,timeout=35).stdout
activities=command('shell','dumpsys','activity','activities').decode(errors='replace')
foreground=[line for line in activities.splitlines()if 'topResumedActivity' in line or 'mResumedActivity' in line]
if not any('app.seasonav1.mobile/' in line for line in foreground):
    raise SystemExit('Open YomaTV in the foreground before capturing; other apps are not captured.')
folder=ROOT/'verification/phone-ui';folder.mkdir(exist_ok=True)
png=command('exec-out','screencap','-p')
assert png.startswith(b'\x89PNG\r\n\x1a\n')
(folder/(args.name+'.png')).write_bytes(png)
report={'physical_device':True,'view':args.name,'android':command('shell','getprop','ro.build.version.release').decode().strip(),'screenshot_bytes':len(png)}
try:
    command('shell','uiautomator','dump','/data/local/tmp/yomatv-design.xml')
    root=ET.fromstring(command('shell','cat','/data/local/tmp/yomatv-design.xml'))
    labels={'Inicio','Temporada','Descargas','Más','Mi biblioteca','Historial','MyAnimeList','Favoritos','Colecciones','Apariencia y reproducción','Notificaciones','Almacenamiento y descargas','Radio anime','Estadísticas','Cola para la PC','Sincronización MAL','Anterior','Siguiente','Marcar visto','Descargar','Audio y servidor','Episodios','Escenas guardadas'}
    report['controls']=[{'label':node.get('text')or node.get('content-desc'),'bounds':node.get('bounds'),'clickable':node.get('clickable')}for node in root.iter('node')if(node.get('text')or node.get('content-desc'))in labels]
except (subprocess.SubprocessError,ET.ParseError):
    report['accessibility_capture_available']=False
(folder/(args.name+'.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(report,ensure_ascii=False))
