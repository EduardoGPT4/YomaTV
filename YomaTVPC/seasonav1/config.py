from __future__ import annotations

import os
import re
import sys
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path

from .engine.storage import read_json, write_json

ROOT = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent
ASSETS = Path(__file__).resolve().parent.parent / "assets"
DAYS = ("Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo")


def data_dir():
    return Path(os.environ.get("ANIMEAV1_DATA_DIR", os.environ.get("SEASONAV1_DATA_DIR", str(ROOT / "datos")))).resolve()


def season_folder(day: date) -> str:
    return ("invierno", "primavera", "verano", "otoño")[(day.month - 1) // 3] + str(day.year)


@dataclass
class Config:
    destination: str = str(ROOT / "descargas")
    review_time: str = "12:00"
    language: str = "SUB"
    language_fallback: str = "wait"
    server: str = "MP4Upload"
    server_fallback: str = "wait"
    height: int = 1080
    quality_fallback: str = "best"
    workers: int = 1
    speed_kib: int = 0
    request_interval: float = 2
    selection: str = "all"
    favorites: list[str] = field(default_factory=list)
    exclusions: list[str] = field(default_factory=list)
    season_source: str = "current"
    long_series: str = "keep"
    autostart: bool = True
    notifications: bool = True
    resident_tray: bool = True
    paused: bool = False
    configured: bool = False
    schedule_enabled: bool = True

    def validate(self):
        if not isinstance(self.review_time, str) or not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", self.review_time):
            raise ValueError("La hora debe escribirse como HH:MM, por ejemplo 12:00.")
        if not self.destination or not isinstance(self.destination, str):
            raise ValueError("Elige una carpeta de destino.")
        choices = {"language": {"SUB", "LAT", "DUB"}, "language_fallback": {"wait", "SUB"},
                   "server": {"MP4Upload", "Voe"}, "server_fallback": {"wait", "other"},
                   "quality_fallback": {"best", "lower", "wait"}, "selection": {"all", "favorites"},
                   "season_source": {"current", "premiere"}, "long_series": {"keep", "split"}}
        for name, values in choices.items():
            if getattr(self, name) not in values:
                raise ValueError(f"Opción inválida: {name}.")
        if self.height not in (720, 1080) or not 1 <= self.workers <= 4 or not 0 <= self.speed_kib <= 1_000_000:
            raise ValueError("Usa 720/1080p, de 1 a 4 descargas y un límite de velocidad válido.")
        if not 1 <= self.request_interval <= 60:
            raise ValueError("La pausa entre peticiones debe ser de 1 a 60 segundos.")
        for entries in (self.favorites, self.exclusions):
            if not isinstance(entries, list) or not all(isinstance(s, str) and re.fullmatch(r"[\w-]+", s) for s in entries):
                raise ValueError("Las listas de animes deben contener sus identificadores del enlace.")
        if type(self.schedule_enabled) is not bool:
            raise ValueError("La automatización de temporada debe estar activada o desactivada.")
        self.destination = str(Path(self.destination).expanduser().resolve())
        return self

    def accepts(self, slug):
        return slug not in self.exclusions and (self.selection == "all" or slug in self.favorites)

    @classmethod
    def load(cls, directory=None):
        value = read_json((directory or data_dir()) / "config.json", {"schedule_enabled": False})
        if not isinstance(value, dict):
            raise ValueError("config.json tiene un formato inválido.")
        allowed = cls.__dataclass_fields__
        return cls(**{k: v for k, v in value.items() if k in allowed}).validate()

    def save(self, directory=None):
        self.validate()
        write_json((directory or data_dir()) / "config.json", asdict(self))
