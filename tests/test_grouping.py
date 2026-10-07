from __future__ import annotations

from datetime import date, timedelta

import pytest

from fotos_plus.grouping import (
    PERIOD_MAX_EMPTY_DAYS,
    TRIP_DISTANCE_KM,
    build_suggestions,
    haversine_km,
    suggestions_counts,
)
from fotos_plus.models import (
    COUNTRY_SOURCE_COORDINATES,
    COUNTRY_SOURCE_UNAVAILABLE,
    LOCATION_KNOWN,
    LOCATION_UNKNOWN,
    STATUS_SUGGESTED,
    Photo,
)

BUENOS_AIRES = (-34.6037, -58.3816)
CORDOBA = (-31.4201, -64.1888)
MEDELLIN = (6.2442, -75.5812)
LIMA = (-12.0464, -77.0428)
NEARBY = (-34.1550, -58.4800)
# Par de coordenadas de una frontera terrestre real: Ciudad del Este (Paraguay) y
# Foz do Iguazu (Brasil) distan ~10 km, asi que las dos quedan en un mismo viaje de
# 200 km y el viaje declara dos paises. Geometria publica, usada como caso de prueba.
CIUDAD_DEL_ESTE = (-25.5095, -54.6112)
FOZ_DO_IGUAZU = (-25.5478, -54.5883)


def photo(
    name: str,
    captured_at: str | None,
    latitude: float | None = None,
    longitude: float | None = None,
) -> Photo:
    return Photo(
        relative_path=name,
        name=name,
        extension=".jpg",
        size_bytes=1,
        sha256=name,
        captured_at=captured_at,
        captured_at_source="exif-datetime-original" if captured_at else None,
        latitude=latitude,
        longitude=longitude,
    )


def located(name: str, day: str, position: tuple[float, float]) -> Photo:
    return photo(f"{name}.jpg", f"{day}T10:00:00", position[0], position[1])


def unlocated(name: str, day: str) -> Photo:
    return photo(f"{name}.jpg", f"{day}T10:00:00")


def video(
    name: str,
    day: str | None,
    latitude: float | None = None,
    longitude: float | None = None,
) -> Photo:
    item = photo(
        f"{name}.mp4",
        f"{day}T10:00:00" if day is not None else None,
        latitude,
        longitude,
    )
    item.extension = ".mp4"
    item.kind = "video"
    item.duration_s = 12.5
    return item


def located_video(
    name: str, day: str, position: tuple[float, float]
) -> Photo:
    return video(name, day, position[0], position[1])


def unlocated_video(name: str, day: str) -> Photo:
    return video(name, day)


def undated_video(name: str) -> Photo:
    return video(name, None, *BUENOS_AIRES)


def test_haversine_known_distance_within_one_percent() -> None:
    distance = haversine_km(BUENOS_AIRES, MEDELLIN)
    assert distance == pytest.approx(4888.0, rel=0.01)


def test_haversine_nearby_pair_within_one_percent() -> None:
    distance = haversine_km(BUENOS_AIRES, NEARBY)
    assert distance == pytest.approx(50.7, rel=0.01)


def test_haversine_zero_for_same_point() -> None:
    assert haversine_km(BUENOS_AIRES, BUENOS_AIRES) == pytest.approx(0.0, abs=1e-9)


def test_haversine_symmetric() -> None:
    assert haversine_km(LIMA, CORDOBA) == pytest.approx(haversine_km(CORDOBA, LIMA))


def test_threshold_is_200_km() -> None:
    assert TRIP_DISTANCE_KM == 200.0


def test_same_place_across_days_is_one_trip() -> None:
    photos = [
        located("a", "2024-01-01", BUENOS_AIRES),
        located("b", "2024-01-05", BUENOS_AIRES),
        located("c", "2024-01-09", (-34.60, -58.38)),
    ]
    result = build_suggestions(photos, "/fotos", "2024-02-01T00:00:00")
    assert len(result.trips) == 1
    assert result.trips[0].photo_count == 3
    assert result.trips[0].first_captured_at.startswith("2024-01-01")
    assert result.trips[0].last_captured_at.startswith("2024-01-09")
    assert result.trips[0].location_state == LOCATION_KNOWN
    assert result.trips[0].status == STATUS_SUGGESTED


