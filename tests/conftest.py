from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from fotos_plus.models import (
    SOURCE_DATETIME,
    SOURCE_DATETIME_ORIGINAL,
    ScanResult,
)

EXIF_DATETIME_ORIGINAL = "2024:07:15 18:22:04"
EXIF_DATETIME = "2024:07:15 18:30:00"


def make_image(path: Path, exif: dict[int, str] | None = None, color: str = "red") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (8, 8), color=color)
    if exif is not None:
        metadata = Image.Exif()
        for tag, value in exif.items():
            metadata[tag] = value
        image.save(path, exif=metadata)
    else:
        image.save(path)
    return path


def make_image_with_exif_ifd(path: Path, exif_ifd: dict[int, str]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (8, 8), color="blue")
    metadata = Image.Exif()
    for tag, value in exif_ifd.items():
        metadata.get_ifd(0x8769)[tag] = value
    image.save(path, exif=metadata)
    return path


@pytest.fixture
def image_factory(tmp_path: Path):
    def factory(name: str, exif: dict[int, str] | None = None, color: str = "red") -> Path:
        return make_image(tmp_path / name, exif, color)

    return factory

@pytest.fixture
def scanned_index(tmp_path: Path):
    from fotos_plus.index import write_index

    def factory(result: ScanResult, path: Path | None = None) -> Path:
        return write_index(result, path or (tmp_path / "indice.json"))

    return factory


__all__ = [
    "EXIF_DATETIME",
    "EXIF_DATETIME_ORIGINAL",
    "SOURCE_DATETIME",
    "SOURCE_DATETIME_ORIGINAL",
    "make_image",
]
