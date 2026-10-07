from __future__ import annotations

import functools
import re
import shutil
import struct
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from .models import SOURCE_CONTAINER_CREATION, Photo

VIDEO_EXTENSIONS = frozenset({".mp4", ".mov", ".3gp"})


@functools.lru_cache(maxsize=1)
def ffmpeg_available() -> bool:
    """Whether a system ffmpeg binary can be shelled out to for posters."""
    return shutil.which("ffmpeg") is not None


def format_duration_s(duration_s: Optional[float]) -> str:
    """Short M:SS mark for a video tile; empty string when unknown."""
    if duration_s is None or duration_s < 0:
        return ""
    total = int(duration_s)
    return f"{total // 60}:{total % 60:02d}"

_ISO6709_RE = re.compile(
    r"([+-]\d{2,3}(?:\.\d+)?)([+-]\d{2,3}(?:\.\d+)?)(?:/.*)?"
)


class VideoError(Exception):
    pass


def _read_boxes(data: bytes, start: int, end: int):
    """Yield (box_type, payload_start, payload_end) for each top-level box."""
    offset = start
    while offset + 8 <= end:
        size, box_type = struct.unpack(">I4s", data[offset : offset + 8])
        header = 8
        if size == 1:
            if offset + 16 > end:
                return
            (size,) = struct.unpack(">Q", data[offset + 8 : offset + 16])
            header = 16
        elif size == 0:
            size = end - offset
        if size < header or offset + size > end:
            return
        yield box_type, offset + header, offset + size
        offset += size


def _parse_mvhd(payload: bytes) -> tuple[Optional[str], Optional[float]]:
    if len(payload) < 20:
        return None, None
    version = payload[0]
    try:
        if version == 1:
            if len(payload) < 36:
                return None, None
            creation = struct.unpack(">Q", payload[8:16])[0]
            timescale = struct.unpack(">I", payload[20:24])[0]
            duration = struct.unpack(">Q", payload[24:32])[0] if len(payload) >= 32 else 0
        else:
            creation = struct.unpack(">I", payload[4:8])[0]
            timescale = struct.unpack(">I", payload[12:16])[0]
            duration = struct.unpack(">I", payload[16:20])[0]
    except struct.error:
        return None, None
    captured_at = None
    if creation:
        # creation_time counts seconds since 1904-01-01 UTC.
        moment = datetime(1904, 1, 1) + timedelta(seconds=creation)
        captured_at = moment.strftime("%Y-%m-%dT%H:%M:%S")
    duration_s = duration / timescale if timescale else None
    return captured_at, duration_s


def _parse_iso6709(text: str) -> Optional[tuple[float, float]]:
    match = _ISO6709_RE.match(text.strip().rstrip("\x00"))
    if not match:
        return None
    try:
        latitude = float(match.group(1))
        longitude = float(match.group(2))
    except ValueError:
        return None
    if latitude == 0.0 and longitude == 0.0:
        return None
    return latitude, longitude


def _scan_for_location(data: bytes, start: int, end: int) -> Optional[tuple[float, float]]:
    """Best-effort GPS lookup in udta '©xyz' and meta/ilst location strings."""
    for name, payload_start, payload_end in _read_boxes(data, start, end):
        payload = data[payload_start:payload_end]
        if name == b"\xa9xyz":
            for chunk in (payload, payload[2:], payload[4:]):
                found = _parse_iso6709(chunk.decode("utf-8", errors="ignore"))
                if found is not None:
                    return found
        elif name in {b"udta", b"moov", b"trak", b"mdia", b"meta", b"ilst"}:
            inner_start = payload_start + 4 if name == b"meta" else payload_start
            found = _scan_for_location(data, inner_start, payload_end)
            if found is not None:
                return found
        elif name == b"data" and len(payload) > 8:
            for chunk in (payload[8:], payload):
                found = _parse_iso6709(chunk.decode("utf-8", errors="ignore"))
                if found is not None:
                    return found
    return None


def read_video_metadata(path: Path) -> tuple[
    Optional[str], Optional[str], Optional[float], Optional[tuple[float, float]]
]:
    """Read capture date, duration and position from an mp4/mov/3gp container.

    Returns (captured_at, source, duration_s, position); missing values come
    back as None. Raises VideoError when the file is not a readable container.
    """
    try:
        data = Path(path).read_bytes()
    except OSError as error:
        raise VideoError(f"cannot read file: {error}") from error
    if len(data) < 8:
        raise VideoError("file too small to hold a container box")
    found_moov = False
    captured_at: Optional[str] = None
    duration_s: Optional[float] = None
    for name, payload_start, payload_end in _read_boxes(data, 0, len(data)):
        if name != b"moov":
            continue
        found_moov = True
        payload = data[payload_start:payload_end]
        for inner, inner_start, inner_end in _read_boxes(
            data, payload_start, payload_end
        ):
            if inner == b"mvhd" and captured_at is None and duration_s is None:
                captured_at, duration_s = _parse_mvhd(
                    data[inner_start:inner_end]
                )
        _ = payload
    if not found_moov:
        raise VideoError("no movie box found")
    position = _scan_for_location(data, 0, len(data))
    source = SOURCE_CONTAINER_CREATION if captured_at is not None else None
    return captured_at, source, duration_s, position


def identify_video(path: Path, relative_path: str, size_bytes: int, sha256: str) -> Photo:
    try:
        captured_at, source, duration_s, position = read_video_metadata(path)
    except VideoError as error:
        from .photos import PhotoError

        raise PhotoError(f"unreadable video: {error}") from error
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
        kind="video",
        duration_s=duration_s,
    )