def test_far_transfer_splits_the_trip() -> None:
    photos = [
        located("a", "2024-01-01", BUENOS_AIRES),
        located("b", "2024-01-02", BUENOS_AIRES),
        located("c", "2024-01-03", MEDELLIN),
        located("d", "2024-01-04", MEDELLIN),
    ]
    result = build_suggestions(photos, "/fotos", "2024-02-01T00:00:00")
    assert len(result.trips) == 2
    assert [trip.photo_count for trip in result.trips] == [2, 2]


def test_near_transfer_keeps_one_trip() -> None:
    photos = [
        located("a", "2024-01-01", BUENOS_AIRES),
        located("b", "2024-01-02", NEARBY),
    ]
    result = build_suggestions(photos, "/fotos", "2024-02-01T00:00:00")
    assert len(result.trips) == 1


def test_transfer_beyond_threshold_splits_the_trip() -> None:
    photos = [
        located("a", "2024-01-01", BUENOS_AIRES),
        located("b", "2024-01-02", CORDOBA),
    ]
    result = build_suggestions(photos, "/fotos", "2024-02-01T00:00:00")
    assert len(result.trips) == 2


def test_long_stay_in_one_place_does_not_fragment() -> None:
    photos = [
        located("a", "2024-01-01", BUENOS_AIRES),
        located("b", "2024-02-15", BUENOS_AIRES),
        located("c", "2024-03-30", BUENOS_AIRES),
    ]
    result = build_suggestions(photos, "/fotos", "2024-02-01T00:00:00")
    assert len(result.trips) == 1
    assert result.trips[0].photo_count == 3


def test_date_alone_never_splits_a_trip() -> None:
    photos = [
        located("a", "2024-01-01", BUENOS_AIRES),
        located("b", "2026-08-01", BUENOS_AIRES),
    ]
    result = build_suggestions(photos, "/fotos", "2024-02-01T00:00:00")
    assert len(result.trips) == 1


def test_consecutive_days_form_one_period() -> None:
    photos = [unlocated("a", "2024-03-01"), unlocated("b", "2024-03-02")]
    result = build_suggestions(photos, "/fotos", "2024-02-01T00:00:00")
    assert len(result.periods) == 1
    assert result.periods[0].photo_count == 2
    assert result.periods[0].first_captured_at.startswith("2024-03-01")
    assert result.periods[0].last_captured_at.startswith("2024-03-02")


def test_gap_within_limit_stays_in_one_period() -> None:
    start = date(2024, 3, 1)
    end = start + timedelta(days=PERIOD_MAX_EMPTY_DAYS + 1)
    photos = [unlocated("a", str(start)), unlocated("b", str(end))]
    result = build_suggestions(photos, "/fotos", "2024-02-01T00:00:00")
    assert len(result.periods) == 1


def test_gap_beyond_limit_splits_into_two_periods() -> None:
    start = date(2024, 3, 1)
    end = date(2024, 3, 2) + timedelta(days=PERIOD_MAX_EMPTY_DAYS + 2)
    photos = [
        unlocated("a", str(start)),
        unlocated("b", "2024-03-02"),
        unlocated("c", str(end)),
        unlocated("d", str(end + timedelta(days=1))),
    ]
    result = build_suggestions(photos, "/fotos", "2024-02-01T00:00:00")
    assert len(result.periods) == 2
    assert [period.photo_count for period in result.periods] == [2, 2]


def test_no_period_covers_the_empty_gap() -> None:
    photos = [unlocated("a", "2024-03-01"), unlocated("b", "2024-06-01")]
    result = build_suggestions(photos, "/fotos", "2024-02-01T00:00:00")
    assert len(result.periods) == 2
    assert result.periods[0].last_captured_at.startswith("2024-03-01")
    assert result.periods[1].first_captured_at.startswith("2024-06-01")


def test_period_location_is_never_known() -> None:
    photos = [unlocated("a", "2024-03-01"), unlocated("b", "2024-03-02")]
    result = build_suggestions(photos, "/fotos", "2024-02-01T00:00:00")
    assert all(period.location_state == LOCATION_UNKNOWN for period in result.periods)
    assert all(period.status == STATUS_SUGGESTED for period in result.periods)


