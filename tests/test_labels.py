from __future__ import annotations

import json
from pathlib import Path

import pytest

from fotos_plus.index import (
    EDITION_SUFFIX,
    SUGGESTIONS_SUFFIX,
    edicion_path_next_to,
    suggestions_path_next_to,
)
from fotos_plus.labels import (
    EDITION_VERSION,
    EMPTY_LABEL_ERROR,
    LabelError,
    LabelOverlay,
    read_edicion,
    remove_label,
    resolve_labels,
    set_label,
    validate_label,
    write_edicion,
)
from fotos_plus.models import (
    LOCATION_KNOWN,
    LOCATION_UNKNOWN,
    STATUS_SUGGESTED,
    PeriodSuggestion,
    SuggestionsResult,
    TripLocation,
    TripSuggestion,
)


def trip(start: str, end: str, country: str | None = "Argentina") -> TripSuggestion:
    location = TripLocation(country=country, countries=[country] if country else [])
    return TripSuggestion(
        photo_count=1,
        first_captured_at=start,
        last_captured_at=end,
        location_state=LOCATION_KNOWN,
        status=STATUS_SUGGESTED,
        location=location,
    )


def period(start: str, end: str) -> PeriodSuggestion:
    return PeriodSuggestion(
        photo_count=1,
        first_captured_at=start,
        last_captured_at=end,
        location_state=LOCATION_UNKNOWN,
        status=STATUS_SUGGESTED,
    )


def suggestions(scanned_at: str = "2026-01-01T00:00:00", trips=(), periods=()):
    return SuggestionsResult(
        root="C:/fotos",
        scanned_at=scanned_at,
        trips=list(trips),
        periods=list(periods),
    )


# --- 1.1 ruta del archivo de edicion -----------------------------------------


def test_edicion_path_next_to_the_index(tmp_path: Path) -> None:
    index_path = tmp_path / "indice.json"

    path = edicion_path_next_to(index_path)

    assert path.name == f"indice{EDITION_SUFFIX}.json"
    assert path.parent == tmp_path


def test_edicion_path_does_not_collide_with_suggestions(tmp_path: Path) -> None:
    index_path = tmp_path / "indice.json"

    assert edicion_path_next_to(index_path) != suggestions_path_next_to(index_path)


def test_edicion_path_keeps_the_index_base_name(tmp_path: Path) -> None:
    index_path = tmp_path / "5d863d53b7cdd449.json"

    assert edicion_path_next_to(index_path).name == "5d863d53b7cdd449-edicion.json"
    assert SUGGESTIONS_SUFFIX != EDITION_SUFFIX


# --- 1.2 lectura --------------------------------------------------------------


def test_missing_edicion_reads_as_empty(tmp_path: Path) -> None:
    overlay = read_edicion(tmp_path / "no-existe.json")

    assert overlay.labels == {}
    assert overlay.based_on_scanned_at is None


def test_valid_edicion_is_indexed_by_first_captured_at(tmp_path: Path) -> None:
    path = tmp_path / "indice-edicion.json"
    path.write_text(
        json.dumps(
            {
                "version": EDITION_VERSION,
                "based_on_scanned_at": "2026-01-01T00:00:00",
                "labels": {"2023-07-19T10:32:39": "Viaje a Bariloche"},
            }
        ),
        encoding="utf-8",
    )

    overlay = read_edicion(path)

    assert overlay.labels == {"2023-07-19T10:32:39": "Viaje a Bariloche"}
    assert overlay.based_on_scanned_at == "2026-01-01T00:00:00"


def test_edition_without_labels_key_reads_as_empty(tmp_path: Path) -> None:
    path = tmp_path / "indice-edicion.json"
    path.write_text(json.dumps({"version": EDITION_VERSION}), encoding="utf-8")

    assert read_edicion(path).labels == {}


