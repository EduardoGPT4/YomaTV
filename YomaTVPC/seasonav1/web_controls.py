"""Authenticated bridge operations over existing web references; never accepts paths."""
from __future__ import annotations
import json
import platform
import re
import secrets
import time
from pathlib import Path
from .database import Database
from .config import Config

def device_info(directory):
    db=Database(directory)
    try:
        with db.transaction() as c:
            c.execute('INSERT OR IGNORE INTO meta(key,value) VALUES(?,?)',('web_device_id',json.dumps(secrets.token_hex(16))))
        return {'id':db.meta('web_device_id'),'name':platform.node()[:80] or 'Mi PC'}
    finally:db.close()

def references(db,installation,ids,require_all=False):
    if not isinstance(installation,str) or not re.fullmatch(r'[a-f0-9]{16,64}',installation) or not isinstance(ids,list) or not 1<=len(ids)<=2000 or any(type(n) is not int or n<1 or n>9999999999 for n in ids):
        raise ValueError('Selecciona solicitudes válidas de esta web.')
    rows=[]
    for offset in range(0,len(ids),500):
        chunk=ids[offset:offset+500]
        rows.extend(db.query('SELECT r.web_id,e.* FROM web_references r JOIN episodes e ON e.id=r.episode_id WHERE r.installation=? AND r.web_id IN ('+','.join('?' for _ in chunk)+')',[installation,*chunk]))
    if require_all and {r['web_id'] for r in rows}!=set(ids):raise ValueError('Hay solicitudes que esta PC no conoce. Envía la cola primero.')
    return rows

def file_state(row):
    if row['status']!='completed' or not row['path']:return None
    try:return Path(row['path']).is_file() and Path(row['path']).stat().st_size==row['bytes']
    except OSError:return False

def check_files(directory,value):
    db=Database(directory)
    try:
        rows=references(db,value.get('installation'),value.get('ids'))
        found={r['web_id']:r for r in rows}
        return {'device':device_info(directory),'items':[{'web_id':n,'present':file_state(found[n]) if n in found else None,'known':n in found} for n in dict.fromkeys(value['ids'])]}
    finally:db.close()

def control_queue(directory,value):
    if not isinstance(value,dict) or value.get('format')!='seasonav1.web-control/v1':raise ValueError('Control de cola inválido.')
    action=value.get('action')
    if action not in {'pause','resume','retry','priority','redownload'}:raise ValueError('Acción inválida.')
    priority=value.get('priority',0)
    if type(priority) is not int or not -10<=priority<=10:raise ValueError('Prioridad inválida.')
    db=Database(directory)
    try:
        with db.transaction() as connection:
            rows=references(db,value.get('installation'),value.get('ids'),True)
            slugs={r['slug'] for r in rows}
            if len(slugs)!=1:raise ValueError('Controla un anime por solicitud.')
            slug=next(iter(slugs))
            if action=='redownload':
                if value.get('confirmation')!='REDESCARGAR':raise ValueError('Confirma la redescarga.')
                if any(r['status']!='completed' or file_state(r) is not False for r in rows):raise ValueError('Solo se restablecen archivos comprobados como ausentes o de otro tamaño.')
                for row in rows:connection.execute("UPDATE episodes SET status='pending',progress=0,next_retry=0,error='' WHERE id=?",(row['id'],))
            elif action=='retry':
                for row in rows:connection.execute("UPDATE episodes SET next_retry=0,error='' WHERE id=? AND status='failed'",(row['id'],))
            else:
                connection.execute('INSERT OR IGNORE INTO anime_controls(slug) VALUES(?)',(slug,))
                column='priority' if action=='priority' else 'paused'
                connection.execute('UPDATE anime_controls SET '+column+'=? WHERE slug=?',(priority if action=='priority' else int(action=='pause'),slug))
        db.log('info','Control web de '+slug+': '+action)
        return {'action':action,'slug':slug,'items':len(rows),'global_paused':Config.load(directory).paused,'control':db.group_control(slug)}
    finally:db.close()

class GroupToken:
    """Cancellation for one anime; global pause still cancels every anime."""
    def __init__(self,parent,db,slug):self.parent,self.db,self.slug=parent,db,slug;self.next_check=0;self.paused=False
    def is_set(self):
        if self.parent.is_set():return True
        if time.monotonic()>=self.next_check:
            self.paused=bool(self.db.group_control(self.slug)['paused']);self.next_check=time.monotonic()+.4
        return self.paused
    def wait(self,seconds):
        end=time.monotonic()+seconds
        while not self.is_set():
            left=end-time.monotonic()
            if left<=0:return False
            self.parent.wait(min(.4,left))
        return True
