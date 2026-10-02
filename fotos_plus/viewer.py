from __future__ import annotations

import base64
import html
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional, Sequence, TYPE_CHECKING

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

    `tag` es el tag que el usuario le asigno. No cambia el contenido de la tarjeta ni su
    rango de fechas: solo decide en que seccion aparece.
    """

    title: str
    kind: str
    photo_count: int
    first_captured_at: Optional[str]
    last_captured_at: Optional[str]
    country: Optional[str] = None
    photos: list[Photo] = field(default_factory=list)
    key: Optional[str] = None
    tag: Optional[str] = None

    @property
    def browse_key(self) -> str:
        """La referencia con la que el visor pide la lista de fotos de este grupo.

        Casi todos los grupos ya traen su propia clave, pero el de las fotos sin
        clasificar no la tiene: el escaneo no declaro ningun viaje ni periodo del que
        sacarla. Ese grupo tambien se puede recorrer, asi que recibe una referencia
        reservada, que no choca con ninguna clave real porque las de los grupos
        sugeridos son marcas de tiempo.
        """
        return self.key if self.key is not None else UNCLASSIFIED_GROUP_KEY


UNTAGGED_SECTION_TITLE = "Sin tag"
TAG_CATALOG_ID = "tag-catalog"
UNCLASSIFIED_GROUP_KEY = "sin-clasificar"
PHOTO_BROWSER_ID = "photo-browser"


@dataclass
class Section:
    """Un conjunto de tarjetas que comparten tag, y el encabezado que las agrupa."""

    tag: Optional[str]
    title: str
    groups: list[Group]

    @property
    def count(self) -> int:
        return len(self.groups)


def _section_date(section: Section) -> str:
    """La fecha mas temprana de la seccion, que es la que le da el orden."""
    return min(group.first_captured_at or "" for group in section.groups)


def group_sections(groups: list[Group]) -> list[Section]:
    """Reparte las tarjetas en secciones, una por tag, y devuelve la lista de secciones.

    Devuelve una lista vacia cuando ningun grupo tiene tag: en ese caso el visor sigue
    mostrando las tarjetas en una unica lista ordenada por fecha, como antes de que
    existieran los tags. Un tag del catalogo sin ningun grupo asignado no produce seccion,
    porque las secciones se arman desde los grupos que hay, no desde el catalogo.

    Las secciones con tag van ordenadas por la fecha mas temprana de su primer grupo, y
    la de los grupos sin tag va al final.
    """
    if not any(group.tag for group in groups):
        return []

    buckets: dict[Optional[str], list[Group]] = {}
    for group in groups:
        buckets.setdefault(group.tag, []).append(group)

    sections = [
        Section(tag=tag, title=tag or UNTAGGED_SECTION_TITLE, groups=buckets[tag])
        for tag in buckets
        if tag is not None
    ]
    sections.sort(key=_section_date)

    untagged = buckets.get(None)
    if untagged:
        sections.append(
            Section(tag=None, title=UNTAGGED_SECTION_TITLE, groups=untagged)
        )
    return sections


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


def _group_from_trip(
    trip, photos: list[Photo], labels: dict[str, str], tags: dict[str, str]
) -> Group:
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
        tag=tags.get(trip.first_captured_at),
    )


def _group_from_period(
    period, photos: list[Photo], labels: dict[str, str], tags: dict[str, str]
) -> Group:
    # Los periodos no declaran pais por diseno: no hay nada que clasificar.
    return Group(
        title=labelled_title("Periodo", period.first_captured_at, labels),
        kind="period",
        photo_count=period.photo_count,
        first_captured_at=period.first_captured_at,
        last_captured_at=period.last_captured_at,
        photos=photos,
        key=period.first_captured_at,
        tag=tags.get(period.first_captured_at),
    )


def _photo_sort_key(photo: Photo) -> str:
    return photo.captured_at or ""


def assign_groups(
    photos: list[Photo],
    suggestions: SuggestionsResult,
    labels: Optional[dict[str, str]] = None,
    tags: Optional[dict[str, str]] = None,
) -> list[Group]:
    """Cruza el indice de fotos con las sugerencias y devuelve los grupos.

    Cada foto cae en el viaje cuyo intervalo la contiene, o en el periodo que la
    contiene; los viajes tienen prioridad sobre los periodos porque son el grupo con
    informacion de lugar. Una foto que no cae en ninguno va al grupo de sin
    clasificar. Ninguna foto se descarta.

    Sale un grupo por cada viaje y cada periodo declarado, mas el de sin clasificar si
    hay huerfanas. Un periodo contenido dentro de un viaje se queda sin fotos propias
    porque estas van al viaje, pero el grupo sigue en la lista para que no desaparezca.

    `labels` son las etiquetas del usuario y `tags` sus tags, ambos indexados por la
    fecha mas temprana del grupo. Las etiquetas cambian el titulo de la tarjeta y los
    tags la seccion en la que aparece: ninguno de los dos toca el contenido de la
    tarjeta ni el orden en que se agrupan las fotos.
    """
    labels = labels or {}
    tags = tags or {}
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
            groups.append(_group_from_trip(trips[index], bucket, labels, tags))
        else:
            groups.append(_group_from_period(periods[index], bucket, labels, tags))

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


def _label_editor(
    group: Group, labels: dict[str, str], token: str, tag_options: Sequence[str] = ()
) -> str:
    """Controles para cambiar la etiqueta y el tag de una tarjeta.

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
    tag_control = _tag_editor(group, token, tag_options)
    return (
        '<form class="label-form"'
        f' data-key="{html.escape(group.key)}"'
        f' data-token="{html.escape(token)}">'
        f'<input class="label-input" type="text" value="{html.escape(current)}"'
        ' placeholder="Nombre del grupo" maxlength="120">'
        f'<button type="submit" class="label-save">Guardar etiqueta</button>'
        f"{remove}"
        f"{tag_control}"
        '<p class="label-error" hidden></p>'
        "</form>"
    )


