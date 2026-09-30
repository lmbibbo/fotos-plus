from __future__ import annotations

import base64
import html
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .index import read_index, read_suggestions, suggestions_path_next_to
from .models import Photo, SuggestionsResult
from .photos import PhotoError, make_thumbnail

THUMBNAILS_PER_GROUP = 5

ORPHAN_TITLE = "Fotos sin clasificar"
FLAT_GRID_TITLE = "Todas las fotos"


@dataclass
class Group:
    """Un grupo de fotos que se muestra como una tarjeta en el visor.

    `kind` distingue los grupos: un viaje, un periodo, o el grupo de fotos que no
    cae en ninguno de los dos. `country` solo se usa para los viajes.
    """

    title: str
    kind: str
    photo_count: int
    first_captured_at: Optional[str]
    last_captured_at: Optional[str]
    country: Optional[str] = None
    photos: list[Photo] = field(default_factory=list)


def _group_from_trip(trip, photos: list[Photo]) -> Group:
    location = trip.location
    country = location.country if location is not None else None
    return Group(
        title=country or "Viaje",
        kind="trip",
        photo_count=trip.photo_count,
        first_captured_at=trip.first_captured_at,
        last_captured_at=trip.last_captured_at,
        country=country,
        photos=photos,
    )


def _group_from_period(period, photos: list[Photo]) -> Group:
    # Los periodos no declaran pais por diseno: no hay nada que clasificar.
    return Group(
        title="Periodo",
        kind="period",
        photo_count=period.photo_count,
        first_captured_at=period.first_captured_at,
        last_captured_at=period.last_captured_at,
        photos=photos,
    )


def _photo_sort_key(photo: Photo) -> str:
    return photo.captured_at or ""


def assign_groups(
    photos: list[Photo], suggestions: SuggestionsResult
) -> list[Group]:
    """Cruza el indice de fotos con las sugerencias y devuelve los grupos.

    Cada foto cae en el viaje cuyo intervalo la contiene, o en el periodo que la
    contiene; los viajes tienen prioridad sobre los periodos porque son el grupo con
    informacion de lugar. Una foto que no cae en ninguno va al grupo de sin
    clasificar. Ninguna foto se descarta.

    Sale un grupo por cada viaje y cada periodo declarado, mas el de sin clasificar si
    hay huerfanas. Un periodo contenido dentro de un viaje se queda sin fotos propias
    porque estas van al viaje, pero el grupo sigue en la lista para que no desaparezca.
    """
    ordered = sorted(photos, key=_photo_sort_key)

    trips = sorted(suggestions.trips, key=lambda t: t.first_captured_at)
    periods = sorted(suggestions.periods, key=lambda p: p.first_captured_at)

    buckets: dict[tuple[str, int], list[Photo]] = {}
    orphans: list[Photo] = []

    # Se crea un grupo por cada viaje y periodo declarado, aunque se quede sin fotos:
    # si un periodo cae dentro de un viaje, sus fotos van al viaje y el periodo se
    # veria con cero fotos. La tarjeta sigue saliendo, para que no desaparezca en
    # silencio algo que el usuario declaro en su biblioteca.
    for index in range(len(trips)):
        buckets[("trip", index)] = []
    for index in range(len(periods)):
        buckets[("period", index)] = []

    for photo in ordered:
        stamp = photo.captured_at
        if stamp is None:
            orphans.append(photo)
            continue

        for index, trip in enumerate(trips):
            if trip.first_captured_at <= stamp <= trip.last_captured_at:
                buckets.setdefault(("trip", index), []).append(photo)
                break
        else:
            for index, period in enumerate(periods):
                if period.first_captured_at <= stamp <= period.last_captured_at:
                    buckets.setdefault(("period", index), []).append(photo)
                    break
            else:
                orphans.append(photo)

    groups: list[Group] = []
    for (kind, index), bucket in buckets.items():
        if kind == "trip":
            groups.append(_group_from_trip(trips[index], bucket))
        else:
            groups.append(_group_from_period(periods[index], bucket))

    if orphans:
        first = min(
            (p.captured_at for p in orphans if p.captured_at),
            default=None,
        )
        last = max(
            (p.captured_at for p in orphans if p.captured_at),
            default=None,
        )
        groups.append(
            Group(
                title=ORPHAN_TITLE,
                kind="orphan",
                photo_count=len(orphans),
                first_captured_at=first,
                last_captured_at=last,
                photos=orphans,
            )
        )

    groups.sort(key=lambda g: g.first_captured_at or "")
    return groups


def _thumbnail_b64(photo: Photo, root: Path) -> Optional[str]:
    path = Path(root) / Path(photo.relative_path)
    try:
        data = make_thumbnail(path)
    except PhotoError:
        return None
    return base64.b64encode(data).decode("ascii")


def _group_thumbs(group: Group, root: Path) -> list[str]:
    thumbs: list[str] = []
    for photo in group.photos:
        if len(thumbs) >= THUMBNAILS_PER_GROUP:
            break
        encoded = _thumbnail_b64(photo, root)
        if encoded is not None:
            thumbs.append(encoded)
    return thumbs