def test_known_and_unknown_location_are_separate_axes() -> None:
    photos = [located("a", "2024-01-01", BUENOS_AIRES), unlocated("b", "2024-03-01")]
    result = build_suggestions(photos, "/fotos", "2024-02-01T00:00:00")
    assert result.trips[0].location_state == LOCATION_KNOWN
    assert result.trips[0].status == STATUS_SUGGESTED
    assert result.periods[0].location_state == LOCATION_UNKNOWN
    assert result.periods[0].status == STATUS_SUGGESTED


def test_same_day_without_position_is_reference_locatable() -> None:
    photos = [
        located("gps", "2024-03-01", BUENOS_AIRES),
        unlocated("nada_1", "2024-03-01"),
        unlocated("nada_2", "2024-03-01"),
    ]
    result = build_suggestions(photos, "/fotos", "2024-02-01T00:00:00")
    assert result.reference_locatable_count == 2
    assert result.periods == []


def test_day_without_position_stays_in_a_period() -> None:
    photos = [
        located("gps", "2024-03-01", BUENOS_AIRES),
        unlocated("nada", "2024-03-02"),
    ]
    result = build_suggestions(photos, "/fotos", "2024-02-01T00:00:00")
    assert result.reference_locatable_count == 0
    assert len(result.periods) == 1
    assert result.periods[0].photo_count == 1


def test_reference_locatable_photos_are_excluded_from_period_totals() -> None:
    photos = [
        located("gps", "2024-03-01", BUENOS_AIRES),
        unlocated("nada", "2024-03-01"),
        unlocated("periodo", "2024-05-01"),
    ]
    result = build_suggestions(photos, "/fotos", "2024-02-01T00:00:00")
    assert result.reference_locatable_count == 1
    assert result.trips_to_audit_count == 1


def test_collection_without_any_position_has_no_trips() -> None:
    photos = [unlocated("a", "2024-03-01"), unlocated("b", "2024-03-02")]
    result = build_suggestions(photos, "/fotos", "2024-02-01T00:00:00")
    assert result.trips == []
    assert len(result.periods) == 1


def test_collection_with_all_positions_has_no_periods() -> None:
    photos = [
        located("a", "2024-03-01", BUENOS_AIRES),
        located("b", "2024-03-02", BUENOS_AIRES),
    ]
    result = build_suggestions(photos, "/fotos", "2024-02-01T00:00:00")
    assert result.periods == []
    assert len(result.trips) == 1


def test_empty_collection_produces_empty_suggestions() -> None:
    result = build_suggestions([], "/fotos", "2024-02-01T00:00:00")
    assert result.trips == []
    assert result.periods == []
    assert result.reference_locatable_count == 0
    assert result.undated_photo_count == 0


def test_undated_photos_are_counted_and_never_grouped() -> None:
    photos = [
        located("a", "2024-01-01", BUENOS_AIRES),
        photo("captura.jpg", None),
        photo("captura2.jpg", None, -34.6037, -58.3816),
        unlocated("b", "2024-03-01"),
    ]
    result = build_suggestions(photos, "/fotos", "2024-02-01T00:00:00")
    assert result.undated_photo_count == 2
    assert result.trips_to_audit_count == 1
    assert result.trips[0].photo_count == 1


def test_build_suggestions_does_not_modify_photos() -> None:
    photos = [located("a", "2024-01-01", BUENOS_AIRES), unlocated("b", "2024-03-01")]
    before = [photo.to_dict() for photo in photos]
    build_suggestions(photos, "/fotos", "2024-02-01T00:00:00")
    assert [photo.to_dict() for photo in photos] == before


def test_dated_video_joins_the_same_trip_as_same_place_photos() -> None:
    photos = [
        located("a", "2024-01-01", BUENOS_AIRES),
        located_video("clip", "2024-01-05", BUENOS_AIRES),
        located("b", "2024-01-09", BUENOS_AIRES),
    ]
    result = build_suggestions(photos, "/fotos", "2024-02-01T00:00:00")
    assert len(result.trips) == 1
    assert result.trips[0].photo_count == 3


def test_dated_video_without_position_joins_a_period() -> None:
    photos = [
        unlocated("a", "2024-01-01"),
        unlocated_video("clip", "2024-01-02"),
    ]
    result = build_suggestions(photos, "/fotos", "2024-02-01T00:00:00")
    assert len(result.trips) == 0
    assert sum(period.photo_count for period in result.periods) == 2