def test_corrupt_json_reports_an_explicit_error(tmp_path: Path) -> None:
    path = tmp_path / "indice-edicion.json"
    path.write_text('{"version": 1, "labels": {s}}', encoding="utf-8")

    with pytest.raises(LabelError) as caught:
        read_edicion(path)

    assert "JSON valido" in str(caught.value)


def test_wrong_version_is_rejected_with_a_clear_message(tmp_path: Path) -> None:
    path = tmp_path / "indice-edicion.json"
    path.write_text(json.dumps({"version": 99, "labels": {}}), encoding="utf-8")

    with pytest.raises(LabelError) as caught:
        read_edicion(path)

    assert "version de edicion no soportada" in str(caught.value)


def test_labels_that_is_not_an_object_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "indice-edicion.json"
    path.write_text(
        json.dumps({"version": EDITION_VERSION, "labels": ["a"]}), encoding="utf-8"
    )

    with pytest.raises(LabelError) as caught:
        read_edicion(path)

    assert "no es un objeto JSON" in str(caught.value)


def test_reading_trims_surrounding_whitespace(tmp_path: Path) -> None:
    path = tmp_path / "indice-edicion.json"
    path.write_text(
        json.dumps(
            {"version": EDITION_VERSION, "labels": {"2024-01-01T00:00:00": "  Casa  "}}
        ),
        encoding="utf-8",
    )

    assert read_edicion(path).labels == {"2024-01-01T00:00:00": "Casa"}


def test_hand_written_empty_label_is_rejected_on_read(tmp_path: Path) -> None:
    path = tmp_path / "indice-edicion.json"
    path.write_text(
        json.dumps({"version": EDITION_VERSION, "labels": {"2024-01-01T00:00:00": "   "}}),
        encoding="utf-8",
    )

    with pytest.raises(LabelError) as caught:
        read_edicion(path)

    assert str(caught.value) == EMPTY_LABEL_ERROR


# --- 1.3 escritura atomica ----------------------------------------------------


def test_writing_records_the_scan_it_was_built_against(tmp_path: Path) -> None:
    path = tmp_path / "indice-edicion.json"

    write_edicion(LabelOverlay(based_on_scanned_at="2026-02-02T10:00:00"), path)

    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["version"] == EDITION_VERSION
    assert data["based_on_scanned_at"] == "2026-02-02T10:00:00"


def test_writing_leaves_no_temporary_file_behind(tmp_path: Path) -> None:
    path = tmp_path / "indice-edicion.json"

    write_edicion(LabelOverlay(based_on_scanned_at="2026-01-01T00:00:00"), path)

    assert [p.name for p in tmp_path.iterdir()] == ["indice-edicion.json"]


def test_overwriting_an_existing_edition_leaves_no_temporary(tmp_path: Path) -> None:
    path = tmp_path / "indice-edicion.json"
    write_edicion(LabelOverlay(based_on_scanned_at="2026-01-01T00:00:00"), path)

    write_edicion(
        LabelOverlay(
            based_on_scanned_at="2026-01-02T00:00:00",
            labels={"2024-01-01T00:00:00": "Casa"},
        ),
        path,
    )

    assert [p.name for p in tmp_path.iterdir()] == ["indice-edicion.json"]
    assert read_edicion(path).labels == {"2024-01-01T00:00:00": "Casa"}


def test_written_file_round_trips(tmp_path: Path) -> None:
    path = tmp_path / "indice-edicion.json"
    overlay = LabelOverlay(
        based_on_scanned_at="2026-01-01T00:00:00",
        labels={"2024-05-01T00:00:00": "Bariloche", "2024-07-01T00:00:00": "Casa"},
    )

    write_edicion(overlay, path)

    assert read_edicion(path) == overlay


# --- 1.4 etiqueta vacia en la escritura ---------------------------------------


@pytest.mark.parametrize("value", ["", "   ", "\t\n "])
def test_writing_an_empty_label_is_rejected(value: str) -> None:
    overlay = LabelOverlay(labels={"2024-01-01T00:00:00": value})

    with pytest.raises(LabelError) as caught:
        write_edicion(overlay, Path("no-llega-a-escribirse.json"))

    assert str(caught.value) == EMPTY_LABEL_ERROR


