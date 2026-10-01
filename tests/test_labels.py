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
    EMPTY_TAG_ERROR,
    LabelError,
    LabelOverlay,
    clear_tag,
    read_edicion,
    remove_label,
    resolve_labels,
    set_label,
    set_tag,
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

# --- Formato v2: catalogo de tags, asignaciones y migracion desde v1 ---


def test_new_overlay_serializes_tags_and_tagged() -> None:
    overlay = LabelOverlay(
        based_on_scanned_at="2026-01-01T00:00:00",
        tags=["Viaje", "Familia"],
        tagged={"2024-05-01T00:00:00": "Familia"},
    )

    data = overlay.to_dict()

    assert data["version"] == EDITION_VERSION
    assert data["version"] == 2
    assert data["tags"] == ["Viaje", "Familia"]
    assert data["tagged"] == {"2024-05-01T00:00:00": "Familia"}


def test_reads_a_v1_file_and_keeps_its_labels(tmp_path: Path) -> None:
    path = tmp_path / "x-edicion.json"
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "based_on_scanned_at": "2026-01-01T00:00:00",
                "labels": {"2024-05-01T00:00:00": "Bariloche"},
            }
        ),
        encoding="utf-8",
    )

    overlay = read_edicion(path)

    assert overlay.labels == {"2024-05-01T00:00:00": "Bariloche"}
    # migrado en memoria: sin tags, y no reescrito todavia en disco
    assert overlay.tags == []
    assert overlay.tagged == {}
    assert json.loads(path.read_text(encoding="utf-8"))["version"] == 1


def test_a_v1_file_is_written_as_v2_on_the_next_save(tmp_path: Path) -> None:
    path = tmp_path / "x-edicion.json"
    path.write_text(
        json.dumps({"version": 1, "labels": {"2024-05-01T00:00:00": "Bariloche"}}),
        encoding="utf-8",
    )
    overlay = read_edicion(path)

    write_edicion(
        LabelOverlay(
            based_on_scanned_at=overlay.based_on_scanned_at,
            labels=overlay.labels,
            tags=["Familia"],
        ),
        path,
    )

    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["version"] == 2
    assert saved["labels"] == {"2024-05-01T00:00:00": "Bariloche"}


def test_rejects_an_unknown_edit_version(tmp_path: Path) -> None:
    path = tmp_path / "x-edicion.json"
    path.write_text(json.dumps({"version": 99}), encoding="utf-8")

    with pytest.raises(LabelError) as error:
        read_edicion(path)

    assert "99" in str(error.value)


def test_tag_names_are_stripped_but_keep_their_case() -> None:
    overlay = LabelOverlay.from_dict(
        {
            "version": 2,
            "tags": ["Viaje", "  Familia  "],
            "tagged": {"2024-05-01T00:00:00": " familia "},
        }
    )

    # la forma guardada es la primera con la que se declaro el tag
    assert overlay.tags == ["Viaje", "Familia"]
    assert overlay.tagged == {"2024-05-01T00:00:00": "Familia"}


def test_catalog_rejects_an_empty_tag(tmp_path: Path) -> None:
    path = tmp_path / "x-edicion.json"
    path.write_text(json.dumps({"version": 2, "tags": ["Viaje", "   "]}), encoding="utf-8")

    with pytest.raises(LabelError) as error:
        read_edicion(path)

    assert str(error.value) == EMPTY_TAG_ERROR


def test_catalog_rejects_two_tags_that_only_differ_in_case() -> None:
    with pytest.raises(LabelError) as error:
        LabelOverlay.from_dict({"version": 2, "tags": ["Familia", "familia"]})

    assert "familia" in str(error.value)


def test_tagged_rejects_a_tag_absent_from_the_catalog() -> None:
    with pytest.raises(LabelError) as error:
        LabelOverlay.from_dict(
            {"version": 2, "tags": ["Viaje"], "tagged": {"2024-05-01T00:00:00": "Familia"}}
        )

    assert "Familia" in str(error.value)


def test_canonical_tag_matches_ignoring_case_and_spaces() -> None:
    overlay = LabelOverlay(tags=["Familia"])

    assert overlay.canonical_tag(" familia ") == "Familia"
    assert overlay.canonical_tag("Viaje") is None
    assert overlay.canonical_tag("   ") is None