def test_undated_video_is_counted_and_never_grouped() -> None:
    photos = [
        located("a", "2024-01-01", BUENOS_AIRES),
        undated_video("clip"),
    ]
    result = build_suggestions(photos, "/fotos", "2024-02-01T00:00:00")
    assert result.undated_photo_count == 1
    assert result.trips[0].photo_count == 1


def constant_country(name: str):
    def classify(photo: Photo) -> str | None:
        return name

    return classify


def by_position(countries: dict[tuple[float, float], str]):
    def classify(photo: Photo) -> str | None:
        return countries.get((photo.latitude, photo.longitude))

    return classify


def test_trip_declares_the_country_of_its_photos() -> None:
    photos = [
        located("a", "2024-01-01", BUENOS_AIRES),
        located("b", "2024-01-02", BUENOS_AIRES),
    ]
    result = build_suggestions(
        photos, "/fotos", "2024-02-01T00:00:00", classify=constant_country("Argentina")
    )
    assert len(result.trips) == 1
    location = result.trips[0].location
    assert location is not None
    assert location.country == "Argentina"
    assert location.countries == ["Argentina"]
    assert location.resolved is True
    assert location.ambiguous is False


def test_country_is_derived_per_photo_not_from_a_centroid() -> None:
    """Un viaje que cruza la frontera, con mayoria en un pais y minoria en el otro.

    El centroide cae en el pais mayoritario y borraria al minoritario. Clasificando
    foto por foto, las fotos del segundo pais siguen en el conteo.
    """
    frontera = {
        (CIUDAD_DEL_ESTE[0], CIUDAD_DEL_ESTE[1]): "Paraguay",
        (FOZ_DO_IGUAZU[0], FOZ_DO_IGUAZU[1]): "Argentina",
    }
    photos = []
    for indice in range(88):
        photos.append(located(f"py{indice:03d}", "2024-06-11", CIUDAD_DEL_ESTE))
    for indice in range(12):
        photos.append(located(f"ar{indice:03d}", "2024-06-12", FOZ_DO_IGUAZU))
    result = build_suggestions(
        photos, "/fotos", "2024-06-20T00:00:00", classify=by_position(frontera)
    )
    location = result.trips[0].location
    assert location is not None
    assert location.country == "Paraguay"
    assert location.countries == ["Paraguay", "Argentina"]
    assert result.multi_country_trips_count == 1
    assert result.trips_with_country_count == 1


def test_interleaved_photos_of_two_countries_still_count_correctly() -> None:
    frontera = {
        (CIUDAD_DEL_ESTE[0], CIUDAD_DEL_ESTE[1]): "Paraguay",
        (FOZ_DO_IGUAZU[0], FOZ_DO_IGUAZU[1]): "Argentina",
    }
    photos = []
    for indice in range(10):
        photos.append(located(f"a{indice}", "2024-06-11", CIUDAD_DEL_ESTE))
        photos.append(located(f"b{indice}", "2024-06-11", FOZ_DO_IGUAZU))
    result = build_suggestions(
        photos, "/fotos", "2024-06-20T00:00:00", classify=by_position(frontera)
    )
    location = result.trips[0].location
    assert location is not None
    assert sorted(location.countries) == ["Argentina", "Paraguay"]
    assert location.country is None
    assert location.ambiguous is True


def test_a_tie_leaves_the_dominant_country_undefined() -> None:
    frontera = {
        (CIUDAD_DEL_ESTE[0], CIUDAD_DEL_ESTE[1]): "Paraguay",
        (FOZ_DO_IGUAZU[0], FOZ_DO_IGUAZU[1]): "Argentina",
    }
    photos = [
        located("a", "2024-06-11", CIUDAD_DEL_ESTE),
        located("b", "2024-06-12", FOZ_DO_IGUAZU),
    ]
    result = build_suggestions(
        photos, "/fotos", "2024-06-20T00:00:00", classify=by_position(frontera)
    )
    location = result.trips[0].location
    assert location is not None
    assert location.country is None
    assert location.countries == ["Paraguay", "Argentina"]
    assert result.trips_with_country_count == 0


