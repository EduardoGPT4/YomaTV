"""Puente HTTP limitado a loopback, al dominio autorizado y a un token local."""
from __future__ import annotations

import hashlib
import hmac
import json
import re
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs,urlsplit

from .engine.catalog import DownloadError
from .engine.storage import FileLock,write_json
from .web_import import import_plan,result_receipts,apply_web_preferences,queue_status
from .web_controls import device_info,check_files,control_queue

PORT=47653
SITE='https://hk-br035.gt.tc'
PROTOCOL='seasonav1.bridge/v1'
MAX_BODY=2*1024*1024


def pairing_token(directory: Path,rotate=False):
    path=directory/'web-bridge.json'
    lock=FileLock(directory/'web-bridge-token.lock')
    deadline=time.monotonic()+2
    while True:
        try:lock.acquire();break
        except DownloadError:
            if time.monotonic()>deadline:raise
            time.sleep(.02)
    try:
        if path.exists() and not rotate:
            value=json.loads(path.read_text(encoding='utf-8'))
            token=value.get('token','')
            if not re.fullmatch(r'[A-Za-z0-9_-]{43}',token):raise ValueError('El código de conexión es inválido. Genera otro desde Conectar web.')
            return token
        token=secrets.token_urlsafe(32)
        write_json(path,{'format':PROTOCOL,'token':token})
        return token
    finally:lock.close()


