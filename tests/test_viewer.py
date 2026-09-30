from __future__ import annotations

from pathlib import Path

import pytest

from fotos_plus.models import (
    LOCATION_KNOWN,
    LOCATION_UNKNOWN,
    STATUS_SUGGESTED,
    PeriodSuggestion,
    Photo,
    TripLocation,
    TripSuggestion,
)
from fotos_plus.viewer import (
    ORPHAN_TITLE,
    THUMBNAILS_PER_GROUP,
    assign_groups,
)


def photo(name: str, captured_at: str | None) -> Photo:
    return Photo(
        relative_path=name,
        name=name,
        extension=".jpg",
        size_bytes=1,
        sha256=name,
        captured_at=captured_at,
    )


def trip(start: str, end: str, country: str | None = "Argentina") -> TripSuggestion:
    location = TripLocation(country=country, countries=[country] if country else [])
    return TripSuggestion(
        photo_count=1,
        first_captured_at=start,
        last_captured_at=end,
        location_state=LOCATION_KNOWN,
        status=STATUS_SUGGESTED,
        location=location,
    )


def period(start: str, end: str) -> PeriodSuggestion:
    return PeriodSuggestion(
        photo_count=1,
        first_captured_at=start,
        last_captured_at=end,
        location_state=LOCATION_UNKNOWN,
        status=STATUS_SUGGESTED,
    )


def suggestions(trips=(), periods=()):
    from fotos_plus.models import SuggestionsResult

    return SuggestionsResult(
        root="C:/fotos",
        scanned_at="2026-01-01T00:00:00",
        trips=list(trips),
        periods=list(periods),
    )


def test_photo_inside_a_trip_lands_in_that_trip() -> None:
    result = assign_groups(
        [photo("a.jpg", "2024-05-02T10:00:00")],
        suggestions(trips=[trip("2024-05-01T00:00:00", "2024-05-05T00:00:00")]),
    )

    assert len(result) == 1
    assert result[0].kind == "trip"
    assert result[0].country == "Argentina"


def test_photo_inside_a_period_lands_in_that_period() -> None:
    result = assign_groups(
        [photo("a.jpg", "2024-05-02T10:00:00")],
        suggestions(periods=[period("2024-05-01T00:00:00", "2024-05-05T00:00:00")]),
    )

    assert len(result) == 1
    assert result[0].kind == "period"
    assert result[0].country is None


def test_photo_outside_every_group_lands_in_the_orphan_group() -> None:
    result = assign_groups(
        [photo("a.jpg", "2030-01-01T10:00:00")],
        suggestions(trips=[trip("2024-05-01T00:00:00", "2024-05-05T00:00:00")]),
    )

    orphan = next(g for g in result if g.kind == "orphan")

    assert orphan.title == ORPHAN_TITLE
    assert [p.name for p in orphan.photos] == ["a.jpg"]
    # el viaje declarado tambien sale, aunque se quede vacio
    assert len(result) == 2


def test_a_trip_wins_over_a_period_that_contains_the_same_photo() -> None:
    result = assign_groups(
        [photo("a.jpg", "2024-05-02T10:00:00")],
        suggestions(
            trips=[trip("2024-05-01T00:00:00", "2024-05-05T00:00:00")],
            periods=[period("2024-05-01T00:00:00", "2024-05-05T00:00:00")],
        ),
    )

    trip_group = next(g for g in result if g.kind == "trip")
    period_group = next(g for g in result if g.kind == "period")

    assert [p.name for p in trip_group.photos] == ["a.jpg"]
    assert period_group.photos == []


def test_photo_on_a_boundary_belongs_to_the_range() -> None:
    result = assign_groups(
        [
            photo("inicio.jpg", "2024-05-01T00:00:00"),
            photo("fin.jpg", "2024-05-05T00:00:00"),
        ],
        suggestions(trips=[trip("2024-05-01T00:00:00", "2024-05-05T00:00:00")]),
    )

    assert len(result) == 1
    assert len(result[0].photos) == 2


def test_no_photo_is_left_out_of_every_group() -> None:
    photos = [
        photo("en-viaje.jpg", "2024-05-02T10:00:00"),
        photo("en-periodo.jpg", "2024-07-02T10:00:00"),
        photo("suelta.jpg", "2025-02-02T10:00:00"),
    ]

    result = assign_groups(
        photos,
        suggestions(
            trips=[trip("2024-05-01T00:00:00", "2024-05-05T00:00:00")],
            periods=[period("2024-07-01T00:00:00", "2024-07-05T00:00:00")],
        ),
    )

    grouped = [p for g in result for p in g.photos]
    assert len(grouped) == len(photos)


