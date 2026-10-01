from __future__ import annotations

import base64
import html
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, TYPE_CHECKING

from .index import (
    edicion_path_next_to,
    read_index,
    read_suggestions,
    suggestions_path_next_to,
)
from .labels import read_edicion, resolve_labels
from .models import Photo, SuggestionsResult
from .photos import PhotoError, make_thumbnail

if TYPE_CHECKING:
    from .labels import LabelResolution

THUMBNAILS_PER_GROUP = 5

ORPHAN_TITLE = "Fotos sin clasificar"
FLAT_GRID_TITLE = "Todas las fotos"


@dataclass
class Group:
    """Un grupo de fotos que se muestra como una tarjeta en el visor.

    `kind` distingue los grupos: un viaje, un periodo, o el grupo de fotos que no
    cae en ninguno de los dos. `country` solo se usa para los viajes.

    `key` es la referencia con la que el usuario puede etiquetar el grupo, y es
    `None` en los grupos que el escaneo no declaro (sin clasificar y grilla plana):
    esos no son un grupo sugerido y no se pueden etiquetar.
    """

    title: str
    kind: str
    photo_count: int
    first_captured_at: Optional[str]
    last_captured_at: Optional[str]
    country: Optional[str] = None
    photos: list[Photo] = field(default_factory=list)
    key: Optional[str] = None


def labelled_title(derived: str, key: Optional[str], labels: dict[str, str]) -> str:
    """La etiqueta del usuario manda sobre el titulo derivado.

    Cuando el grupo no tiene etiqueta, o no hay archivo de edicion, gana el titulo
    que se deriva de la sugerencia.
    """
    if key is not None:
        label = labels.get(key)
        if label:
            return label
    return derived


def _group_from_trip(trip, photos: list[Photo], labels: dict[str, str]) -> Group:
    location = trip.location
    country = location.country if location is not None else None
    return Group(
        title=labelled_title(country or "Viaje", trip.first_captured_at, labels),
        kind="trip",
        photo_count=trip.photo_count,
        first_captured_at=trip.first_captured_at,
        last_captured_at=trip.last_captured_at,
        country=country,
        photos=photos,
        key=trip.first_captured_at,
    )


def _group_from_period(period, photos: list[Photo], labels: dict[str, str]) -> Group:
    # Los periodos no declaran pais por diseno: no hay nada que clasificar.
    return Group(
        title=labelled_title("Periodo", period.first_captured_at, labels),
        kind="period",
        photo_count=period.photo_count,
        first_captured_at=period.first_captured_at,
        last_captured_at=period.last_captured_at,
        photos=photos,
        key=period.first_captured_at,
    )


def _photo_sort_key(photo: Photo) -> str:
    return photo.captured_at or ""


def assign_groups(
    photos: list[Photo],
    suggestions: SuggestionsResult,
    labels: Optional[dict[str, str]] = None,
) -> list[Group]:
    """Cruza el indice de fotos con las sugerencias y devuelve los grupos.

    Cada foto cae en el viaje cuyo intervalo la contiene, o en el periodo que la
    contiene; los viajes tienen prioridad sobre los periodos porque son el grupo con
    informacion de lugar. Una foto que no cae en ninguno va al grupo de sin
    clasificar. Ninguna foto se descarta.

    Sale un grupo por cada viaje y cada periodo declarado, mas el de sin clasificar si
    hay huerfanas. Un periodo contenido dentro de un viaje se queda sin fotos propias
    porque estas van al viaje, pero el grupo sigue en la lista para que no desaparezca.

    `labels` son las etiquetas del usuario, indexadas por la fecha mas temprana del
    grupo: solo cambian el titulo de la tarjeta, no su contenido ni su orden.
    """
    labels = labels or {}
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
            groups.append(_group_from_trip(trips[index], bucket, labels))
        else:
            groups.append(_group_from_period(periods[index], bucket, labels))

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