def test_a_trip_whose_photos_resolve_nowhere_declares_an_unknown_country() -> None:
    photos = [located("a", "2024-01-01", BUENOS_AIRES)]
    result = build_suggestions(
        photos, "/fotos", "2024-02-01T00:00:00", classify=constant_country(None)
    )
    trip = result.trips[0]
    assert trip.location is not None
    assert trip.location.country is None
    assert trip.location.countries == []
    assert trip.location.source == COUNTRY_SOURCE_UNAVAILABLE
    assert trip.location_state == LOCATION_KNOWN
    assert result.trips_without_country_count == 1


def test_partially_resolved_trip_only_counts_resolved_photos() -> None:
    def classify(photo: Photo) -> str | None:
        if photo.name.startswith("a"):
            return "Argentina"
        return None

    photos = [
        located("a1", "2024-01-01", BUENOS_AIRES),
        located("a2", "2024-01-01", BUENOS_AIRES),
        located("b1", "2024-01-01", CORDOBA),
    ]
    result = build_suggestions(
        photos, "/fotos", "2024-02-01T00:00:00", classify=classify
    )
    location = result.trips[0].location
    assert location is not None
    assert location.country == "Argentina"
    assert location.countries == ["Argentina"]


def test_periods_never_declare_a_country() -> None:
    photos = [
        located("a", "2024-01-01", BUENOS_AIRES),
        unlocated("b", "2024-03-01"),
        unlocated("c", "2024-03-02"),
    ]
    result = build_suggestions(
        photos, "/fotos", "2024-04-01T00:00:00", classify=constant_country("Argentina")
    )
    assert len(result.periods) == 1
    period = result.periods[0]
    assert not hasattr(period, "location")
    assert "location" not in period.to_dict()
    assert period.location_state == LOCATION_UNKNOWN


def test_a_period_between_trips_of_different_countries_stays_without_country() -> None:
    """Copiar el pais del viaje vecino afirmaria algo que ninguna foto del periodo respalda."""
    para = {BUENOS_AIRES: "Paraguay"}
    brasil = {CORDOBA: "Brazil"}
    photos = [
        located("py", "2024-01-01", BUENOS_AIRES),
        unlocated("medio", "2024-02-01"),
        located("br", "2024-03-01", CORDOBA),
    ]

    def classify(photo: Photo) -> str | None:
        return para.get((photo.latitude, photo.longitude)) or brasil.get(
            (photo.latitude, photo.longitude)
        )

    result = build_suggestions(
        photos, "/fotos", "2024-04-01T00:00:00", classify=classify
    )
    assert len(result.trips) == 2
    assert [trip.location.country for trip in result.trips] == ["Paraguay", "Brazil"]
    assert len(result.periods) == 1
    assert "location" not in result.periods[0].to_dict()


def test_location_state_keeps_its_meaning_with_a_country_present() -> None:
    photos = [located("a", "2024-01-01", BUENOS_AIRES)]
    result = build_suggestions(
        photos, "/fotos", "2024-02-01T00:00:00", classify=constant_country("Argentina")
    )
    trip = result.trips[0]
    assert trip.location_state == LOCATION_KNOWN
    assert trip.location is not None
    assert trip.location.country == "Argentina"
    assert trip.location.source == COUNTRY_SOURCE_COORDINATES


def test_without_a_classifier_every_trip_declares_an_unknown_country() -> None:
    photos = [located("a", "2024-01-01", BUENOS_AIRES)]
    result = build_suggestions(photos, "/fotos", "2024-02-01T00:00:00")
    assert result.trips[0].location.country is None
    assert result.trips[0].location.countries == []
    assert result.countries_version is None


def test_countries_version_is_recorded_on_the_result() -> None:
    photos = [located("a", "2024-01-01", BUENOS_AIRES)]
    result = build_suggestions(
        photos,
        "/fotos",
        "2024-02-01T00:00:00",
        classify=constant_country("Argentina"),
        countries_version=7,
    )
    assert result.countries_version == 7
    assert result.to_dict()["countries_version"] == 7


def test_country_counts_appear_in_the_summary() -> None:
    photos = [located("a", "2024-01-01", BUENOS_AIRES)]
    result = build_suggestions(
        photos,
        "/fotos",
        "2024-02-01T00:00:00",
        classify=constant_country("Argentina"),
        countries_version=1,
    )
    counts = suggestions_counts(result)
    assert counts["trips_with_country"] == 1
    assert counts["trips_without_country"] == 0
    assert counts["multi_country_trips"] == 0
    assert counts["countries_version"] == 1
