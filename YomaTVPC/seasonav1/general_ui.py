"""Panel general basado en la selección por enlace de AnimeAV1."""
from __future__ import annotations

import os
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, ttk

from .config import Config
from .engine.presentation import count_text, short_failure
from .engine.selection import select_episodes
from .manual import enqueue_catalog, read_catalog, retry_jobs
from .theme import CARD, GREEN, MINT, MUTED, RED
from .tray import spawn

LABELS = {'pending': '⏳ En cola', 'downloading': '⬇ Descargando', 'verifying': 'Verificando',
          'paused': 'Pausado', 'completed': '✔ Descargado', 'failed': '✖ Falló'}


class DownloadPanel(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=12)
        self.app, self.catalog, self.busy = app, None, False
        cfg = Config.load(app.directory)
        self.url = tk.StringVar(value=app.db.meta('manual_last_url', ''))
        self.ranges = tk.StringVar(value='')
        self.language = tk.StringVar(value=cfg.language)
        self.server = tk.StringVar(value=cfg.server)
        self.height = tk.StringVar(value=str(cfg.height))
        self.destination = tk.StringVar(value=cfg.destination)
        self.heading = tk.StringVar(value='Descarga cualquier anime del catálogo')
        self.selection_text = tk.StringVar(value='Pega la ficha de un anime o el enlace de un capítulo.')
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        sidebar_box = ttk.Frame(self, style='Card.TFrame', width=305)
        sidebar_box.grid(row=0, column=0, sticky='ns', padx=(0, 15))
        sidebar_box.grid_propagate(False)
        sidebar_box.columnconfigure(0, weight=1)
        sidebar_box.rowconfigure(0, weight=1)
        self.sidebar_canvas = tk.Canvas(sidebar_box, bg=CARD, highlightthickness=0, width=288)
        self.sidebar_canvas.grid(row=0, column=0, sticky='nsew')
        sidebar_scroll = ttk.Scrollbar(sidebar_box, command=self.sidebar_canvas.yview)
        sidebar_scroll.grid(row=0, column=1, sticky='ns')
        self.sidebar_canvas.configure(yscrollcommand=sidebar_scroll.set)
        sidebar = ttk.Frame(self.sidebar_canvas, style='Card.TFrame', padding=16)
        sidebar_window = self.sidebar_canvas.create_window((0, 0), window=sidebar, anchor='nw')
        sidebar.bind('<Configure>', lambda _: self.sidebar_canvas.configure(scrollregion=self.sidebar_canvas.bbox('all')))
        self.sidebar_canvas.bind('<Configure>', lambda event: self.sidebar_canvas.itemconfigure(sidebar_window, width=event.width))
        sidebar.columnconfigure(0, weight=1)
        ttk.Label(sidebar, text='Preparar descarga', style='CardHeading.TLabel').grid(row=0, column=0, sticky='w', pady=(0, 14))
        ttk.Label(sidebar, text='Enlace de AnimeAV1', style='Card.TLabel').grid(row=1, column=0, sticky='w')
        self.url_entry = ttk.Entry(sidebar, textvariable=self.url, width=31)
        self.url_entry.grid(row=2, column=0, sticky='ew', pady=(6, 8))
        self.url_entry.bind('<Return>', lambda _: self.analyze())
        self.analyze_button = ttk.Button(sidebar, text='Analizar enlace', command=self.analyze)
        self.analyze_button.grid(row=3, column=0, sticky='ew')
        ttk.Button(sidebar, text='Explorar catálogo web ↗', command=lambda: webbrowser.open('https://hk-br035.gt.tc/seasonav1/')).grid(row=4, column=0, sticky='ew', pady=(6, 16))
        ttk.Label(sidebar, text='Capítulos o rangos', style='Card.TLabel').grid(row=5, column=0, sticky='w')
        ttk.Entry(sidebar, textvariable=self.ranges).grid(row=6, column=0, sticky='ew', pady=6)
        ttk.Label(sidebar, text='Ej.: 1-12,15,20-100 · admite especiales', style='CardMuted.TLabel', wraplength=270).grid(row=7, column=0, sticky='w')
        ttk.Button(sidebar, text='Seleccionar rango', command=self.apply_range).grid(row=8, column=0, sticky='ew', pady=(6, 16))
        options = ttk.Frame(sidebar, style='Card.TFrame')
        options.grid(row=9, column=0, sticky='ew')
        options.columnconfigure(1, weight=1)
        for row, (label, variable, values) in enumerate((('Idioma', self.language, ('SUB', 'LAT', 'DUB')),
                                                       ('Servidor', self.server, ('MP4Upload', 'Voe')),
                                                       ('Calidad', self.height, ('1080', '720')))):
            ttk.Label(options, text=label, style='Card.TLabel').grid(row=row, column=0, sticky='w', padx=(0, 10), pady=5)
            ttk.Combobox(options, textvariable=variable, values=values, state='readonly', width=14).grid(row=row, column=1, sticky='ew', pady=5)
        ttk.Label(sidebar, text='Carpeta de destino', style='Card.TLabel').grid(row=10, column=0, sticky='w', pady=(14, 5))
        ttk.Label(sidebar, textvariable=self.destination, style='CardMuted.TLabel', wraplength=260).grid(row=11, column=0, sticky='w')
        ttk.Button(sidebar, text='Elegir carpeta', command=self.choose_folder).grid(row=12, column=0, sticky='ew', pady=(6, 12))
        ttk.Label(sidebar, text='Los capítulos se descargan en orden.\nLa cola, los parciales y la web comparten\nel mismo registro de descargas.', style='CardMuted.TLabel', wraplength=270).grid(row=13, column=0, sticky='w')
        right = ttk.Frame(self)
        right.grid(row=0, column=1, sticky='nsew')
        right.columnconfigure(0, weight=1)
        right.rowconfigure(2, weight=1)
        ttk.Label(right, textvariable=self.heading, font=('Segoe UI', 14, 'bold'), wraplength=590).grid(row=0, column=0, sticky='ew', pady=(0, 6))
        toolbar = ttk.Frame(right)
        toolbar.grid(row=1, column=0, sticky='ew', pady=(0, 10))
        ttk.Label(toolbar, textvariable=self.selection_text, style='Muted.TLabel', wraplength=420).pack(side='left')
        ttk.Button(toolbar, text='Todos', command=lambda: self.select_all()).pack(side='right')
        table = ttk.Frame(right)
        table.grid(row=2, column=0, sticky='nsew')
        table.columnconfigure(0, weight=1)
        table.rowconfigure(0, weight=1)
        self.tree = ttk.Treeview(table, columns=('number', 'state', 'percent'), show='headings', selectmode='extended')
        for key, label, width in (('number', 'Capítulo', 105), ('state', 'Estado', 290), ('percent', '%', 60)):
            self.tree.heading(key, text=label)
            self.tree.column(key, width=width, minwidth=60, stretch=key == 'state')
        set_tags(self.tree)
        self.tree.grid(row=0, column=0, sticky='nsew')
        scroll = ttk.Scrollbar(table, command=self.tree.yview)
        scroll.grid(row=0, column=1, sticky='ns')
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.bind('<<TreeviewSelect>>', lambda _: self.update_controls())
        self.language.trace_add('write', lambda *_: self.refresh())
        actions = ttk.Frame(right)
        actions.grid(row=3, column=0, sticky='ew', pady=(12, 0))
        self.download_button = ttk.Button(actions, text='Descargar selección', style='Accent.TButton', command=self.download, state='disabled')
        self.download_button.pack(side='left')
        ttk.Button(actions, text='Ver cola general', command=lambda: app.tabs.select(app.queue_tab)).pack(side='right')

    def select_all(self):
        self.tree.selection_set(self.tree.get_children())
        self.update_controls()

    def update_controls(self):
        if self.catalog:
            self.selection_text.set(count_text(len(self.tree.selection()), 'capítulo seleccionado', 'capítulos seleccionados') + ' · Ctrl / Shift para elegir')
        self.download_button.configure(state='normal' if self.catalog and self.tree.selection() and not self.busy else 'disabled')

    def reload_preferences(self):
        cfg = Config.load(self.app.directory)
        for variable, value in ((self.language, cfg.language), (self.server, cfg.server), (self.height, str(cfg.height)), (self.destination, cfg.destination)):
            variable.set(value)

    def choose_folder(self):
        chosen = filedialog.askdirectory(initialdir=self.destination.get())
        if chosen:
            self.destination.set(chosen)

    def analyze(self):
        if self.busy:
            return
        url = self.url.get()
        self.busy = True
        self.analyze_button.configure(state='disabled')
        self.app.activate.configure(state='disabled')
        self.update_controls()
        self.app.status.set('Leyendo capítulos del HTML público; no se consultará el horario completo…')
        def done(catalog):
            self.busy = False
            self.analyze_button.configure(state='normal')
            self.show_catalog(catalog)
            self.app.status.set(f'{catalog.title}: {len(catalog.episodes)} capítulos disponibles. Elige tu selección.')
        self.app.background(lambda: read_catalog(self.app.directory, url), done, self.finish_error)

    def finish_error(self):
        self.busy = False
        self.analyze_button.configure(state='normal')
        self.update_controls()

    def show_catalog(self, catalog):
        self.catalog = catalog
        self.heading.set(catalog.title)
        self.tree.delete(*self.tree.get_children())
        for episode in catalog.episodes:
            self.tree.insert('', 'end', iid=episode.number, values=(f'Capítulo {episode.number}', 'Disponible', '—'))
        self.tree.selection_set([catalog.selected] if catalog.selected else self.tree.get_children())
        self.refresh()

    def apply_range(self):
        if not self.catalog or self.busy:
            return
        try:
            chosen = select_episodes(self.ranges.get(), self.catalog.episodes)
            self.tree.selection_set([episode.number for episode in chosen])
            self.update_controls()
        except Exception as exc:
            self.app.status.set(str(exc))

    def refresh(self):
        if not self.catalog:
            return
        rows = {row['number']: row for row in self.app.db.query('SELECT * FROM episodes WHERE slug=? AND language=?', (self.catalog.slug, self.language.get()))}
        cfg = Config.load(self.app.directory)
        for number in self.tree.get_children():
            row = rows.get(number)
            state = row['status'] if row else 'available'
            label = row_label(row, cfg.paused) if row else 'Disponible'
            percent = f"{row['progress']:.0f}%" if row and (row['progress'] or state in {'downloading', 'completed'}) else '—'
            self.tree.item(number, values=(f'Capítulo {number}', label, percent), tags=(state,))
        self.update_controls()

    def download(self):
        if self.busy or not self.catalog or not self.tree.selection():
            return
        numbers = list(self.tree.selection())
        catalog = self.catalog
        preferences = {'language': self.language.get(), 'server': self.server.get(), 'height': int(self.height.get()), 'destination': self.destination.get()}
        self.busy = True
        self.app.activate.configure(state='disabled')
        self.update_controls()
        self.app.status.set('Añadiendo la selección a la cola; los parciales y archivos completados se conservan…')
        def done(result):
            self.busy = False
            self.app.reload_web_preferences()
            spawn(self.app.directory, '--resume-queue')
            self.app.tabs.select(self.app.queue_tab)
            self.app.status.set(f"{result['items']} capítulos preparados ({result['added']} nuevos). Descargando en la bandeja.")
        def work():
            result=enqueue_catalog(self.app.directory, catalog, numbers, preferences)
            cfg=Config.load(self.app.directory)
            if cfg.autostart or cfg.schedule_enabled:
                from .windows_tasks import install
                try:self.app.db.set_meta('task',{'name':install(cfg,self.app.directory),'installed':True,'time':cfg.review_time})
                except Exception as exc:
                    self.app.db.log('warning','Cola preparada; no se pudo activar el inicio con Windows: '+str(exc))
            return result
        self.app.background(work, done, self.finish_error)


