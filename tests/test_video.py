from __future__ import annotations

import calendar
import struct
from pathlib import Path

import pytest

from fotos_plus.models import SOURCE_CONTAINER_CREATION
from fotos_plus.photos import PhotoError, identify, is_supported
from fotos_plus.video import _parse_mvhd, read_video_metadata


def _box(box_type: bytes, payload: bytes) -> bytes:
    return struct.pack(">I", 8 + len(payload)) + box_type + payload


def make_video(
    path: Path,
    captured_at: str | None = "2024-07-15T18:22:04",
    timescale: int = 1000,
    duration: int = 12500,
    latitude: str | None = None,
    longitude: str | None = None,
) -> Path:
    """Write a minimal ftyp+moov container readable by the box parser."""
    if captured_at is None:
        creation = 0
    else:
        moment = tuple(int(part) for part in captured_at.replace("T", "-").replace(":", "-").split("-"))
        creation = calendar.timegm(moment) + 2082844800
    mvhd = _box(
        b"mvhd",
        struct.pack(">IIII", 0, creation, 0, timescale) + struct.pack(">I", duration) + bytes(4),
    )
    boxes = [mvhd]
    if latitude is not None and longitude is not None:
        text = f"{latitude}{longitude}/".encode("utf-8")
        boxes.append(_box(b"udta", _box(b"\xa9xyz", text)))
    moov = _box(b"moov", b"".join(boxes))
    ftyp = _box(b"ftyp", b"isom" + struct.pack(">I", 0) + b"isomiso2")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(ftyp + moov)
    return path


def test_supported_video_extensions_are_accepted() -> None:
    for suffix in (".mp4", ".MP4", ".mov", ".3gp"):
        assert is_supported(Path(f"clip{suffix}"))
    assert not is_supported(Path("clip.avi"))


def test_video_identify_reads_date_duration_and_kind(tmp_path: Path) -> None:
    path = make_video(tmp_path / "clip.mp4")

    photo = identify(path, "clip.mp4")

    assert photo.kind == "video"
    assert photo.extension == ".mp4"
    assert photo.captured_at == "2024-07-15T18:22:04"
    assert photo.captured_at_source == SOURCE_CONTAINER_CREATION
    assert photo.duration_s == 12.5
    assert photo.size_bytes == path.stat().st_size
    assert len(photo.sha256) == 64


def test_each_accepted_extension_identifies(tmp_path: Path) -> None:
    for suffix in (".mp4", ".mov", ".3gp"):
        path = make_video(tmp_path / f"clip{suffix}")

        photo = identify(path, f"clip{suffix}")

        assert photo.kind == "video"
        assert photo.captured_at == "2024-07-15T18:22:04"


def test_video_without_creation_time_registers_dateless(tmp_path: Path) -> None:
    path = make_video(tmp_path / "clip.mp4", captured_at=None)

    photo = identify(path, "clip.mp4")

    assert photo.kind == "video"
    assert photo.captured_at is None
    assert photo.captured_at_source is None
    assert photo.duration_s == 12.5


def test_video_gps_is_read_when_present(tmp_path: Path) -> None:
    path = make_video(
        tmp_path / "clip.mp4", latitude="+40.7128", longitude="-074.0060"
    )

    photo = identify(path, "clip.mp4")

    assert photo.latitude == pytest.approx(40.7128)
    assert photo.longitude == pytest.approx(-74.0060)


def test_video_without_gps_registers_without_position(tmp_path: Path) -> None:
    path = make_video(tmp_path / "clip.mp4")

    photo = identify(path, "clip.mp4")

    assert photo.latitude is None
    assert photo.longitude is None


def test_corrupt_video_raises_photo_error(tmp_path: Path) -> None:
    path = tmp_path / "clip.mp4"
    path.write_bytes(b"not a container at all" * 4)

    with pytest.raises(PhotoError):
        identify(path, "clip.mp4")


def test_truncated_video_raises_photo_error(tmp_path: Path) -> None:
    path = tmp_path / "clip.mp4"
    path.write_bytes(b"\x00\x00")

    with pytest.raises(PhotoError):
        identify(path, "clip.mp4")


def test_scan_inventories_videos_and_continues_past_broken_ones(
    tmp_path: Path,
) -> None:
    from fotos_plus.scanner import scan

    root = tmp_path / "fotos"
    make_video(root / "bueno.mp4")
    (root / "roto.mp4").write_bytes(b"garbage" * 8)

    result = scan(root)

    assert [photo.name for photo in result.photos] == ["bueno.mp4"]
    assert result.photos[0].kind == "video"
    assert [error.relative_path for error in result.errors] == ["roto.mp4"]


def test_parse_mvhd_rejects_short_payload() -> None:
    assert _parse_mvhd(b"\x00" * 10) == (None, None)


def test_read_video_metadata_without_moov(tmp_path: Path) -> None:
    from fotos_plus.video import VideoError

    path = tmp_path / "clip.mp4"
    path.write_bytes(_box(b"ftyp", b"isom"))

    with pytest.raises(VideoError):
        read_video_metadata(path)
