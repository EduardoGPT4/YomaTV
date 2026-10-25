from __future__ import annotations

import json
import os
import queue
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageTk

from .config import ASSETS, DAYS, Config
from .brand import APP_NAME
from .database import Database
from .engine.storage import FileLock
from .http import HttpClient
from .schedule import SCHEDULE_URL, parse_schedule
from .theme import BG, GREEN, MINT, MUTED, RED, configure_theme
from .tray import spawn
from .instance import Instance, send
from .windows_tasks import install, inspect, uninstall

LABELS = {"pending": "En cola", "downloading": "⬇ Descargando", "verifying": "Verificando",
          "paused": "Pausado", "completed": "✔ Completado", "failed": "✖ Error"}
MAPPINGS = {"language_fallback": {"Esperar el idioma solicitado": "wait", "Usar SUB si falta": "SUB"},
            "server_fallback": {"Esperar el servidor elegido": "wait", "Probar otro compatible": "other"},
            "quality_fallback": {"Aceptar la mejor disponible": "best", "Aceptar resolución menor": "lower", "Esperar calidad exacta": "wait"},
            "selection": {"Todos los animes": "all", "Solo favoritos": "favorites"},
            "season_source": {"Temporada actual al empezar": "current", "Temporada de estreno": "premiere"},
            "long_series": {"Mantener carpeta inicial": "keep", "Separar capítulos por temporada": "split"}}