def test_groups_come_back_in_ascending_date_order() -> None:
    result = assign_groups(
        [
            photo("c.jpg", "2024-09-01T10:00:00"),
            photo("a.jpg", "2024-01-01T10:00:00"),
            photo("b.jpg", "2024-05-01T10:00:00"),
        ],
        suggestions(
            trips=[
                trip("2024-09-01T00:00:00", "2024-09-02T00:00:00"),
                trip("2024-01-01T00:00:00", "2024-01-02T00:00:00"),
                trip("2024-05-01T00:00:00", "2024-05-02T00:00:00"),
            ]
        ),
    )

    assert [g.first_captured_at for g in result] == [
        "2024-01-01T00:00:00",
        "2024-05-01T00:00:00",
        "2024-09-01T00:00:00",
    ]


def test_undated_photos_go_to_the_orphan_group() -> None:
    result = assign_groups(
        [photo("sin-fecha.jpg", None)],
        suggestions(trips=[trip("2024-05-01T00:00:00", "2024-05-05T00:00:00")]),
    )

    orphan = next(g for g in result if g.kind == "orphan")

    assert [p.name for p in orphan.photos] == ["sin-fecha.jpg"]
    assert orphan.first_captured_at is None


def test_thumbnails_per_group_is_five() -> None:
    assert THUMBNAILS_PER_GROUP == 5


def _write_photos(root: Path, names: list[str]) -> None:
    from tests.conftest import make_sized_image

    for name in names:
        make_sized_image(root / name, width=400, height=300)


def test_html_has_one_card_per_group(tmp_path: Path) -> None:
    from fotos_plus.viewer import render_html

    root = tmp_path / "fotos"
    _write_photos(root, ["a.jpg"])
    groups = [
        assign_groups(
            [photo("a.jpg", "2024-01-01T00:00:00")],
            suggestions(trips=[trip("2024-01-01T00:00:00", "2024-01-02T00:00:00")]),
        )[0]
    ]

    document = render_html(groups, str(root))

    assert document.count('<article class="card"') == 1


def test_html_shows_country_for_a_trip_and_not_for_a_period(tmp_path: Path) -> None:
    import json
    import re

    from fotos_plus.viewer import render_html

    root = tmp_path / "fotos"
    _write_photos(root, ["a.jpg", "b.jpg"])
    groups = assign_groups(
        [photo("a.jpg", "2024-01-01T00:00:00"), photo("b.jpg", "2024-07-01T00:00:00")],
        suggestions(
            trips=[trip("2024-01-01T00:00:00", "2024-01-02T00:00:00")],
            periods=[period("2024-07-01T00:00:00", "2024-07-02T00:00:00")],
        ),
    )

    document = render_html(groups, str(root))
    data = json.loads(re.search(r'id="viewer-data">(.*?)</script>', document, re.S).group(1))
    by_kind = {g["kind"]: g for g in data["groups"]}

    assert by_kind["trip"]["country"] == "Argentina"
    assert by_kind["period"]["country"] is None


def test_html_embeds_thumbnails_and_data_without_a_server(tmp_path: Path) -> None:
    from fotos_plus.viewer import render_html

    root = tmp_path / "fotos"
    _write_photos(root, ["a.jpg"])
    groups = assign_groups(
        [photo("a.jpg", "2024-01-01T00:00:00")],
        suggestions(trips=[trip("2024-01-01T00:00:00", "2024-01-02T00:00:00")]),
    )

    document = render_html(groups, str(root))

    assert "data:image/jpeg;base64," in document
    assert 'id="viewer-data"' in document
    assert "http://" not in document
    assert "https://" not in document
    assert "fetch(" not in document


def test_group_with_fewer_than_five_photos_shows_all_of_them(tmp_path: Path) -> None:
    from fotos_plus.viewer import render_html

    root = tmp_path / "fotos"
    names = [f"{i}.jpg" for i in range(3)]
    _write_photos(root, names)
    groups = assign_groups(
        [photo(name, "2024-01-01T00:00:00") for name in names],
        suggestions(trips=[trip("2024-01-01T00:00:00", "2024-01-02T00:00:00")]),
    )

    document = render_html(groups, str(root))

    assert document.count('class="thumb"') == 3


