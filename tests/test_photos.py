from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from fotos_plus.photos import (
    EXTENSION_ONLY_EXTENSIONS,
    FULLY_READABLE_EXTENSIONS,
    RENDER_SIZE,
    SUPPORTED_EXTENSIONS,
    THUMBNAIL_SIZE,
    PhotoError,
    cached_render,
    identify,
    is_supported,
    make_render,
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


def test_render_caps_the_longest_edge(tmp_path: Path) -> None:
    from PIL import Image as pil_image
    from io import BytesIO

    path = make_sized_image(tmp_path / "grande.jpg", width=4000, height=3000)

    data = make_render(path)

    with pil_image.open(BytesIO(data)) as rendered:
        assert rendered.width == RENDER_SIZE
        assert rendered.height < rendered.width
        assert rendered.format == "JPEG"


def test_render_leaves_a_small_photo_alone(tmp_path: Path) -> None:
    """Una foto que ya cabe no se agranda: el render es una version para ver, no un lupa."""
    from PIL import Image as pil_image
    from io import BytesIO

    path = make_sized_image(tmp_path / "chica.jpg", width=320, height=240)

    data = make_render(path)

    with pil_image.open(BytesIO(data)) as rendered:
        assert rendered.width == 320
        assert rendered.height == 240


def test_render_is_far_smaller_than_a_large_original(tmp_path: Path) -> None:
    """El peso del render deja de depender del original: es lo que lo hace navegable."""
    path = make_sized_image(tmp_path / "pesada.jpg", width=6000, height=4000, color="red")

    original_size = path.stat().st_size
    data = make_render(path)

    assert len(data) < original_size


def test_render_of_a_vertical_photo_is_vertical(tmp_path: Path) -> None:
    """Los pixeles estan apaisados y la marca de orientacion dice que serote."""
    from PIL import Image as pil_image
    from io import BytesIO

    path = make_sized_image(
        tmp_path / "vertical.jpg", width=4000, height=3000, orientation=6
    )

    data = make_render(path)

    with pil_image.open(BytesIO(data)) as rendered:
        assert rendered.height > rendered.width


def test_render_of_an_unreadable_photo_reports_a_photo_error(tmp_path: Path) -> None:
    path = tmp_path / "rota.jpg"
    path.write_bytes(b"esto no es una imagen")

    with pytest.raises(PhotoError):
        make_render(path)


def test_render_path_is_keyed_by_content_hash(tmp_path: Path) -> None:
    from fotos_plus.index import render_path_for, renders_dir_next_to

    index_path = tmp_path / "indice.json"

    renders_dir = renders_dir_next_to(index_path)
    first = render_path_for(renders_dir, "a" * 64)
    second = render_path_for(renders_dir, "b" * 64)

    assert renders_dir == tmp_path / "indice-renders"
    assert first != second
    assert first.name == f"{'a' * 64}.jpg"


def test_render_path_does_not_depend_on_the_photo_location(tmp_path: Path) -> None:
    """Misma foto en dos carpetas resuelve al mismo render: es lo que sobrevive al traslado."""
    from fotos_plus.index import render_path_for, renders_dir_next_to

    renders_dir = renders_dir_next_to(tmp_path / "indice.json")
    digest = "c" * 64

    assert render_path_for(renders_dir, digest) == render_path_for(renders_dir, digest)


def test_cached_render_produces_and_stores_on_first_call(tmp_path: Path) -> None:
    from fotos_plus.index import render_path_for, renders_dir_next_to

    photo_path = make_sized_image(tmp_path / "foto.jpg", width=1200, height=900)
    digest = hashlib.sha256(photo_path.read_bytes()).hexdigest()
    render_path = render_path_for(renders_dir_next_to(tmp_path / "indice.json"), digest)

    data = cached_render(photo_path, digest, render_path)

    assert data
    assert render_path.is_file()
    assert render_path.read_bytes() == data


def test_cached_render_does_not_reprocess_the_original(tmp_path: Path) -> None:
    """La segunda peticion sale del archivo guardado, sin volver a abrir la foto."""
    from fotos_plus.index import render_path_for, renders_dir_next_to

    photo_path = make_sized_image(tmp_path / "foto.jpg", width=1200, height=900)
    digest = hashlib.sha256(photo_path.read_bytes()).hexdigest()
    render_path = render_path_for(renders_dir_next_to(tmp_path / "indice.json"), digest)
    first = cached_render(photo_path, digest, render_path)

    # Si el original desaparece, la segunda peticion igual tiene que poder responder.
    photo_path.unlink()
    second = cached_render(photo_path, digest, render_path)

    assert second == first


def test_cached_render_ignores_the_render_of_other_content(tmp_path: Path) -> None:
    """Cambio el contenido, cambio el hash, y el render viejo deja de servir."""
    from fotos_plus.index import render_path_for, renders_dir_next_to

    renders_dir = renders_dir_next_to(tmp_path / "indice.json")
    photo_path = make_sized_image(tmp_path / "foto.jpg", width=800, height=600, color="red")
    old_digest = hashlib.sha256(photo_path.read_bytes()).hexdigest()
    old_render = render_path_for(renders_dir, old_digest)
    cached_render(photo_path, old_digest, old_render)

    make_sized_image(tmp_path / "foto.jpg", width=800, height=600, color="blue")
    new_digest = hashlib.sha256(photo_path.read_bytes()).hexdigest()
    new_render = render_path_for(renders_dir, new_digest)
    data = cached_render(photo_path, new_digest, new_render)

    assert new_digest != old_digest
    assert new_render != old_render
    assert old_render.is_file(), "el render anterior se conserva, no se borra"
    assert new_render.read_bytes() == data


def test_deleting_the_cache_costs_time_and_nothing_else(tmp_path: Path) -> None:
    """El cache es descartable: se borra entero y todo se vuelve a producir."""
    from fotos_plus.index import render_path_for, renders_dir_next_to

    photo_path = make_sized_image(tmp_path / "foto.jpg", width=1000, height=800)
    digest = hashlib.sha256(photo_path.read_bytes()).hexdigest()
    renders_dir = renders_dir_next_to(tmp_path / "indice.json")
    first = cached_render(photo_path, digest, render_path_for(renders_dir, digest))

    for stored in renders_dir.iterdir():
        stored.unlink()
    renders_dir.rmdir()
    second = cached_render(photo_path, digest, render_path_for(renders_dir, digest))

    assert second == first


def test_cached_render_survives_a_cache_that_cannot_be_written(tmp_path: Path) -> None:
    """El cache es una optimizacion: si no se puede guardar, se entrega igual."""
    from fotos_plus.index import render_path_for, renders_dir_next_to

    photo_path = make_sized_image(tmp_path / "foto.jpg", width=600, height=400)
    digest = hashlib.sha256(photo_path.read_bytes()).hexdigest()
    # Un archivo donde deberia ir el directorio hace fallar el mkdir.
    renders_dir = renders_dir_next_to(tmp_path / "indice.json")
    renders_dir.write_bytes(b"estorbo")

    data = cached_render(photo_path, digest, render_path_for(renders_dir, digest))

    assert data
