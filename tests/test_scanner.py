from __future__ import annotations

import os
from pathlib import Path

import pytest

from fotos_plus.scanner import ScanRootError, scan
from tests.conftest import make_image


def test_finds_photos_in_nested_directories(tmp_path: Path) -> None:
    make_image(tmp_path / "raiz.jpg", color="red")
    make_image(tmp_path / "2024/playa/agua.jpg", color="green")
    make_image(tmp_path / "2024/playa/arena/pesca.jpg", color="blue")

    result = scan(tmp_path)

    assert [photo.relative_path for photo in result.photos] == [
        "2024/playa/agua.jpg",
        "2024/playa/arena/pesca.jpg",
        "raiz.jpg",
    ]


def test_relative_path_matches_position_in_tree(tmp_path: Path) -> None:
    make_image(tmp_path / "viajes/2024/playa/IMG_0001.jpg", color="red")

    result = scan(tmp_path)

    photo = result.photos[0]
    assert photo.relative_path == "viajes/2024/playa/IMG_0001.jpg"
    assert (tmp_path / photo.relative_path).is_file()
    assert photo.name == "IMG_0001.jpg"


def test_non_photo_files_are_ignored(tmp_path: Path) -> None:
    make_image(tmp_path / "foto.jpg")
    (tmp_path / "documento.pdf").write_bytes(b"%PDF-1.4")
    (tmp_path / "notas.txt").write_text("hola")
    (tmp_path / "video.mp4").write_bytes(b"\x00\x00\x00\x18ftypmp42")

    result = scan(tmp_path)

    assert [photo.name for photo in result.photos] == ["foto.jpg"]


def test_empty_folder_gives_empty_inventory(tmp_path: Path) -> None:
    result = scan(tmp_path)

    assert result.photos == []
    assert result.errors == []


def test_corrupt_photo_is_reported_and_scan_continues(tmp_path: Path) -> None:
    make_image(tmp_path / "buena1.jpg")
    (tmp_path / "rota.jpg").write_bytes(b"no soy una imagen")
    make_image(tmp_path / "buena2.jpg")

    result = scan(tmp_path)

    assert [photo.name for photo in result.photos] == ["buena1.jpg", "buena2.jpg"]
    assert [error.relative_path for error in result.errors] == ["rota.jpg"]
    assert "unreadable image" in result.errors[0].error


def test_unreadable_directory_is_reported(tmp_path: Path, monkeypatch) -> None:
    make_image(tmp_path / "visible.jpg", color="red")
    locked = tmp_path / "cerrado"
    locked.mkdir()
    real_scandir = os.scandir

    def failing_scandir(path):
        if Path(path) == locked:
            raise PermissionError(13, "Permission denied", str(path))
        return real_scandir(path)

    monkeypatch.setattr(os, "scandir", failing_scandir)
    result = scan(tmp_path)

    assert [photo.name for photo in result.photos] == ["visible.jpg"]
    assert [error.relative_path for error in result.errors] == ["cerrado"]
    assert "cannot list directory" in result.errors[0].error


@pytest.mark.skipif(os.name == "nt", reason="en Windows los permisos no bloquean la lectura")
def test_unreadable_directory_with_real_permissions(tmp_path: Path) -> None:
    make_image(tmp_path / "visible.jpg", color="red")
    locked = tmp_path / "cerrado"
    make_image(locked / "oculta.jpg", color="blue")
    locked.chmod(0o000)
    try:
        result = scan(tmp_path)
    finally:
        locked.chmod(0o755)

    assert [photo.name for photo in result.photos] == ["visible.jpg"]
    assert any("cerrado" in error.relative_path for error in result.errors)


def test_results_are_sorted_and_deterministic(tmp_path: Path) -> None:
    for name in ("z.jpg", "a.jpg", "m/b.jpg", "m/a.jpg"):
        make_image(tmp_path / name)

    first = [photo.relative_path for photo in scan(tmp_path).photos]
    second = [photo.relative_path for photo in scan(tmp_path).photos]

    assert first == second == ["a.jpg", "m/a.jpg", "m/b.jpg", "z.jpg"]


