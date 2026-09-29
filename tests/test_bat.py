from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from fotos_plus.index import read_index
from tests.conftest import make_image

BAT = Path(__file__).resolve().parent.parent / "fotos-plus.bat"


def index_files(directory: Path) -> list[Path]:
    return sorted(
        path for path in directory.glob("*.json") if "sugerencias" not in path.name
    )

pytestmark = pytest.mark.skipif(
    sys.platform != "win32" or shutil.which("cmd") is None,
    reason="el lanzador es un archivo .bat y necesita cmd.exe",
)


def build_library(root: Path) -> Path:
    library = root / "fotos"
    library.mkdir()
    make_image(library / "una.jpg", color="red")
    make_image(library / "sub/dos.jpg", color="green")
    return library


def run_bat(*args: str, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["cmd", "/c", str(BAT), *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
    )


def test_bat_assumes_scan_and_matches_explicit_scan(tmp_path: Path) -> None:
    library = build_library(tmp_path)
    implied_index = tmp_path / "implicito.json"
    explicit_index = tmp_path / "explicito.json"

    implied = run_bat(str(library), "--index", str(implied_index), cwd=tmp_path)
    explicit = run_bat(
        "scan", str(library), "--index", str(explicit_index), cwd=tmp_path
    )

    assert implied.returncode == 0, implied.stderr
    assert explicit.returncode == 0, explicit.stderr
    assert implied_index.is_file()
    assert explicit_index.is_file()

    implied_result = read_index(implied_index)
    explicit_result = read_index(explicit_index)
    assert [photo.relative_path for photo in implied_result.photos] == [
        "sub/dos.jpg",
        "una.jpg",
    ]
    assert implied_result.to_dict()["photos"] == explicit_result.to_dict()["photos"]
    assert [line for line in implied.stdout.splitlines() if "Fotos" in line] == [
        line for line in explicit.stdout.splitlines() if "Fotos" in line
    ]


def test_bat_propagates_exit_code_zero(tmp_path: Path) -> None:
    library = build_library(tmp_path)

    result = run_bat(
        "scan", str(library), "--index", str(tmp_path / "i.json"), cwd=tmp_path
    )

    assert result.returncode == 0


def test_bat_propagates_exit_code_one_for_usage_error(tmp_path: Path) -> None:
    result = run_bat("scan", cwd=tmp_path)

    assert result.returncode == 1


def test_bat_propagates_exit_code_two_for_missing_path(tmp_path: Path) -> None:
    result = run_bat(
        "scan", str(tmp_path / "no-existe"), "--index", str(tmp_path / "i.json"),
        cwd=tmp_path,
    )

    assert result.returncode == 2


def test_bat_shows_help_without_arguments(tmp_path: Path) -> None:
    result = run_bat(cwd=tmp_path)

    assert result.returncode == 0
    assert "scan" in result.stdout


def test_bat_passes_scan_help_through(tmp_path: Path) -> None:
    result = run_bat("scan", "--help", cwd=tmp_path)

    assert result.returncode == 0
    assert "--index" in result.stdout
    assert "--index-dir" in result.stdout


def test_bat_passes_index_dir_through(tmp_path: Path) -> None:
    library = build_library(tmp_path)
    destino = tmp_path / "indices"

    result = run_bat(str(library), "--index-dir", str(destino), cwd=tmp_path)

    assert result.returncode == 0, result.stderr
    assert len(index_files(destino)) == 1
    assert len(list(destino.glob("*-sugerencias.json"))) == 1


def test_bat_saves_the_index_in_the_invocation_folder_by_default(
    tmp_path: Path
) -> None:
    elsewhere = tmp_path / "otro-lugar"
    elsewhere.mkdir()
    library = build_library(tmp_path)

    result = run_bat("scan", str(library), cwd=elsewhere)

    assert result.returncode == 0, result.stderr
    written = index_files(elsewhere)
    assert len(written) == 1
    assert [photo.name for photo in read_index(written[0]).photos] == [
        "dos.jpg",
        "una.jpg",
    ]
    assert len(list(elsewhere.glob("*-sugerencias.json"))) == 1


def test_bat_default_folder_applies_when_scan_is_implied(tmp_path: Path) -> None:
    library = build_library(tmp_path)

    result = run_bat(str(library), cwd=tmp_path)

    assert result.returncode == 0, result.stderr
    assert len(index_files(tmp_path)) == 1


def test_bat_explicit_index_wins_over_the_invocation_folder(tmp_path: Path) -> None:
    library = build_library(tmp_path)
    puntual = tmp_path / "puntual.json"

    result = run_bat(str(library), "--index", str(puntual), cwd=tmp_path)

    assert result.returncode == 0, result.stderr
    assert puntual.is_file()
    extra = [item for item in index_files(tmp_path) if item != puntual]
    assert not extra
    assert (tmp_path / "puntual-sugerencias.json").is_file()


def test_bat_explicit_index_dir_wins_over_the_invocation_folder(
    tmp_path: Path
) -> None:
    library = build_library(tmp_path)
    destino = tmp_path / "elegido"

    result = run_bat(str(library), "--index-dir", str(destino), cwd=tmp_path)

    assert result.returncode == 0, result.stderr
    assert len(index_files(destino)) == 1
    assert not list(tmp_path.glob("*.json"))


def test_bat_help_does_not_write_any_index(tmp_path: Path) -> None:
    result = run_bat(cwd=tmp_path)

    assert result.returncode == 0
    assert not list(tmp_path.glob("*.json"))


def test_bat_does_not_modify_the_photo_folder(tmp_path: Path) -> None:
    library = build_library(tmp_path)
    antes = sorted(path.name for path in library.rglob("*"))

    run_bat(str(library), "--index", str(tmp_path / "i.json"), cwd=tmp_path)

    assert sorted(path.name for path in library.rglob("*")) == antes
