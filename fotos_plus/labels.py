"""The edition file: what the user wrote, stored next to the index.

It holds six things, and they are separate axes. Three name or classify groups and are
keyed by the group's earliest date: `labels` gives it a name, `tagged` assigns it a tag, and
`tags` is the catalogue those tags are chosen from. The other three do not name groups at all
and are keyed by the photo's content hash, so they survive the photo being moved to another
folder: `marked` is a flat list of hashes recording which photos the user kept, and
`photo_tagged` maps a hash to the buckets that photo belongs to, chosen from the separate
`photo_tags` catalogue.

The group axes and the photo axes do not share a catalogue, so the same name may be used on
both without the two referring to each other.

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

EDITION_VERSION = 4

# Version 1 only had `labels`. Version 2 added the tag catalogue and the assignments.
# Version 3 adds `marked`, the photos the user kept. Version 4 adds the bucket catalogue and
# the bucket assignments. Earlier versions are still read and migrated to the current one in
# memory, without rewriting the file yet.
SUPPORTED_EDITIONS = (1, 2, 3, 4)

EMPTY_LABEL_ERROR = "una etiqueta no puede estar vacia"
EMPTY_TAG_ERROR = "un tag no puede estar vacio"
EMPTY_BUCKET_ERROR = "un cubo no puede estar vacio"
MARK_SHAPE_ERROR = "una marca tiene que ser 64 caracteres hexadecimales en minuscula"
BUCKET_KEY_ERROR = (
    "una asignacion de cubo tiene que ser 64 caracteres hexadecimales en minuscula"
)

HASH_LENGTH = 64
_HEX_DIGITS = set("0123456789abcdef")


class LabelError(Exception):
    """Error de validacion al trabajar con las etiquetas.

    No es un fallo del programa: el mensaje dice que paso y la operacion se puede
    corregir o descartar sin haber tocado ningun archivo.
    """


def _clean_name(value: object, not_text: str, empty: str) -> str:
    """Valida que un nombre de la biblioteca de etiquetas sea usable y lo devuelve sin
    espacios alrededor.

    Los tres catálogos --etiquetas, tags y cubos-- rechazan lo mismo: un valor que no sea
    texto y un texto que quede vacío al quitarle los espacios de los bordes. Cada uno
    reporta su propio motivo, asi que el mensaje se recibe por parametro.
    """
    if not isinstance(value, str):
        raise LabelError(not_text)
    cleaned = value.strip()
    if not cleaned:
        raise LabelError(empty)
    return cleaned


def _clean_text(value: object) -> str:
    """Valida que un texto de etiqueta sea usable y lo devuelve sin espacios alrededor."""
    return _clean_name(value, "una etiqueta tiene que ser texto", EMPTY_LABEL_ERROR)


def _clean_tag(value: object) -> str:
    """Valida que un nombre de tag sea usable y lo devuelve sin espacios alrededor."""
    return _clean_name(value, "un tag tiene que ser texto", EMPTY_TAG_ERROR)


def _clean_bucket(value: object) -> str:
    """Valida que un nombre de cubo sea usable y lo devuelve sin espacios alrededor."""
    return _clean_name(value, "un cubo tiene que ser texto", EMPTY_BUCKET_ERROR)


def _tag_identity(value: str) -> str:
    """La forma con la que se comparan dos nombres de tag para saber si son el mismo.

    Solo decide si dos nombres son el mismo tag. La forma en la que se muestra y se guarda
    es la que el usuario escribio, para que un tag escrito como "Viaje" no se vea como "viaje".
    """
    return value.strip().casefold()


def _clean_hash(value: object, error: str) -> str:
    """Valida un hash de contenido y lo devuelve exactamente como se guarda.

    Un hash de foto es el contenido del archivo, siempre en minuscula porque es lo que
    produce el escaneo. Se exige esa forma exacta para que una foto no pueda quedar
    registrada dos veces bajo dos escrituras distintas.
    """
    if not isinstance(value, str):
        raise LabelError(error)
    if len(value) != HASH_LENGTH or not set(value) <= _HEX_DIGITS:
        raise LabelError(error)
    return value


def _clean_mark(value: object) -> str:
    """Validates a photo mark and returns the hash exactly as it is stored."""
    return _clean_hash(value, MARK_SHAPE_ERROR)


def _copy_photo_tagged(overlay: "LabelOverlay") -> dict[str, list[str]]:
    """Copia las asignaciones de cubos con sus listas propias.

    Cada operacion devuelve un overlay nuevo y no toca el que recibio, asi que la copia
    tiene que ser profunda: si dos overlays compartieran la misma lista, agregar un cubo en
    uno se veria en el otro.
    """
    return {key: list(value) for key, value in overlay.photo_tagged.items()}


@dataclass
class LabelOverlay:
    """What the user wrote, held in the edition file.

    `labels` names a group, `tagged` classifies it, and `tags` is the catalogue those names
    are chosen from. All three are keyed by the group's earliest date, which is the same
    value the viewer already uses to order the cards and is unique among groups because the
    scanner hands out photos without overlap.

    The photo axes are keyed by content hash instead, so they survive the photo moving folder
    and survive the derived group changing. `marked` is a flat list of hashes and records
    only whether the user kept the photo. `photo_tagged` maps a hash to the buckets that
    photo belongs to, and `photo_tags` is the separate catalogue those bucket names are
    chosen from.

    A photo may belong to any number of buckets, so `photo_tagged` holds a list rather than a
    single name. That is the one place the photo axes differ in shape from the group axes,
    which hold exactly one tag each.

    Saving a label, a tag, a mark or a bucket does not touch the other axes. Every operation
    rebuilds the whole overlay field by field, so each one has to carry the rest through.
    """

    based_on_scanned_at: Optional[str] = None
    labels: dict[str, str] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    tagged: dict[str, str] = field(default_factory=dict)
    marked: list[str] = field(default_factory=list)
    photo_tags: list[str] = field(default_factory=list)
    photo_tagged: dict[str, list[str]] = field(default_factory=dict)

    def is_marked(self, sha256: str) -> bool:
        """Whether that photo is marked."""
        return sha256 in self.marked

    def buckets_for(self, sha256: str) -> list[str]:
        """The buckets that photo belongs to, in catalogue order. Empty if it is in none."""
        held = self.photo_tagged.get(sha256, [])
        order = {name: position for position, name in enumerate(self.photo_tags)}
        return sorted(held, key=lambda name: (order.get(name, len(order)), name))

    def canonical_bucket(self, name: object) -> Optional[str]:
        """El nombre del catalogo de cubos que corresponde a este nombre, o None si no esta.

        Comparar sin mayusculas y sin espacios permite que " favorito " encuentre el cubo
        "Favoritas" ya guardado en vez de crear una segunda entrada equivalente.
        """
        try:
            cleaned = _clean_bucket(name)
        except LabelError:
            return None
        identity = _tag_identity(cleaned)
        for existing in self.photo_tags:
            if _tag_identity(existing) == identity:
                return existing
        return None

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
            "photo_tags": list(self.photo_tags),
            "photo_tagged": {
                key: self.buckets_for(key) for key in sorted(self.photo_tagged)
            },
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

        # A v1 file has no `tags` nor `tagged`, a v2 file has no `marked`, and a v3 file has
        # neither `photo_tags` nor `photo_tagged`. Each is migrated in memory to the current
        # shape with whatever is missing empty, and the file is written at the current version
        # the first time the user saves anything. Reading it never rewrites it.
        tags = cls._read_tags(data.get("tags"))
        tagged = cls._read_tagged(data.get("tagged"), tags)
        marked = cls._read_marked(data.get("marked"))
        photo_tags = cls._read_photo_tags(data.get("photo_tags"))
        photo_tagged = cls._read_photo_tagged(data.get("photo_tagged"), photo_tags)

        return cls(
            based_on_scanned_at=based_on,
            labels=labels,
            tags=tags,
            tagged=tagged,
            marked=marked,
            photo_tags=photo_tags,
            photo_tagged=photo_tagged,
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
    def _read_photo_tags(raw: object) -> list[str]:
        """El catalogo de cubos, validado con las mismas reglas que el de tags.

        Vive aparte a proposito: un mismo nombre puede ser un tag de grupo y un cubo de
        foto sin que los dos se refieran a la misma cosa.
        """
        if raw is None:
            return []
        if not isinstance(raw, list):
            raise LabelError("'photo_tags' del archivo de edicion no es una lista JSON")

        buckets: list[str] = []
        seen: set[str] = set()
        for value in raw:
            cleaned = _clean_bucket(value)
            identity = _tag_identity(cleaned)
            if identity in seen:
                raise LabelError(f"'photo_tags' repite el cubo {cleaned!r}")
            seen.add(identity)
            buckets.append(cleaned)
        return buckets

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

    @staticmethod
    def _read_photo_tagged(
        raw: object, photo_tags: list[str]
    ) -> dict[str, list[str]]:
        """Las asignaciones de cubos, validadas contra el catalogo de cubos ya leido.

        La clave es el hash de contenido de la foto y la lista son los cubos que tiene, en
        orden de catalogo y sin repeticiones. A diferencia de los grupos, una foto puede
        estar en varios cubos a la vez, asi que el valor es una lista.
        """
        if raw is None:
            return {}
        if not isinstance(raw, dict):
            raise LabelError("'photo_tagged' del archivo de edicion no es un objeto JSON")

        order = {name: position for position, name in enumerate(photo_tags)}
        known = {_tag_identity(name): name for name in photo_tags}
        photo_tagged: dict[str, list[str]] = {}
        for key, value in raw.items():
            _clean_hash(key, BUCKET_KEY_ERROR)
            if not isinstance(value, list):
                raise LabelError(
                    f"'photo_tagged[{key!r}]' del archivo de edicion no es una lista JSON"
                )
            held: list[str] = []
            seen: set[str] = set()
            for entry in value:
                cleaned = _clean_bucket(entry)
                canonical = known.get(_tag_identity(cleaned))
                if canonical is None:
                    raise LabelError(f"el cubo {cleaned!r} no esta en 'photo_tags'")
                if canonical in seen:
                    continue
                seen.add(canonical)
                held.append(canonical)
            photo_tagged[key] = sorted(held, key=lambda name: (order[name], name))
        return photo_tagged


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

    Se vuelven a validar las etiquetas, los tags, las marcas y los cubos antes de escribir:
    el archivo tambien puede venir editado a mano, y no debe quedar guardada una etiqueta
    vacia, una asignacion a un tag que no esta en el catalogo, una marca mal formada ni un
    cubo que no existe en su catalogo.
    """
    for value in overlay.labels.values():
        _clean_text(value)
    LabelOverlay._read_tags(list(overlay.tags))
    LabelOverlay._read_tagged(dict(overlay.tagged), list(overlay.tags))
    LabelOverlay._read_marked(list(overlay.marked))
    LabelOverlay._read_photo_tags(list(overlay.photo_tags))
    LabelOverlay._read_photo_tagged(
        {key: list(value) for key, value in overlay.photo_tagged.items()},
        list(overlay.photo_tags),
    )
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
        photo_tags=list(overlay.photo_tags),
        photo_tagged=_copy_photo_tagged(overlay),
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
        photo_tags=list(overlay.photo_tags),
        photo_tagged=_copy_photo_tagged(overlay),
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
        photo_tags=list(overlay.photo_tags),
        photo_tagged=_copy_photo_tagged(overlay),
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
        photo_tags=list(overlay.photo_tags),
        photo_tagged=_copy_photo_tagged(overlay),
    )


