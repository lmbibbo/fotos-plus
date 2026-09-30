from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional, Sequence

from .grouping import build_suggestions, suggestions_counts
from .index import (
    index_path_for,
    indexes_dir,
    suggestions_path_next_to,
    write_index,
    write_suggestions,
)
from .photos import EXTENSION_ONLY_EXTENSIONS, FULLY_READABLE_EXTENSIONS
from .places import countries_version, country_of
from .progress import ProgressReporter, progress_enabled
from .scanner import ScanRootError, scan
from .viewer import build_view

EXIT_OK = 0
EXIT_USAGE = 1
EXIT_PATH_ERROR = 2


def _formats_help() -> str:
    complete = ", ".join(sorted(FULLY_READABLE_EXTENSIONS))
    partial = ", ".join(sorted(EXTENSION_ONLY_EXTENSIONS))
    return (
        f"formatos leidos por completo: {complete}\n"
        f"formatos aceptados por extension (metadatos parciales): {partial}"
    )


class UsageError(Exception):
    pass


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise UsageError(message)


def build_parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(
        prog="fotos-plus",
        description="Organizador de fotos.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan_parser = subparsers.add_parser(
        "scan",
        help="Recorre una carpeta e identifica las fotos que contiene.",
        epilog=_formats_help(),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    scan_parser.add_argument("path", help="Carpeta a escanear.")
    scan_parser.add_argument(
        "--index",
        type=Path,
        default=None,
        help=(
            "Ruta del archivo de indice. Tiene prioridad sobre --index-dir."
        ),
    )
    scan_parser.add_argument(
        "--index-dir",
        type=Path,
        default=None,
        help=(
            "Carpeta donde se guardan los indices, uno por carpeta escaneada "
            f"(por defecto: {indexes_dir()})."
        ),
    )

    view_parser = subparsers.add_parser(
        "view",
        help="Genera un visualizador HTML autocontenido desde un indice escaneado.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    view_parser.add_argument("index", type=Path, help="Ruta del archivo de indice.")
    view_parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=(
            "Ruta del HTML a escribir. Por defecto se escribe junto al indice."
        ),
    )
    return parser


def _print_summary(index_path: Path, result, stream) -> None:
    found = len(result.photos)
    duplicates = result.duplicate_count
    print(f"Carpeta escaneada: {result.root}", file=stream)
    print(f"Fotos encontradas: {found}", file=stream)
    print(f"Duplicados: {duplicates}", file=stream)
    print(f"Archivos con error: {len(result.errors)}", file=stream)
    print(f"Indice: {index_path}", file=stream)
    for error in result.errors:
        print(f"  - {error.relative_path}: {error.error}", file=stream)


def _print_suggestion_summary(path: Path, result, stream) -> None:
    counts = suggestions_counts(result)
    print(f"Sugerencias de viaje: {counts['trips']}", file=stream)
    if result.countries_version is not None:
        print(f"Viajes con pais: {counts['trips_with_country']}", file=stream)
        print(f"Viajes sin pais: {counts['trips_without_country']}", file=stream)
        if counts["multi_country_trips"]:
            print(
                f"Viajes que cruzan paises: {counts['multi_country_trips']}",
                file=stream,
            )
        print(
            f"Version del conjunto de paises: {result.countries_version}", file=stream
        )
    print(f"Periodos sugeridos sin ubicacion: {counts['periods']}", file=stream)
    print(f"Fotos por auditar: {counts['photos_to_audit']}", file=stream)
    print(
        f"Fotos ubicables por referencia: {counts['reference_locatable']}", file=stream
    )
    print(f"Fotos sin fecha: {counts['undated']}", file=stream)
    print(f"Sugerencias: {path}", file=stream)


def _write_suggestion_file(result, index_path: Path):
    suggestions_path = suggestions_path_next_to(index_path)
    try:
        version = countries_version()
        notice = None
    except Exception as error:
        version = None
        notice = str(error)

    if version is None:

        def classify(photo):
            return None

    else:

        def classify(photo):
            if not photo.has_position:
                return None
            country = country_of(photo.latitude, photo.longitude)
            return country.name if country is not None else None

    suggestions = build_suggestions(
        result.photos,
        result.root,
        result.scanned_at,
        classify=classify,
        countries_version=version,
        countries_notice=notice,
    )
    return write_suggestions(suggestions, suggestions_path), suggestions


def _write_viewer_file(index_path: Path, output: Optional[Path]) -> Path:
    document = build_view(index_path)[0]
    target = Path(output) if output is not None else index_path.with_suffix(".html")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(document, encoding="utf-8")
    return target


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except UsageError as error:
        parser.print_usage(sys.stderr)
        print(str(error), file=sys.stderr)
        return EXIT_USAGE

    if args.command == "view":
        index_path = Path(args.index)
        if not index_path.is_file():
            print(f"No existe el indice: {index_path}", file=sys.stderr)
            return EXIT_PATH_ERROR
        try:
            target = _write_viewer_file(index_path, args.output)
        except (OSError, ValueError) as error:
            print(f"No se genero el visualizador: {error}", file=sys.stderr)
            return EXIT_PATH_ERROR
        print(f"Visualizador: {target}", file=sys.stdout)
        return EXIT_OK

    if args.command == "scan":
        root = Path(args.path)
        reporter = (
            ProgressReporter(sys.stdout) if progress_enabled(sys.stdout) else None
        )
        try:
            result = scan(root, progress=reporter)
        except ScanRootError as error:
            print(str(error), file=sys.stderr)
            return EXIT_PATH_ERROR
        if reporter is not None:
            reporter.finish()
        index_path = args.index or index_path_for(root, args.index_dir)
        write_index(result, index_path)
        _print_summary(index_path, result, sys.stdout)
        try:
            suggestions_path, suggestions = _write_suggestion_file(result, index_path)
        except Exception as error:
            print(
                "No se genero el archivo de sugerencias de viajes y periodos: "
                f"{error}",
                file=sys.stderr,
            )
            return EXIT_OK
        _print_suggestion_summary(suggestions_path, suggestions, sys.stdout)
        return EXIT_OK

    parser.print_usage(sys.stderr)
    return EXIT_USAGE


if __name__ == "__main__":
    raise SystemExit(main())
