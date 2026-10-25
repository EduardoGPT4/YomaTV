"""Diagnóstico del ejecutable sin consultar Internet ni instalar tareas."""
import json
import subprocess
import tempfile
from pathlib import Path

import imageio_ffmpeg

from .engine.download import worker_command
from .engine.storage import write_json


def run(report):
    import sys
    import os
    result={"frozen":bool(getattr(sys,"frozen",False)),"extraction":getattr(sys,"_MEIPASS",None),"pid":os.getpid()}
    report.parent.mkdir(parents=True,exist_ok=True)
    try:
        from .gui import App
        from .brand import VERSION
        from .web_controls import device_info
        from .config import ASSETS
        from .windows_tasks import task_xml
        import pystray
        with tempfile.TemporaryDirectory(dir=report.parent) as directory:
            result.update(version=VERSION,device_identity=len(device_info(Path(directory))['id'])==32)
            app=App(Path(directory));app.withdraw();app.update()
            result.update(tk=app.tk.call("info","patchlevel"),title=app.title(),sqlite=app.db.connection.execute("PRAGMA integrity_check").fetchone()[0])
            result.update(tabs=[app.tabs.tab(tab,'text') for tab in app.tabs.tabs()],
                          general_download_default=app.tabs.select()==str(app.download_tab),
                          new_install_season_enabled=app.cfg.schedule_enabled)
            from .engine.catalog import Catalog, Episode
            from .config import Config
            from .manual import enqueue_catalog
            catalog=Catalog('Naruto','naruto',[Episode(str(n),f'https://animeav1.com/media/naruto/{n}') for n in [1,2,100,220]],None,[])
            app.download_tab.show_catalog(catalog)
            app.download_tab.ranges.set('1-2,220');app.download_tab.apply_range()
            result['range_selection']=list(app.download_tab.tree.selection())
            cfg=Config.load(Path(directory));cfg.autostart=False;cfg.notifications=False;cfg.save(Path(directory))
            queued=enqueue_catalog(Path(directory),catalog,result['range_selection'])
            repeated=enqueue_catalog(Path(directory),catalog,result['range_selection'])
            app.queue_tab.refresh()
            result.update(general_queued=queued['added'],duplicates_added=repeated['added'],queue_rows=len(app.queue_tab.tree.get_children()))
            app.destroy()
        options={"creationflags":subprocess.CREATE_NO_WINDOW} if hasattr(subprocess,"CREATE_NO_WINDOW") else {}
        worker=subprocess.run([*worker_command(),"--version"],capture_output=True,text=True,timeout=90,check=True,**options)
        ffmpeg=subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),"-version"],capture_output=True,text=True,timeout=30,check=True,**options)
        result.update(yt_dlp=worker.stdout.strip(),ffmpeg=ffmpeg.stdout.splitlines()[0],
                      tray_menu=pystray.Icon.HAS_MENU,tray_notifications=pystray.Icon.HAS_NOTIFICATION,
                      icon=(ASSETS/"yomatv.ico").is_file(),task_xml_bytes=len(task_xml(["SeasonAV1.exe","--scheduled"],report.parent,"12:00","S-1-5-21-1")))
        result["ok"]=result["sqlite"]=="ok" and result["icon"] and result["tray_menu"] and result['general_download_default'] and not result['new_install_season_enabled'] and result['range_selection']==['1','2','220'] and result['general_queued']==3 and result['duplicates_added']==0 and result['queue_rows']==3
    except Exception as exc:result.update(ok=False,error=str(exc))
    write_json(report,result)
    return 0 if result["ok"] else 1