def _label_editor(group: Group, labels: dict[str, str], token: str) -> str:
    """Controles para cambiar la etiqueta de una tarjeta.

    Solo aparece en la pagina servida. Quitar la etiqueta es una accion aparte y no
    se llega borrando el texto: el campo vacio no se puede enviar.
    """
    if group.key is None:
        return ""
    current = labels.get(group.key, "")
    remove = (
        f'<button type="button" class="label-remove">Quitar etiqueta</button>'
        if current
        else ""
    )
    return (
        '<form class="label-form"'
        f' data-key="{html.escape(group.key)}"'
        f' data-token="{html.escape(token)}">'
        f'<input class="label-input" type="text" value="{html.escape(current)}"'
        ' placeholder="Nombre del grupo" maxlength="120">'
        f'<button type="submit" class="label-save">Guardar</button>'
        f"{remove}"
        '<p class="label-error" hidden></p>'
        "</form>"
    )


def _group_card(
    group: Group, root: Path, labels: dict[str, str], token: Optional[str] = None
) -> str:
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
    editor = _label_editor(group, labels, token) if token is not None else ""
    key_attribute = f' data-key="{html.escape(group.key)}"' if group.key else ""
    return (
        f'<article class="card"{key_attribute}>'
        f'<h2>{html.escape(group.title)}</h2>'
        f'<p class="meta">{html.escape(" · ".join(meta))}</p>'
        f"{editor}"
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
.label-form { display: flex; gap: 6px; flex-wrap: wrap; margin: 0 0 10px; }
.label-input { flex: 1 1 140px; min-width: 0; font: inherit; font-size: 12px;
               padding: 5px 8px; border-radius: 6px; border: 1px solid #3c4149;
               background: #14161a; color: #e8eaed; }
.label-save, .label-remove { font: inherit; font-size: 12px; cursor: pointer;
                            padding: 5px 10px; border-radius: 6px;
                            border: 1px solid #3c4149; background: #2c3036;
                            color: #e8eaed; }
.label-remove { border-color: #5a3a3a; color: #e0b4b4; }
.label-error { flex: 1 0 100%; color: #e0b4b4; font-size: 12px; margin: 2px 0 0; }
.aviso { color: #d8c69a; font-size: 13px; margin: 0 0 12px; }
"""

# Se inyecta solo en la pagina servida. El export estatico no lo lleva: sin servidor
# no habria donde guardar, asi que es preferible que el archivo no ofrezca el control.
EDIT_SCRIPT = """
<script>
(function () {
  function mostrarError(form, mensaje) {
    var box = form.querySelector(".label-error");
    if (!box) { return; }
    box.textContent = mensaje;
    box.hidden = !mensaje;
  }

  function aplicarTitulo(card, titulo) {
    var heading = card.querySelector("h2");
    if (heading) { heading.textContent = titulo; }
  }

  function alternarBotonQuitar(form, visible) {
    var boton = form.querySelector(".label-remove");
    if (!boton) { return; }
    boton.hidden = !visible;
  }

  function enviar(form, body, card, titulo) {
    var boton = form.querySelector(".label-save");
    if (boton) { boton.disabled = true; }
    fetch("/api/labels", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Fotos-Plus-Token": form.getAttribute("data-token")
      },
      body: JSON.stringify(body)
    }).then(function (respuesta) {
      return respuesta.json().then(function (datos) {
        return { ok: respuesta.ok, datos: datos };
      });
    }).then(function (resultado) {
      if (resultado.ok) {
        mostrarError(form, "");
        aplicarTitulo(card, titulo);
        alternarBotonQuitar(form, body.action !== "remove");
      } else {
        mostrarError(form, resultado.datos.error || "No se pudo guardar");
      }
    }).catch(function () {
      mostrarError(form, "No se pudo hablar con el servidor local");
    }).then(function () {
      if (boton) { boton.disabled = false; }
    });
  }

  document.querySelectorAll(".label-form").forEach(function (form) {
    var card = form.closest(".card");
    var campo = form.querySelector(".label-input");
    var key = form.getAttribute("data-key");
    var tituloOriginal = card ? card.querySelector("h2").textContent : "";

    form.addEventListener("submit", function (evento) {
      evento.preventDefault();
      var texto = campo.value.trim();
      // Una etiqueta vacia no se envia: quitarla es una accion aparte.
      if (!texto) {
        mostrarError(form, "Una etiqueta no puede estar vacia");
        return;
      }
      mostrarError(form, "");
      enviar(
        form,
        { action: "set", key: key, text: texto, token: form.getAttribute("data-token") },
        card,
        texto
      );
    });

    var quitar = form.querySelector(".label-remove");
    if (quitar) {
      quitar.addEventListener("click", function () {
        mostrarError(form, "");
        enviar(
          form,
          { action: "remove", key: key, token: form.getAttribute("data-token") },
          card,
          tituloOriginal
        );
      });
    }
  });
})();
</script>
"""


def _drift_notice(drift: Optional["LabelResolution"]) -> str:
    """Aviso de que el escaneo se movio y algunas etiquetas quedaron sin grupo."""
    if drift is None or not drift.drifted:
        return ""
    parts: list[str] = []
    if drift.scan_advanced:
        parts.append("El escaneo se rehizo despues de escribir las etiquetas.")
    if drift.dangling_count:
        total = drift.resolved_count + drift.dangling_count
        parts.append(
            f"{drift.dangling_count} de {total} etiquetas ya no corresponden a "
            "ningun grupo. Siguen guardadas."
        )
    return f'<p class="aviso">{" ".join(parts)}</p>'


def render_html(
    groups: list[Group],
    root: str,
    flat: bool = False,
    labels: Optional[dict[str, str]] = None,
    token: Optional[str] = None,
    drift: Optional["LabelResolution"] = None,
) -> str:
    """Genera el documento del visor.

    Sin `token` el documento es de solo lectura: muestra las etiquetas vigentes pero no
    ofrece ningun control para cambiarlas, porque sin servidor no habria donde
    guardarlas. Con `token` la pagina viene con los controles de edicion.
    """
    labels = labels or {}
    editable = token is not None

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
        body = "".join(
            _group_card(group, Path(root), labels, token) for group in groups
        )
        title = "Viajes y periodos sugeridos"
        subtitle = "sugerencias sin confirmar: no son definitivas"

    mode = "editable" if editable else "solo-lectura"
    if editable:
        notices = f"{subtitle} · servido desde el equipo, las etiquetas se guardan solas"
    elif flat:
        notices = subtitle
    else:
        # El modo de solo lectura tiene que notarse leyendo la pagina, no solo
        # mirando el atributo del body: sin servidor no se puede cambiar nada.
        notices = f"{subtitle} · solo lectura: para cambiar los nombres, usa view --serve"
    script = EDIT_SCRIPT if editable else ""

    return (
        "<!doctype html>\n"
        '<html lang="es">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{html.escape(title)}</title>\n"
        f"<style>{CSS}</style>\n"
        "</head>\n"
        f'<body data-mode="{mode}">\n'
        f"<h1>{html.escape(title)}</h1>\n"
        f'<p class="notice">{html.escape(notices)}</p>\n'
        f"{_drift_notice(drift)}"
        f'<div class="grid">{body}</div>\n'
        '<script type="application/json" id="viewer-data">'
        f"{json.dumps(_payload(groups, root, flat), ensure_ascii=False)}"
        "</script>\n"
        f"{script}"
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

    # El archivo de edicion se lee para pintar los titulos, pero el HTML exportado
    # sigue siendo de solo lectura: se genera sin token, asi que no trae controles ni
    # forma de escribir nada. El archivo de edicion no se crea aqui.
    overlay = read_edicion(edicion_path_next_to(index_path))
    resolution = resolve_labels(overlay, suggestions)

    groups = assign_groups(result.photos, suggestions, labels=resolution.labels)
    return (
        render_html(
            groups,
            root,
            flat=False,
            labels=resolution.labels,
            token=None,
            drift=resolution,
        ),
        False,
    )
