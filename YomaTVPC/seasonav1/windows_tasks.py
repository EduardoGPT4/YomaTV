"""Programador de tareas del usuario actual, sin servicio ni privilegios de administrador."""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path

from .config import ROOT
from .brand import APP_NAME

NS = "http://schemas.microsoft.com/windows/2004/02/mit/task"


def launch_command(*args):
    if getattr(sys, "frozen", False):
        return [sys.executable, *args]
    python = Path(sys.executable)
    if os.name == "nt" and python.name.lower() == "python.exe" and python.with_name("pythonw.exe").is_file():
        python = python.with_name("pythonw.exe")
    return [str(python), "-X", "utf8", "-m", "seasonav1", *args]


def system_command(command, check=True):
    options = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}
    result = subprocess.run(command, capture_output=True, text=True, errors="replace", timeout=40, **options)
    if check and result.returncode:
        raise RuntimeError((result.stderr or result.stdout).strip() or "Windows rechazó la tarea programada.")
    return result


def current_sid():
    if os.name != "nt": raise RuntimeError("El Programador de tareas necesita Windows.")
    return system_command(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
                           "[System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value"]).stdout.strip()


def task_name(directory, sid):
    digest = hashlib.sha256((str(directory.resolve()).casefold() + sid).encode()).hexdigest()[:10]
    return "SeasonAV1-" + digest


def task_xml(command, directory, review_time, sid, autostart=True, now=None, schedule_enabled=True):
    now = now or datetime.now()
    hour, minute = map(int, review_time.split(":"))
    boundary = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if boundary <= now: boundary += timedelta(days=1)
    task = ET.Element("Task", {"version": "1.2", "xmlns": NS})
    def add(parent, name, text=None, **attrs):
        node = ET.SubElement(parent, name, attrs)
        if text is not None: node.text = str(text)
        return node
    info = add(task, "RegistrationInfo")
    add(info, "Author", APP_NAME)
    add(info, "Description", "Revisión diaria del horario AnimeAV1 y recuperación al iniciar sesión.")
    triggers = add(task, "Triggers")
    if schedule_enabled:
        daily = add(triggers, "CalendarTrigger")
        add(daily, "StartBoundary", boundary.isoformat())
        add(daily, "Enabled", "true")
        add(add(daily, "ScheduleByDay"), "DaysInterval", "1")
    if autostart:
        logon = add(triggers, "LogonTrigger")
        add(logon, "Enabled", "true")
        add(logon, "UserId", sid)
        add(logon, "Delay", "PT30S")
    principal = add(add(task, "Principals"), "Principal", id="User")
    add(principal, "UserId", sid)
    add(principal, "LogonType", "InteractiveToken")
    add(principal, "RunLevel", "LeastPrivilege")
    settings = add(task, "Settings")
    # La invocación diaria avisa a la bandeja residente y termina. Instance evita duplicados.
    for name, text in (("MultipleInstancesPolicy", "Parallel"), ("DisallowStartIfOnBatteries", "false"),
                       ("StopIfGoingOnBatteries", "false"), ("StartWhenAvailable", "true"),
                       ("RunOnlyIfNetworkAvailable", "false"), ("AllowStartOnDemand", "true"),
                       ("Enabled", "true"), ("WakeToRun", "false"), ("ExecutionTimeLimit", "PT0S"), ("Priority", "7")):
        add(settings, name, text)
    restart = add(settings, "RestartOnFailure")
    add(restart, "Interval", "PT15M")
    add(restart, "Count", "3")
    execution = add(add(task, "Actions", Context="User"), "Exec")
    add(execution, "Command", command[0])
    add(execution, "Arguments", subprocess.list2cmdline(command[1:]))
    add(execution, "WorkingDirectory", ROOT)
    return ET.tostring(task, encoding="utf-16", xml_declaration=True)


def install(cfg, directory, command=None):
    sid = current_sid()
    name = task_name(directory, sid)
    xml = task_xml(command or launch_command("--data-dir", str(directory), "--scheduled"), directory, cfg.review_time, sid, cfg.autostart, schedule_enabled=cfg.schedule_enabled)
    file = directory / "windows-task.xml"
    directory.mkdir(parents=True, exist_ok=True)
    file.write_bytes(xml)
    system_command(["schtasks.exe", "/Create", "/TN", name, "/XML", str(file), "/F"])
    return name


def inspect(directory):
    name = task_name(directory, current_sid())
    result = system_command(["schtasks.exe", "/Query", "/TN", name, "/XML"], check=False)
    return {"name": name, "installed": result.returncode == 0, "xml": result.stdout if result.returncode == 0 else ""}


def uninstall(directory):
    name = task_name(directory, current_sid())
    status = system_command(["schtasks.exe", "/Query", "/TN", name], check=False)
    if not status.returncode:
        system_command(["schtasks.exe", "/Delete", "/TN", name, "/F"])
