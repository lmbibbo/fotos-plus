from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .index import write_json_atomic
from .models import SuggestionsResult

EDITION_VERSION = 1

EMPTY_LABEL_ERROR = "una etiqueta no puede estar vacia"


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


@dataclass
class LabelOverlay:
    """Etiquetas escritas por el usuario, indexadas por la fecha mas temprana del grupo.

    La clave es `first_captured_at` del grupo, que es el mismo dato que el visor ya
    usa para ordenar las tarjetas. Es unica entre los grupos porque el escaneo reparte
    las fotos sin solaparse: cada grupo arranca en una foto distinta.
    """

    based_on_scanned_at: Optional[str] = None
    labels: dict[str, str] = field(default_factory=dict)

    def title_for(self, key: str) -> Optional[str]:
        """Etiqueta vigente para una referencia, o None si el grupo no tiene."""
        return self.labels.get(key)

    def to_dict(self) -> dict:
        return {
            "version": EDITION_VERSION,
            "based_on_scanned_at": self.based_on_scanned_at,
            "labels": dict(sorted(self.labels.items())),
        }

    @classmethod
    def from_dict(cls, data: object) -> "LabelOverlay":
        if not isinstance(data, dict):
            raise LabelError("el archivo de edicion no es un objeto JSON")
        version = data.get("version")
        if version != EDITION_VERSION:
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

        return cls(based_on_scanned_at=based_on, labels=labels)


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

    Se vuelve a validar cada etiqueta antes de escribir: el archivo tambien puede
    venir editado a mano, y no debe quedar guardada una etiqueta vacia.
    """
    for value in overlay.labels.values():
        _clean_text(value)
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
    """Como quedan las etiquetas al cruzarlas con los grupos del escaneo vigente."""

    labels: dict[str, str] = field(default_factory=dict)
    unresolved: list[str] = field(default_factory=list)
    ambiguous: list[str] = field(default_factory=list)
    scan_advanced: bool = False

    @property
    def resolved_count(self) -> int:
        return len(self.labels)

    @property
    def dangling_count(self) -> int:
        return len(self.unresolved) + len(self.ambiguous)

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

    Una etiqueta se aplica solo si su referencia resuelve a exactamente un grupo. Las
    que no resuelven no se descartan: quedan listadas para que el usuario decida, y
    siguen guardadas en el archivo.
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
    return LabelOverlay(based_on_scanned_at=overlay.based_on_scanned_at, labels=labels)