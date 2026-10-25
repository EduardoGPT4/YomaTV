"""Intercambio explícito de colas y resultados con YomaTV Web."""
from __future__ import annotations

import json
import re
import time
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from .config import Config, season_folder
from .database import Database
from .engine.catalog import DownloadError, normalize_url, Episode
from .engine.storage import FileLock, write_json
from .schedule import ScheduledAnime

WEB_PREFERENCES={"language","server","height","quality_fallback","language_fallback","server_fallback","review_time",
                 "workers","speed_kib","selection","long_series","season_source","favorites","exclusions"}

def configure_web_preferences(cfg,preferences,strict=False):
    if not isinstance(preferences,dict) or (strict and not set(preferences)<=WEB_PREFERENCES):
        raise ValueError("Preferencias web inválidas.")
    for key,value in preferences.items():
        if key not in WEB_PREFERENCES:continue
        if key in {"height","workers","speed_kib"} and type(value) is not int:
            raise ValueError("La calidad y los límites deben ser números enteros.")
        if key in {"favorites","exclusions"}:
            if not isinstance(value,list) or len(value)>5000 or not all(isinstance(s,str) and re.fullmatch(r"[A-Za-z0-9_-]{1,240}",s) for s in value):
                raise ValueError("Lista de animes inválida.")
            value=sorted(set(value))
        elif key not in {"height","workers","speed_kib"} and not isinstance(value,str):
            raise ValueError("Opción de descarga inválida.")
        setattr(cfg,key,value)
    return cfg.validate()

def apply_web_preferences(directory: Path,value):
    if not isinstance(value,dict) or value.get('format')!='seasonav1.web-settings/v1' or not isinstance(value.get('preferences'),dict):
        raise ValueError('Selecciona preferencias válidas de YomaTV Web.')
    old=Config.load(directory)
    cfg=configure_web_preferences(Config.load(directory),value['preferences'],strict=True)
    changed=sorted(key for key in WEB_PREFERENCES if getattr(old,key)!=getattr(cfg,key))
    if changed:cfg.save(directory)
    return {'changed':changed,'review_time':cfg.review_time,'paused':cfg.paused}

def queue_status(directory: Path,installation: str,identifiers: list[int]):
    db=Database(directory)
    try:
        cfg=Config.load(directory);jobs=[]
        for offset in range(0,len(identifiers),500):
            chunk=identifiers[offset:offset+500];marks=','.join('?' for _ in chunk)
            rows=db.query(f'SELECT r.web_id,e.status,e.progress,e.error,c.paused AS group_paused,c.priority FROM web_references r JOIN episodes e ON e.id=r.episode_id LEFT JOIN anime_controls c ON c.slug=e.slug WHERE r.installation=? AND r.web_id IN ({marks})',[installation,*chunk])
            for row in rows:
                status=row['status'];error=(row['error'] or '').lower()
                reason='Sin conexión' if any(v in error for v in ('getaddrinfo','dns','connection','timed out','sin conexión')) else 'Fuente no disponible' if 'sin ' in error or '404' in error else 'Error de descarga'
                if cfg.paused and status in {'pending','downloading','verifying'}:status='paused'
                if row['group_paused'] and status in {'pending','downloading','verifying'}:status='paused'
                jobs.append({'web_id':row['web_id'],'status':status,'priority':row['priority'] or 0,'group_paused':bool(row['group_paused']),'progress':max(0,min(100,row['progress'] or 0)),'reason':reason if status=='failed' else ''})
        return {'jobs':jobs,'paused':cfg.paused}
    finally:db.close()


def load_plan(path: Path):
    if path.stat().st_size>2*1024*1024:
        raise ValueError("La cola web no puede exceder 2 MB.")
    value=json.loads(path.read_text(encoding="utf-8-sig"))
    return validate_plan(value)


def validate_plan(value):
    if not isinstance(value,dict) or value.get("format")!="seasonav1.web-plan/v1":
        raise ValueError("Selecciona una cola exportada por YomaTV Web.")
    if not re.fullmatch(r"[a-f0-9]{16,64}",str(value.get("installation",""))) or not re.fullmatch(r"[a-f0-9]{16,64}",str(value.get("plan_id",""))):
        raise ValueError("La cola no tiene un identificador válido.")
    items=value.get("items")
    if not isinstance(items,list) or not 1<=len(items)<=2000:
        raise ValueError("La cola debe contener entre 1 y 2.000 capítulos.")
    settings=value.get("preferences",{})
    if not isinstance(settings,dict):raise ValueError("Preferencias inválidas.")
    for item in items:
        if not isinstance(item,dict):raise ValueError("Capítulo inválido.")
        slug=item.get("slug","");number=str(item.get("number",""))
        if not isinstance(slug,str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,240}",slug) or not re.fullmatch(r"\d{1,5}(?:\.\d{1,4})?",number):
            raise ValueError("Un capítulo tiene un identificador inválido.")
        normalized,parsed_slug,parsed_number=normalize_url(str(item.get("url","")))
        if parsed_slug!=slug or parsed_number!=number or normalized!=f"https://animeav1.com/media/{slug}/{number}":
            raise ValueError("La cola contiene una dirección ajena al capítulo.")
        revision=item.get('request_revision','')
        if not isinstance(revision,str) or (revision and not re.fullmatch(r'[a-f0-9]{32}',revision)):raise ValueError('Revisión de descarga inválida.')
        if not isinstance(item.get("web_id"),int) or item["web_id"]<1 or item.get("language") not in {"SUB","LAT","DUB"}:
            raise ValueError("Identificador web o idioma inválido.")
        if item["language"]!=settings.get("language","SUB"):
            raise ValueError("Exporta una cola de un solo idioma.")
        if not isinstance(item.get("title"),str) or not 1<=len(item["title"])<=500 or not 1<=int(item.get("weekday",0))<=7:
            raise ValueError("Título o día inválido.")
        if item.get("start_date"):date.fromisoformat(item["start_date"])
        item["number"]=number
    return value


