from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Optional

from PIL import Image, UnidentifiedImageError

from .models import SOURCE_DATETIME, SOURCE_DATETIME_ORIGINAL, Photo

FULLY_READABLE_EXTENSIONS = frozenset(
    {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".bmp", ".gif"}
)
EXTENSION_ONLY_EXTENSIONS = frozenset({".heic", ".heif", ".dng", ".nef", ".cr2", ".arw"})
SUPPORTED_EXTENSIONS = FULLY_READABLE_EXTENSIONS | EXTENSION_ONLY_EXTENSIONS

HASH_CHUNK_SIZE = 1024 * 1024

EXIF_IFD_TAG = 0x8769
EXIF_TAG_DATETIME_ORIGINAL = 0x9003
EXIF_TAG_DATETIME = 0x0132


class PhotoError(Exception):
    pass


def is_supported(path: Path) -> bool:
    return path.suffix.lower() in SUPPORTED_EXTENSIONS


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(HASH_CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parse_exif_date(value: str) -> Optional[str]:
    text = value.strip().rstrip("\x00")
    try:
        return (
            f"{text[0:4]}-{text[5:7]}-{text[8:10]}"
            f"T{text[11:13]}:{text[14:16]}:{text[17:19]}"
        )
    except (IndexError, ValueError):
        return None


def _exif_capture_date(image: Image.Image) -> tuple[Optional[str], Optional[str]]:
    try:
        exif = image.getexif()
    except (AttributeError, OSError, ValueError):
        return None, None
    if not exif:
        return None, None
    try:
        exif_ifd = exif.get_ifd(EXIF_IFD_TAG)
    except (AttributeError, OSError, ValueError):
        exif_ifd = {}

    candidates = (
        (exif_ifd.get(EXIF_TAG_DATETIME_ORIGINAL), SOURCE_DATETIME_ORIGINAL),
        (exif.get(EXIF_TAG_DATETIME_ORIGINAL), SOURCE_DATETIME_ORIGINAL),
        (exif.get(EXIF_TAG_DATETIME), SOURCE_DATETIME),
        (exif_ifd.get(EXIF_TAG_DATETIME), SOURCE_DATETIME),
    )
    for raw, source in candidates:
        if not isinstance(raw, str):
            continue
        parsed = _parse_exif_date(raw)
        if parsed is not None:
            return parsed, source
    return None, None


def _read_capture_date(path: Path) -> tuple[Optional[str], Optional[str]]:
    extension = path.suffix.lower()
    if extension in EXTENSION_ONLY_EXTENSIONS:
        try:
            with Image.open(path) as image:
                return _exif_capture_date(image)
        except (UnidentifiedImageError, OSError, ValueError):
            return None, None
    try:
        with Image.open(path) as image:
            captured_at, source = _exif_capture_date(image)
            image.verify()
    except (UnidentifiedImageError, OSError, ValueError) as error:
        raise PhotoError(f"unreadable image: {error}") from error
    return captured_at, source


def identify(path: Path, relative_path: str) -> Photo:
    if not is_supported(path):
        raise PhotoError(f"unsupported extension: {path.suffix.lower() or 'none'}")
    try:
        size_bytes = path.stat().st_size
    except OSError as error:
        raise PhotoError(f"cannot stat file: {error}") from error
    try:
        sha256 = sha256_file(path)
    except OSError as error:
        raise PhotoError(f"cannot read file: {error}") from error

    captured_at, source = _read_capture_date(path)
    return Photo(
        relative_path=relative_path,
        name=path.name,
        extension=path.suffix.lower(),
        size_bytes=size_bytes,
        sha256=sha256,
        captured_at=captured_at,
        captured_at_source=source,
    )
