from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def main():
    if getattr(sys,"frozen",False):os.environ.pop("PYINSTALLER_RESET_ENVIRONMENT",None)
    from .stdio import prepare
    prepare()
    if len(sys.argv)>1 and sys.argv[1]=="--worker":
        import yt_dlp
        yt_dlp.main(sys.argv[2:]);return 0
    from .config import Config,data_dir
    from .brand import APP_NAME
    from .database import Database
    from .engine.storage import write_json
    parser=argparse.ArgumentParser(description=APP_NAME + ": catálogo completo por enlace, web y temporada opcional.")
    parser.add_argument("--data-dir",type=Path)
    modes=parser.add_mutually_exclusive_group()
    for name,help in (("window","Abrir descargador, cola y configuración"),("tray","Mantener bandeja opcional"),
                       ("run-now","Revisar y descargar ahora"),("resume","Continuar pendientes y parciales"),("scheduled","Revisar solo si hay trabajo vencido"),
                       ("dry-run","Mostrar lo que descargaría sin bajar videos"),("install","Activar tarea diaria y revisión al iniciar Windows"),
                       ("uninstall","Desactivar la tarea propia"),("inspect-task","Consultar la tarea propia")):
        modes.add_argument("--"+name,action="store_true",help=help)
    modes.add_argument("--import-web",type=Path,help="Importar una cola exportada por YomaTV Web")
    modes.add_argument("--export-web",type=Path,help="Guardar resultados verificados para la web")
    modes.add_argument("--resume-web",action="store_true",help=argparse.SUPPRESS)
    modes.add_argument("--resume-queue",action="store_true",help="Continuar la cola general sin revisar el horario")
    parser.add_argument("--history",action="store_true")
    parser.add_argument("--pair-web",action="store_true",help="Mostrar el código para conectar la web con este equipo")
    parser.add_argument("--report",type=Path)
    parser.add_argument("--self-test",type=Path)
    parser.add_argument("--spawn-self-test",type=Path,help=argparse.SUPPRESS)
    args=parser.parse_args()
    directory=(args.data_dir or data_dir()).resolve();directory.mkdir(parents=True,exist_ok=True)
    if args.self_test:
        from .selftest import run
        return run(args.self_test)
    if args.spawn_self_test:
        from .tray import spawn
        write_json(args.spawn_self_test.with_suffix(".parent.json"),{"extraction":getattr(sys,"_MEIPASS",None),"pid":os.getpid()})
        spawn(directory,"--self-test",str(args.spawn_self_test.resolve()))
        return 0
    try:
        if args.import_web or args.export_web:
            from .web_import import import_plan,export_results
            if args.import_web:
                result=import_plan(directory,args.import_web)
                cfg=Config.load(directory)
                if cfg.autostart:
                    from .windows_tasks import install
                    db=Database(directory)
                    try:db.set_meta("task",{"name":install(cfg,directory),"installed":True,"time":cfg.review_time})
                    finally:db.close()
                from .tray import spawn
                spawn(directory,"--resume-web")
            else:result=export_results(directory,args.export_web)
            if args.report:write_json(args.report,result)
            print(json.dumps(result,ensure_ascii=False));return 0
        if args.install or args.uninstall or args.inspect_task:
            from .windows_tasks import install,inspect,uninstall
            with_db=Database(directory)
            try:
                if args.install:
                    cfg=Config.load(directory);cfg.configured=True;cfg.save(directory)
                    name=install(cfg,directory);result={"installed":True,"name":name,"time":cfg.review_time}
                    with_db.set_meta("task",result)
                elif args.uninstall:
                    uninstall(directory);result={"installed":False};with_db.set_meta("task",result)
                else:result=inspect(directory)
            finally:with_db.close()
            if args.report:write_json(args.report,result)
            print(json.dumps(result,ensure_ascii=False));return 0
        if args.dry_run:
            from .runner import Runner
            runner=Runner(directory)
            try:result=runner.run(force=True,dry_run=True)
            finally:runner.close()
            if args.report:write_json(args.report,result)
            print(json.dumps(result,ensure_ascii=False,indent=2));return 0
        if args.scheduled:
            from datetime import datetime
            from .schedule import work_due
            cfg=Config.load(directory)
            db=Database(directory)
            try:
                due=work_due(db,cfg,datetime.now().astimezone())
            finally:db.close()
            if (cfg.paused or not cfg.configured or not due) and not cfg.resident_tray:return 0
        if args.resume or args.resume_web or args.resume_queue:
            cfg=Config.load(directory);cfg.paused=False;cfg.save(directory)
        if args.run_now or args.resume or args.resume_web or args.resume_queue or args.scheduled or args.tray:
            from .tray import Tray
            from .instance import Instance
            action="review" if args.run_now else "resume_queue" if args.resume_queue else "resume_web" if args.resume_web else "resume" if args.resume else "scheduled"
            with Instance(directory,"tray") as instance:
                if not instance.claim({"action":action}):return 0
                return Tray(directory,force=args.run_now,resident=args.tray,instance=instance,resume=args.resume or args.resume_web or args.resume_queue,queue_only=args.resume_web or args.resume_queue).run()
        from .gui import main as gui_main
        gui_main(directory,args.history,args.pair_web);return 0
    except Exception as exc:
        if args.report:write_json(args.report,{"ok":False,"error":str(exc)})
        if sys.stderr:print(str(exc),file=sys.stderr)
        if not any((args.scheduled,args.run_now,args.resume,args.resume_web,args.resume_queue,args.import_web,args.export_web,args.dry_run,args.install,args.uninstall,args.inspect_task,args.tray)):
            from tkinter import messagebox
            messagebox.showerror(APP_NAME,str(exc))
        return 1


if __name__=="__main__":
    raise SystemExit(main())