def validate_bucket(
    name: object, sha256: object, known_hashes: Iterable[str]
) -> tuple[str, str]:
    """Valida una asignacion de cubo antes de escribirla.

    Devuelve el hash limpio y el nombre limpio. Rechaza con un motivo el nombre vacio, el
    hash mal formado y el hash que no corresponde a ninguna foto del indice vigente.
    """
    cleaned_hash = _clean_hash(sha256, BUCKET_KEY_ERROR)
    cleaned_name = _clean_bucket(name)
    if cleaned_hash not in set(known_hashes):
        raise LabelError(f"el hash {cleaned_hash} no corresponde a ninguna foto actual")
    return cleaned_hash, cleaned_name


def bucket_photo(
    overlay: LabelOverlay,
    sha256: object,
    name: object,
    known_hashes: Iterable[str],
    scanned_at: Optional[str] = None,
) -> LabelOverlay:
    """Devuelve un overlay nuevo con esa foto en ese cubo. No muta el overlay de entrada.

    Una foto puede estar en varios cubos, asi que agregar uno deja los demas como estaban.
    Si el cubo no estaba en el catalogo se agrega al final, que es el orden en que el
    usuario los fue creando; si ya habia uno equivalente por mayusculas o espacios se
    reutiliza ese. Agregar un cubo que la foto ya tiene no lo duplica.
    """
    cleaned_hash, cleaned_name = validate_bucket(name, sha256, known_hashes)

    photo_tags = list(overlay.photo_tags)
    identity = _tag_identity(cleaned_name)
    canonical = next(
        (entry for entry in photo_tags if _tag_identity(entry) == identity), None
    )
    if canonical is None:
        canonical = cleaned_name
        photo_tags.append(canonical)

    order = {entry: position for position, entry in enumerate(photo_tags)}
    held = list(overlay.photo_tagged.get(cleaned_hash, []))
    if canonical not in held:
        held.append(canonical)
    held.sort(key=lambda entry: (order.get(entry, len(order)), entry))

    photo_tagged = _copy_photo_tagged(overlay)
    photo_tagged[cleaned_hash] = held

    return LabelOverlay(
        based_on_scanned_at=scanned_at or overlay.based_on_scanned_at,
        labels=dict(overlay.labels),
        tags=list(overlay.tags),
        tagged=dict(overlay.tagged),
        marked=list(overlay.marked),
        photo_tags=photo_tags,
        photo_tagged=photo_tagged,
    )


