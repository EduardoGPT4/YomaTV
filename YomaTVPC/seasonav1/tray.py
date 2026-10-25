from __future__ import annotations

import os
import subprocess
import sys
import threading

import pystray
from PIL import Image

from .config import ASSETS, ROOT, Config
from .brand import APP_NAME
from .engine.catalog import DownloadError
from .runner import Runner
from .instance import send
from .windows_tasks import launch_command


def spawn(directory, *args):
    options = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}
    environment=dict(os.environ)
    if getattr(sys,"frozen",False):
        environment["PYINSTALLER_RESET_ENVIRONMENT"]="1"
    return subprocess.Popen(launch_command("--data-dir", str(directory), *args), cwd=ROOT, env=environment, **options)


class Tray:
    def __init__(self, directory, force=False, resident=False, instance=None, resume=False, queue_only=False):
        self.directory, self.force, self.resident = directory, force, resident
        self.instance, self.resume = instance, resume
        self.queue_only=queue_only
        self.restart_queue_only=False
        self.start_lock = threading.RLock()
        self.token = threading.Event()
        self.thread = None
        self.exiting = False
        self.last_error = None
        self.restart_requested=False
        self.bridge=None
        with Image.open(ASSETS / "yomatv-preview.png") as image:
            art = image.copy()
        self.icon = pystray.Icon("YomaTV", art, APP_NAME, pystray.Menu(
            pystray.MenuItem("Descargador y cola general", lambda *_: self.open_window(), default=True),
            pystray.MenuItem("Conectar con la web", lambda *_: self.open_window(pair=True)),
            pystray.MenuItem("Revisar temporada ahora", lambda *_: self.start(True), enabled=lambda _: not self.busy),
            pystray.MenuItem(lambda _: "Continuar" if self.paused else "Pausar", lambda *_: self.toggle_pause()),
            pystray.MenuItem("Abrir carpeta", lambda *_: self.open_folder()),
            pystray.MenuItem("Historial", lambda *_: self.open_window(True)),
            pystray.MenuItem("Salir", lambda *_: self.exit())))

    @property
    def busy(self):
        return self.thread is not None and self.thread.is_alive()

    @property
    def paused(self):
        return Config.load(self.directory).paused

    def notify(self, title, message):
        try:
            if self.icon.HAS_NOTIFICATION:
                self.icon.notify(message[:250], title[:60])
        except Exception:
            pass  # Un bloqueo de notificaciones de Windows no invalida una descarga.

    def open_folder(self):
        folder = Config.load(self.directory).destination
        os.makedirs(folder, exist_ok=True)
        os.startfile(folder)

    def open_window(self, history=False,pair=False):
        if not send(self.directory, "window", {"action": "show", "history": history,"pair":pair}):
            spawn(self.directory, "--window", *(["--history"] if history else []), *(["--pair-web"] if pair else []))

    def receive_web_queue(self,result):
        cfg=Config.load(self.directory)
        if cfg.autostart:
            from .database import Database
            from .windows_tasks import install
            db=Database(self.directory)
            try:
                db.set_meta('task',{'name':install(cfg,self.directory),'installed':True,'time':cfg.review_time})
            except Exception:
                db.log('warning','Cola web recibida; no se pudo actualizar la hora de la tarea de Windows.')
                self.notify(APP_NAME,'Cola recibida. Revisa la hora de la tarea desde la configuración.')
            finally:db.close()
        if not self.exiting:
            send(self.directory,'window',{'action':'web_settings'})
            self.handle_command({'action':'resume_web'})
            self.notify(APP_NAME,f"Cola web recibida: {result['items']} capítulos. Continúa en la bandeja.")

    def receive_web_settings(self,result):
        cfg=Config.load(self.directory)
        if cfg.autostart and 'review_time' in result['changed']:
            from .database import Database
            from .windows_tasks import install
            db=Database(self.directory)
            try:db.set_meta('task',{'name':install(cfg,self.directory),'installed':True,'time':cfg.review_time})
            except Exception:
                db.log('warning','Preferencias web guardadas; no se pudo actualizar la hora de la tarea de Windows.')
                self.notify(APP_NAME,'Preferencias guardadas. Revisa la tarea de Windows desde la configuración.')
            finally:db.close()
        send(self.directory,'window',{'action':'web_settings'})
        if self.busy and not cfg.paused and not self.exiting:
            with self.start_lock:
                self.restart_requested=True
                self.restart_queue_only=getattr(self,'active_queue_only',False)
                self.token.set()
        self.icon.update_menu()

    def receive_web_control(self,result):
        send(self.directory,'window',{'action':'web_settings'})
        if result['action'] in {'resume','retry','redownload'} and not self.exiting and not Config.load(self.directory).paused:
            self.start(False,True)
        self.icon.update_menu()

    def handle_command(self, command):
        try:
            action = command.get("action")
            if action == "review":
                cfg = Config.load(self.directory)
                cfg.paused = False
                cfg.save(self.directory)
                self.start(True)
            elif action in {"resume","resume_web","resume_queue"}:
                cfg = Config.load(self.directory)
                cfg.paused = False
                cfg.save(self.directory)
                self.start(False,True) if action in {"resume_web","resume_queue"} else self.start(False)
            elif action == "scheduled":
                self.start_when_due()
            elif action == "exit":
                self.exit()
            self.icon.update_menu()
        except Exception as exc:
            self.notify(APP_NAME, str(exc))

    def start_when_due(self):
        from datetime import datetime
        from .database import Database
        from .schedule import work_due
        cfg = Config.load(self.directory)
        if cfg.paused or not cfg.configured:
            return
        db = Database(self.directory)
        try:
            due = work_due(db, cfg, datetime.now().astimezone())
        finally:
            db.close()
        if due:
            self.start(False) if cfg.schedule_enabled else self.start(False,True)

    def toggle_pause(self):
        cfg = Config.load(self.directory)
        cfg.paused = not cfg.paused
        cfg.save(self.directory)
        if cfg.paused:
            self.token.set()
        else:
            self.start(False,True)
        self.icon.update_menu()

    def start(self, force=False, queue_only=False):
        with self.start_lock:
            self._start(force,queue_only)

    def _start(self, force=False, queue_only=False):
        if self.busy:
            if (self.token.is_set() or queue_only) and not self.exiting:
                self.restart_requested=True
                self.restart_queue_only=queue_only
            return
        self.token = threading.Event()
        self.active_queue_only=queue_only
        self.last_error = None
        def work():
            runner = None
            try:
                runner = Runner(self.directory, self.notify, self.token)
                runner.run(force,queue_only=True) if queue_only else runner.run(force)
            except Exception as exc:
                self.last_error = str(exc)
                self.notify(APP_NAME + " · Revisión detenida", str(exc))
            finally:
                if runner is not None:
                    runner.close()
                try: cfg = Config.load(self.directory)
                except Exception: cfg = None
                if self.restart_requested and cfg is not None and not cfg.paused and not self.exiting:
                    with self.start_lock:
                        self.restart_requested=False
                        self.thread=None
                        self.start(False,self.restart_queue_only)
                elif cfg is None or self.exiting or (not self.resident and not cfg.resident_tray and not cfg.paused):
                    self.token.wait(3)
                    self.icon.stop()
        self.thread = threading.Thread(target=work, name="SeasonAV1-review", daemon=False)
        self.thread.start()

    def exit(self):
        self.exiting = True
        self.token.set()
        if not self.busy:
            self.icon.stop()

    def run(self):
        from .web_bridge import WebBridge
        from .database import Database
        try:self.bridge=WebBridge(self.directory,self.receive_web_queue,on_settings=self.receive_web_settings,on_control=self.receive_web_control).start()
        except (OSError,ValueError,DownloadError):
            db=Database(self.directory)
            try:db.log('warning','Conexión web local no disponible. Revisa el puerto 47653 o genera otro código de conexión.')
            finally:db.close()
            self.bridge=None
        def setup(icon):
            icon.visible = True
            if self.force or self.resume:
                self.start(self.force,self.queue_only)
            else:
                self.start_when_due()
            cfg=Config.load(self.directory)
            if not self.busy and not self.resident and not cfg.resident_tray and not cfg.paused:
                icon.stop()
            if self.instance is not None:
                self.instance.dispatch(self.handle_command)
        try:
            self.icon.run(setup)
            if self.thread:self.thread.join()
        finally:
            if self.bridge:self.bridge.close()
        return 1 if self.last_error else 0