def _tag_editor(
    group: Group, token: str, tag_options: Sequence[str] = ()
) -> str:
    """Selector de tag, con opcion de escribir uno nuevo y de quitar el actual.

    El `datalist` es uno solo en todo el documento, asi que no se emite aca: el input
    apunta a el por id. Un tag vigente que ya no esta en el catalogo se agrega igual a
    `tag_options`, para que un tag al que ya no se le asigno ningun grupo siga pudiendo
    elegirse.
    """
    if group.key is None:
        return ""
    current = group.tag or ""
    remove = (
        f'<button type="button" class="tag-remove">Quitar tag</button>' if current else ""
    )
    return (
        '<div class="tag-controls"'
        f' data-key="{html.escape(group.key)}"'
        f' data-token="{html.escape(token)}">'
        f'<input class="tag-input" type="text" list="{TAG_CATALOG_ID}"'
        f' value="{html.escape(current)}"'
        ' placeholder="Tag" maxlength="60">'
        f'<button type="button" class="tag-save">Guardar tag</button>'
        f"{remove}"
        '<p class="tag-error" hidden></p>'
        "</div>"
    )


def _tag_catalog(tag_options: Sequence[str], groups: Sequence[Group]) -> str:
    """El `datalist` unico con los nombres que el selector ofrece.

    Reune el catalogo y los tags que tienen alguna tarjeta, para que ninguno de los dos
    quede fuera por el hecho de que el otro no lo liste.
    """
    vigente = [group.tag for group in groups if group.tag]
    names = list(dict.fromkeys([*tag_options, *vigente]))
    if not names:
        return ""
    options = "".join(
        f'<option value="{html.escape(name)}"></option>' for name in names
    )
    return f'<datalist id="{TAG_CATALOG_ID}">{options}</datalist>'