def unbucket_photo(overlay: LabelOverlay, sha256: object, name: object) -> LabelOverlay:
    """Devuelve un overlay nuevo sin esa foto en ese cubo. No muta el overlay de entrada.

    Quitar un cubo no toca los demas que tenga la foto, ni la borra del catalogo, que es lo
    que permite volver a elegirlo despues. Si era el ultimo, la foto deja de tener
    asignaciones y queda como una foto mas de su grupo.

    No se valida contra el escaneo a proposito: un cubo que quedo huerfano por un rescaneo
    tiene que poder quitarse igual.
    """
    cleaned_hash = _clean_hash(sha256, BUCKET_KEY_ERROR)
    canonical = overlay.canonical_bucket(name)
    if canonical is None:
        raise LabelError(f"el cubo {_clean_bucket(name)!r} no esta en 'photo_tags'")

    held = list(overlay.photo_tagged.get(cleaned_hash, []))
    if canonical in held:
        held.remove(canonical)

    photo_tagged = _copy_photo_tagged(overlay)
    if held:
        photo_tagged[cleaned_hash] = held
    else:
        photo_tagged.pop(cleaned_hash, None)

    return LabelOverlay(
        based_on_scanned_at=overlay.based_on_scanned_at,
        labels=dict(overlay.labels),
        tags=list(overlay.tags),
        tagged=dict(overlay.tagged),
        marked=list(overlay.marked),
        photo_tags=list(overlay.photo_tags),
        photo_tagged=photo_tagged,
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
        photo_tags=list(overlay.photo_tags),
        photo_tagged=_copy_photo_tagged(overlay),
    )


