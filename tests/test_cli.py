from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from fotos_plus.cli import EXIT_OK, EXIT_PATH_ERROR, EXIT_USAGE, main
from fotos_plus.index import read_index
from tests.conftest import make_image


def build_library(root: Path) -> Path:
    library = root / "fotos"
    library.mkdir()
    make_image(library / "2024/playa/agua.jpg", color="red")
    make_image(library / "2024/montana/nieve.jpg", color="green")
    (library / "2024/montana/copia.jpg").write_bytes(
        (library / "2024/playa/agua.jpg").read_bytes()
    )
    (library / "notas.txt").write_text("no soy una foto")
    (library / "rota.jpg").write_bytes(b"no soy una imagen")
    return library


def snapshot(root: Path) -> dict[str, tuple[int, str]]:
    state = {}
    for path in sorted(root.rglob("*")):
        if path.is_file():
            state[path.relative_to(root).as_posix()] = (
                path.stat().st_size,
                hashlib.sha256(path.read_bytes()).hexdigest(),
            )
    return state


def test_scan_exits_zero_and_writes_index(tmp_path: Path, capsys) -> None:
    library = build_library(tmp_path)
    index_path = tmp_path / "indice.json"

    code = main(["scan", str(library), "--index", str(index_path)])

    assert code == EXIT_OK
    assert index_path.is_file()
    result = read_index(index_path)
    assert [photo.relative_path for photo in result.photos] == [
        "2024/montana/copia.jpg",
        "2024/montana/nieve.jpg",
        "2024/playa/agua.jpg",
    ]


def test_scan_of_missing_path_exits_with_path_error(tmp_path: Path, capsys) -> None:
    code = main(["scan", str(tmp_path / "no-existe")])

    assert code == EXIT_PATH_ERROR
    assert "does not exist" in capsys.readouterr().err


def test_scan_of_file_instead_of_folder_exits_with_path_error(
    tmp_path: Path, capsys
) -> None:
    photo = make_image(tmp_path / "foto.jpg", color="red")

    code = main(["scan", str(photo)])

    assert code == EXIT_PATH_ERROR
    assert "not a directory" in capsys.readouterr().err


def test_invalid_arguments_exit_with_usage_error(capsys) -> None:
    assert main([]) == EXIT_USAGE
    assert main(["scan"]) == EXIT_USAGE
    assert main(["orden-desconocido"]) == EXIT_USAGE
    assert capsys.readouterr().err


def test_summary_matches_the_written_index(tmp_path: Path, capsys) -> None:
    library = build_library(tmp_path)
    index_path = tmp_path / "indice.json"

    main(["scan", str(library), "--index", str(index_path)])
    out = capsys.readouterr().out
    result = read_index(index_path)

    assert f"Fotos encontradas: {len(result.photos)}" in out
    assert f"Duplicados: {result.duplicate_count}" in out
    assert f"Archivos con error: {len(result.errors)}" in out
    assert str(index_path) in out
    assert "rota.jpg: unreadable image" in out


def test_two_scans_do_not_alter_the_library(tmp_path: Path) -> None:
    library = build_library(tmp_path)
    before = snapshot(library)

    main(["scan", str(library), "--index", str(tmp_path / "a.json")])
    after_first = snapshot(library)
    main(["scan", str(library), "--index", str(tmp_path / "b.json")])
    after_second = snapshot(library)

    assert after_first == before
    assert after_second == before


def test_default_index_path_is_used_when_not_given(
    tmp_path: Path, capsys, monkeypatch
) -> None:
    library = build_library(tmp_path)
    state = tmp_path / "estado"
    monkeypatch.setenv("LOCALAPPDATA", str(state))

    main(["scan", str(library)])
    out = capsys.readouterr().out

    index_path = state / "fotos-plus" / "indexes"
    assert index_path.is_dir()
    written = list(index_path.glob("*.json"))
    assert len(written) == 1
    assert str(written[0]) in out
