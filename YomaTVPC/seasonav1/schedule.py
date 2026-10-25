from __future__ import annotations

import html
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from .engine.catalog import DownloadError, ORIGIN, PageParser, literal_property

SCHEDULE_URL = ORIGIN + "/horario"


class StructureChanged(DownloadError):
    pass


@dataclass
class ScheduledAnime:
    slug: str
    title: str
    weekday: int
    latest: str
    published: str
    start_date: str | None = None

    @property
    def url(self):
        return ORIGIN + "/media/" + self.slug


def parse_schedule(source, timezone=None):
    parser = PageParser()
    parser.feed(source)
    state = next((s for s in parser.scripts if "kit.start(" in s and "data:" in s), "")
    try:
        media = literal_property(state, "media")
    except (DownloadError, ValueError) as exc:
        raise StructureChanged("AnimeAV1 cambió la estructura del horario o entregó una página de verificación.") from exc
    if not isinstance(media, list) or not media:
        raise StructureChanged("El horario no contiene la lista esperada de animes. No se inició ninguna descarga; revisa el sitio o actualiza YomaTV.")
    result = {}
    for item in media:
        if not isinstance(item, dict) or not item.get("latestEpisode"):
            continue
        try:
            slug, title = item["slug"], item["title"]
            latest = item["latestEpisode"]
            number, published = str(latest["number"]), latest["createdAt"]
            if not re.fullmatch(r"[a-zA-Z0-9_-]+", slug) or not re.fullmatch(r"\d+(?:\.\d+)?", number) or not isinstance(title, str):
                raise ValueError("campos inválidos")
            moment = datetime.fromisoformat(published.replace("Z", "+00:00"))
            if moment.tzinfo is None:
                raise ValueError("publicación sin zona horaria")
            # Mismo criterio del horario web: última publicación en hora local.
            weekday = moment.astimezone(timezone).isoweekday()
            result[slug] = ScheduledAnime(slug, html.unescape(title), weekday, number, published, item.get("startDate"))
        except (KeyError, ValueError, TypeError, AttributeError) as exc:
            raise StructureChanged("Una entrada del horario cambió de formato; se detuvo la revisión para evitar descargas equivocadas.") from exc
    if not result:
        raise StructureChanged("El horario no tiene publicaciones utilizables.")
    return sorted(result.values(), key=lambda a: (a.weekday, a.title.casefold()))


def due_date(now: datetime, review_time: str) -> date:
    hour, minute = map(int, review_time.split(":"))
    return now.date() if (now.hour, now.minute) >= (hour, minute) else now.date() - timedelta(days=1)


def missed_weekdays(previous: str | None, target: date) -> set[int]:
    if not previous:
        return set(range(1, 8))
    previous_date = date.fromisoformat(previous)
    days = (target - previous_date).days
    return { (previous_date + timedelta(days=i)).isoweekday() for i in range(1, min(7, max(0, days)) + 1) }


def work_due(database,cfg,now):
    interrupted=database.query("SELECT id FROM episodes WHERE status IN ('downloading','verifying') LIMIT 1")
    if not cfg.schedule_enabled:
        return bool(database.pending()) or bool(interrupted)
    return (not database.meta("initialized",False) or
            database.meta("last_review","")<str(due_date(now,cfg.review_time)) or
            bool(database.pending()) or bool(interrupted) or bool(database.meta("scan_failures",[])))
