from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pytest

from fotos_plus.cli import EXIT_OK, EXIT_PATH_ERROR, EXIT_USAGE, main
from fotos_plus.index import read_index, read_suggestions, suggestions_path_next_to
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
    assert len(written) == 2
    index_file = next(path for path in written if "sugerencias" not in path.name)
    assert read_index(index_file).root == str(library)
    assert str(index_file) in out


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
    monkeypatch.setenv("XDG_STATE_HOME", str(state))

    main(["scan", str(library)])
    out = capsys.readouterr().out

    # El codigo usa LOCALAPPDATA en win32 y XDG_STATE_HOME en POSIX; ambos
    # apuntan a "state" arriba, asi que la ruta esperada es la misma.
    index_path = state / "fotos-plus" / "indexes"
    assert index_path.is_dir()
    written = list(index_path.glob("*.json"))
    assert len(written) == 2
    index_file = next(path for path in written if "sugerencias" not in path.name)
    assert str(index_file) in out


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


TAG_DATETIME_ORIGINAL = 0x9003


def build_library_with_positions(root: Path) -> Path:
    from tests.conftest import EXIF_DATETIME_ORIGINAL, make_image_with_gps

    library = root / "fotos"
    library.mkdir()
    make_image_with_gps(
        library / "viaje.jpg",
        latitude=(34, 36, 12.0),
        longitude=(58, 22, 54.0),
        latitude_ref="S",
        longitude_ref="W",
    )
    make_image(
        library / "periodo.jpg",
        exif={TAG_DATETIME_ORIGINAL: "2020:01:05 09:00:00"},
        color="blue",
    )
    (library / "captura.png").write_bytes(
        make_image(root / "origen.png", color="green").read_bytes()
    )
    return library


def test_scan_writes_suggestions_next_to_the_index(tmp_path: Path, capsys) -> None:
    library = build_library_with_positions(tmp_path)
    index_path = tmp_path / "indice.json"

    code = main(["scan", str(library), "--index", str(index_path)])

    assert code == EXIT_OK
    suggestions_path = suggestions_path_next_to(index_path)
    assert suggestions_path.is_file()
    assert read_suggestions(suggestions_path).root == str(library)


def test_summary_reports_suggestions_not_confirmed_trips(
    tmp_path: Path, capsys
) -> None:
    library = build_library_with_positions(tmp_path)
    index_path = tmp_path / "indice.json"

    main(["scan", str(library), "--index", str(index_path)])
    out = capsys.readouterr().out
    suggestions = read_suggestions(suggestions_path_next_to(index_path))

    assert f"Sugerencias de viaje: {len(suggestions.trips)}" in out
    assert f"Periodos sugeridos sin ubicacion: {len(suggestions.periods)}" in out
    assert str(suggestions_path_next_to(index_path)) in out
    assert "viajes confirmados" not in out.lower()
    lowered = out.lower()
    assert "periodos confirmados" not in lowered


def test_index_dir_also_receives_the_suggestions_file(tmp_path: Path, capsys) -> None:
    library = build_library_with_positions(tmp_path)
    destino = tmp_path / "mis-indices"

    main(["scan", str(library), "--index-dir", str(destino)])

    written = list(destino.glob("*-sugerencias.json"))
    assert len(written) == 1
    assert read_suggestions(written[0]).root == str(library)
    assert len(list(destino.glob("*.json"))) == 2


def test_suggestion_failure_does_not_stop_the_index(
    tmp_path: Path, capsys, monkeypatch
) -> None:
    import fotos_plus.cli as cli

    library = build_library_with_positions(tmp_path)
    index_path = tmp_path / "indice.json"

    def broken(*args, **kwargs):
        raise RuntimeError("agrupado roto")

    monkeypatch.setattr(cli, "build_suggestions", broken)
    code = main(["scan", str(library), "--index", str(index_path)])

    captured = capsys.readouterr()
    assert code == EXIT_OK
    assert index_path.is_file()
    assert read_index(index_path).root == str(library)
    assert not suggestions_path_next_to(index_path).exists()
    assert "No se genero el archivo de sugerencias" in captured.err