def test_write_rejects_a_hand_edited_assignment_to_an_unknown_tag(tmp_path: Path) -> None:
    path = tmp_path / "x-edicion.json"
    overlay = LabelOverlay(
        tags=["Viaje"],
        tagged={"2024-05-01T00:00:00": "Familia"},
    )

    with pytest.raises(LabelError):
        write_edicion(overlay, path)

    assert not path.exists()


def test_write_rejects_a_repeated_tag_in_the_catalog(tmp_path: Path) -> None:
    path = tmp_path / "x-edicion.json"

    with pytest.raises(LabelError):
        write_edicion(LabelOverlay(tags=["Familia", " FAMILIA "]), path)

    assert not path.exists()


def test_tags_survive_a_write_and_read_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "x-edicion.json"
    overlay = LabelOverlay(
        based_on_scanned_at="2026-01-01T00:00:00",
        labels={"2024-05-01T00:00:00": "Navidad"},
        tags=["Viaje", "Familia"],
        tagged={"2024-05-01T00:00:00": "Familia"},
    )

    write_edicion(overlay, path)

    assert read_edicion(path) == overlay


# --- Operaciones de tag ---


def _groups(*keys: str) -> SuggestionsResult:
    return SuggestionsResult(
        root="r",
        scanned_at="2026-01-01T00:00:00",
        trips=[trip(key, key) for key in keys],
        periods=[],
    )


def test_set_tag_creates_the_tag_in_the_catalog() -> None:
    groups = _groups("2024-05-01T00:00:00")

    overlay = set_tag(LabelOverlay(tags=["Viaje"]), groups, "2024-05-01T00:00:00", "Trabajo")

    assert overlay.tags == ["Viaje", "Trabajo"]
    assert overlay.tagged == {"2024-05-01T00:00:00": "Trabajo"}


def test_set_tag_reuses_an_equivalent_existing_tag() -> None:
    groups = _groups("2024-05-01T00:00:00")
    before = LabelOverlay(tags=["Familia"])

    overlay = set_tag(before, groups, "2024-05-01T00:00:00", " familia ")

    assert overlay.tags == ["Familia"]
    assert overlay.tagged == {"2024-05-01T00:00:00": "Familia"}


def test_set_tag_does_not_mutate_the_overlay_it_receives() -> None:
    groups = _groups("2024-05-01T00:00:00")
    before = LabelOverlay(tags=["Viaje"])

    set_tag(before, groups, "2024-05-01T00:00:00", "Familia")

    assert before.tags == ["Viaje"]
    assert before.tagged == {}


def test_set_tag_replaces_the_previous_tag_of_the_group() -> None:
    groups = _groups("2024-05-01T00:00:00")
    before = LabelOverlay(tags=["Viaje", "Familia"], tagged={"2024-05-01T00:00:00": "Familia"})

    overlay = set_tag(before, groups, "2024-05-01T00:00:00", "Viaje")

    assert overlay.tagged == {"2024-05-01T00:00:00": "Viaje"}
    # el catalogo conserva los dos tags
    assert overlay.tags == ["Viaje", "Familia"]


def test_set_tag_keeps_the_title_of_the_group() -> None:
    groups = _groups("2024-05-01T00:00:00")
    before = LabelOverlay(
        labels={"2024-05-01T00:00:00": "Navidad"},
        tags=["Familia"],
    )

    overlay = set_tag(before, groups, "2024-05-01T00:00:00", "Familia")

    assert overlay.labels == {"2024-05-01T00:00:00": "Navidad"}
    assert overlay.tagged == {"2024-05-01T00:00:00": "Familia"}


def test_set_tag_rejects_an_empty_tag() -> None:
    groups = _groups("2024-05-01T00:00:00")

    with pytest.raises(LabelError) as error:
        set_tag(LabelOverlay(), groups, "2024-05-01T00:00:00", "   ")

    assert str(error.value) == EMPTY_TAG_ERROR


def test_set_tag_rejects_a_reference_that_does_not_resolve() -> None:
    groups = _groups("2024-05-01T00:00:00")

    with pytest.raises(LabelError) as error:
        set_tag(LabelOverlay(), groups, "2030-01-01T00:00:00", "Familia")

    assert "no corresponde a ningun grupo actual" in str(error.value)


