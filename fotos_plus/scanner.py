from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Iterator, Optional

from .models import Photo, ScanError, ScanResult
from .photos import PhotoError, identify, is_supported


class ScanRootError(Exception):
    pass


def _check_root(root: Path) -> None:
    if not root.exists():
        raise ScanRootError(f"path does not exist: {root}")
    if not root.is_dir():
        raise ScanRootError(f"path is not a directory: {root}")
    if not os.access(root, os.R_OK | os.X_OK):
        raise ScanRootError(f"path is not readable: {root}")


def _relative_path(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _iter_directories(root: Path, errors: list[ScanError]) -> Iterator[Path]:
    stack = [root]
    while stack:
        current = stack.pop()
        try:
            with os.scandir(current) as entries:
                children = sorted(entries, key=lambda entry: entry.name)
        except OSError as error:
            errors.append(
                ScanError(
                    relative_path=_relative_path(current, root),
                    error=f"cannot list directory: {error.strerror or error}",
                )
            )
            continue
        for entry in children:
            if entry.is_dir(follow_symlinks=False):
                stack.append(Path(entry.path))
        yield current


def _iter_candidates(root: Path, errors: list[ScanError]) -> Iterator[Path]:
    directories = list(_iter_directories(root, errors))
    directories.sort(key=lambda directory: len(directory.parts), reverse=True)
    for directory in directories:
        try:
            with os.scandir(directory) as entries:
                children = sorted(entries, key=lambda entry: entry.name)
        except OSError as error:
            errors.append(
                ScanError(
                    relative_path=_relative_path(directory, root),
                    error=f"cannot list directory: {error.strerror or error}",
                )
            )
            continue
        for entry in children:
            if entry.is_file() and is_supported(Path(entry.name)):
                yield Path(entry.path)


def _mark_duplicates(photos: list[Photo]) -> None:
    by_hash: dict[str, list[Photo]] = {}
    for photo in photos:
        by_hash.setdefault(photo.sha256, []).append(photo)
    for group in by_hash.values():
        if len(group) < 2:
            continue
        ordered = sorted(
            group, key=lambda photo: (len(photo.relative_path), photo.relative_path)
        )
        original = ordered[0]
        for duplicate in ordered[1:]:
            duplicate.duplicate_of = original.relative_path


def scan(root: Path) -> ScanResult:
    root = Path(root)
    _check_root(root)

    errors: list[ScanError] = []
    photos: list[Photo] = []
    for path in _iter_candidates(root, errors):
        relative = _relative_path(path, root)
        try:
            photos.append(identify(path, relative))
        except PhotoError as error:
            errors.append(ScanError(relative_path=relative, error=str(error)))

    photos.sort(key=lambda photo: photo.relative_path)
    _mark_duplicates(photos)
    errors.sort(key=lambda error: error.relative_path)

    return ScanResult(
        root=str(root),
        scanned_at=datetime.now().isoformat(timespec="seconds"),
        photos=photos,
        errors=errors,
    )
