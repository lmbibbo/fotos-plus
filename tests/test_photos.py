from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from fotos_plus.photos import (
    EXTENSION_ONLY_EXTENSIONS,
    FULLY_READABLE_EXTENSIONS,
    SUPPORTED_EXTENSIONS,
    PhotoError,
    identify,
    is_supported,
)
from tests.conftest import (
    EXIF_DATETIME,
    EXIF_DATETIME_ORIGINAL,
    SOURCE_DATETIME,
    SOURCE_DATETIME_ORIGINAL,
    make_image,
    make_image_with_exif_ifd,
)

TAG_DATETIME_ORIGINAL = 0x9003
TAG_DATETIME = 0x0132


def test_pdf_and_txt_are_not_supported(tmp_path: Path) -> None:
    assert not is_supported(tmp_path / "documento.pdf")
    assert not is_supported(tmp_path / "notas.txt")


def test_heic_is_supported(tmp_path: Path) -> None:
    assert is_supported(tmp_path / "foto.heic")
    assert ".heic" in EXTENSION_ONLY_EXTENSIONS


def test_supported_extensions_are_disjoint_and_complete() -> None:
    assert not FULLY_READABLE_EXTENSIONS & EXTENSION_ONLY_EXTENSIONS
    assert SUPPORTED_EXTENSIONS == FULLY_READABLE_EXTENSIONS | EXTENSION_ONLY_EXTENSIONS


def test_same_content_gives_same_hash(tmp_path: Path) -> None:
    first = make_image(tmp_path / "a.jpg")
    second = make_image(tmp_path / "b.jpg")
    assert first.read_bytes() == second.read_bytes()
    assert (
        identify(first, "a.jpg").sha256 == identify(second, "b.jpg").sha256
    )


def test_different_content_gives_different_hash(tmp_path: Path) -> None:
    first = make_image(tmp_path / "a.jpg")
    other = tmp_path / "c.jpg"
    other.write_bytes(first.read_bytes() + b"0")
    assert identify(first, "a.jpg").sha256 != identify(other, "c.jpg").sha256


def test_large_file_is_hashed_in_chunks(tmp_path: Path, monkeypatch) -> None:
    from fotos_plus import photos

    large = tmp_path / "grande.jpg"
    large.write_bytes(b"x" * (3 * 1024 * 1024 + 17))

    reads: list[int] = []
    real_open = Path.open

    class RecordingFile:
        def __init__(self, inner):
            self._inner = inner

        def read(self, size=-1):
            reads.append(size)
            return self._inner.read(size)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return self._inner.__exit__(*args)

    def recording_open(self, *args, **kwargs):
        return RecordingFile(real_open(self, *args, **kwargs))

    monkeypatch.setattr(Path, "open", recording_open)
    digest = photos.sha256_file(large)
    monkeypatch.undo()

    assert reads and max(reads) <= photos.HASH_CHUNK_SIZE
    assert len(reads) >= 4
    assert digest == hashlib.sha256(large.read_bytes()).hexdigest()


def test_capture_date_from_datetime_original(tmp_path: Path) -> None:
    photo_path = make_image(
        tmp_path / "playa.jpg", exif={TAG_DATETIME_ORIGINAL: EXIF_DATETIME_ORIGINAL}
    )
    photo = identify(photo_path, "playa.jpg")
    assert photo.captured_at == "2024-07-15T18:22:04"
    assert photo.captured_at_source == SOURCE_DATETIME_ORIGINAL


def test_capture_date_from_datetime_original_in_exif_ifd(tmp_path: Path) -> None:
    photo_path = make_image_with_exif_ifd(
        tmp_path / "camara.jpg", {TAG_DATETIME_ORIGINAL: EXIF_DATETIME_ORIGINAL}
    )
    photo = identify(photo_path, "camara.jpg")
    assert photo.captured_at == "2024-07-15T18:22:04"
    assert photo.captured_at_source == SOURCE_DATETIME_ORIGINAL


def test_datetime_original_wins_over_datetime(tmp_path: Path) -> None:
    photo_path = make_image(
        tmp_path / "playa.jpg",
        exif={
            TAG_DATETIME_ORIGINAL: EXIF_DATETIME_ORIGINAL,
            TAG_DATETIME: EXIF_DATETIME,
        },
    )
    photo = identify(photo_path, "playa.jpg")
    assert photo.captured_at == "2024-07-15T18:22:04"
    assert photo.captured_at_source == SOURCE_DATETIME_ORIGINAL


def test_capture_date_falls_back_to_datetime(tmp_path: Path) -> None:
    photo_path = make_image(tmp_path / "playa.jpg", exif={TAG_DATETIME: EXIF_DATETIME})
    photo = identify(photo_path, "playa.jpg")
    assert photo.captured_at == "2024-07-15T18:30:00"
    assert photo.captured_at_source == SOURCE_DATETIME


def test_capture_date_is_empty_without_exif(tmp_path: Path) -> None:
    photo_path = make_image(tmp_path / "captura.jpg")
    photo = identify(photo_path, "captura.jpg")
    assert photo.captured_at is None
    assert photo.captured_at_source is None


def test_photo_keeps_basic_data(tmp_path: Path) -> None:
    photo_path = make_image(tmp_path / "viaje/IMG_1.jpg")
    photo = identify(photo_path, "viaje/IMG_1.jpg")
    assert photo.name == "IMG_1.jpg"
    assert photo.extension == ".jpg"
    assert photo.size_bytes == photo_path.stat().st_size
    assert photo.relative_path == "viaje/IMG_1.jpg"
    assert photo.duplicate_of is None


def test_missing_exif_date_does_not_fall_back_to_mtime(tmp_path: Path) -> None:
    photo_path = make_image(tmp_path / "captura.jpg")
    photo = identify(photo_path, "captura.jpg")
    assert photo.captured_at is None
    assert photo.captured_at != photo_path.stat().st_mtime


def test_garbage_with_photo_extension_raises(tmp_path: Path) -> None:
    broken = tmp_path / "rota.jpg"
    broken.write_bytes(b"esto no es una imagen")
    with pytest.raises(PhotoError):
        identify(broken, "rota.jpg")


def test_heic_accepted_by_extension_even_if_unreadable(tmp_path: Path) -> None:
    fake = tmp_path / "iphone.heic"
    fake.write_bytes(b"no es heic de verdad")
    photo = identify(fake, "iphone.heic")
    assert photo.extension == ".heic"
    assert photo.captured_at is None
    assert photo.size_bytes == fake.stat().st_size