def test_set_tag_rejects_an_ambiguous_reference() -> None:
    groups = SuggestionsResult(
        root="r",
        scanned_at="2026-01-01T00:00:00",
        trips=[trip("2024-05-01T00:00:00", "2024-05-02T00:00:00")],
        periods=[period("2024-05-01T00:00:00", "2024-05-02T00:00:00")],
    )

    with pytest.raises(LabelError) as error:
        set_tag(LabelOverlay(), groups, "2024-05-01T00:00:00", "Familia")

    assert "es ambigua" in str(error.value)


def test_clear_tag_drops_the_assignment_and_keeps_the_catalog() -> None:
    before = LabelOverlay(
        tags=["Viaje", "Familia"],
        tagged={"2024-05-01T00:00:00": "Familia"},
    )

    overlay = clear_tag(before, "2024-05-01T00:00:00")

    assert overlay.tagged == {}
    assert overlay.tags == ["Viaje", "Familia"]


def test_clear_tag_rejects_a_group_without_a_tag() -> None:
    with pytest.raises(LabelError) as error:
        clear_tag(LabelOverlay(tags=["Familia"]), "2024-05-01T00:00:00")

    assert "no tiene tag para quitar" in str(error.value)


def test_saving_a_title_keeps_the_tags(tmp_path: Path) -> None:
    groups = _groups("2024-05-01T00:00:00")
    overlay = set_tag(LabelOverlay(), groups, "2024-05-01T00:00:00", "Familia")

    renamed = set_label(overlay, groups, "2024-05-01T00:00:00", "Navidad")

    assert renamed.tags == ["Familia"]
    assert renamed.tagged == {"2024-05-01T00:00:00": "Familia"}


def test_removing_a_title_keeps_the_tags() -> None:
    groups = _groups("2024-05-01T00:00:00")
    overlay = set_label(
        set_tag(LabelOverlay(), groups, "2024-05-01T00:00:00", "Familia"),
        groups,
        "2024-05-01T00:00:00",
        "Navidad",
    )

    untitled = remove_label(overlay, "2024-05-01T00:00:00")

    assert untitled.labels == {}
    assert untitled.tags == ["Familia"]
    assert untitled.tagged == {"2024-05-01T00:00:00": "Familia"}


def test_resolution_reports_resolved_tags() -> None:
    groups = _groups("2024-05-01T00:00:00", "2024-09-01T00:00:00")
    overlay = LabelOverlay(
        tags=["Viaje"],
        tagged={
            "2024-05-01T00:00:00": "Viaje",
            "2024-09-01T00:00:00": "Viaje",
        },
    )

    resolution = resolve_labels(overlay, groups)

    assert resolution.tagged_count == 2
    assert resolution.tags == overlay.tagged
    assert resolution.drifted is False


def test_resolution_reports_a_tag_left_dangling_by_a_rescan() -> None:
    groups = _groups("2024-05-01T00:00:00")
    overlay = LabelOverlay(
        tags=["Viaje"],
        tagged={
            "2024-05-01T00:00:00": "Viaje",
            "2030-01-01T00:00:00": "Viaje",
        },
    )

    resolution = resolve_labels(overlay, groups)

    assert resolution.tagged_count == 1
    assert resolution.unresolved_tags == ["2030-01-01T00:00:00"]
    assert resolution.dangling_count == 1
    assert resolution.drifted is True
    # la asignacion huerfana sigue guardada
    assert overlay.tagged["2030-01-01T00:00:00"] == "Viaje"


def test_a_dangling_tag_alone_marks_the_overlay_as_drifted() -> None:
    groups = _groups("2024-05-01T00:00:00")
    overlay = LabelOverlay(based_on_scanned_at="2026-01-01T00:00:00", tags=["Viaje"])

    resolution = resolve_labels(overlay, groups)

    assert resolution.scan_advanced is False
    assert resolution.drifted is False

    orphan = LabelOverlay(
        based_on_scanned_at="2026-01-01T00:00:00",
        tags=["Viaje"],
        tagged={"2030-01-01T00:00:00": "Viaje"},
    )

    assert resolve_labels(orphan, groups).drifted is True
