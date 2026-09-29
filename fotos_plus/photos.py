from __future__ import annotations

import hashlib
import numbers
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

GPS_IFD_TAG = 0x8825
GPS_TAG_LATITUDE_REF = 0x0001
GPS_TAG_LATITUDE = 0x0002
GPS_TAG_LONGITUDE_REF = 0x0003
GPS_TAG_LONGITUDE = 0x0004

Position = tuple[float, float]


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


def _gps_coordinate(values, reference) -> Optional[float]:
    if not isinstance(values, (tuple, list)) or len(values) != 3:
        return None
    if any(not isinstance(value, numbers.Rational) for value in values):
        return None
    degrees, minutes, seconds = (float(value) for value in values)
    decimal = degrees + minutes / 60.0 + seconds / 3600.0
    if isinstance(reference, str) and reference.strip().upper() in {"S", "W"}:
        decimal = -decimal
    return decimal


def _exif_position(image: Image.Image) -> Optional[Position]:
    try:
        exif = image.getexif()
    except (AttributeError, OSError, ValueError):
        return None
    if not exif:
        return None
    try:
        gps_ifd = exif.get_ifd(GPS_IFD_TAG)
    except (AttributeError, OSError, ValueError):
        return None
    if not gps_ifd:
        return None

    latitude = _gps_coordinate(
        gps_ifd.get(GPS_TAG_LATITUDE), gps_ifd.get(GPS_TAG_LATITUDE_REF)
    )
    longitude = _gps_coordinate(
        gps_ifd.get(GPS_TAG_LONGITUDE), gps_ifd.get(GPS_TAG_LONGITUDE_REF)
    )
    if latitude is None or longitude is None:
        return None
    if latitude == 0.0 and longitude == 0.0:
        return None
    return latitude, longitude


def _read_metadata(path: Path) -> tuple[Optional[str], Optional[str], Optional[Position]]:
    extension = path.suffix.lower()
    if extension in EXTENSION_ONLY_EXTENSIONS:
        try:
            with Image.open(path) as image:
                captured_at, source = _exif_capture_date(image)
                return captured_at, source, _exif_position(image)
        except (UnidentifiedImageError, OSError, ValueError):
            return None, None, None
    try:
        with Image.open(path) as image:
            captured_at, source = _exif_capture_date(image)
            position = _exif_position(image)
            try:
                image.verify()
            except RuntimeError:
                with Image.open(path) as check:
                    check.verify()
    except (UnidentifiedImageError, OSError, ValueError) as error:
        raise PhotoError(f"unreadable image: {error}") from error
    return captured_at, source, position


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

    captured_at, source, position = _read_metadata(path)
    latitude, longitude = position if position is not None else (None, None)
    return Photo(
        relative_path=relative_path,
        name=path.name,
        extension=path.suffix.lower(),
        size_bytes=size_bytes,
        sha256=sha256,
        captured_at=captured_at,
        captured_at_source=source,
        latitude=latitude,
        longitude=longitude,
    )