def set_tags(tree):
    for state, color in (('completed', GREEN), ('downloading', MINT), ('verifying', MINT), ('failed', RED), ('paused', MUTED), ('available', MUTED)):
        tree.tag_configure(state, foreground=color)


def row_label(row, paused):
    state = row['status']
    if paused and state in {'pending', 'downloading', 'verifying'}:
        return 'Pausado'
    return LABELS.get(state, state) + (': ' + short_failure(row['error']) if state == 'failed' else '')


class QueuePanel(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=12)
        self.app, self.rows = app, {}
        self.summary = tk.StringVar(value='La web, los enlaces y la temporada usan esta misma cola.')
        self.filter = tk.StringVar(value='Pendientes')
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        top = ttk.Frame(self)
        top.grid(row=0, column=0, sticky='ew', pady=(0, 12))
        ttk.Label(top, textvariable=self.summary, style='Muted.TLabel').pack(side='left')
        combo = ttk.Combobox(top, textvariable=self.filter, values=('Pendientes', 'Todos', 'Completados', 'Fallidos'), state='readonly', width=15)
        combo.pack(side='right')
        combo.bind('<<ComboboxSelected>>', lambda _: self.refresh())
        table = ttk.Frame(self)
        table.grid(row=1, column=0, sticky='nsew')
        table.columnconfigure(0, weight=1)
        table.rowconfigure(0, weight=1)
        self.tree = ttk.Treeview(table, columns=('title', 'number', 'language', 'state', 'percent'), show='headings', selectmode='extended')
        for key, label, width in (('title', 'Anime', 350), ('number', 'Capítulo', 85), ('language', 'Idioma', 70), ('state', 'Estado', 220), ('percent', '%', 60)):
            self.tree.heading(key, text=label)
            self.tree.column(key, width=width, minwidth=55, stretch=key in {'title', 'state'})
        self.tree.grid(row=0, column=0, sticky='nsew')
        set_tags(self.tree)
        scroll = ttk.Scrollbar(table, command=self.tree.yview)
        scroll.grid(row=0, column=1, sticky='ns')
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.bind('<Double-1>', lambda _: self.open_video())
        actions = ttk.Frame(self)
        actions.grid(row=2, column=0, sticky='ew', pady=(12, 0))
        ttk.Button(actions, text='Continuar cola', style='Accent.TButton', command=app.resume_queue).pack(side='left')
        self.retry_button = ttk.Button(actions, text='Reintentar fallidos', command=self.retry)
        self.retry_button.pack(side='left', padx=8)
        ttk.Button(actions, text='Abrir video seleccionado', command=self.open_video).pack(side='right')

    def refresh(self):
        selected = set(self.tree.selection())
        y = self.tree.yview()
        rows = self.app.db.query('SELECT e.*,a.title FROM episodes e JOIN anime a ON a.slug=e.slug ORDER BY a.title COLLATE NOCASE,CAST(e.number AS REAL),e.language')
        self.rows = {str(row['id']): row for row in rows}
        completed = sum(row['status'] == 'completed' for row in rows)
        failed = sum(row['status'] == 'failed' for row in rows)
        self.summary.set(f'{len(rows)} capítulos · {completed} descargados · {failed} fallidos')
        self.retry_button.configure(text=f'Reintentar fallidos ({failed})', state='normal' if failed else 'disabled')
        self.tree.delete(*self.tree.get_children())
        paused = Config.load(self.app.directory).paused
        for row in rows:
            if self.filter.get() == 'Pendientes' and row['status'] == 'completed':
                continue
            if self.filter.get() == 'Completados' and row['status'] != 'completed':
                continue
            if self.filter.get() == 'Fallidos' and row['status'] != 'failed':
                continue
            self.tree.insert('', 'end', iid=str(row['id']), values=(row['title'], row['number'], row['language'], row_label(row, paused), f"{row['progress']:.0f}%"), tags=(row['status'],))
        self.tree.selection_set([key for key in selected if self.tree.exists(key)])
        if y:
            self.tree.yview_moveto(y[0])

    def retry(self):
        selected = list(self.tree.selection()) or [key for key, row in self.rows.items() if row['status'] == 'failed']
        count = retry_jobs(self.app.directory, selected)
        if count:
            self.app.resume_queue()
            self.app.status.set(count_text(count, 'capítulo enviado a reintento', 'capítulos enviados a reintento'))
        self.refresh()

    def open_video(self):
        selected = self.tree.selection()
        row = self.rows.get(selected[0]) if selected else None
        if row and row['status'] == 'completed' and row['path'] and Path(row['path']).is_file():
            os.startfile(row['path'])
        else:
            self.app.status.set('Selecciona un capítulo completado cuyo video siga en su carpeta.')
