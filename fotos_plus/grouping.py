from __future__ import annotations

import math
from datetime import date
from typing import Optional, Sequence

from .models import (
    LOCATION_KNOWN,
    LOCATION_UNKNOWN,
    PeriodSuggestion,
    Photo,
    SuggestionsResult,
    TripSuggestion,
)

EARTH_RADIUS_KM = 6371.0088

TRIP_DISTANCE_KM = 200.0
PERIOD_MAX_EMPTY_DAYS = 1


def haversine_km(
    first: tuple[float, float], second: tuple[float, float]
) -> float:
    lat1, lon1 = first
    lat2, lon2 = second
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    return 2.0 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def _photo_day(photo: Photo) -> Optional[date]:
    if not photo.captured_at:
        return None
    return date.fromisoformat(photo.captured_at[:10])


def _group_bounds(photos: Sequence[Photo]) -> tuple[str, str]:
    ordered = sorted(photo.captured_at for photo in photos if photo.captured_at)
    return ordered[0], ordered[-1]


def _trip_suggestions(positioned: Sequence[Photo]) -> list[TripSuggestion]:
    ordered = sorted(positioned, key=lambda photo: (photo.captured_at, photo.relative_path))
    groups: list[list[Photo]] = []
    for photo in ordered:
        position = (photo.latitude, photo.longitude)
        if groups:
            previous = groups[-1][-1]
            previous_position = (previous.latitude, previous.longitude)
            if haversine_km(previous_position, position) < TRIP_DISTANCE_KM:
                groups[-1].append(photo)
                continue
        groups.append([photo])

    suggestions = []
    for group in groups:
        first, last = _group_bounds(group)
        suggestions.append(
            TripSuggestion(
                photo_count=len(group),
                first_captured_at=first,
                last_captured_at=last,
                location_state=LOCATION_KNOWN,
            )
        )
    return suggestions


def _period_suggestions(
    unpositioned: Sequence[Photo], days_with_position: set[date]
) -> tuple[list[PeriodSuggestion], int]:
    days: dict[date, list[Photo]] = {}
    reference_count = 0
    for photo in unpositioned:
        day = _photo_day(photo)
        if day is None:
            continue
        if day in days_with_position:
            reference_count += 1
            continue
        days.setdefault(day, []).append(photo)

    groups: list[list[date]] = []
    for day in sorted(days):
        if groups:
            previous_day = groups[-1][-1]
            if (day - previous_day).days - 1 <= PERIOD_MAX_EMPTY_DAYS:
                groups[-1].append(day)
                continue
        groups.append([day])

    periods = []
    for group in groups:
        collected: list[Photo] = []
        for day in group:
            collected.extend(days[day])
        first, last = _group_bounds(collected)
        periods.append(
            PeriodSuggestion(
                photo_count=len(collected),
                first_captured_at=first,
                last_captured_at=last,
                location_state=LOCATION_UNKNOWN,
            )
        )
    return periods, reference_count


def build_suggestions(
    photos: Sequence[Photo], root: str, scanned_at: str
) -> SuggestionsResult:
    dated = [photo for photo in photos if photo.captured_at]
    undated = [photo for photo in photos if not photo.captured_at]

    positioned = [photo for photo in dated if photo.has_position]
    unpositioned = [photo for photo in dated if not photo.has_position]

    days_with_position = {
        day for day in (_photo_day(photo) for photo in positioned) if day is not None
    }

    trips = _trip_suggestions(positioned)
    periods, reference_count = _period_suggestions(unpositioned, days_with_position)

    return SuggestionsResult(
        root=root,
        scanned_at=scanned_at,
        trips=trips,
        periods=periods,
        reference_locatable_count=reference_count,
        undated_photo_count=len(undated),
    )


def suggestions_counts(result: SuggestionsResult) -> dict:
    return {
        "trips": len(result.trips),
        "periods": len(result.periods),
        "photos_to_audit": result.trips_to_audit_count,
        "reference_locatable": result.reference_locatable_count,
        "undated": result.undated_photo_count,
    }
