import re
from decimal import Decimal

from .catalog import DownloadError, Episode


def select_episodes(expression: str, episodes: list[Episode]) -> list[Episode]:
    """Filtra capítulos publicados sin expandir rangos potencialmente enormes."""
    selected = set()
    for part in expression.split(","):
        match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*(?:-\s*(\d+(?:\.\d+)?))?\s*", part)
        if not match:
            raise DownloadError("Usa capítulos o rangos como 1-12,15,20-30.")
        first, last = match.groups()
        lower, upper = Decimal(first), Decimal(last or first)
        if lower > upper:
            raise DownloadError(f"El rango {part.strip()} está invertido.")
        matches = [e.number for e in episodes if lower <= Decimal(e.number) <= upper]
        if not matches:
            raise DownloadError(f"No hay capítulos publicados para {part.strip()}.")
        selected.update(matches)
    return sorted((e for e in episodes if e.number in selected), key=lambda e: Decimal(e.number))