def import_plan(directory: Path,path: Path | dict):
    plan=validate_plan(path) if isinstance(path,dict) else load_plan(path)
    cfg=Config.load(directory)
    configure_web_preferences(cfg,plan['preferences']);cfg.configured=True;cfg.paused=False
    old=Config.load(directory)
    paused=Config.load(directory);paused.paused=True;paused.save(directory)
    db=None;lock=FileLock(directory/"review.lock")
    try:
        deadline=time.monotonic()+35
        while True:
            try:lock.acquire();break
            except DownloadError:
                if time.monotonic()>deadline:raise RuntimeError("La descarga todavía se está pausando. Intenta importar la cola de nuevo.")
                time.sleep(.2)
        db=Database(directory);refs=[];added=0
        for item in plan["items"]:
            slug=item["slug"];existing=db.anime(slug)
            latest=max(str(existing["latest"]) if existing else "0",item["number"],key=Decimal)
            anime=ScheduledAnime(slug,item["title"],int(item["weekday"]),latest,datetime.now().astimezone().isoformat(),item.get("start_date"))
            initial=season_folder(date.fromisoformat(item["start_date"])) if cfg.season_source=="premiere" and item.get("start_date") else season_folder(date.today())
            season=existing["season"] if existing else initial
            db.upsert_anime(anime,season)
            before=db.query("SELECT id FROM episodes WHERE slug=? AND number=? AND language=?",(slug,item["number"],cfg.language))
            episode_season=season_folder(date.today()) if cfg.long_series=="split" else season
            db.add_episode(slug,Episode(item["number"],item["url"]),cfg.language,episode_season)
            row=db.query("SELECT id,status FROM episodes WHERE slug=? AND number=? AND language=?",(slug,item["number"],cfg.language))[0]
            if row["status"]!="completed":db.update(row["id"],status="pending",next_retry=0,error="")
            if not before:added+=1
            refs.append({"web_id":item["web_id"],"episode_id":row["id"],"slug":slug,"number":item["number"],"language":cfg.language,"request_revision":item.get("request_revision","")})
        imports=db.meta("web_imports",[])
        imports=[p for p in imports if (p["plan_id"],p["installation"])!=(plan["plan_id"],plan["installation"])]
        replaced_ids={r["web_id"] for r in refs}
        for previous in imports:
            if previous["installation"]==plan["installation"]:
                previous["items"]=[r for r in previous["items"] if r["web_id"] not in replaced_ids]
        imports=[p for p in imports if p["items"]]
        imports.append({"plan_id":plan["plan_id"],"installation":plan["installation"],"items":refs})
        db.set_meta("web_imports",imports[-50:])
        db.log("info",f"Cola web importada: {added} capítulos nuevos, {len(refs)} referencias. Destino conservado: {cfg.destination}")
        cfg.save(directory)
        return {"added":added,"items":len(refs),"review_time":cfg.review_time}
    except Exception:
        old.save(directory)
        raise
    finally:
        if db is not None:db.close()
        lock.close()


def result_receipts(directory: Path,installation=None,identifiers=None):
    db=Database(directory)
    try:
        grouped={};completed=0
        conditions=["e.status='completed'"];args=[]
        if installation is not None:conditions.append('r.installation=?');args.append(installation)
        batches=[None] if identifiers is None else [identifiers[i:i+500] for i in range(0,len(identifiers),500)]
        for batch in batches:
            clause=' AND '.join(conditions);params=list(args)
            if batch is not None:clause+=' AND r.web_id IN ('+','.join('?' for _ in batch)+')';params.extend(batch)
            rows=db.query("SELECT r.plan_id,r.installation,r.web_id,e.slug,e.number,e.language,e.bytes,e.sha256,COALESCE(v.revision,'') AS request_revision FROM web_references r JOIN episodes e ON e.id=r.episode_id LEFT JOIN web_reference_runs v ON v.installation=r.installation AND v.web_id=r.web_id WHERE "+clause+' ORDER BY r.installation,r.plan_id,r.web_id',params)
            for row in rows:
                if not re.fullmatch(r'[a-f0-9]{64}',row['sha256'] or '') or not isinstance(row['bytes'],int) or row['bytes']<1024:continue
                key=(row['installation'],row['plan_id'])
                grouped.setdefault(key,[]).append({k:v for k,v in row.items() if k not in {'installation','plan_id'}} | {'status':'completed'})
                completed+=1
        plans=[{'plan_id':key[1],'installation':key[0],'items':items} for key,items in grouped.items()]
        chunks=[];current=[]
        for plan in plans:
            candidate={"format":"seasonav1.web-results/v1","plans":[*current,plan]}
            if current and len(json.dumps(candidate,ensure_ascii=False,indent=2).encode())>1_800_000:
                chunks.append(current);current=[]
            current.append(plan)
        if current:chunks.append(current)
        return {"completed":completed,"receipts":[{"format":"seasonav1.web-results/v1","plans":chunk} for chunk in chunks]}
    finally:db.close()


def export_results(directory: Path,path: Path):
    result=result_receipts(directory)
    if not result['completed']:raise ValueError("Todavía no hay capítulos de una cola web terminados y verificados.")
    files=[]
    for index,receipt in enumerate(result['receipts'],1):
        target=path if len(result['receipts'])==1 else path.with_name(f"{path.stem}-{index:02d}.json")
        write_json(target,receipt | {"created_at":datetime.now().astimezone().isoformat()})
        files.append(str(target))
    return {"completed":result['completed'],"files":files}
