from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional, Sequence

from .index import default_index_path, write_index
from .photos import EXTENSION_ONLY_EXTENSIONS, FULLY_READABLE_EXTENSIONS
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
        help="Ruta del archivo de indice (por defecto, uno por carpeta escaneada).",
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
        try:
            result = scan(root)
        except ScanRootError as error:
            print(str(error), file=sys.stderr)
            return EXIT_PATH_ERROR
        index_path = args.index or default_index_path(root)
        write_index(result, index_path)
        _print_summary(index_path, result, sys.stdout)
        return EXIT_OK

    parser.print_usage(sys.stderr)
    return EXIT_USAGE


if __name__ == "__main__":
    raise SystemExit(main())