def test_rejected_empty_label_leaves_the_previous_file_untouched(tmp_path: Path) -> None:
    path = tmp_path / "indice-edicion.json"
    write_edicion(
        LabelOverlay(
            based_on_scanned_at="2026-01-01T00:00:00",
            labels={"2024-01-01T00:00:00": "Casa"},
        ),
        path,
    )
    before = path.read_bytes()

    with pytest.raises(LabelError):
        write_edicion(
            LabelOverlay(
                based_on_scanned_at="2026-01-01T00:00:00",
                labels={"2024-01-01T00:00:00": "  "},
            ),
            path,
        )

    assert path.read_bytes() == before
    assert read_edicion(path).labels == {"2024-01-01T00:00:00": "Casa"}


# --- 2.1 resolucion de la referencia ------------------------------------------


def test_a_reference_to_one_group_resolves() -> None:
    groups = suggestions(trips=[trip("2024-05-01T00:00:00", "2024-05-02T00:00:00")])

    resolution = resolve_labels(
        LabelOverlay(labels={"2024-05-01T00:00:00": "Bariloche"}), groups
    )

    assert resolution.labels == {"2024-05-01T00:00:00": "Bariloche"}
    assert resolution.unresolved == []
    assert resolution.ambiguous == []


def test_a_reference_to_no_group_is_reported_and_not_applied() -> None:
    groups = suggestions(trips=[trip("2024-05-01T00:00:00", "2024-05-02T00:00:00")])

    with pytest.raises(LabelError) as caught:
        validate_label("2030-01-01T00:00:00", "Perdida", groups)

    assert "no corresponde a ningun grupo actual" in str(caught.value)


def test_an_ambiguous_reference_is_rejected() -> None:
    groups = suggestions(
        trips=[trip("2024-05-01T00:00:00", "2024-05-02T00:00:00")],
        periods=[period("2024-05-01T00:00:00", "2024-05-02T00:00:00")],
    )

    with pytest.raises(LabelError) as caught:
        validate_label("2024-05-01T00:00:00", "Repetida", groups)

    assert "es ambigua" in str(caught.value)


def test_an_ambiguous_reference_is_reported_when_resolving() -> None:
    groups = suggestions(
        trips=[trip("2024-05-01T00:00:00", "2024-05-02T00:00:00")],
        periods=[period("2024-05-01T00:00:00", "2024-05-02T00:00:00")],
    )

    resolution = resolve_labels(
        LabelOverlay(labels={"2024-05-01T00:00:00": "Repetida"}), groups
    )

    assert resolution.labels == {}
    assert resolution.ambiguous == ["2024-05-01T00:00:00"]


def test_an_empty_label_is_rejected_before_the_reference_is_checked() -> None:
    groups = suggestions(trips=[trip("2024-05-01T00:00:00", "2024-05-02T00:00:00")])

    with pytest.raises(LabelError) as caught:
        validate_label("2024-05-01T00:00:00", "   ", groups)

    assert str(caught.value) == EMPTY_LABEL_ERROR


def test_a_missing_reference_is_rejected() -> None:
    with pytest.raises(LabelError) as caught:
        validate_label("", "Bariloche", suggestions())

    assert "falta la referencia" in str(caught.value)


def test_setting_a_label_trims_it_and_does_not_mutate_the_original() -> None:
    groups = suggestions(trips=[trip("2024-05-01T00:00:00", "2024-05-02T00:00:00")])
    original = LabelOverlay(based_on_scanned_at="2026-01-01T00:00:00")

    updated = set_label(
        original, groups, "2024-05-01T00:00:00", "  Bariloche  ", "2026-03-01T00:00:00"
    )

    assert updated.labels == {"2024-05-01T00:00:00": "Bariloche"}
    assert updated.based_on_scanned_at == "2026-03-01T00:00:00"
    assert original.labels == {}


