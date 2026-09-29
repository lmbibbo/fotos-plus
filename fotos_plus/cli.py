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
from .progress import ProgressReporter, progress_enabled
from .scanner import ScanRootError, scan

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
    print(f"Periodos sugeridos sin ubicacion: {counts['periods']}", file=stream)
    print(f"Fotos por auditar: {counts['photos_to_audit']}", file=stream)
    print(
        f"Fotos ubicables por referencia: {counts['reference_locatable']}", file=stream
    )
    print(f"Fotos sin fecha: {counts['undated']}", file=stream)
    print(f"Sugerencias: {path}", file=stream)


def _write_suggestion_file(result, index_path: Path):
    suggestions_path = suggestions_path_next_to(index_path)
    suggestions = build_suggestions(result.photos, result.root, result.scanned_at)
    return write_suggestions(suggestions, suggestions_path), suggestions


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except UsageError as error:
        parser.print_usage(sys.stderr)
        print(str(error), file=sys.stderr)
        return EXIT_USAGE

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
