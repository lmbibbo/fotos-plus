"""The edition file: what the user wrote, stored next to the index.

It holds four things, and they are separate axes. Three name or classify groups and are
keyed by the group's earliest date: `labels` gives it a name, `tagged` assigns it a tag, and
`tags` is the catalogue those tags are chosen from. The fourth, `marked`, does not name
groups at all: it marks individual photos and is stored as a flat list of content hashes, so
that it survives the photo being moved to another folder.

The file has a single writer, the editor, and is written atomically. Earlier versions are
still readable and are migrated in memory when read.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional

from .index import write_json_atomic
from .models import SuggestionsResult

EDITION_VERSION = 3

# Version 1 only had `labels`. Version 2 added the tag catalogue and the assignments.
# Version 3 adds `marked`, the photos the user kept. Earlier versions are still read and
# migrated to the current one in memory, without rewriting the file yet.
SUPPORTED_EDITIONS = (1, 2, 3)

EMPTY_LABEL_ERROR = "una etiqueta no puede estar vacia"
EMPTY_TAG_ERROR = "un tag no puede estar vacio"
MARK_SHAPE_ERROR = "una marca tiene que ser 64 caracteres hexadecimales en minuscula"

MARK_LENGTH = 64
_HEX_DIGITS = set("0123456789abcdef")


class LabelError(Exception):
    """Error de validacion al trabajar con las etiquetas.

    No es un fallo del programa: el mensaje dice que paso y la operacion se puede
    corregir o descartar sin haber tocado ningun archivo.
    """


def _clean_text(value: object) -> str:
    """Valida que un texto de etiqueta sea usable y lo devuelve sin espacios alrededor."""
    if not isinstance(value, str):
        raise LabelError("una etiqueta tiene que ser texto")
    cleaned = value.strip()
    if not cleaned:
        raise LabelError(EMPTY_LABEL_ERROR)
    return cleaned


def _clean_tag(value: object) -> str:
    """Valida que un nombre de tag sea usable y lo devuelve sin espacios alrededor."""
    if not isinstance(value, str):
        raise LabelError("un tag tiene que ser texto")
    cleaned = value.strip()
    if not cleaned:
        raise LabelError(EMPTY_TAG_ERROR)
    return cleaned


def _tag_identity(value: str) -> str:
    """La forma con la que se comparan dos nombres de tag para saber si son el mismo.

    Solo decide si dos nombres son el mismo tag. La forma con la que se muestra y se guarda
    es la que el usuario escribio, para que un tag escrito como "Viaje" no se vea como "viaje".
    """
    return value.strip().casefold()


def _clean_mark(value: object) -> str:
    """Validates a photo mark and returns the hash exactly as it is stored.

    A mark is the content hash of the photo, always lowercase because that is what the
    scanner produces. That exact shape is required so one photo cannot end up recorded
    twice under two different spellings.
    """
    if not isinstance(value, str):
        raise LabelError(MARK_SHAPE_ERROR)
    if len(value) != MARK_LENGTH or not set(value) <= _HEX_DIGITS:
        raise LabelError(MARK_SHAPE_ERROR)
    return value


@dataclass
class LabelOverlay:
    """What the user wrote, held in the edition file.

    `labels` names a group, `tagged` classifies it, and `tags` is the catalogue those names
    are chosen from. All three are keyed by the group's earliest date, which is the same
    value the viewer already uses to order the cards and is unique among groups because the
    scanner hands out photos without overlap.

    `marked` is the fourth axis and is not keyed by group: it is a flat list of photo
    content hashes. It marks the photo rather than the group, so it survives the photo
    moving folder and survives the derived group changing. Saving a label or a tag does
    not touch it.
    """

    based_on_scanned_at: Optional[str] = None
    labels: dict[str, str] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    tagged: dict[str, str] = field(default_factory=dict)
    marked: list[str] = field(default_factory=list)

    def is_marked(self, sha256: str) -> bool:
        """Whether that photo is marked."""
        return sha256 in self.marked

    def title_for(self, key: str) -> Optional[str]:
        """Etiqueta vigente para una referencia, o None si el grupo no tiene."""
        return self.labels.get(key)

    def tag_for(self, key: str) -> Optional[str]:
        """Tag vigente para una referencia, o None si el grupo no tiene."""
        return self.tagged.get(key)

    def canonical_tag(self, name: object) -> Optional[str]:
        """El nombre del catalogo que corresponde a este nombre, o None si no esta.

        Comparar sin mayculas y sin espacios permite que " familia " encuentre el tag
        "Familia" ya guardado en vez de crear una segunda entrada equivalente.
        """
        try:
            cleaned = _clean_tag(name)
        except LabelError:
            return None
        identity = _tag_identity(cleaned)
        for existing in self.tags:
            if _tag_identity(existing) == identity:
                return existing
        return None

    def to_dict(self) -> dict:
        return {
            "version": EDITION_VERSION,
            "based_on_scanned_at": self.based_on_scanned_at,
            "labels": dict(sorted(self.labels.items())),
            "tags": list(self.tags),
            "tagged": dict(sorted(self.tagged.items())),
            "marked": sorted(self.marked),
        }

    @classmethod
    def from_dict(cls, data: object) -> "LabelOverlay":
        if not isinstance(data, dict):
            raise LabelError("el archivo de edicion no es un objeto JSON")
        version = data.get("version")
        if version not in SUPPORTED_EDITIONS:
            raise LabelError(f"version de edicion no soportada: {version!r}")

        raw = data.get("labels")
        if raw is None:
            raw = {}
        if not isinstance(raw, dict):
            raise LabelError("'labels' del archivo de edicion no es un objeto JSON")

        labels: dict[str, str] = {}
        for key, value in raw.items():
            if not isinstance(key, str):
                raise LabelError("las claves de 'labels' tienen que ser texto")
            labels[key] = _clean_text(value)

        based_on = data.get("based_on_scanned_at")
        if based_on is not None and not isinstance(based_on, str):
            raise LabelError("'based_on_scanned_at' del archivo de edicion no es texto")

        # A v1 file has no `tags` nor `tagged`, and a v2 file has no `marked`. Each is
        # migrated in memory to the current shape with whatever is missing empty, and the
        # file is written at the current version the first time the user saves anything.
        # Reading it never rewrites it.
        tags = cls._read_tags(data.get("tags"))
        tagged = cls._read_tagged(data.get("tagged"), tags)
        marked = cls._read_marked(data.get("marked"))

        return cls(
            based_on_scanned_at=based_on,
            labels=labels,
            tags=tags,
            tagged=tagged,
            marked=marked,
        )

    @staticmethod
    def _read_marked(raw: object) -> list[str]:
        """The marks, validated: complete lowercase hashes only, no duplicates."""
        if raw is None:
            return []
        if not isinstance(raw, list):
            raise LabelError("'marked' del archivo de edicion no es una lista JSON")

        marked: list[str] = []
        seen: set[str] = set()
        for value in raw:
            cleaned = _clean_mark(value)
            if cleaned in seen:
                continue
            seen.add(cleaned)
            marked.append(cleaned)
        return sorted(marked)

    @staticmethod
    def _read_tags(raw: object) -> list[str]:
        """El catalogo, validado: sin entradas vacias y sin nombres equivalentes repetidos."""
        if raw is None:
            return []
        if not isinstance(raw, list):
            raise LabelError("'tags' del archivo de edicion no es una lista JSON")

        tags: list[str] = []
        seen: set[str] = set()
        for value in raw:
            cleaned = _clean_tag(value)
            identity = _tag_identity(cleaned)
            if identity in seen:
                raise LabelError(f"'tags' repite el tag {cleaned!r}")
            seen.add(identity)
            tags.append(cleaned)
        return tags

    @staticmethod
    def _read_tagged(raw: object, tags: list[str]) -> dict[str, str]:
        """Las asignaciones, validadas contra el catalogo ya leido."""
        if raw is None:
            return {}
        if not isinstance(raw, dict):
            raise LabelError("'tagged' del archivo de edicion no es un objeto JSON")

        known = {_tag_identity(name): name for name in tags}
        tagged: dict[str, str] = {}
        for key, value in raw.items():
            if not isinstance(key, str):
                raise LabelError("las claves de 'tagged' tienen que ser texto")
            cleaned = _clean_tag(value)
            canonical = known.get(_tag_identity(cleaned))
            if canonical is None:
                raise LabelError(f"el tag {cleaned!r} no esta en 'tags'")
            tagged[key] = canonical
        return tagged


def read_edicion(path: Path) -> LabelOverlay:
    """Lee el archivo de edicion. Si no existe, devuelve uno vacio sin error."""
    path = Path(path)
    if not path.is_file():
        return LabelOverlay()
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as error:
        raise LabelError(f"no se pudo leer el archivo de edicion: {error}") from error
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as error:
        raise LabelError(
            f"el archivo de edicion no es JSON valido: {error}"
        ) from error
    return LabelOverlay.from_dict(data)


def write_edicion(overlay: LabelOverlay, path: Path) -> Path:
    """Escribe el archivo de edicion de forma atomica.

    Se vuelven a validar las etiquetas, los tags y las marcas antes de escribir: el archivo
    tambien puede venir editado a mano, y no debe quedar guardada una etiqueta vacia, una
    asignacion a un tag que no esta en el catalogo ni una marca mal formada.
    """
    for value in overlay.labels.values():
        _clean_text(value)
    LabelOverlay._read_tags(list(overlay.tags))
    LabelOverlay._read_tagged(dict(overlay.tagged), list(overlay.tags))
    LabelOverlay._read_marked(list(overlay.marked))
    return write_json_atomic(overlay.to_dict(), path)


def group_key_counts(suggestions: SuggestionsResult) -> Counter:
    """Cuantos grupos del escaneo arrancan en cada fecha mas temprana."""
    counts: Counter = Counter()
    for trip in suggestions.trips:
        counts[trip.first_captured_at] += 1
    for period in suggestions.periods:
        counts[period.first_captured_at] += 1
    return counts


@dataclass
class LabelResolution:
    """Como quedan las etiquetas y los tags al cruzarlos con los grupos del escaneo vigente."""

    labels: dict[str, str] = field(default_factory=dict)
    tags: dict[str, str] = field(default_factory=dict)
    unresolved: list[str] = field(default_factory=list)
    ambiguous: list[str] = field(default_factory=list)
    unresolved_tags: list[str] = field(default_factory=list)
    ambiguous_tags: list[str] = field(default_factory=list)
    scan_advanced: bool = False

    @property
    def resolved_count(self) -> int:
        return len(self.labels)

    @property
    def tagged_count(self) -> int:
        return len(self.tags)

    @property
    def dangling_count(self) -> int:
        return (
            len(self.unresolved)
            + len(self.ambiguous)
            + len(self.unresolved_tags)
            + len(self.ambiguous_tags)
        )

    @property
    def drifted(self) -> bool:
        """True si hay que avisar al usuario de que algo cambio respecto del escaneo."""
        return self.scan_advanced or self.dangling_count > 0


DERIVED_TITLES = {"trip": "Viaje", "period": "Periodo"}


def derived_title(kind: str, key: str, suggestions: SuggestionsResult) -> str:
    """Titulo que tendria un grupo sin etiqueta, tal como lo derivaba el escaneo."""
    for trip in suggestions.trips:
        if trip.first_captured_at == key:
            location = trip.location
            country = location.country if location is not None else None
            return country or DERIVED_TITLES["trip"]
    for period in suggestions.periods:
        if period.first_captured_at == key:
            return DERIVED_TITLES["period"]
    return DERIVED_TITLES.get(kind, "Grupo")


def _scan_advanced(based_on: Optional[str], current: Optional[str]) -> bool:
    # Ambos instantes salen de `datetime.now().isoformat(timespec="seconds")`, asi que
    # el orden lexicografico coincide con el cronologico.
    if based_on is None or current is None:
        return False
    return current > based_on


def resolve_labels(
    overlay: LabelOverlay, suggestions: SuggestionsResult
) -> LabelResolution:
    """Cruza el archivo de edicion con los grupos del escaneo vigente.

    Una etiqueta o un tag se aplican solo si su referencia resuelve a exactamente un grupo.
    Los que no resuelven no se descartan: quedan listados para que el usuario decida, y
    siguen guardados en el archivo.
    """
    counts = group_key_counts(suggestions)
    resolution = LabelResolution(
        scan_advanced=_scan_advanced(overlay.based_on_scanned_at, suggestions.scanned_at)
    )
    for key in sorted(overlay.labels):
        matches = counts.get(key, 0)
        if matches == 0:
            resolution.unresolved.append(key)
        elif matches > 1:
            resolution.ambiguous.append(key)
        else:
            resolution.labels[key] = overlay.labels[key]
    for key in sorted(overlay.tagged):
        matches = counts.get(key, 0)
        if matches == 0:
            resolution.unresolved_tags.append(key)
        elif matches > 1:
            resolution.ambiguous_tags.append(key)
        else:
            resolution.tags[key] = overlay.tagged[key]
    return resolution


def validate_label(key: object, text: object, suggestions: SuggestionsResult) -> str:
    """Valida una edicion antes de escribirla y devuelve el texto limpio.

    Rechaza con un motivo la etiqueta vacia, la referencia que no resuelve a ningun
    grupo y la referencia ambigua.
    """
    if not isinstance(key, str) or not key.strip():
        raise LabelError("falta la referencia del grupo a etiquetar")

    cleaned = _clean_text(text)

    matches = group_key_counts(suggestions).get(key, 0)
    if matches == 0:
        raise LabelError(f"la referencia {key} no corresponde a ningun grupo actual")
    if matches > 1:
        raise LabelError(
            f"la referencia {key} es ambigua: corresponde a {matches} grupos"
        )
    return cleaned


def set_label(
    overlay: LabelOverlay,
    suggestions: SuggestionsResult,
    key: object,
    text: object,
    scanned_at: Optional[str] = None,
) -> LabelOverlay:
    """Devuelve un overlay nuevo con la etiqueta puesta. No muta el overlay de entrada."""
    cleaned = validate_label(key, text, suggestions)
    labels = dict(overlay.labels)
    labels[str(key).strip()] = cleaned
    return LabelOverlay(
        based_on_scanned_at=scanned_at or overlay.based_on_scanned_at,
        labels=labels,
        tags=list(overlay.tags),
        tagged=dict(overlay.tagged),
        marked=list(overlay.marked),
    )


def remove_label(overlay: LabelOverlay, key: object) -> LabelOverlay:
    """Devuelve un overlay nuevo sin la etiqueta de ese grupo.

    No se valida contra el escaneo a proposito: una etiqueta que quedo huerfana por un
    rescaneo tiene que poder quitarse igual.
    """
    if not isinstance(key, str) or not key.strip():
        raise LabelError("falta la referencia del grupo al que quitarle la etiqueta")
    normalized = key.strip()
    if normalized not in overlay.labels:
        raise LabelError(f"el grupo {normalized} no tiene etiqueta para quitar")

    labels = dict(overlay.labels)
    del labels[normalized]
    return LabelOverlay(
        based_on_scanned_at=overlay.based_on_scanned_at,
        labels=labels,
        tags=list(overlay.tags),
        tagged=dict(overlay.tagged),
        marked=list(overlay.marked),
    )


def validate_tag(key: object, name: object, suggestions: SuggestionsResult) -> str:
    """Valida una asignacion de tag antes de escribirla y devuelve el nombre limpio.

    Rechaza con un motivo el tag vacio, la referencia que no resuelve a ningun grupo y la
    referencia ambigua.
    """
    if not isinstance(key, str) or not key.strip():
        raise LabelError("falta la referencia del grupo al que asignarle el tag")

    cleaned = _clean_tag(name)

    matches = group_key_counts(suggestions).get(key, 0)
    if matches == 0:
        raise LabelError(f"la referencia {key} no corresponde a ningun grupo actual")
    if matches > 1:
        raise LabelError(f"la referencia {key} es ambigua: corresponde a {matches} grupos")
    return cleaned


def set_tag(
    overlay: LabelOverlay,
    suggestions: SuggestionsResult,
    key: object,
    name: object,
    scanned_at: Optional[str] = None,
) -> LabelOverlay:
    """Devuelve un overlay nuevo con el tag puesto. No muta el overlay de entrada.

    Si el tag no estaba en el catalogo se agrega al final, que es el orden en que el
    usuario los fue creando. Si ya habia uno equivalente por mayusculas o espacios se
    reutiliza ese, para no dejar dos entradas que sean el mismo tag.
    """
    cleaned = validate_tag(key, name, suggestions)
    normalized_key = str(key).strip()

    tags = list(overlay.tags)
    identity = _tag_identity(cleaned)
    canonical = next((entry for entry in tags if _tag_identity(entry) == identity), None)
    if canonical is None:
        canonical = cleaned
        tags.append(canonical)

    tagged = dict(overlay.tagged)
    tagged[normalized_key] = canonical

    return LabelOverlay(
        based_on_scanned_at=scanned_at or overlay.based_on_scanned_at,
        labels=dict(overlay.labels),
        tags=tags,
        tagged=tagged,
        marked=list(overlay.marked),
    )


def clear_tag(overlay: LabelOverlay, key: object) -> LabelOverlay:
    """Devuelve un overlay nuevo sin el tag de ese grupo.

    El tag se queda en el catalogo: quitarlo de una tarjeta no lo borra de la biblioteca
    de tags que el usuario puede volver a elegir.
    """
    if not isinstance(key, str) or not key.strip():
        raise LabelError("falta la referencia del grupo al que quitarle el tag")
    normalized = key.strip()
    if normalized not in overlay.tagged:
        raise LabelError(f"el grupo {normalized} no tiene tag para quitar")

    tagged = dict(overlay.tagged)
    del tagged[normalized]
    return LabelOverlay(
        based_on_scanned_at=overlay.based_on_scanned_at,
        labels=dict(overlay.labels),
        tags=list(overlay.tags),
        tagged=tagged,
        marked=list(overlay.marked),
    )


def mark_photo(overlay: LabelOverlay, sha256: object) -> LabelOverlay:
    """Returns a new overlay with the photo marked. Does not mutate the overlay it got.

    Marking a photo that was already marked does not duplicate it: it is the same
    operation, which is why it can be applied again without checking anything first.
    """
    cleaned = _clean_mark(sha256)
    marked = set(overlay.marked)
    marked.add(cleaned)
    return _with_marked(overlay, marked)


def unmark_photo(overlay: LabelOverlay, sha256: object) -> LabelOverlay:
    """Returns a new overlay without that mark. Does not mutate the overlay it got.

    Unmarking a photo that carries no mark is not an error: it is the same gesture, and it
    does not have to read the current state to decide what to do.
    """
    cleaned = _clean_mark(sha256)
    marked = set(overlay.marked)
    marked.discard(cleaned)
    return _with_marked(overlay, marked)


def _with_marked(overlay: LabelOverlay, marked: set[str]) -> LabelOverlay:
    return LabelOverlay(
        based_on_scanned_at=overlay.based_on_scanned_at,
        labels=dict(overlay.labels),
        tags=list(overlay.tags),
        tagged=dict(overlay.tagged),
        marked=sorted(marked),
    )


def prune_marked(overlay: LabelOverlay, known_hashes: Iterable[str]) -> LabelOverlay:
    """Drops from memory the marks of photos the index no longer has.

    It does not rewrite the file: the mark stays stored in case the photo comes back,
    which is what happens when a drive is disconnected. It just stops being counted so it
    can be shown.
    """
    known = set(known_hashes)
    kept = [value for value in overlay.marked if value in known]
    if len(kept) == len(overlay.marked):
        return overlay
    return _with_marked(overlay, set(kept))