class App(tk.Tk):
    def __init__(self, directory, history=False, autostart_review=False, instance=None):
        super().__init__()
        self.instance = instance
        self.directory, self.db = directory, Database(directory)
        self.cfg = Config.load(directory)
        self.events = queue.Queue()
        self.pending_work = 0
        self.title(APP_NAME + " · Catálogo, cola y temporada")
        self.geometry("1180x820")
        self.minsize(960, 680)
        self.configure(bg=BG)
        if os.name == "nt" and (ASSETS / "yomatv.ico").is_file():
            self.iconbitmap(default=str(ASSETS / "yomatv.ico"))
        configure_theme(self)
        ttk.Style(self).configure("TCheckbutton", background=BG, foreground="#e5edf8")
        self.status = tk.StringVar(value="Pega un enlace de cualquier anime y elige capítulos, rangos o todos. La temporada automática es opcional.")
        self.summary = tk.StringVar()
        self.day_filter = tk.StringVar(value="Toda la semana")
        self.vars = {}
        self._closing_requested=False
        self.pair_window=None
        self.protocol("WM_DELETE_WINDOW",self.close)
        body = ttk.Frame(self, padding=20)
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=1)
        body.rowconfigure(1, weight=1)
        header = ttk.Frame(body)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        with Image.open(ASSETS / "yomatv-preview.png") as image:
            image.thumbnail((62,62))
            self.photo = ImageTk.PhotoImage(image, master=self)
        ttk.Label(header, image=self.photo).pack(side="left", padx=(0,14))
        heading = ttk.Frame(header)
        heading.pack(side="left")
        ttk.Label(heading, text=APP_NAME, style="Title.TLabel").pack(anchor="w")
        ttk.Label(heading, textvariable=self.summary, style="Muted.TLabel").pack(anchor="w")
        self.tabs = ttk.Notebook(body)
        self.tabs.grid(row=1, column=0, sticky="nsew")
        from .general_ui import DownloadPanel, QueuePanel
        self.download_tab = DownloadPanel(self.tabs, self)
        self.tabs.add(self.download_tab, text="Descargar anime")
        self.queue_tab = QueuePanel(self.tabs, self)
        self.tabs.add(self.queue_tab, text="Cola general")
        weekly = ttk.Frame(self.tabs, padding=12)
        weekly.columnconfigure(0, weight=1)
        weekly.rowconfigure(1, weight=1)
        self.weekly_tab = weekly
        self.tabs.add(weekly, text="Temporada")
        tools = ttk.Frame(weekly)
        tools.grid(row=0, column=0, sticky="ew", pady=(0,10))
        combo = ttk.Combobox(tools, textvariable=self.day_filter, values=("Toda la semana", *DAYS), state="readonly", width=18)
        combo.pack(side="left")
        combo.bind("<<ComboboxSelected>>", lambda _: self.refresh_table())
        ttk.Button(tools, text="Actualizar horario", command=self.fetch_schedule).pack(side="left", padx=8)
        ttk.Button(tools, text="Revisar temporada ahora", command=self.review).pack(side="left")
        ttk.Button(tools, text="Favoritos", command=lambda: self.mark_list("favorites")).pack(side="right")
        ttk.Button(tools, text="Excluir selección", command=lambda: self.mark_list("exclusions")).pack(side="right", padx=8)
        self.tree = ttk.Treeview(weekly, columns=("day","title","latest","state","count"), show="headings", selectmode="extended")
        for key,title,width in (("day","Día",110),("title","Anime",390),("latest","Último",65),("state","Estado",190),("count","Guardados",85)):
            self.tree.heading(key,text=title)
            self.tree.column(key,width=width,stretch=key in {"title","state"},minwidth=50)
        for status,color in (("completed",GREEN),("downloading",MINT),("failed",RED),("excluded",MUTED)):
            self.tree.tag_configure(status,foreground=color)
        self.tree.grid(row=1,column=0,sticky="nsew")
        scroll = ttk.Scrollbar(weekly,command=self.tree.yview)
        scroll.grid(row=1,column=1,sticky="ns")
        self.tree.configure(yscrollcommand=scroll.set)
        ttk.Label(weekly,text="Ctrl / Shift para seleccionar varios. Favoritos y exclusiones se alternan al pulsar su botón.",style="Muted.TLabel").grid(row=2,column=0,sticky="w",pady=(8,0))
        settings = ttk.Frame(self.tabs,padding=14)
        self.tabs.add(settings,text="Configuración")
        settings.columnconfigure(0,weight=1)
        settings.columnconfigure(1,weight=1)
        left,right=ttk.Frame(settings),ttk.Frame(settings)
        left.grid(row=0,column=0,sticky="nsew",padx=(0,20))
        right.grid(row=0,column=1,sticky="nsew")
        for frame in (left,right): frame.columnconfigure(1,weight=1)
        destination = tk.StringVar(value=self.cfg.destination)
        self.vars["destination"]=destination
        ttk.Label(left,text="Carpeta de destino").grid(row=0,column=0,columnspan=2,sticky="w",pady=(0,5))
        ttk.Entry(left,textvariable=destination).grid(row=1,column=0,columnspan=2,sticky="ew")
        ttk.Button(left,text="Elegir carpeta",command=self.choose_folder).grid(row=2,column=0,columnspan=2,sticky="ew",pady=(6,14))
        self.field(left,3,"review_time","Hora de revisión (HH:MM)")
        self.field(left,4,"height","Calidad preferida",("1080","720"))
        self.field(left,5,"quality_fallback","Si no existe esa calidad",MAPPINGS["quality_fallback"])
        self.field(left,6,"language","Idioma",("SUB","LAT","DUB"))
        self.field(left,7,"language_fallback","Si falta el idioma",MAPPINGS["language_fallback"])
        self.field(left,8,"server","Servidor preferido",("MP4Upload","Voe"))
        self.field(left,9,"server_fallback","Si falla o falta",MAPPINGS["server_fallback"])
        self.field(right,0,"workers","Descargas simultáneas (1–4)")
        self.field(right,1,"speed_kib","Límite total KiB/s (0 = libre)")
        self.field(right,2,"request_interval","Pausa entre consultas (s)")
        self.field(right,3,"selection","Descargar",MAPPINGS["selection"])
        self.field(right,4,"season_source","Carpeta de temporada",MAPPINGS["season_source"])
        self.field(right,5,"long_series","Animes de larga duración",MAPPINGS["long_series"])
        for row,(key,label) in enumerate((("schedule_enabled","Activar revisión automática de temporada"),("autostart","Iniciar en la bandeja con Windows"),("notifications","Mostrar notificaciones"),("resident_tray","Mantener bandeja abierta al terminar")),6):
            variable=tk.BooleanVar(value=getattr(self.cfg,key))
            self.vars[key]=variable
            ttk.Checkbutton(right,text=label,variable=variable).grid(row=row,column=0,columnspan=2,sticky="w",pady=5)
        ttk.Label(settings,text="La automatización solo sigue el horario semanal. Su primer lote descarga todos sus capítulos en orden.\nLos enlaces y la web descargan únicamente la selección que pediste; puedes usarlos con la automatización apagada.",style="Muted.TLabel",wraplength=1020).grid(row=1,column=0,columnspan=2,sticky="w",pady=(18,0))
        history_tab=ttk.Frame(self.tabs,padding=12)
        self.history_tab = history_tab
        history_tab.columnconfigure(0,weight=1);history_tab.rowconfigure(0,weight=1)
        self.tabs.add(history_tab,text="Historial")
        self.history=tk.Text(history_tab,bg="#162133",fg=MUTED,relief="flat",wrap="word",state="disabled",font=("Consolas",9))
        self.history.grid(row=0,column=0,sticky="nsew")
        hs=ttk.Scrollbar(history_tab,command=self.history.yview);hs.grid(row=0,column=1,sticky="ns")
        self.history.configure(yscrollcommand=hs.set)
        self.history.tag_configure("error",foreground=RED);self.history.tag_configure("warning",foreground="#e8bb70")
        actions=ttk.Frame(body)
        actions.grid(row=2,column=0,sticky="ew",pady=(12,8))
        self.activate=ttk.Button(actions,text="Guardar configuración",command=self.save_activate)
        self.activate.pack(side="left")
        ttk.Button(actions,text="Continuar cola",command=self.resume_queue).pack(side="left",padx=8)
        self.pause_button=ttk.Button(actions,text="Pausar",command=self.pause)
        self.pause_button.pack(side="left")
        ttk.Button(actions,text="Prueba de temporada",command=self.dry_run).pack(side="left",padx=8)
        ttk.Button(actions,text="Abrir carpeta",command=self.open_folder).pack(side="right")
        ttk.Button(actions,text="Desactivar horario",command=self.remove_task).pack(side="right",padx=8)
        web_actions=ttk.Frame(body)
        web_actions.grid(row=3,column=0,sticky="ew",pady=(0,8))
        ttk.Label(web_actions,text="YomaTV Web",style="Muted.TLabel").pack(side="left")
        ttk.Button(web_actions,text="Conectar web",command=self.pair_web).pack(side="right",padx=8)
        ttk.Button(web_actions,text="Exportar resultados web",command=self.export_web).pack(side="right")
        ttk.Button(web_actions,text="Importar cola web",command=self.import_web).pack(side="right",padx=8)
        ttk.Label(body,textvariable=self.status,wraplength=990).grid(row=4,column=0,sticky="ew")
        if history: self.tabs.select(history_tab)
        else: self.tabs.select(self.download_tab)
        self.refresh_table()
        self.after(200,self.poll)
        self.after(2000,self.refresh)
        if autostart_review and self.cfg.configured and self.cfg.schedule_enabled and not self.db.meta("initialized",False) and not self.db.meta("running") and not self.cfg.paused:
            self.after(800,self.review)

    def field(self,frame,row,key,label,choices=None):
        value=getattr(self.cfg,key)
        if isinstance(choices,dict): value=next(text for text,v in choices.items() if v==value)
        variable=tk.StringVar(value=str(value));self.vars[key]=variable
        ttk.Label(frame,text=label).grid(row=row,column=0,sticky="w",padx=(0,10),pady=5)
        widget=ttk.Combobox(frame,textvariable=variable,values=list(choices),state="readonly",width=20) if choices else ttk.Entry(frame,textvariable=variable,width=20)
        widget.grid(row=row,column=1,sticky="ew",pady=5)

    def choose_folder(self):
        folder=filedialog.askdirectory(initialdir=self.vars["destination"].get())
        if folder:self.vars["destination"].set(folder)

    def background(self,work,success,on_error=None):
        self.pending_work += 1
        self.activate.configure(state='disabled')
        def run():
            try:self.events.put(("done",(success,work())))
            except Exception as exc:self.events.put(("error",(str(exc),on_error)))
        threading.Thread(target=run,daemon=True).start()

    def fetch_schedule(self):
        self.status.set("Leyendo el horario público…")
        def work():
            schedule=parse_schedule(HttpClient(self.db).fetch(SCHEDULE_URL))
            from dataclasses import asdict
            self.db.set_meta("weekly_schedule",[asdict(a) for a in schedule])
            return len(schedule)
        self.background(work,lambda count:self.status.set(f"Horario actualizado: {count} animes. Puedes elegir favoritos o exclusiones."))

    def form_config(self):
        cfg=Config.load(self.directory)
        for key,variable in self.vars.items():
            value=variable.get()
            if key in MAPPINGS:value=MAPPINGS[key][value]
            if key in {"height","workers","speed_kib"}:value=int(value)
            if key=="request_interval":value=float(value)
            setattr(cfg,key,value)
        cfg.configured=True
        return cfg.validate()

    def save_activate(self):
        try:cfg=self.form_config()
        except (ValueError,KeyError) as exc:
            self.status.set(str(exc));return
        self.activate.configure(state="disabled")
        self.status.set("Guardando la configuración y conservando la cola…")
        def work():
            old=Config.load(self.directory)
            original_paused=old.paused
            was_running=bool(self.db.meta('running'))
            old.paused=True;old.save(self.directory)
            try:
                deadline=time.monotonic()+20
                while True:
                    try:
                        with FileLock(self.directory/"review.lock"):break
                    except Exception:
                        if time.monotonic()>deadline:raise RuntimeError("La descarga está terminando de pausarse. Inténtalo de nuevo.")
                        time.sleep(0.3)
                cfg.paused=original_paused;cfg.save(self.directory)
                if cfg.autostart or cfg.schedule_enabled:
                    name=install(cfg,self.directory)
                    self.db.set_meta("task",{"name":name,"time":cfg.review_time,"installed":True})
                else:
                    uninstall(self.directory);name=None;self.db.set_meta("task",{"installed":False})
                if cfg.schedule_enabled and not self.db.meta('initialized',False) and not cfg.paused:
                    spawn(self.directory,"--run-now")
                elif not cfg.paused:
                    spawn(self.directory,"--resume-queue")
                else:
                    spawn(self.directory,"--tray")
                return name
            except Exception:
                old.paused=original_paused;old.save(self.directory)
                if was_running and not original_paused:spawn(self.directory,'--resume-queue')
                raise
        self.background(work,lambda _:self.status.set("Configuración guardada. Descargas en la bandeja; temporada automática " + ("activada." if cfg.schedule_enabled else "apagada.")))

    def review(self):
        cfg=Config.load(self.directory);cfg.paused=False;cfg.save(self.directory)
        spawn(self.directory,"--run-now")
        self.status.set("Revisión de temporada iniciada. El primer lote descarga todos sus capítulos; el progreso aparece en Cola general.")

    def resume_queue(self):
        cfg=Config.load(self.directory);cfg.paused=False;cfg.configured=True;cfg.save(self.directory)
        spawn(self.directory,"--resume-queue")
        self.status.set("Continuando los capítulos pendientes, sin explorar todo el horario.")

    def pause(self):
        cfg=Config.load(self.directory);cfg.paused=not cfg.paused;cfg.save(self.directory)
        if not cfg.paused:spawn(self.directory,"--resume-queue")
        self.status.set("Pausando y conservando los parciales…" if cfg.paused else "Continuando la cola…")

    def mark_list(self,key):
        selected=set(self.tree.selection())
        if not selected:return
        cfg=Config.load(self.directory);entries=set(getattr(cfg,key))
        entries=entries-selected if selected<=entries else entries|selected
        setattr(cfg,key,sorted(entries));cfg.save(self.directory)
        self.refresh_table()
        self.status.set(f"Lista actualizada: {len(entries)} animes. Activa «Solo favoritos» en Configuración si lo deseas.")

    def dry_run(self):
        report=self.directory/"previsualizacion.json"
        process=spawn(self.directory,"--dry-run","--report",str(report))
        self.status.set("Calculando qué se descargaría. No se descargan videos ni se modifica la cola.")
        def work():
            if process.wait()!=0:raise RuntimeError("El modo de prueba detectó un error. Consulta el historial.")
            return json.loads(report.read_text(encoding="utf-8"))
        self.background(work,lambda result:self.status.set(f"Prueba: {len(result['items'])} capítulos por descargar de {result['selected']} animes. Detalle en {report.name}."))

    def open_folder(self):
        folder=Config.load(self.directory).destination
        os.makedirs(folder,exist_ok=True);os.startfile(folder)

    def pair_web(self):
        from .web_bridge import pairing_token
        import webbrowser
        if self.pair_window is not None and self.pair_window.winfo_exists():
            self.pair_window.lift();return
        token=tk.StringVar(value=pairing_token(self.directory))
        window=self.pair_window=tk.Toplevel(self)
        window.title('Conectar ' + APP_NAME + ' con la web');window.configure(bg=BG)
        window.transient(self);window.resizable(False,False)
        body=ttk.Frame(window,padding=24);body.pack(fill='both',expand=True)
        ttk.Label(body,text='Tu web y tu PC, conectadas',style='Title.TLabel').pack(anchor='w')
        ttk.Label(body,text='1. Copia el código de este equipo.\n2. En la web pulsa «Conectar YomaTV» y pégalo.\n3. Permite el acceso a la red local si el navegador lo solicita.\n\nDespués, «Preparar» inicia la descarga en la bandeja. Los códigos y las colas de SeasonAV1 siguen funcionando.',wraplength=470).pack(anchor='w',pady=16)
        ttk.Entry(body,textvariable=token,state='readonly',show='•',width=50).pack(fill='x')
        feedback=tk.StringVar(value='El código permanece en tu equipo y en ese navegador.')
        def copy():
            self.clipboard_clear();self.clipboard_append(token.get());feedback.set('Código copiado. Pégalo en la web en este mismo equipo.')
        def revoke():
            token.set(pairing_token(self.directory,rotate=True));feedback.set('Conexiones anteriores revocadas. Copia el nuevo código y empareja de nuevo.')
        buttons=ttk.Frame(body);buttons.pack(fill='x',pady=12)
        ttk.Button(buttons,text='Copiar código',command=copy).pack(side='left')
        ttk.Button(buttons,text='Abrir web',command=lambda:webbrowser.open('https://hk-br035.gt.tc/seasonav1/')).pack(side='left',padx=8)
        ttk.Button(buttons,text='Revocar conexiones',command=revoke).pack(side='right')
        ttk.Label(body,textvariable=feedback,wraplength=470,style='Muted.TLabel').pack(anchor='w')
        if not send(self.directory,'tray',{'action':'ping'}):spawn(self.directory,'--tray')

    def import_web(self):
        filename=filedialog.askopenfilename(title="Importar cola web y sus preferencias",filetypes=[("Cola de YomaTV Web","*.json")])
        if not filename:return
        self.activate.configure(state="disabled")
        self.status.set("Importando la cola web; se conservan las descargas existentes y la carpeta de destino…")
        def work():
            from pathlib import Path
            from .web_import import import_plan
            result=import_plan(self.directory,Path(filename))
            cfg=Config.load(self.directory)
            if cfg.autostart:
                name=install(cfg,self.directory)
                self.db.set_meta("task",{"name":name,"installed":True,"time":cfg.review_time})
            spawn(self.directory,"--resume-web")
            return result
        def done(result):
            self.reload_web_preferences()
            self.status.set(f"Cola web importada: {result['added']} capítulos nuevos. Se aplicaron sus preferencias; las descargas continúan en la bandeja.")
        self.background(work,done)

    def reload_web_preferences(self):
        self.cfg=Config.load(self.directory)
        for key,variable in self.vars.items():
            value=getattr(self.cfg,key)
            if key in MAPPINGS:value=next(label for label,v in MAPPINGS[key].items() if v==value)
            variable.set(value)
        if not self.download_tab.busy:self.download_tab.reload_preferences()

    def export_web(self):
        filename=filedialog.asksaveasfilename(title="Guardar resultados para YomaTV Web",initialfile="SeasonAV1-resultados.json",defaultextension=".json",filetypes=[("Resultados de SeasonAV1","*.json")])
        if not filename:return
        def work():
            from pathlib import Path
            from .web_import import export_results
            return export_results(self.directory,Path(filename))
        self.background(work,lambda result:self.status.set(f"{result['completed']} resultados verificados guardados en {len(result['files'])} archivo(s). Usa «Importar resultados» en la web."))

    def remove_task(self):
        def work():
            cfg=Config.load(self.directory);cfg.schedule_enabled=False;cfg.autostart=False;cfg.save(self.directory)
            uninstall(self.directory);self.db.set_meta("task",{"installed":False})
        def done(_):
            self.reload_web_preferences()
            self.status.set("Horario automático e inicio con Windows desactivados. Los datos y las descargas se conservan.")
        self.background(work,done)

    def refresh_table(self):
        schedule=self.db.meta("weekly_schedule",[])
        selected=set(self.tree.selection())
        cfg=Config.load(self.directory)
        counts={row["slug"]:row["n"] for row in self.db.query("SELECT slug,COUNT(*) n FROM episodes WHERE status='completed' GROUP BY slug")}
        active={row["slug"]:row for row in self.db.query("""SELECT slug,status,number,error,progress FROM episodes WHERE status<>'completed'
             ORDER BY CASE status WHEN 'downloading' THEN 5 WHEN 'verifying' THEN 4 WHEN 'failed' THEN 3 WHEN 'paused' THEN 2 ELSE 1 END,id DESC""")}
        self.tree.delete(*self.tree.get_children())
        for anime in schedule:
            day=DAYS[anime["weekday"]-1]
            if self.day_filter.get()!="Toda la semana" and self.day_filter.get()!=day:continue
            status="completed" if counts.get(anime["slug"]) else "pending"
            detail="✔ Al día" if status=="completed" else "Pendiente de revisión"
            if anime["slug"] in active:
                row=active[anime["slug"]];status=row["status"]
                detail=LABELS[status]+f" · {row['number']}"+(f" · {row['progress']:.0f}%" if status=="downloading" else "")
            if not cfg.accepts(anime["slug"]):status,detail="excluded","Excluido"
            if anime["slug"] in cfg.favorites:detail="★ "+detail
            self.tree.insert("","end",iid=anime["slug"],values=(day,anime["title"],anime["latest"],detail,counts.get(anime["slug"],0)),tags=(status,))
        self.tree.selection_set([s for s in selected if self.tree.exists(s)])
        task=self.db.meta("task",{})
        self.summary.set("Descargas por enlace y desde la web · Temporada " + (f"automática a las {cfg.review_time}" if cfg.schedule_enabled else "manual"))
        self.pause_button.configure(text="Continuar" if cfg.paused else "Pausar")
        history=self.db.query("SELECT created,level,message FROM history ORDER BY id DESC LIMIT 150")
        self.history.configure(state="normal");self.history.delete("1.0","end")
        for item in reversed(history):
            self.history.insert("end",time.strftime("%d/%m %H:%M",time.localtime(item["created"]))+" "+item["message"]+"\n",item["level"])
        self.history.configure(state="disabled")
        self.download_tab.refresh()
        self.queue_tab.refresh()

    def refresh(self):
        self.refresh_table();self.after(2000,self.refresh)

    def poll(self):
        if self.instance is not None:
            while True:
                try:command=self.instance.commands.get_nowait()
                except queue.Empty:break
                if command and command.get("action")=="show":
                    self.show_window(command.get("history",False))
                    if command.get('pair'):self.pair_web()
                elif command and command.get('action')=='web_settings':
                    self.reload_web_preferences()
                    self.status.set('Cola recibida desde la web. Preferencias actualizadas; las descargas continúan en la bandeja.')
        while True:
            try:event,value=self.events.get_nowait()
            except queue.Empty:break
            self.pending_work -= 1
            if not self.pending_work:self.activate.configure(state="normal")
            if event=="error":
                message,on_error=value
                if on_error:on_error()
                self.status.set(message)
            else:callback,result=value;callback(result)
            self.refresh_table()
        if self._closing_requested:
            if str(self.activate["state"])!="disabled":
                self.destroy();return
        self.after(200,self.poll)

    def show_window(self, history=False):
        if history:self.tabs.select(self.history_tab)
        self.deiconify()
        self.lift()
        self.focus_force()

    def close(self):
        if str(self.activate["state"])=="disabled":
            self._closing_requested=True
            self.status.set("Terminando de guardar la configuración antes de cerrar…")
        else:self.destroy()

    def destroy(self):
        for callback in self.tk.call("after","info"):self.after_cancel(callback)
        self.db.close();super().destroy()


def main(directory,history=False,pair=False):
    with Instance(directory,"window") as instance:
        if not instance.claim({"action":"show","history":history,"pair":pair}):return
        if Config.load(directory).configured and not send(directory,"tray",{"action":"ping"}):
            spawn(directory,"--tray")
        app=App(directory,history,autostart_review=True,instance=instance)
        if pair:app.after(0,app.pair_web)
        app.mainloop()
