from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

INDEX_VERSION = 1
SUGGESTIONS_VERSION = 1

SOURCE_DATETIME_ORIGINAL = "exif-datetime-original"
SOURCE_DATETIME = "exif-datetime"

STATUS_SUGGESTED = "sugerido"
LOCATION_KNOWN = "known"
LOCATION_UNKNOWN = "unknown"

PROVISIONAL_NOTICE = (
    "sugerencias de viajes y periodos sin confirmar: no son viajes ni periodos "
    "definitivos, y se reescriben en cada escaneo"
)


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
    latitude: Optional[float] = None
    longitude: Optional[float] = None

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
            "latitude": self.latitude,
            "longitude": self.longitude,
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
            latitude=data.get("latitude"),
            longitude=data.get("longitude"),
        )

    @property
    def has_position(self) -> bool:
        return self.latitude is not None and self.longitude is not None


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


@dataclass
class TripSuggestion:
    photo_count: int
    first_captured_at: str
    last_captured_at: str
    location_state: str = LOCATION_KNOWN
    status: str = STATUS_SUGGESTED

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "location_state": self.location_state,
            "photo_count": self.photo_count,
            "first_captured_at": self.first_captured_at,
            "last_captured_at": self.last_captured_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TripSuggestion":
        return cls(
            photo_count=data["photo_count"],
            first_captured_at=data["first_captured_at"],
            last_captured_at=data["last_captured_at"],
            location_state=data.get("location_state", LOCATION_KNOWN),
            status=data.get("status", STATUS_SUGGESTED),
        )


@dataclass
class PeriodSuggestion:
    photo_count: int
    first_captured_at: str
    last_captured_at: str
    location_state: str = LOCATION_UNKNOWN
    status: str = STATUS_SUGGESTED

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "location_state": self.location_state,
            "photo_count": self.photo_count,
            "first_captured_at": self.first_captured_at,
            "last_captured_at": self.last_captured_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PeriodSuggestion":
        return cls(
            photo_count=data["photo_count"],
            first_captured_at=data["first_captured_at"],
            last_captured_at=data["last_captured_at"],
            location_state=data.get("location_state", LOCATION_UNKNOWN),
            status=data.get("status", STATUS_SUGGESTED),
        )


@dataclass
class SuggestionsResult:
    root: str
    scanned_at: str
    trips: list[TripSuggestion] = field(default_factory=list)
    periods: list[PeriodSuggestion] = field(default_factory=list)
    reference_locatable_count: int = 0
    undated_photo_count: int = 0
    provisional: bool = True
    notice: str = PROVISIONAL_NOTICE

    def to_dict(self) -> dict:
        return {
            "version": SUGGESTIONS_VERSION,
            "provisional": self.provisional,
            "notice": self.notice,
            "root": self.root,
            "scanned_at": self.scanned_at,
            "trips": [trip.to_dict() for trip in self.trips],
            "periods": [period.to_dict() for period in self.periods],
            "reference_locatable_count": self.reference_locatable_count,
            "undated_photo_count": self.undated_photo_count,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SuggestionsResult":
        return cls(
            root=data["root"],
            scanned_at=data["scanned_at"],
            trips=[TripSuggestion.from_dict(item) for item in data.get("trips", [])],
            periods=[PeriodSuggestion.from_dict(item) for item in data.get("periods", [])],
            reference_locatable_count=data.get("reference_locatable_count", 0),
            undated_photo_count=data.get("undated_photo_count", 0),
            provisional=data.get("provisional", True),
            notice=data.get("notice", PROVISIONAL_NOTICE),
        )

    @property
    def trips_to_audit_count(self) -> int:
        return sum(period.photo_count for period in self.periods)