class WebBridge:
    def __init__(self,directory: Path,on_queue,port=PORT,origins=(SITE,),on_settings=None,on_control=None):
        self.directory=directory
        self.on_queue=on_queue
        self.on_settings=on_settings or (lambda result:None)
        self.on_control=on_control or (lambda result:None)
        self.origins=frozenset(origins)
        self.port=port
        self.importing=threading.Lock()
        self.closed=threading.Event()
        self.server=self.thread=None

    def start(self):
        pairing_token(self.directory)
        bridge=self
        class Handler(BaseHTTPRequestHandler):
            server_version='SeasonAV1'
            sys_version=''
            def log_message(self,*_):pass
            def setup(self):
                super().setup();self.connection.settimeout(5)
            def trusted(self):
                hosts=self.headers.get_all('Host',[])
                origins=self.headers.get_all('Origin',[])
                return hosts==[f'127.0.0.1:{bridge.port}'] and len(origins)==1 and origins[0] in bridge.origins
            def respond(self,status,value=None):
                body=json.dumps(value or {},ensure_ascii=False,separators=(',',':')).encode()
                self.send_response(status)
                if self.trusted():
                    self.send_header('Access-Control-Allow-Origin',self.headers['Origin'])
                    self.send_header('Vary','Origin')
                    self.send_header('Access-Control-Allow-Methods','GET, POST, OPTIONS')
                    self.send_header('Access-Control-Allow-Headers','Authorization, Content-Type')
                    self.send_header('Access-Control-Allow-Private-Network','true')
                    self.send_header('Access-Control-Max-Age','600')
                self.send_header('Cache-Control','no-store')
                self.send_header('X-Content-Type-Options','nosniff')
                self.send_header('Content-Type','application/json; charset=utf-8')
                if status!=204:self.send_header('Content-Length',str(len(body)))
                self.send_header('Connection','close')
                self.end_headers()
                if status!=204:
                    try:self.wfile.write(body)
                    except (BrokenPipeError,ConnectionResetError):pass
            def allowed(self):
                if not self.trusted():
                    self.respond(403,{'ok':False,'message':'Origen o dirección no autorizados.'});return False
                if bridge.closed.is_set():
                    self.respond(503,{'ok':False,'message':'SeasonAV1 se está cerrando.'});return False
                auth=self.headers.get_all('Authorization',[])
                try:expected=('Bearer '+pairing_token(bridge.directory)).encode()
                except (OSError,ValueError,DownloadError):
                    self.respond(503,{'ok':False,'message':'El código local no está disponible. Genera otro desde Conectar web.'});return False
                if len(auth)!=1 or not hmac.compare_digest(auth[0].encode(),expected):
                    self.respond(401,{'ok':False,'message':'El código de conexión cambió. Empareja SeasonAV1 de nuevo.'});return False
                return True
            def do_OPTIONS(self):
                methods={'/ping':'GET','/queue':'POST','/results':'GET','/status':'GET','/settings':'POST','/control':'POST','/files':'POST'}
                path=urlsplit(self.path).path
                requested={v.strip().lower() for v in self.headers.get('Access-Control-Request-Headers','').split(',') if v.strip()}
                if not self.trusted() or self.headers.get('Access-Control-Request-Method')!=methods.get(path) or not requested<={'authorization','content-type'}:
                    self.respond(403,{'ok':False,'message':'Solicitud no autorizada.'});return
                self.respond(204)
            def do_GET(self):
                if not self.allowed():return
                path=urlsplit(self.path)
                if path.path=='/ping' and not path.query:
                    from .brand import APP_NAME, VERSION
                    self.respond(200,{'ok':True,'app':'SeasonAV1','display_name':APP_NAME,'protocol':PROTOCOL,'version':VERSION,'device':device_info(bridge.directory),'capabilities':['queue','settings','live_status','filtered_results','general_downloads','group_control','file_presence','device_identity']});return
                if path.path=='/status':
                    args=parse_qs(path.query,keep_blank_values=True);installation=args.get('installation',[]);ids=args.get('ids',[])
                    if set(args)!={'installation','ids'} or len(installation)!=1 or not re.fullmatch(r'[a-f0-9]{16,64}',installation[0]) or len(ids)!=1 or not re.fullmatch(r'[1-9]\d{0,9}(?:,[1-9]\d{0,9}){0,1999}',ids[0]):
                        self.respond(422,{'ok':False,'message':'Solicitudes web inválidas.'});return
                    try:self.respond(200,{'ok':True,**queue_status(bridge.directory,installation[0],[int(n) for n in ids[0].split(',')])})
                    except Exception:self.respond(500,{'ok':False,'message':'No se pudo consultar el estado de la cola.'})
                    return
                if path.path=='/results':
                    args=parse_qs(path.query,keep_blank_values=True);installation=args.get('installation',[])
                    identifiers=args.get('ids',[])
                    if not set(args)<={'installation','ids'} or len(installation)!=1 or not re.fullmatch(r'[a-f0-9]{16,64}',installation[0]):
                        self.respond(422,{'ok':False,'message':'Identificador de web inválido.'});return
                    if 'ids' in args and (len(identifiers)!=1 or not re.fullmatch(r'[1-9]\d{0,9}(?:,[1-9]\d{0,9}){0,1999}',identifiers[0])):
                        self.respond(422,{'ok':False,'message':'Solicitudes inválidas.'});return
                    try:
                        result=result_receipts(bridge.directory,installation[0],[int(n) for n in identifiers[0].split(',')] if identifiers else None)
                        signature=hashlib.sha256(json.dumps(result,sort_keys=True).encode()).hexdigest()
                        self.respond(200,{'ok':True,'signature':signature,**result})
                    except Exception:self.respond(500,{'ok':False,'message':'No se pudo consultar el registro de descargas.'})
                    return
                self.respond(404,{'ok':False,'message':'Ruta desconocida.'})
            def do_POST(self):
                if not self.allowed():return
                if self.path not in {'/queue','/settings','/control','/files'}:
                    self.respond(404,{'ok':False,'message':'Ruta desconocida.'});return
                lengths=self.headers.get_all('Content-Length',[])
                if self.headers.get('Transfer-Encoding') or len(lengths)!=1 or not lengths[0].isdigit():
                    self.respond(411,{'ok':False,'message':'Falta el tamaño de la cola.'});return
                if len(lengths[0])>10:
                    self.respond(413,{'ok':False,'message':'La cola puede ocupar hasta 2 MB.'});return
                length=int(lengths[0])
                if not 1<=length<=MAX_BODY:
                    self.respond(413,{'ok':False,'message':'La cola puede ocupar hasta 2 MB.'});return
                if self.headers.get('Content-Type','').split(';')[0].strip().lower()!='application/json':
                    self.respond(415,{'ok':False,'message':'Usa una cola JSON.'});return
                if not bridge.importing.acquire(blocking=False):
                    self.respond(409,{'ok':False,'message':'Otra cola se está incorporando. Intenta enviar de nuevo en unos segundos.'});return
                try:
                    body=self.rfile.read(length)
                    if len(body)!=length:raise ValueError('La cola llegó incompleta.')
                    plan=json.loads(body)
                    if not isinstance(plan,dict):raise ValueError('Cola inválida.')
                    if self.path=='/files':
                        result=check_files(bridge.directory,plan)
                        self.respond(200,{'ok':True,**result})
                    elif self.path=='/control':
                        result=control_queue(bridge.directory,plan)
                        bridge.on_control(result)
                        self.respond(200,{'ok':True,**result})
                    elif self.path=='/settings':
                        result=apply_web_preferences(bridge.directory,plan)
                        if result['changed']:bridge.on_settings(result)
                        self.respond(200,{'ok':True,'message':'Preferencias aplicadas en SeasonAV1.',**result})
                    else:
                        result=import_plan(bridge.directory,plan)
                        bridge.on_queue(result)
                        self.respond(200,{'ok':True,'message':'Cola recibida. SeasonAV1 continúa en la bandeja.',**result})
                except (ValueError,TypeError,KeyError,DownloadError) as error:
                    self.respond(422,{'ok':False,'message':str(error)[:220]})
                except RuntimeError as error:
                    self.respond(409,{'ok':False,'message':str(error)[:220]})
                except Exception:
                    self.respond(500,{'ok':False,'message':'No se pudo incorporar la cola. Se conserva en la web.'})
                finally:bridge.importing.release()
        self.server=ThreadingHTTPServer(('127.0.0.1',self.port),Handler)
        self.port=self.server.server_address[1]
        self.server.daemon_threads=True
        self.thread=threading.Thread(target=self.server.serve_forever,name='SeasonAV1-web-bridge',daemon=True)
        self.thread.start()
        return self

    def close(self):
        self.closed.set()
        if self.server:
            self.server.shutdown();self.server.server_close()
        if self.thread:self.thread.join(timeout=2)
