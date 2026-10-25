"""Ejecutable YomaTV con catálogo por enlace, temporada y puente web."""
import os
import subprocess
import sys
from pathlib import Path

root=Path(__file__).resolve().parent
subprocess.run([sys.executable,"-m","PyInstaller","--noconfirm","--onefile","--windowed",
               "--noupx","--name","YomaTV","--icon",str(root/"assets/yomatv.ico"),
               "--version-file",str(root/"assets/version.txt"),
               "--add-data",str(root/"assets")+os.pathsep+"assets","--distpath",str(root/"build/release"),
               "--workpath",str(root/"build"),"--specpath",str(root/"build"),
               "--collect-all","yt_dlp","--collect-all","imageio_ffmpeg","--collect-all","json5",
               "--hidden-import","pystray._win32",str(root/"Launcher.py")],
               cwd=root,env={**os.environ,"PYINSTALLER_CONFIG_DIR":str(root/"build/cache")},check=True)
