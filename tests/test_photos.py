from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from fotos_plus.photos import (
    EXTENSION_ONLY_EXTENSIONS,
    FULLY_READABLE_EXTENSIONS,
    SUPPORTED_EXTENSIONS,
    THUMBNAIL_SIZE,
    PhotoError,
    identify,
    is_supported,
    make_thumbnail,
)
from tests.conftest import (
    EXIF_DATETIME,
    EXIF_DATETIME_ORIGINAL,
    SOURCE_DATETIME,
    SOURCE_DATETIME_ORIGINAL,
    make_image,
    make_image_with_exif_ifd,
    make_image_with_gps,
    make_sized_image,
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


def test_truncated_png_is_reported_as_error(tmp_path: Path) -> None:
    source = make_image(tmp_path / "origen.png")
    original = source.read_bytes()
    truncated = tmp_path / "truncada.png"
    truncated.write_bytes(original[: len(original) // 2])
    with pytest.raises(PhotoError):
        identify(truncated, "truncada.png")


def test_valid_png_survives_the_metadata_read(tmp_path: Path) -> None:
    photo_path = make_image(
        tmp_path / "mapa.png", exif={TAG_DATETIME_ORIGINAL: EXIF_DATETIME_ORIGINAL}
    )
    photo = identify(photo_path, "mapa.png")
    assert photo.extension == ".png"
    assert photo.captured_at == "2024-07-15T18:22:04"
    assert photo.has_position is False


def test_heic_accepted_by_extension_even_if_unreadable(tmp_path: Path) -> None:
    fake = tmp_path / "iphone.heic"
    fake.write_bytes(b"no es heic de verdad")
    photo = identify(fake, "iphone.heic")
    assert photo.extension == ".heic"
    assert photo.captured_at is None
    assert photo.size_bytes == fake.stat().st_size


def test_position_from_gps_ifd(tmp_path: Path) -> None:
    photo_path = make_image_with_gps(
        tmp_path / "buenosaires.jpg",
        latitude=(34, 36, 12.0),
        longitude=(58, 22, 54.0),
        latitude_ref="S",
        longitude_ref="W",
    )
    photo = identify(photo_path, "buenosaires.jpg")
    assert photo.latitude == pytest.approx(-34.603333, abs=1e-5)
    assert photo.longitude == pytest.approx(-58.381667, abs=1e-5)
    assert photo.has_position is True


def test_position_northern_eastern_hemisphere(tmp_path: Path) -> None:
    photo_path = make_image_with_gps(
        tmp_path / "colombia.jpg",
        latitude=(4, 42, 0.0),
        longitude=(74, 4, 48.0),
        latitude_ref="N",
        longitude_ref="W",
    )
    photo = identify(photo_path, "colombia.jpg")
    assert photo.latitude == pytest.approx(4.7, abs=1e-5)
    assert photo.longitude == pytest.approx(-74.08, abs=1e-5)


def test_position_absent_without_gps_ifd(tmp_path: Path) -> None:
    photo_path = make_image(tmp_path / "captura.jpg")
    photo = identify(photo_path, "captura.jpg")
    assert photo.latitude is None
    assert photo.longitude is None
    assert photo.has_position is False


def test_position_absent_when_gps_ifd_is_empty(tmp_path: Path) -> None:
    photo_path = make_image_with_gps(
        tmp_path / "vacia.jpg",
        latitude=None,
        longitude=None,
        empty_ifd=True,
    )
    photo = identify(photo_path, "vacia.jpg")
    assert photo.latitude is None
    assert photo.longitude is None
    assert photo.has_position is False


def test_position_zero_zero_is_not_a_position(tmp_path: Path) -> None:
    photo_path = make_image_with_gps(
        tmp_path / "fallofix.jpg",
        latitude=(0, 0, 0.0),
        longitude=(0, 0, 0.0),
    )
    photo = identify(photo_path, "fallofix.jpg")
    assert photo.latitude is None
    assert photo.longitude is None
    assert photo.has_position is False


def test_position_requires_both_axes(tmp_path: Path) -> None:
    photo_path = make_image_with_gps(
        tmp_path / "solo_lat.jpg",
        latitude=(34, 36, 12.0),
        longitude=None,
    )
    photo = identify(photo_path, "solo_lat.jpg")
    assert photo.latitude is None
    assert photo.longitude is None


def test_photo_without_gps_keeps_capture_date(tmp_path: Path) -> None:
    photo_path = make_image(
        tmp_path / "fecha.jpg", exif={TAG_DATETIME_ORIGINAL: EXIF_DATETIME_ORIGINAL}
    )
    photo = identify(photo_path, "fecha.jpg")
    assert photo.captured_at == "2024-07-15T18:22:04"
    assert photo.latitude is None


def test_photo_with_gps_keeps_capture_date(tmp_path: Path) -> None:
    photo_path = make_image_with_gps(
        tmp_path / "congps.jpg",
        latitude=(34, 36, 12.0),
        longitude=(58, 22, 54.0),
    )
    photo = identify(photo_path, "congps.jpg")
    assert photo.captured_at == "2024-07-15T18:22:04"
    assert photo.has_position is True


def test_position_costs_no_extra_image_open(tmp_path: Path, monkeypatch) -> None:
    from PIL import Image as pil_image

    photo_path = make_image_with_gps(
        tmp_path / "unapertura.jpg",
        latitude=(34, 36, 12.0),
        longitude=(58, 22, 54.0),
    )

    opens: list[Path] = []
    real_open = pil_image.open

    def counting_open(file, *args, **kwargs):
        opens.append(file)
        return real_open(file, *args, **kwargs)

    monkeypatch.setattr(pil_image, "open", counting_open)
    photo = identify(photo_path, "unapertura.jpg")
    monkeypatch.undo()

    assert photo.has_position is True
    assert photo.captured_at == "2024-07-15T18:22:04"
    assert len(opens) == 1


def test_thumbnail_of_a_landscape_photo_keeps_its_proportion(tmp_path: Path) -> None:
    from PIL import Image as pil_image
    from io import BytesIO

    path = make_sized_image(tmp_path / "apaisada.jpg", width=400, height=300)

    data = make_thumbnail(path)

    with pil_image.open(BytesIO(data)) as thumbnail:
        assert thumbnail.width == THUMBNAIL_SIZE
        assert thumbnail.height < thumbnail.width
        assert thumbnail.format == "JPEG"


def test_thumbnail_of_a_vertical_photo_is_vertical(tmp_path: Path) -> None:
    """Los pixeles estan apaisados y la marca de orientacion dice que se rote."""
    from PIL import Image as pil_image
    from io import BytesIO

    path = make_sized_image(
        tmp_path / "vertical.jpg", width=400, height=300, orientation=6
    )

    data = make_thumbnail(path)

    with pil_image.open(BytesIO(data)) as thumbnail:
        assert thumbnail.height > thumbnail.width


def test_thumbnail_of_an_unreadable_photo_reports_a_photo_error(tmp_path: Path) -> None:
    path = tmp_path / "rota.jpg"
    path.write_bytes(b"esto no es una imagen")

    with pytest.raises(PhotoError):
        make_thumbnail(path)