def test_scan_does_not_mark_suggestions_as_confirmed_in_the_file(
    tmp_path: Path,
) -> None:
    library = build_library_with_positions(tmp_path)
    index_path = tmp_path / "indice.json"

    main(["scan", str(library), "--index", str(index_path)])
    loaded = read_suggestions(suggestions_path_next_to(index_path))

    assert loaded.provisional is True
    assert all(trip.status == "sugerido" for trip in loaded.trips)
    assert all(period.status == "sugerido" for period in loaded.periods)


def test_scan_of_folder_without_positions_still_writes_suggestions(
    tmp_path: Path,
) -> None:
    library = build_library(tmp_path)
    index_path = tmp_path / "indice.json"

    code = main(["scan", str(library), "--index", str(index_path)])

    assert code == EXIT_OK
    loaded = read_suggestions(suggestions_path_next_to(index_path))
    assert loaded.trips == []


def test_scan_of_empty_folder_still_writes_suggestions(tmp_path: Path) -> None:
    empty = tmp_path / "vacia"
    empty.mkdir()
    index_path = tmp_path / "indice.json"

    code = main(["scan", str(empty), "--index", str(index_path)])

    assert code == EXIT_OK
    suggestions_path = suggestions_path_next_to(index_path)
    assert suggestions_path.is_file()
    loaded = read_suggestions(suggestions_path)
    assert loaded.trips == []
    assert loaded.periods == []


def test_view_writes_an_html_next_to_the_index(tmp_path: Path, capsys) -> None:
    library = build_library(tmp_path)
    index_path = tmp_path / "indice.json"
    assert main(["scan", str(library), "--index", str(index_path)]) == EXIT_OK

    before_index = index_path.read_bytes()
    before_suggestions = suggestions_path_next_to(index_path).read_bytes()

    code = main(["view", str(index_path)])

    assert code == EXIT_OK
    generated = index_path.with_suffix(".html")
    assert generated.is_file()
    assert "Visualizador" in capsys.readouterr().out
    # el indice y las sugerencias no se tocan
    assert index_path.read_bytes() == before_index
    assert suggestions_path_next_to(index_path).read_bytes() == before_suggestions


def test_view_output_html_has_one_card_per_suggestion(tmp_path: Path) -> None:
    library = build_library(tmp_path)
    index_path = tmp_path / "indice.json"
    assert main(["scan", str(library), "--index", str(index_path)]) == EXIT_OK

    assert main(["view", str(index_path)]) == EXIT_OK

    document = index_path.with_suffix(".html").read_text(encoding="utf-8")
    loaded = read_suggestions(suggestions_path_next_to(index_path))
    expected = len(loaded.trips) + len(loaded.periods)
    assert document.count('<article class="card"') == max(expected, 1)
    assert "data:image/jpeg;base64," in document


def test_view_writes_a_flat_grid_without_suggestions(tmp_path: Path) -> None:
    library = build_library(tmp_path)
    index_path = tmp_path / "indice.json"
    assert main(["scan", str(library), "--index", str(index_path)]) == EXIT_OK
    suggestions_path_next_to(index_path).unlink()

    code = main(["view", str(index_path)])

    assert code == EXIT_OK
    document = index_path.with_suffix(".html").read_text(encoding="utf-8")
    assert 'class="card flat"' in document


def test_view_reports_a_missing_index(tmp_path: Path, capsys) -> None:
    code = main(["view", str(tmp_path / "no-existe.json")])

    assert code == EXIT_PATH_ERROR
    assert "No existe el indice" in capsys.readouterr().err


def test_view_honours_an_explicit_output_path(tmp_path: Path) -> None:
    library = build_library(tmp_path)
    index_path = tmp_path / "indice.json"
    assert main(["scan", str(library), "--index", str(index_path)]) == EXIT_OK
    destino = tmp_path / "salida" / "visor.html"

    code = main(["view", str(index_path), "--output", str(destino)])

    assert code == EXIT_OK
    assert destino.is_file()
    assert not index_path.with_suffix(".html").exists()


def test_view_reports_a_failure_with_a_non_zero_exit(tmp_path: Path, capsys) -> None:
    library = build_library(tmp_path)
    index_path = tmp_path / "indice.json"
    assert main(["scan", str(library), "--index", str(index_path)]) == EXIT_OK
    # un directorio ocupa la ruta de salida, asi que no se puede escribir el archivo
    destino = tmp_path / "visor.html"
    destino.mkdir()

    code = main(["view", str(index_path), "--output", str(destino)])

    assert code != EXIT_OK
    assert "No se genero el visualizador" in capsys.readouterr().err
