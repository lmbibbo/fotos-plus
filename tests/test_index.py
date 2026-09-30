from __future__ import annotations

import json
from pathlib import Path

from fotos_plus.index import (
    default_index_path,
    index_path_for,
    read_index,
    read_suggestions,
    suggestions_path_for,
    suggestions_path_next_to,
    write_index,
    write_suggestions,
)
from fotos_plus.models import (
    LOCATION_KNOWN,
    LOCATION_UNKNOWN,
    STATUS_SUGGESTED,
    SUGGESTIONS_VERSION,
    PeriodSuggestion,
    Photo,
    ScanError,
    ScanResult,
    SuggestionsResult,
    TripSuggestion,
)


def make_result(root: Path) -> ScanResult:
    return ScanResult(
        root=str(root),
        scanned_at="2026-09-28T14:03:11",
        photos=[
            Photo(
                relative_path="2024/playa/IMG_0001.jpg",
                name="IMG_0001.jpg",
                extension=".jpg",
                size_bytes=3145728,
                sha256="a" * 64,
                captured_at="2024-07-15T18:22:04",
                captured_at_source="exif-datetime-original",
            ),
            Photo(
                relative_path="copia.jpg",
                name="copia.jpg",
                extension=".jpg",
                size_bytes=3145728,
                sha256="a" * 64,
                duplicate_of="2024/playa/IMG_0001.jpg",
            ),
        ],
        errors=[ScanError(relative_path="rota.jpg", error="unreadable image")],
    )


def test_write_index_leaves_a_single_file_and_no_temporary(
    tmp_path: Path, scanned_index
) -> None:
    result = make_result(tmp_path)
    path = scanned_index(result, tmp_path / "indice.json")

    assert path.is_file()
    assert [item.name for item in tmp_path.iterdir()] == ["indice.json"]


def test_index_round_trip_keeps_every_value(tmp_path: Path, scanned_index) -> None:
    result = make_result(tmp_path)
    path = scanned_index(result, tmp_path / "indice.json")

    loaded = read_index(path)

    assert loaded.root == result.root
    assert loaded.scanned_at == result.scanned_at
    assert [photo.to_dict() for photo in loaded.photos] == [
        photo.to_dict() for photo in result.photos
    ]
    assert [error.to_dict() for error in loaded.errors] == [
        error.to_dict() for error in result.errors
    ]
    assert loaded.duplicate_count == 1


def test_index_has_version_root_scanned_at_photos_and_errors(
    tmp_path: Path, scanned_index
) -> None:
    path = scanned_index(make_result(tmp_path), tmp_path / "indice.json")
    data = json.loads(path.read_text(encoding="utf-8"))

    assert data["version"] == 1
    assert data["root"] == str(tmp_path)
    assert data["scanned_at"] == "2026-09-28T14:03:11"
    assert len(data["photos"]) == 2
    assert data["errors"] == [
        {"relative_path": "rota.jpg", "error": "unreadable image"}
    ]
    assert data["photos"][0]["sha256"] == "a" * 64
    assert data["photos"][0]["duplicate_of"] is None


def test_default_index_path_is_stable_per_folder(tmp_path: Path) -> None:
    first = default_index_path(tmp_path / "vacaciones")
    second = default_index_path(tmp_path / "vacaciones")
    other = default_index_path(tmp_path / "otro")

    assert first == second
    assert first != other
    assert first.suffix == ".json"
    assert first.parent.name == "indexes"


def test_default_index_path_follows_case_insensitive_paths(tmp_path: Path) -> None:
    lower = default_index_path(tmp_path / "Fotos")
    upper = default_index_path(tmp_path / "fotos")

    assert lower == upper


def test_rescan_replaces_previous_index(tmp_path: Path) -> None:
    from fotos_plus.scanner import scan
    from tests.conftest import make_image

    photos = tmp_path / "fotos"
    photos.mkdir()
    make_image(photos / "una.jpg", color="red")
    index_path = tmp_path / "indice.json"

    first = scan(photos)
    write_index(first, index_path)
    make_image(photos / "dos.jpg", color="blue")
    second = scan(photos)
    write_index(second, index_path)

    loaded = read_index(index_path)
    assert [photo.name for photo in loaded.photos] == ["dos.jpg", "una.jpg"]
    assert [item.name for item in tmp_path.iterdir() if item.is_file()] == [
        "indice.json"
    ]


