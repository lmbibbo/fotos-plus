from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

INDEX_VERSION = 1

SOURCE_DATETIME_ORIGINAL = "exif-datetime-original"
SOURCE_DATETIME = "exif-datetime"


@dataclass
class Photo:
    relative_path: str
    name: str
    extension: str
    size_bytes: int
    sha256: str
    captured_at: Optional[str] = None
    captured_at_source: Optional[str] = None
    duplicate_of: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "relative_path": self.relative_path,
            "name": self.name,
            "extension": self.extension,
            "size_bytes": self.size_bytes,
            "sha256": self.sha256,
            "captured_at": self.captured_at,
            "captured_at_source": self.captured_at_source,
            "duplicate_of": self.duplicate_of,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Photo":
        return cls(
            relative_path=data["relative_path"],
            name=data["name"],
            extension=data["extension"],
            size_bytes=data["size_bytes"],
            sha256=data["sha256"],
            captured_at=data.get("captured_at"),
            captured_at_source=data.get("captured_at_source"),
            duplicate_of=data.get("duplicate_of"),
        )


@dataclass
class ScanError:
    relative_path: str
    error: str

    def to_dict(self) -> dict:
        return {"relative_path": self.relative_path, "error": self.error}

    @classmethod
    def from_dict(cls, data: dict) -> "ScanError":
        return cls(relative_path=data["relative_path"], error=data["error"])


@dataclass
class ScanResult:
    root: str
    scanned_at: str
    photos: list[Photo] = field(default_factory=list)
    errors: list[ScanError] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "version": INDEX_VERSION,
            "root": self.root,
            "scanned_at": self.scanned_at,
            "photos": [photo.to_dict() for photo in self.photos],
            "errors": [error.to_dict() for error in self.errors],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ScanResult":
        return cls(
            root=data["root"],
            scanned_at=data["scanned_at"],
            photos=[Photo.from_dict(item) for item in data.get("photos", [])],
            errors=[ScanError.from_dict(item) for item in data.get("errors", [])],
        )

    @property
    def duplicate_count(self) -> int:
        return sum(1 for photo in self.photos if photo.duplicate_of is not None)
