from __future__ import annotations

import json
from pathlib import Path

from fotos_plus.index import default_index_path, read_index, write_index
from fotos_plus.models import Photo, ScanError, ScanResult


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