def _photo_card(b64: str, alt: str) -> str:
    return (
        f'<img class="thumb" src="data:image/jpeg;base64,{b64}" alt="{html.escape(alt)}">'
    )


def _group_card(group: Group, root: Path) -> str:
    # Se muestra la cantidad de fotos que tiene el grupo de verdad, no el `photo_count`
    # de la sugerencia: ese numero cuenta solo las fotos con posicion, asi que queda
    # muy por debajo del total y haria pensar que faltan fotos.
    meta: list[str] = [f"{len(group.photos)} fotos"]
    if group.first_captured_at and group.last_captured_at:
        start = group.first_captured_at[:10]
        end = group.last_captured_at[:10]
        if start == end:
            meta.append(start)
        else:
            meta.append(f"{start} – {end}")
    if group.country:
        meta.append(group.country)

    thumbs = "".join(
        _photo_card(b64, group.title) for b64 in _group_thumbs(group, root)
    )
    if not thumbs:
        # Grupo declarado que se quedo sin fotos, normalmente porque cae dentro de
        # un viaje. Se avisa para que no parezca que falta el grupo.
        thumbs = '<p class="vacio">Sin fotos propias: caen en otro grupo.</p>'
    return (
        '<article class="card">'
        f'<h2>{html.escape(group.title)}</h2>'
        f'<p class="meta">{html.escape(" · ".join(meta))}</p>'
        f'<div class="thumbs">{thumbs}</div>'
        "</article>"
    )


def _flat_card(photo: Photo, root: Path) -> str:
    encoded = _thumbnail_b64(photo, root)
    if encoded is None:
        return ""
    stamp = (photo.captured_at or "")[:10]
    return (
        '<article class="card flat">'
        f"{_photo_card(encoded, photo.name)}"
        f'<p class="meta">{html.escape(stamp)}</p>'
        "</article>"
    )


CSS = """
:root { color-scheme: dark; }
body { margin: 0; padding: 24px; background: #14161a; color: #e8eaed;
       font-family: system-ui, -apple-system, "Segoe UI", sans-serif; }
h1 { font-size: 20px; margin: 0 0 4px; }
.notice { color: #9aa0a6; font-size: 13px; margin: 0 0 24px; }
.grid { display: grid; gap: 16px;
        grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); }
.card { background: #1e2126; border: 1px solid #2c3036; border-radius: 10px;
        padding: 14px; }
.card.flat { padding: 8px; }
.card h2 { font-size: 15px; margin: 0 0 4px; }
.meta { color: #9aa0a6; font-size: 12px; margin: 0 0 10px; }
.thumbs { display: grid; gap: 6px;
          grid-template-columns: repeat(5, 1fr); }
.vacio { grid-column: 1 / -1; color: #9aa0a6; font-size: 12px; margin: 0; }
.card.flat .thumb { width: 100%; height: auto; display: block; }
.thumb { width: 100%; height: auto; display: block; border-radius: 4px;
         background: #2c3036; }
"""


def render_html(groups: list[Group], root: str, flat: bool = False) -> str:
    if flat:
        body = "".join(
            _flat_card(photo, Path(root))
            for photo in sorted(
                (p for g in groups for p in g.photos), key=_photo_sort_key
            )
        )
        title = FLAT_GRID_TITLE
        subtitle = "sin archivo de sugerencias: se muestran todas las fotos sin agrupar"
    else:
        body = "".join(_group_card(group, Path(root)) for group in groups)
        title = "Viajes y periodos sugeridos"
        subtitle = "sugerencias sin confirmar: no son definitivas"

    return (
        "<!doctype html>\n"
        '<html lang="es">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{html.escape(title)}</title>\n"
        f"<style>{CSS}</style>\n"
        "</head>\n"
        "<body>\n"
        f"<h1>{html.escape(title)}</h1>\n"
        f'<p class="notice">{html.escape(subtitle)}</p>\n'
        f'<div class="grid">{body}</div>\n'
        '<script type="application/json" id="viewer-data">'
        f"{json.dumps(_payload(groups, root, flat), ensure_ascii=False)}"
        "</script>\n"
        "</body>\n"
        "</html>\n"
    )


def _payload(groups: list[Group], root: str, flat: bool) -> dict:
    return {
        "flat": flat,
        "groups": [
            {
                "title": group.title,
                "kind": group.kind,
                "photo_count": group.photo_count,
                "first_captured_at": group.first_captured_at,
                "last_captured_at": group.last_captured_at,
                "country": group.country,
            }
            for group in groups
        ],
    }


def build_view(index_path: Path) -> tuple[str, bool]:
    """Devuelve el HTML del visor y si se genero en modo grid plano."""
    index_path = Path(index_path)
    result = read_index(index_path)
    root = result.root

    suggestions_path = suggestions_path_next_to(index_path)
    if not suggestions_path.is_file():
        groups = [
            Group(
                title=FLAT_GRID_TITLE,
                kind="flat",
                photo_count=len(result.photos),
                first_captured_at=None,
                last_captured_at=None,
                photos=list(result.photos),
            )
        ]
        return render_html(groups, root, flat=True), True

    suggestions = read_suggestions(suggestions_path)
    groups = assign_groups(result.photos, suggestions)
    return render_html(groups, root, flat=False), False