def _with_photo_tagged(
    overlay: LabelOverlay, photo_tagged: dict[str, list[str]]
) -> LabelOverlay:
    """Overlay nuevo con las asignaciones de cubos dadas y todo lo demas igual."""
    return LabelOverlay(
        based_on_scanned_at=overlay.based_on_scanned_at,
        labels=dict(overlay.labels),
        tags=list(overlay.tags),
        tagged=dict(overlay.tagged),
        marked=list(overlay.marked),
        photo_tags=list(overlay.photo_tags),
        photo_tagged=photo_tagged,
    )


def _resolve_hashes(values: Iterable[str], known_hashes: Iterable[str]) -> set[str]:
    """De estos hashes de contenido, los que el indice vigente todavia tiene.

    Las marcas y las asignaciones de cubos se guardan por hash y no por ruta, asi que las
    dos se podan con la misma regla: si el hash no esta en el indice, todavia no se cuenta
    para que se muestre, pero sigue en el archivo por si la foto vuelve.
    """
    known = set(known_hashes)
    return {value for value in values if value in known}


def prune_marked(overlay: LabelOverlay, known_hashes: Iterable[str]) -> LabelOverlay:
    """Drops from memory the marks of photos the index no longer has.

    It does not rewrite the file: the mark stays stored in case the photo comes back,
    which is what happens when a drive is disconnected. It just stops being counted so it
    can be shown.
    """
    kept = _resolve_hashes(overlay.marked, known_hashes)
    if len(kept) == len(overlay.marked):
        return overlay
    return _with_marked(overlay, kept)


def prune_photo_tagged(overlay: LabelOverlay, known_hashes: Iterable[str]) -> LabelOverlay:
    """Drops from memory the bucket assignments of photos the index no longer has.

    Los nombres del catalogo no se podan: si un cubo se queda sin fotos deja de producir
    seccion, pero sigue disponible para cuando el usuario vuelva a elegirlo, y si la foto
    vuelve recupera su asignacion sin haber escrito nada.
    """
    known = set(known_hashes)
    kept = {
        key: list(value)
        for key, value in overlay.photo_tagged.items()
        if key in known
    }
    if len(kept) == len(overlay.photo_tagged):
        return overlay
    return _with_photo_tagged(overlay, kept)