def test_group_caps_at_five_thumbnails(tmp_path: Path) -> None:
    from fotos_plus.viewer import render_html

    root = tmp_path / "fotos"
    names = [f"{i}.jpg" for i in range(8)]
    _write_photos(root, names)
    groups = assign_groups(
        [photo(name, "2024-01-01T00:00:00") for name in names],
        suggestions(trips=[trip("2024-01-01T00:00:00", "2024-01-02T00:00:00")]),
    )

    document = render_html(groups, str(root))

    assert document.count('class="thumb"') == 5


def test_every_declared_suggestion_gets_a_group_even_with_no_photos() -> None:
    """Un periodo contenido en un viaje se queda sin fotos, pero no desaparece."""
    result = assign_groups(
        [photo("a.jpg", "2024-01-10T10:00:00")],
        suggestions(
            trips=[trip("2024-01-01T00:00:00", "2024-01-31T00:00:00")],
            periods=[period("2024-01-10T00:00:00", "2024-01-10T00:00:00")],
        ),
    )

    kinds = sorted(g.kind for g in result)
    period_group = next(g for g in result if g.kind == "period")

    assert kinds == ["period", "trip"]
    assert period_group.photos == []
    # la foto se queda en el viaje, no se duplica
    trip_group = next(g for g in result if g.kind == "trip")
    assert [p.name for p in trip_group.photos] == ["a.jpg"]


def test_group_reports_its_real_size_not_the_suggested_count() -> None:
    """El photo_count de la sugerencia cuenta solo fotos con posicion."""
    group = assign_groups(
        [photo(f"{i}.jpg", "2024-01-10T10:00:00") for i in range(4)],
        suggestions(trips=[trip("2024-01-01T00:00:00", "2024-01-31T00:00:00")]),
    )[0]

    assert group.photo_count == 1
    assert len(group.photos) == 4


def test_an_unreadable_photo_does_not_abort_the_whole_group(tmp_path: Path) -> None:
    from fotos_plus.viewer import render_html

    root = tmp_path / "fotos"
    _write_photos(root, ["ok.jpg"])
    (root / "rota.jpg").write_bytes(b"no es una imagen")
    groups = assign_groups(
        [photo("rota.jpg", "2024-01-01T00:00:00"), photo("ok.jpg", "2024-01-01T01:00:00")],
        suggestions(trips=[trip("2024-01-01T00:00:00", "2024-01-02T00:00:00")]),
    )

    document = render_html(groups, str(root))

    assert 'class="thumb"' in document
    assert document.count('class="thumb"') == 1


def test_flat_mode_renders_all_photos_without_grouping(tmp_path: Path) -> None:
    from fotos_plus.index import write_index
    from fotos_plus.models import ScanResult
    from fotos_plus.viewer import build_view

    root = tmp_path / "fotos"
    names = [f"{i}.jpg" for i in range(4)]
    _write_photos(root, names)

    photos = [photo(name, "2024-01-01T00:00:00") for name in names]
    index_path = tmp_path / "indice.json"
    write_index(ScanResult(root=str(root), scanned_at="2026-01-01T00:00:00", photos=photos), index_path)

    # sin archivo de sugerencias contiguo
    document, flat = build_view(index_path)

    assert flat is True
    assert document.count('class="thumb"') == 4
    assert 'class="card flat"' in document


def test_with_suggestions_generates_cards_not_flat(tmp_path: Path) -> None:
    from fotos_plus.index import write_index, write_suggestions, suggestions_path_next_to
    from fotos_plus.models import ScanResult
    from fotos_plus.viewer import build_view

    root = tmp_path / "fotos"
    names = ["a.jpg", "b.jpg"]
    _write_photos(root, names)

    photos = [photo("a.jpg", "2024-01-01T00:00:00"), photo("b.jpg", "2024-07-01T00:00:00")]
    index_path = tmp_path / "indice.json"
    write_index(ScanResult(root=str(root), scanned_at="2026-01-01T00:00:00", photos=photos), index_path)
    suggestions_path = suggestions_path_next_to(index_path)
    write_suggestions(
        suggestions(
            trips=[trip("2024-01-01T00:00:00", "2024-01-02T00:00:00")],
            periods=[period("2024-07-01T00:00:00", "2024-07-02T00:00:00")],
        ),
        suggestions_path,
    )

    document, flat = build_view(index_path)

    assert flat is False
    assert document.count('<article class="card"') == 2
