from __future__ import annotations

import hashlib
import sys
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


def test_index_dir_where_the_index_is_written(tmp_path: Path, capsys) -> None:
    library = build_library(tmp_path)
    destino = tmp_path / "mis-indices"

    code = main(["scan", str(library), "--index-dir", str(destino)])
    out = capsys.readouterr().out

    assert code == EXIT_OK
    assert destino.is_dir()
    written = list(destino.glob("*.json"))
    assert len(written) == 1
    assert read_index(written[0]).root == str(library)
    assert str(written[0]) in out


def test_index_wins_over_index_dir(tmp_path: Path, capsys) -> None:
    library = build_library(tmp_path)
    destino = tmp_path / "mis-indices"
    puntual = tmp_path / "este-indice.json"

    code = main(
        [
            "scan",
            str(library),
            "--index",
            str(puntual),
            "--index-dir",
            str(destino),
        ]
    )

    assert code == EXIT_OK
    assert puntual.is_file()
    assert not destino.exists()
    assert read_index(puntual).root == str(library)


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


def test_summary_starts_on_its_own_line_after_progress(
    tmp_path: Path, capsys, monkeypatch
) -> None:
    library = build_library(tmp_path)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True, raising=False)

    main(["scan", str(library), "--index", str(tmp_path / "i.json")])
    out = capsys.readouterr().out

    progress_line, first_summary_line = out.split("\n")[:2]
    assert "100%)" in progress_line
    assert first_summary_line == f"Carpeta escaneada: {library}"


def test_progress_is_shown_in_a_terminal(
    tmp_path: Path, capsys, monkeypatch
) -> None:
    library = build_library(tmp_path)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True, raising=False)

    main(["scan", str(library), "--index", str(tmp_path / "i.json")])
    out = capsys.readouterr().out

    assert "\r" in out
    assert "Escaneando..." in out
    assert "Fotos encontradas: 3" in out


def test_progress_is_not_shown_when_output_is_redirected(
    tmp_path: Path, capsys
) -> None:
    library = build_library(tmp_path)

    main(["scan", str(library), "--index", str(tmp_path / "i.json")])
    out = capsys.readouterr().out

    assert "\r" not in out
    assert "Escaneando" not in out
    assert "Fotos encontradas: 3" in out


def test_progress_can_be_disabled_by_environment(
    tmp_path: Path, capsys, monkeypatch
) -> None:
    library = build_library(tmp_path)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True, raising=False)
    monkeypatch.setenv("FOTOS_PLUS_NO_PROGRESS", "1")

    main(["scan", str(library), "--index", str(tmp_path / "i.json")])
    out = capsys.readouterr().out

    assert "\r" not in out
    assert "Escaneando" not in out
    assert "Fotos encontradas: 3" in out


def test_no_progress_line_when_folder_has_no_photos(
    tmp_path: Path, capsys, monkeypatch
) -> None:
    empty = tmp_path / "vacia"
    empty.mkdir()
    (empty / "notas.txt").write_text("nada aqui")
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True, raising=False)

    code = main(["scan", str(empty), "--index", str(tmp_path / "i.json")])
    out = capsys.readouterr().out

    assert code == EXIT_OK
    assert "Escaneando" not in out
    assert "Fotos encontradas: 0" in out


def test_progress_reaches_one_hundred_percent(
    tmp_path: Path, capsys, monkeypatch
) -> None:
    library = tmp_path / "fotos"
    library.mkdir()
    for number in range(30):
        make_image(library / f"foto-{number:03d}.jpg", color="red")
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True, raising=False)

    main(["scan", str(library), "--index", str(tmp_path / "i.json")])
    out = capsys.readouterr().out

    assert "30/30 (100%)" in out