def test_removing_a_label_deletes_the_entry() -> None:
    overlay = LabelOverlay(
        based_on_scanned_at="2026-01-01T00:00:00",
        labels={"2024-05-01T00:00:00": "Bariloche"},
    )

    updated = remove_label(overlay, "2024-05-01T00:00:00")

    assert updated.labels == {}
    assert updated.based_on_scanned_at == "2026-01-01T00:00:00"
    assert overlay.labels == {"2024-05-01T00:00:00": "Bariloche"}


def test_a_dangling_label_can_still_be_removed() -> None:
    """Una etiqueta que quedo huerfana por un rescaneo tiene que poder limpiarse."""
    overlay = LabelOverlay(labels={"2030-01-01T00:00:00": "Perdida"})

    assert remove_label(overlay, "2030-01-01T00:00:00").labels == {}


def test_removing_a_label_that_does_not_exist_is_rejected() -> None:
    with pytest.raises(LabelError) as caught:
        remove_label(LabelOverlay(), "2024-05-01T00:00:00")

    assert "no tiene etiqueta para quitar" in str(caught.value)


# --- 2.2 deriva respecto del escaneo ------------------------------------------


def test_an_aligned_edit_file_shows_no_drift() -> None:
    groups = suggestions(
        scanned_at="2026-01-01T00:00:00",
        trips=[trip("2024-05-01T00:00:00", "2024-05-02T00:00:00")],
    )
    overlay = LabelOverlay(
        based_on_scanned_at="2026-01-01T00:00:00",
        labels={"2024-05-01T00:00:00": "Bariloche"},
    )

    resolution = resolve_labels(overlay, groups)

    assert resolution.scan_advanced is False
    assert resolution.drifted is False
    assert resolution.resolved_count == 1
    assert resolution.dangling_count == 0


def test_a_newer_scan_reports_drift_and_keeps_the_labels() -> None:
    groups = suggestions(
        scanned_at="2026-06-01T00:00:00",
        trips=[trip("2024-05-01T00:00:00", "2024-05-02T00:00:00")],
    )
    overlay = LabelOverlay(
        based_on_scanned_at="2026-01-01T00:00:00",
        labels={"2024-05-01T00:00:00": "Bariloche"},
    )

    resolution = resolve_labels(overlay, groups)

    assert resolution.scan_advanced is True
    assert resolution.drifted is True
    # la etiqueta sigue aplicando y no se descarta
    assert resolution.labels == {"2024-05-01T00:00:00": "Bariloche"}


def test_drift_counts_split_resolved_from_dangling() -> None:
    groups = suggestions(
        scanned_at="2026-01-01T00:00:00",
        trips=[
            trip("2024-05-01T00:00:00", "2024-05-02T00:00:00"),
            trip("2024-09-01T00:00:00", "2024-09-02T00:00:00"),
        ],
    )
    overlay = LabelOverlay(
        based_on_scanned_at="2026-01-01T00:00:00",
        labels={
            "2024-05-01T00:00:00": "Bariloche",
            "2024-09-01T00:00:00": "Cusco",
            "2030-01-01T00:00:00": "Perdida",
        },
    )

    resolution = resolve_labels(overlay, groups)

    assert resolution.resolved_count == 2
    assert resolution.dangling_count == 1
    assert resolution.unresolved == ["2030-01-01T00:00:00"]
    assert resolution.drifted is True


def test_an_edit_file_without_a_scan_stamp_is_not_reported_as_drifted() -> None:
    groups = suggestions(
        scanned_at="2026-06-01T00:00:00",
        trips=[trip("2024-05-01T00:00:00", "2024-05-02T00:00:00")],
    )

    resolution = resolve_labels(
        LabelOverlay(labels={"2024-05-01T00:00:00": "Bariloche"}), groups
    )

    assert resolution.scan_advanced is False
    assert resolution.drifted is False