def _group_card(
    group: Group,
    root: Path,
    labels: dict[str, str],
    token: Optional[str] = None,
    tag_options: Sequence[str] = (),
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
    editor = (
        _label_editor(group, labels, token, tag_options) if token is not None else ""
    )
    key_attribute = f' data-key="{html.escape(group.key)}"' if group.key else ""
    # El recorrido solo se ofrece si hay algo que recorrer. Un grupo declarado que se
    # quedo sin fotos propias no tendria nada que mostrar, asi que no recibe el boton.
    browse = ""
    if token is not None and group.photos:
        browse = (
            f'<button type="button" class="browse-open"'
            f' data-browse-key="{html.escape(group.browse_key)}">Ver fotos</button>'
        )
    # El tag viaja en la tarjeta para que el arrastre pueda leer el destino sin
    # preguntar al servidor. Vacio significa que el grupo no tiene tag.
    tag_attribute = f' data-tag="{html.escape(group.tag)}"' if group.tag else ' data-tag=""'
    return (
        f'<article class="card"{key_attribute}{tag_attribute}>'
        f'<h2>{html.escape(group.title)}</h2>'
        f'<p class="meta">{html.escape(" · ".join(meta))}</p>'
        f"{browse}"
        f"{editor}"
        f'<div class="thumbs">{thumbs}</div>'
        "</article>"
    )


def _browser_overlay(token: Optional[str] = None) -> str:
    """El recorrido de fotos a pantalla completa, oculto hasta que se abre.

    Es una sola pieza en el documento, no una por grupo: abrir un grupo la llena con la
    lista que pide el servidor, asi que no hay nada que preparar antes. Se emite solo
    cuando hay token, porque sin servidor no hay renders que pedir.
    """
    if token is None:
        return ""
    return (
        f'<div class="browser" id="{PHOTO_BROWSER_ID}" data-token="{html.escape(token)}" hidden>'
        '<div class="browser-bar">'
        f'<p class="browser-title" id="{PHOTO_BROWSER_ID}-group"></p>'
        f'<p class="browser-position" id="{PHOTO_BROWSER_ID}-position"></p>'
        f'<button type="button" class="browser-close" id="{PHOTO_BROWSER_ID}-close">'
        "Cerrar</button>"
        "</div>"
        f'<img class="browser-image" id="{PHOTO_BROWSER_ID}-image" alt="">'
        f'<p class="browser-status" id="{PHOTO_BROWSER_ID}-status"></p>'
        '<div class="browser-actions">'
        f'<button type="button" class="browser-prev" id="{PHOTO_BROWSER_ID}-prev">'
        "Anterior</button>"
        f'<button type="button" class="browser-mark" id="{PHOTO_BROWSER_ID}-mark">'
        "Marcar</button>"
        f'<button type="button" class="browser-next" id="{PHOTO_BROWSER_ID}-next">'
        "Siguiente</button>"
        "</div>"
        "</div>"
    )


def _section_html(
    section: Section,
    root: Path,
    labels: dict[str, str],
    token: Optional[str] = None,
    tag_options: Sequence[str] = (),
) -> str:
    """Una seccion de tarjetas que comparten tag.

    El encabezado es tambien zona de destino: soltar una tarjeta ahi le asigna el tag de
    la seccion. La de "Sin tag" lleva el atributo vacio, que es lo que hace que soltar
    ahi le quite el tag en lugar de asignarle una cadena vacia.
    """
    drop = html.escape(section.tag or "")
    cards = "".join(
        _group_card(group, root, labels, token, tag_options) for group in section.groups
    )
    plural = "grupo" if section.count == 1 else "grupos"
    return (
        f'<section class="tag-section" data-drop="{drop}">'
        f'<h2 class="tag-section-title">{html.escape(section.title)}'
        f'<span class="tag-section-count">{section.count} {plural}</span></h2>'
        f'<div class="grid">{cards}</div>'
        "</section>"
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
.tag-section { margin: 0 0 28px; border-radius: 10px; }
.tag-section-title { font-size: 14px; margin: 0 0 10px; color: #c8ccd2;
                     display: flex; align-items: baseline; gap: 8px; }
.tag-section-count { font-size: 12px; color: #9aa0a6; font-weight: normal; }
.tag-controls { display: flex; gap: 6px; flex-wrap: wrap; margin: 0 0 10px; }
.tag-input { flex: 1 1 110px; min-width: 0; font: inherit; font-size: 12px;
             padding: 5px 8px; border-radius: 6px; border: 1px solid #3c4149;
             background: #14161a; color: #e8eaed; }
.tag-save, .tag-remove { font: inherit; font-size: 12px; cursor: pointer;
                         padding: 5px 10px; border-radius: 6px;
                         border: 1px solid #3c4149; background: #2c3036;
                         color: #e8eaed; }
.tag-remove { border-color: #5a3a3a; color: #e0b4b4; }
.tag-error { flex: 1 0 100%; color: #e0b4b4; font-size: 12px; margin: 2px 0 0; }
.card[draggable="true"] { cursor: grab; }
.card.destino, .tag-section.destino { outline: 2px dashed #6f8fbf; outline-offset: 3px; }
.browse-open { font: inherit; font-size: 12px; cursor: pointer; margin: 0 0 8px;
               padding: 5px 10px; border-radius: 6px; border: 1px solid #3c4149;
               background: #2c3036; color: #e8eaed; }
.browse-open:hover { background: #363b42; }
.browser { position: fixed; inset: 0; z-index: 50; display: flex;
           flex-direction: column; align-items: center; gap: 12px; padding: 16px;
           background: #0b0c0e; color: #e8eaed; }
.browser[hidden] { display: none; }
.browser-bar { display: flex; align-items: center; gap: 12px; width: 100%;
               max-width: 1100px; }
.browser-title { margin: 0; font-size: 14px; }
.browser-position { margin: 0 auto 0 0; font-size: 13px; color: #9aa3ad; }
.browser-image { max-width: 100%; max-height: 78vh; object-fit: contain;
                 background: #000; }
.browser-status { margin: 0; min-height: 1em; font-size: 12px; color: #9aa3ad; }
.browser-actions { display: flex; gap: 10px; }
.browser-actions button, .browser-close { font: inherit; font-size: 13px;
             cursor: pointer; padding: 7px 14px; border-radius: 6px;
             border: 1px solid #3c4149; background: #2c3036; color: #e8eaed; }
.browser-mark[aria-pressed="true"] { background: #3c6e47; border-color: #4f8a5d; }
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

  // --- Tags: selector y arrastre ---
  //
  // Un solo manejador cubre los tres gestos: soltar sobre una seccion, sobre una
  // tarjeta o sobre "Sin tag". Todos se resuelven leyendo el `data-tag` del destino,
  // y un destino sin tag produce `clear_tag` en lugar de una asignacion vacia.

  function mostrarErrorTag(control, mensaje) {
    var box = control.querySelector(".tag-error");
    if (!box) { return; }
    box.textContent = mensaje;
    box.hidden = !mensaje;
  }

  function postTag(control, body) {
    var boton = control.querySelector(".tag-save");
    if (boton) { boton.disabled = true; }
    return fetch("/api/labels", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Fotos-Plus-Token": control.getAttribute("data-token")
      },
      body: JSON.stringify(body)
    }).then(function (respuesta) {
      return respuesta.json().then(function (resultado) {
        return { ok: respuesta.ok, datos: resultado };
      });
    }).then(function (resultado) {
      if (!resultado.ok) {
        throw new Error(resultado.datos.error || "No se pudo guardar el tag");
      }
      // La seccion reordena las tarjetas, asi que se vuelve a pedir la pagina
      // completa en lugar de mover nodos a mano.
      window.location.reload();
    });
  }

  document.querySelectorAll(".tag-controls").forEach(function (control) {
    var card = control.closest(".card");
    var campo = control.querySelector(".tag-input");
    var boton = control.querySelector(".tag-save");
    var quitar = control.querySelector(".tag-remove");
    var key = control.getAttribute("data-key");
    var token = control.getAttribute("data-token");

    function guardar() {
      var texto = campo.value.trim();
      // Un tag vacio no se envia: quitarlo es una accion aparte.
      if (!texto) {
        mostrarErrorTag(control, "Un tag no puede estar vacio");
        return;
      }
      mostrarErrorTag(control, "");
      postTag(control, { action: "set_tag", key: key, tag: texto, token: token })
        .catch(function (error) {
          mostrarErrorTag(control, error.message);
          if (boton) { boton.disabled = false; }
        });
    }

    if (boton) { boton.addEventListener("click", guardar); }

    if (quitar) {
      quitar.addEventListener("click", function () {
        mostrarErrorTag(control, "");
        postTag(control, { action: "clear_tag", key: key, token: token })
          .catch(function (error) {
            mostrarErrorTag(control, error.message);
          });
      });
    }
  });

  var arrastrando = null;

  // Resalta el destino mientras la tarjeta esta encima: sin esto no se ve donde va a
  // caer. Se limpia en dragend, que es el unico evento que fires siempre.
  function marcarDestino(elemento) {
    if (elemento) { elemento.classList.add("destino"); }
  }

  function limpiarDestinos() {
    document.querySelectorAll(".destino").forEach(function (elemento) {
      elemento.classList.remove("destino");
    });
  }

  document.querySelectorAll(".card").forEach(function (card) {
    card.setAttribute("draggable", "true");

    card.addEventListener("dragstart", function (evento) {
      arrastrando = card;
      evento.dataTransfer.effectAllowed = "move";
      // Firefox exige que haya datos para iniciar el arrastre.
      evento.dataTransfer.setData("text/plain", card.getAttribute("data-key") || "");
    });

    card.addEventListener("dragend", function () {
      arrastrando = null;
      limpiarDestinos();
    });

    card.addEventListener("dragover", function (evento) {
      evento.preventDefault();
      evento.dataTransfer.dropEffect = "move";
      limpiarDestinos();
      marcarDestino(card);
    });

    card.addEventListener("dragleave", function () {
      card.classList.remove("destino");
    });

    card.addEventListener("drop", function (evento) {
      evento.preventDefault();
      evento.stopPropagation();
      var origen = arrastrando;
      arrastrando = null;
      limpiarDestinos();
      if (!origen || origen === card) { return; }
      soltar(origen, card.getAttribute("data-tag") || "");
    });
  });

  document.querySelectorAll(".tag-section").forEach(function (seccion) {
    seccion.addEventListener("dragover", function (evento) {
      evento.preventDefault();
      evento.dataTransfer.dropEffect = "move";
      limpiarDestinos();
      marcarDestino(seccion);
    });

    seccion.addEventListener("dragleave", function () {
      seccion.classList.remove("destino");
    });

    seccion.addEventListener("drop", function (evento) {
      evento.preventDefault();
      var origen = arrastrando;
      arrastrando = null;
      limpiarDestinos();
      if (!origen) { return; }
      soltar(origen, seccion.getAttribute("data-drop") || "");
    });
  });

  function soltar(origen, tagDestino) {
    var control = origen.querySelector(".tag-controls");
    if (!control) { return; }
    var cuerpo = {
      key: origen.getAttribute("data-key"),
      token: control.getAttribute("data-token")
    };
    if (tagDestino) {
      cuerpo.action = "set_tag";
      cuerpo.tag = tagDestino;
    } else {
      cuerpo.action = "clear_tag";
    }
    postTag(control, cuerpo).catch(function (error) {
      // La tarjeta conserva el tag que tenia: no se toca el DOM hasta que el
      // servidor confirma.
      mostrarErrorTag(control, error.message);
    });
  }

  // --- Recorrido de fotos de un grupo ---
  //
  // El token viaja en un encabezado y no en la URL, justamente para que el navegador
  // lo mande solo en peticiones propias del visor. Eso obliga a que la imagen no venga
  // en un `src`: se pide con fetch y se muestra como blob, porque un `src` no puede
  // llevar el encabezado.

  var browser = document.getElementById("photo-browser");
  if (browser) {
    var token = browser.getAttribute("data-token");
    var imagen = document.getElementById("photo-browser-image");
    var posicion = document.getElementById("photo-browser-position");
    var titulo = document.getElementById("photo-browser-group");
    var estado = document.getElementById("photo-browser-status");
    var botonMarcar = document.getElementById("photo-browser-mark");
    var botonPrevio = document.getElementById("photo-browser-prev");
    var botonSiguiente = document.getElementById("photo-browser-next");
    var botonCerrar = document.getElementById("photo-browser-close");

    var lista = [];
    var indice = 0;
    var urlActual = null;

    function soltarImagen() {
      if (urlActual) {
        URL.revokeObjectURL(urlActual);
        urlActual = null;
      }
    }

    function pintarMarca(foto) {
      botonMarcar.setAttribute("aria-pressed", foto.marked ? "true" : "false");
      botonMarcar.textContent = foto.marked ? "Quitar la marca" : "Marcar";
    }

    function mostrar(indiceNuevo) {
      // En los extremos no se pasa: el recorrido se queda en la ultima o la primera
      // foto en lugar de dar la vuelta o salirse del grupo.
      indice = Math.max(0, Math.min(indiceNuevo, lista.length - 1));
      var foto = lista[indice];
      posicion.textContent = (indice + 1) + " de " + lista.length;
      pintarMarca(foto);
      estado.textContent = "";
      soltarImagen();
      fetch("/render?ref=" + encodeURIComponent(foto.ref), {
        headers: { "X-Fotos-Plus-Token": token }
      }).then(function (respuesta) {
        if (!respuesta.ok) { throw new Error("No se pudo preparar la foto"); }
        return respuesta.blob();
      }).then(function (blob) {
        urlActual = URL.createObjectURL(blob);
        imagen.src = urlActual;
      }).catch(function () {
        estado.textContent = "No se pudo mostrar esta foto";
      });
    }

    function abrir(clave) {
      estado.textContent = "Cargando...";
      fetch("/api/photos?group=" + encodeURIComponent(clave), {
        headers: { "X-Fotos-Plus-Token": token }
      }).then(function (respuesta) {
        return respuesta.json().then(function (datos) {
          if (!respuesta.ok) {
            throw new Error(datos.error || "No se pudo abrir el grupo");
          }
          return datos;
        });
      }).then(function (datos) {
        lista = datos.photos;
        if (!lista.length) {
          estado.textContent = "Este grupo no tiene fotos";
          return;
        }
        titulo.textContent = datos.title;
        browser.hidden = false;
        mostrar(0);
      }).catch(function (error) {
        estado.textContent = error.message;
      });
    }

    function cerrar() {
      browser.hidden = true;
      soltarImagen();
      imagen.removeAttribute("src");
      lista = [];
    }

    function alternarMarca() {
      var foto = lista[indice];
      if (!foto) { return; }
      var marcada = !foto.marked;
      fetch("/api/marks", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Fotos-Plus-Token": token
        },
        body: JSON.stringify({
          action: marcada ? "mark" : "unmark",
          ref: foto.ref,
          token: token
        })
      }).then(function (respuesta) {
        return respuesta.json().then(function (datos) {
          if (!respuesta.ok) {
            throw new Error(datos.error || "No se pudo guardar la marca");
          }
          return datos;
        });
      }).then(function (datos) {
        // El estado cambia recien cuando el servidor confirma, y sin recargar la
        // pagina: la respuesta trae la marca ya guardada.
        foto.marked = datos.marked;
        pintarMarca(foto);
      }).catch(function (error) {
        estado.textContent = error.message;
      });
    }

    document.querySelectorAll(".browse-open").forEach(function (boton) {
      boton.addEventListener("click", function () {
        abrir(boton.getAttribute("data-browse-key"));
      });
    });

    botonPrevio.addEventListener("click", function () { mostrar(indice - 1); });
    botonSiguiente.addEventListener("click", function () { mostrar(indice + 1); });
    botonMarcar.addEventListener("click", alternarMarca);
    botonCerrar.addEventListener("click", cerrar);

    function escribiendo(evento) {
      var destino = evento.target;
      if (!destino) { return false; }
      return destino.tagName === "INPUT" || destino.tagName === "TEXTAREA" ||
             destino.tagName === "SELECT" || destino.isContentEditable;
    }

    document.addEventListener("keydown", function (evento) {
      if (browser.hidden) { return; }
      // Escribir con el teclado es asunto de otro campo: las flechas se dejan pasar.
      if (escribiendo(evento)) { return; }
      if (evento.key === "ArrowLeft") {
        evento.preventDefault();
        mostrar(indice - 1);
      } else if (evento.key === "ArrowRight") {
        evento.preventDefault();
        mostrar(indice + 1);
      } else if (evento.key === "Escape") {
        evento.preventDefault();
        cerrar();
      }
    });
  }
})();
</script>
"""


def _drift_notice(drift: Optional["LabelResolution"]) -> str:
    """Aviso de que el escaneo se movio y algunas ediciones quedaron sin grupo."""
    if drift is None or not drift.drifted:
        return ""
    parts: list[str] = []
    if drift.scan_advanced:
        parts.append("El escaneo se rehizo despues de escribir los nombres y tags.")
    if drift.dangling_count:
        # El total mezcla nombres y tags: los dos se guardan contra la misma lista de
        # grupos y se avisan juntos, asi que el texto no dice solo "etiquetas".
        total = drift.resolved_count + drift.tagged_count + drift.dangling_count
        parts.append(
            f"{drift.dangling_count} de {total} nombres y tags ya no corresponden a "
            "ningun grupo. Siguen guardados."
        )
    return f'<p class="aviso">{" ".join(parts)}</p>'


def render_html(
    groups: list[Group],
    root: str,
    flat: bool = False,
    labels: Optional[dict[str, str]] = None,
    token: Optional[str] = None,
    drift: Optional["LabelResolution"] = None,
    tag_options: Sequence[str] = (),
    marked: Optional[Iterable[str]] = None,
) -> str:
    """Genera el documento del visor.

    Sin `token` el documento es de solo lectura: muestra las etiquetas y los tags
    vigentes pero no ofrece ningun control para cambiarlos, porque sin servidor no habria
    donde guardarlos. Con `token` la pagina viene con los controles de edicion.

    `tag_options` son los nombres del catalogo que el selector de tag ofrece.

    `marked` son los hashes de las fotos marcadas. Solo se usa cuando hay token: sin
    servidor el HTML exportado no lleva el inventario ni las marcas.
    """
    labels = labels or {}
    editable = token is not None
    if not editable:
        marked = None

    if flat:
        cards = "".join(
            _flat_card(photo, Path(root))
            for photo in sorted(
                (p for g in groups for p in g.photos), key=_photo_sort_key
            )
        )
        body = f'<div class="grid">{cards}</div>'
        title = FLAT_GRID_TITLE
        subtitle = "sin archivo de sugerencias: se muestran todas las fotos sin agrupar"
    else:
        # Con tags asignados las tarjetas van en secciones; sin tags, en una sola
        # grilla ordenada por fecha, que es como se veia antes de que existieran.
        sections = group_sections(groups)
        if sections:
            body = "".join(
                _section_html(section, Path(root), labels, token, tag_options)
                for section in sections
            )
        else:
            cards = "".join(
                _group_card(group, Path(root), labels, token, tag_options)
                for group in groups
            )
            body = f'<div class="grid">{cards}</div>'
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
    # El catalogo de tags solo aparece en la pagina servida: sin servidor no hay a quien
    # elegirle un tag.
    catalog = _tag_catalog(tag_options, groups) if editable else ""
    browser = _browser_overlay(token) if editable else ""

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
        f"{body}\n"
        f"{catalog}"
        f"{browser}"
        '<script type="application/json" id="viewer-data">'
        f"{json.dumps(_payload(groups, root, flat, marked), ensure_ascii=False)}"
        "</script>\n"
        f"{script}"
        "</body>\n"
        "</html>\n"
    )


def _payload(
    groups: list[Group], root: str, flat: bool, marked: Optional[Iterable[str]] = None
) -> dict:
    """Los datos que el visor embebe en la pagina.

    Sin servidor la pagina es un documento para leer: se lleva lo que describe las
    tarjetas y nada mas. Servida, cada grupo ademas trae su referencia y cuantas fotos
    tiene marcadas, que es lo que la tarjeta necesita para abrir el recorrido sin
    tener que preguntar antes. Las fotos sueltas no van aqui, se piden por grupo.
    """
    if marked is None:
        marks: frozenset = frozenset()
        served = False
    else:
        marks = frozenset(marked)
        served = True

    payload_groups = []
    for group in groups:
        entry = {
            "title": group.title,
            "kind": group.kind,
            "photo_count": group.photo_count,
            "first_captured_at": group.first_captured_at,
            "last_captured_at": group.last_captured_at,
            "country": group.country,
        }
        if served:
            entry["browse_key"] = group.browse_key
            entry["marked_count"] = sum(
                1 for photo in group.photos if photo.sha256 in marks
            )
        payload_groups.append(entry)

    return {
        "flat": flat,
        "groups": payload_groups,
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

    groups = assign_groups(
        result.photos, suggestions, labels=resolution.labels, tags=resolution.tags
    )
    return (
        render_html(
            groups,
            root,
            flat=False,
            labels=resolution.labels,
            token=None,
            drift=resolution,
            tag_options=overlay.tags,
        ),
        False,
    )