def test_identical_copies_are_marked_as_duplicates(tmp_path: Path) -> None:
    original = make_image(tmp_path / "original.jpg", color="red")
    copy = tmp_path / "copias/copia.jpg"
    copy.parent.mkdir(parents=True, exist_ok=True)
    copy.write_bytes(original.read_bytes())
    make_image(tmp_path / "otra.jpg", color="blue")

    result = scan(tmp_path)
    by_path = {photo.relative_path: photo for photo in result.photos}

    assert by_path["copias/copia.jpg"].duplicate_of == "original.jpg"
    assert by_path["original.jpg"].duplicate_of is None
    assert by_path["otra.jpg"].duplicate_of is None
    assert result.duplicate_count == 1


def test_duplicate_original_is_the_shortest_relative_path(tmp_path: Path) -> None:
    first = make_image(tmp_path / "zz/original.jpg", color="red")
    second = tmp_path / "aa/copia.jpg"
    second.parent.mkdir(parents=True, exist_ok=True)
    second.write_bytes(first.read_bytes())
    third = tmp_path / "mm/otra-copia.jpg"
    third.parent.mkdir(parents=True, exist_ok=True)
    third.write_bytes(first.read_bytes())

    result = scan(tmp_path)
    by_path = {photo.relative_path: photo for photo in result.photos}

    assert by_path["aa/copia.jpg"].duplicate_of is None
    assert by_path["mm/otra-copia.jpg"].duplicate_of == "aa/copia.jpg"
    assert by_path["zz/original.jpg"].duplicate_of == "aa/copia.jpg"
    assert result.duplicate_count == 2


def test_missing_root_raises(tmp_path: Path) -> None:
    with pytest.raises(ScanRootError):
        scan(tmp_path / "no-existe")


def test_file_instead_of_directory_raises(tmp_path: Path) -> None:
    archivo = tmp_path / "foto.jpg"
    make_image(archivo)
    with pytest.raises(ScanRootError):
        scan(archivo)


def test_progress_callback_receives_total_and_counts_up(tmp_path: Path) -> None:
    make_image(tmp_path / "una.jpg", color="red")
    make_image(tmp_path / "sub/dos.jpg", color="green")
    (tmp_path / "tres.png").write_bytes(b"no soy una imagen")
    (tmp_path / "notas.txt").write_text("no es foto")
    seen: list[tuple[int, int]] = []

    result = scan(tmp_path, progress=lambda done, total: seen.append((done, total)))

    assert seen[-1] == (3, 3)
    assert [done for done, _ in seen] == [1, 2, 3]
    assert {total for _, total in seen} == {3}
    assert len(result.photos) + len(result.errors) == 3


def test_progress_total_excludes_non_photos(tmp_path: Path) -> None:
    make_image(tmp_path / "foto.jpg", color="red")
    for name in ("a.pdf", "b.txt", "c.mp4", "d.mov"):
        (tmp_path / name).write_bytes(b"x")
    seen: list[tuple[int, int]] = []

    scan(tmp_path, progress=lambda done, total: seen.append((done, total)))

    assert {total for _, total in seen} == {1}


def test_progress_callback_failure_does_not_abort_the_scan(tmp_path: Path) -> None:
    make_image(tmp_path / "una.jpg", color="red")
    make_image(tmp_path / "dos.jpg", color="green")

    def boom(done: int, total: int) -> None:
        raise RuntimeError("el progreso fallo")

    result = scan(tmp_path, progress=boom)

    assert [photo.name for photo in result.photos] == ["dos.jpg", "una.jpg"]


def test_scan_without_progress_callback_still_works(tmp_path: Path) -> None:
    make_image(tmp_path / "una.jpg", color="red")

    assert [photo.name for photo in scan(tmp_path).photos] == ["una.jpg"]