def test_index_path_for_without_dir_keeps_the_state_directory(tmp_path: Path) -> None:
    root = tmp_path / "fotos"

    assert index_path_for(root) == default_index_path(root)
    assert index_path_for(root, None) == default_index_path(root)


def test_index_path_for_uses_the_given_dir_and_same_file_name(
    tmp_path: Path,
) -> None:
    root = tmp_path / "fotos"
    destino = tmp_path / "mis-indices"

    with_dir = index_path_for(root, destino)
    without_dir = index_path_for(root)

    assert with_dir.parent == destino
    assert with_dir.name == without_dir.name


def test_two_folders_scanned_to_the_same_dir_do_not_overwrite(
    tmp_path: Path, scanned_index
) -> None:
    destino = tmp_path / "mis-indices"
    first = tmp_path / "vacaciones"
    second = tmp_path / "cumpleanos"
    first.mkdir()
    second.mkdir()

    write_index(make_result(first), index_path_for(first, destino))
    write_index(make_result(second), index_path_for(second, destino))

    files = sorted(item.name for item in destino.iterdir())
    assert len(files) == 2
    assert files == sorted(
        [index_path_for(first, destino).name, index_path_for(second, destino).name]
    )
    assert read_index(index_path_for(first, destino)).root == str(first)
    assert read_index(index_path_for(second, destino)).root == str(second)


def test_index_dir_is_created_when_missing(tmp_path: Path) -> None:
    from fotos_plus.scanner import scan
    from tests.conftest import make_image

    fotos = tmp_path / "fotos"
    fotos.mkdir()
    make_image(fotos / "una.jpg", color="red")
    destino = tmp_path / "nuevo" / "indices"

    write_index(scan(fotos), index_path_for(fotos, destino))

    assert destino.is_dir()
    assert read_index(index_path_for(fotos, destino)).photos[0].name == "una.jpg"


def make_suggestions(root: Path) -> SuggestionsResult:
    return SuggestionsResult(
        root=str(root),
        scanned_at="2026-09-28T14:03:11",
        trips=[
            TripSuggestion(
                photo_count=120,
                first_captured_at="2025-05-02T08:00:00",
                last_captured_at="2025-05-10T19:00:00",
                location_state=LOCATION_KNOWN,
                status=STATUS_SUGGESTED,
            )
        ],
        periods=[
            PeriodSuggestion(
                photo_count=12,
                first_captured_at="2024-03-01T10:00:00",
                last_captured_at="2024-03-04T18:00:00",
                location_state=LOCATION_UNKNOWN,
                status=STATUS_SUGGESTED,
            )
        ],
        reference_locatable_count=20,
        undated_photo_count=3,
    )


def test_suggestions_round_trip_keeps_every_value(tmp_path: Path) -> None:
    result = make_suggestions(tmp_path)
    path = write_suggestions(result, tmp_path / "sugerencias.json")

    loaded = read_suggestions(path)

    assert loaded.to_dict() == result.to_dict()


def test_suggestions_declare_themselves_provisional(tmp_path: Path) -> None:
    path = write_suggestions(make_suggestions(tmp_path), tmp_path / "sugerencias.json")
    data = json.loads(path.read_text(encoding="utf-8"))

    assert data["provisional"] is True
    assert "sugerencias" in data["notice"].lower()
    assert all(trip["status"] == STATUS_SUGGESTED for trip in data["trips"])
    assert all(period["status"] == STATUS_SUGGESTED for period in data["periods"])


def test_suggestions_keep_location_state_separate_from_status(tmp_path: Path) -> None:
    path = write_suggestions(make_suggestions(tmp_path), tmp_path / "sugerencias.json")
    data = json.loads(path.read_text(encoding="utf-8"))

    assert data["trips"][0]["location_state"] == LOCATION_KNOWN
    assert data["periods"][0]["location_state"] == LOCATION_UNKNOWN


def test_suggestions_have_their_own_format_version(tmp_path: Path) -> None:
    path = write_suggestions(make_suggestions(tmp_path), tmp_path / "sugerencias.json")
    data = json.loads(path.read_text(encoding="utf-8"))

    assert data["version"] == SUGGESTIONS_VERSION
    assert data["root"] == str(tmp_path)
    assert data["scanned_at"] == "2026-09-28T14:03:11"


def test_suggestions_declare_their_countries_version(tmp_path: Path) -> None:
    result = make_suggestions(tmp_path)
    result.countries_version = 3
    path = write_suggestions(result, tmp_path / "sugerencias.json")
    data = json.loads(path.read_text(encoding="utf-8"))

    assert data["countries_version"] == 3
    assert read_suggestions(path).countries_version == 3


def test_suggestions_from_before_the_country_field_still_load(tmp_path: Path) -> None:
    """Un archivo escrito por la version 1 se lee completo, sin perder sugerencias."""
    legacy = {
        "version": 1,
        "provisional": True,
        "notice": "sugerencias de viajes y periodos sin confirmar",
        "root": str(tmp_path),
        "scanned_at": "2026-09-28T14:03:11",
        "trips": [
            {
                "status": STATUS_SUGGESTED,
                "location_state": LOCATION_KNOWN,
                "photo_count": 120,
                "first_captured_at": "2025-05-02T08:00:00",
                "last_captured_at": "2025-05-10T19:00:00",
            },
            {
                "status": STATUS_SUGGESTED,
                "location_state": LOCATION_KNOWN,
                "photo_count": 60,
                "first_captured_at": "2025-02-10T10:00:00",
                "last_captured_at": "2025-02-20T20:00:00",
            },
        ],
        "periods": [
            {
                "status": STATUS_SUGGESTED,
                "location_state": LOCATION_UNKNOWN,
                "photo_count": 12,
                "first_captured_at": "2024-03-01T10:00:00",
                "last_captured_at": "2024-03-04T18:00:00",
            }
        ],
        "reference_locatable_count": 20,
        "undated_photo_count": 3,
    }
    path = tmp_path / "sugerencias.json"
    path.write_text(json.dumps(legacy), encoding="utf-8")

    loaded = read_suggestions(path)

    assert len(loaded.trips) == 2
    assert len(loaded.periods) == 1
    assert loaded.countries_version is None
    for trip in loaded.trips:
        assert trip.location is None
    assert loaded.trips_with_country_count == 0


def test_write_suggestions_leaves_a_single_file_and_no_temporary(
    tmp_path: Path,
) -> None:
    path = write_suggestions(make_suggestions(tmp_path), tmp_path / "sugerencias.json")

    assert path.is_file()
    assert [item.name for item in tmp_path.iterdir()] == ["sugerencias.json"]


def test_suggestions_path_for_shares_the_root_name_with_the_index(
    tmp_path: Path,
) -> None:
    root = tmp_path / "fotos"
    destino = tmp_path / "mis-indices"

    index = index_path_for(root, destino)
    suggestions = suggestions_path_for(root, destino)

    assert suggestions.parent == destino
    assert suggestions.name.startswith(index.stem)
    assert "sugerencias" in suggestions.name


def test_suggestions_path_next_to_an_explicit_index(tmp_path: Path) -> None:
    index = tmp_path / "mi-indice.json"
    suggestions = suggestions_path_next_to(index)

    assert suggestions.parent == tmp_path
    assert suggestions.name == "mi-indice-sugerencias.json"


def test_two_folders_scanned_to_the_same_dir_do_not_overwrite_suggestions(
    tmp_path: Path,
) -> None:
    destino = tmp_path / "mis-indices"
    first = tmp_path / "vacaciones"
    second = tmp_path / "cumpleanos"
    first.mkdir()
    second.mkdir()

    write_suggestions(make_suggestions(first), suggestions_path_for(first, destino))
    write_suggestions(make_suggestions(second), suggestions_path_for(second, destino))

    files = sorted(item.name for item in destino.iterdir())
    assert len(files) == 2
    assert read_suggestions(suggestions_path_for(first, destino)).root == str(first)
    assert read_suggestions(suggestions_path_for(second, destino)).root == str(second)


def test_suggestions_counts_the_photos_that_need_auditing(tmp_path: Path) -> None:
    result = make_suggestions(tmp_path)

    assert result.trips_to_audit_count == 12

