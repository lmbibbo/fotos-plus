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
    TAG_CATALOG_ID,
    THUMBNAILS_PER_GROUP,
    UNTAGGED_SECTION_TITLE,
    assign_groups,
    group_sections,
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
    # las miniaturas siguen en la grilla responsive, no apiladas en una columna
    assert '<div class="grid">' in document


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


# --- export estatico: refleja las etiquetas y sigue siendo de solo lectura ------


def test_the_export_reflects_the_saved_labels(tmp_path: Path) -> None:
    """Escenario 'El export refleja las etiquetas'.

    El archivo de edicion existe y el HTML exportado sale con los titulos de las
    etiquetas, sin ningun control para cambiarlas.
    """
    from fotos_plus.index import (
        edicion_path_next_to,
        suggestions_path_next_to,
        write_index,
        write_suggestions,
    )
    from fotos_plus.labels import LabelOverlay, write_edicion
    from fotos_plus.models import ScanResult
    from fotos_plus.viewer import build_view

    root = tmp_path / "fotos"
    _write_photos(root, ["a.jpg", "b.jpg"])

    photos = [photo("a.jpg", "2024-01-01T00:00:00"), photo("b.jpg", "2024-07-01T00:00:00")]
    index_path = tmp_path / "indice.json"
    write_index(ScanResult(root=str(root), scanned_at="2026-01-01T00:00:00", photos=photos), index_path)
    write_suggestions(
        suggestions(
            trips=[trip("2024-01-01T00:00:00", "2024-01-02T00:00:00")],
            periods=[period("2024-07-01T00:00:00", "2024-07-02T00:00:00")],
        ),
        suggestions_path_next_to(index_path),
    )
    write_edicion(
        LabelOverlay(
            based_on_scanned_at="2026-01-01T00:00:00",
            labels={"2024-01-01T00:00:00": "Viaje a Bariloche"},
        ),
edicion_path_next_to(index_path),
    )

    document, flat = build_view(index_path)

    assert flat is False
    assert "<h2>Viaje a Bariloche</h2>" in document
    # el resto de los datos de la tarjeta no cambian
    assert "Argentina" in document
    # y sigue siendo de solo lectura
    assert 'data-mode="solo-lectura"' in document
    assert "solo lectura" in document
    assert "<form" not in document
    assert "fetch(" not in document


def test_a_labelled_period_card_declares_no_country() -> None:
    """Escenario 'Etiqueta sobre un periodo': sin pais, porque el periodo no declara."""
    from fotos_plus.viewer import render_html

    groups = assign_groups(
        [photo("a.jpg", "2024-07-01T00:00:00")],
        suggestions(periods=[period("2024-07-01T00:00:00", "2024-07-02T00:00:00")]),
        labels={"2024-07-01T00:00:00": "Sin fecha clara"},
    )

    assert groups[0].kind == "period"
    assert groups[0].title == "Sin fecha clara"
    assert groups[0].country is None

    document = render_html(groups, "C:/fotos", labels={"2024-07-01T00:00:00": "Sin fecha clara"})
    assert "<h2>Sin fecha clara</h2>" in document
    assert "Argentina" not in document


def test_a_labelled_trip_keeps_its_other_data() -> None:
    """Escenario 'Grupo con etiqueta': la etiqueta cambia el titulo y nada mas."""
    groups = assign_groups(
        [photo("a.jpg", "2024-01-01T00:00:00")],
        suggestions(trips=[trip("2024-01-01T00:00:00", "2024-01-05T00:00:00")]),
        labels={"2024-01-01T00:00:00": "Viaje a Bariloche"},
    )

    group = groups[0]
    assert group.title == "Viaje a Bariloche"
    assert group.country == "Argentina"
    assert group.first_captured_at == "2024-01-01T00:00:00"
    assert group.last_captured_at == "2024-01-05T00:00:00"
    assert group.photo_count == 1


# --- Secciones por tag ---


def _tagged(*entries: tuple[str, str | None]) -> dict[str, str]:
    return {key: tag for key, tag in entries if tag is not None}


def test_tags_reach_the_groups_without_touching_their_content() -> None:
    result = suggestions(
        trips=[trip("2024-05-01T00:00:00", "2024-05-02T00:00:00")]
    )
    photos = [photo("a.jpg", "2024-05-01T10:00:00")]

    plain = assign_groups(photos, result)
    tagged = assign_groups(
        photos,
        result,
        labels={},
        tags={"2024-05-01T00:00:00": "Familia"},
    )

    assert tagged[0].tag == "Familia"
    # el tag no altera la cantidad de fotos ni el rango
    assert tagged[0].photo_count == plain[0].photo_count
    assert tagged[0].first_captured_at == plain[0].first_captured_at
    assert tagged[0].last_captured_at == plain[0].last_captured_at


def test_no_sections_when_nothing_is_tagged() -> None:
    groups = assign_groups(
        [photo("a.jpg", "2024-05-01T10:00:00")],
        suggestions(trips=[trip("2024-05-01T00:00:00", "2024-05-02T00:00:00")]),
    )

    assert group_sections(groups) == []


def test_one_section_per_tag() -> None:
    result = suggestions(
        trips=[
            trip("2024-05-01T00:00:00", "2024-05-02T00:00:00"),
            trip("2024-06-01T00:00:00", "2024-06-02T00:00:00"),
            trip("2024-07-01T00:00:00", "2024-07-02T00:00:00"),
        ]
    )
    photos = [
        photo("a.jpg", "2024-05-01T10:00:00"),
        photo("b.jpg", "2024-06-01T10:00:00"),
        photo("c.jpg", "2024-07-01T10:00:00"),
    ]
    groups = assign_groups(
        photos,
        result,
        tags={
            "2024-05-01T00:00:00": "Viaje",
            "2024-06-01T00:00:00": "Familia",
            "2024-07-01T00:00:00": "Viaje",
        },
    )

    sections = group_sections(groups)

    assert [section.title for section in sections] == ["Viaje", "Familia"]
    assert [section.count for section in sections] == [2, 1]


def test_untagged_groups_get_their_own_section_at_the_end() -> None:
    result = suggestions(
        trips=[
            trip("2024-05-01T00:00:00", "2024-05-02T00:00:00"),
            trip("2024-06-01T00:00:00", "2024-06-02T00:00:00"),
        ]
    )
    photos = [
        photo("a.jpg", "2024-05-01T10:00:00"),
        photo("b.jpg", "2024-06-01T10:00:00"),
    ]
    groups = assign_groups(
        photos,
        result,
        tags={"2024-06-01T00:00:00": "Viaje"},
    )

    sections = group_sections(groups)

    assert [section.tag for section in sections] == ["Viaje", None]
    assert sections[-1].title == UNTAGGED_SECTION_TITLE
    assert sections[-1].count == 1


def test_sections_are_ordered_by_the_date_of_their_first_group() -> None:
    result = suggestions(
        trips=[
            trip("2024-05-01T00:00:00", "2024-05-02T00:00:00"),
            trip("2024-06-01T00:00:00", "2024-06-02T00:00:00"),
        ]
    )
    photos = [
        photo("a.jpg", "2024-05-01T10:00:00"),
        photo("b.jpg", "2024-06-01T10:00:00"),
    ]
    groups = assign_groups(
        photos,
        result,
        tags={
            "2024-06-01T00:00:00": "Familia",
            "2024-05-01T00:00:00": "Viaje",
        },
    )

    sections = group_sections(groups)

    # el tag mas reciente sigue apareciendo despues: manda la fecha, no el catalogo
    assert [section.title for section in sections] == ["Viaje", "Familia"]


def test_sections_keep_the_date_order_inside_them() -> None:
    result = suggestions(
        trips=[
            trip("2024-05-01T00:00:00", "2024-05-02T00:00:00"),
            trip("2024-07-01T00:00:00", "2024-07-02T00:00:00"),
        ]
    )
    photos = [
        photo("a.jpg", "2024-05-01T10:00:00"),
        photo("b.jpg", "2024-07-01T10:00:00"),
    ]
    groups = assign_groups(
        photos,
        result,
        tags={
            "2024-05-01T00:00:00": "Viaje",
            "2024-07-01T00:00:00": "Viaje",
        },
    )

    section = group_sections(groups)[0]

    assert [group.first_captured_at for group in section.groups] == [
        "2024-05-01T00:00:00",
        "2024-07-01T00:00:00",
    ]


def test_a_tag_with_no_assigned_groups_gets_no_section() -> None:
    groups = assign_groups(
        [photo("a.jpg", "2024-05-01T10:00:00")],
        suggestions(trips=[trip("2024-05-01T00:00:00", "2024-05-02T00:00:00")]),
        tags={"2024-05-01T00:00:00": "Viaje"},
    )

    # el catalogo puede traer "Trabajo", pero ninguna tarjeta lo tiene
    sections = group_sections(groups)

    assert [section.title for section in sections] == ["Viaje"]


def _tagged_html(
    root: Path, tags: dict[str, str], catalog=(), token: str | None = None
) -> str:
    """Genera el documento del visor con tags ya resueltos en las tarjetas.

    Sin `token` sale el export de solo lectura; con token, la pagina editable.
    """
    from fotos_plus.viewer import render_html

    result = suggestions(
        trips=[
            trip("2024-01-01T00:00:00", "2024-01-02T00:00:00"),
            trip("2024-06-01T00:00:00", "2024-06-02T00:00:00"),
        ]
    )
    photos = [
        photo("a.jpg", "2024-01-01T10:00:00"),
        photo("b.jpg", "2024-06-01T10:00:00"),
    ]
    groups = assign_groups(photos, result, tags=tags)
    return render_html(groups, str(root), token=token, tag_options=catalog)


def test_html_renders_a_section_per_tag(tmp_path: Path) -> None:
    root = tmp_path / "fotos"
    _write_photos(root, ["a.jpg", "b.jpg"])

    document = _tagged_html(
        root,
        {
            "2024-01-01T00:00:00": "Viaje",
            "2024-06-01T00:00:00": "Familia",
        },
    )

    assert document.count('<section class="tag-section"') == 2
    assert 'data-drop="Viaje"' in document
    assert 'data-drop="Familia"' in document
    assert document.count('<article class="card"') == 2


def test_html_shows_the_group_count_on_each_section(tmp_path: Path) -> None:
    root = tmp_path / "fotos"
    _write_photos(root, ["a.jpg", "b.jpg"])

    document = _tagged_html(
        root,
        {
            "2024-01-01T00:00:00": "Viaje",
            "2024-06-01T00:00:00": "Viaje",
        },
    )

    assert document.count('<section class="tag-section"') == 1
    assert '<span class="tag-section-count">2 grupos</span>' in document


def test_html_uses_the_singular_for_a_single_group(tmp_path: Path) -> None:
    root = tmp_path / "fotos"
    _write_photos(root, ["a.jpg", "b.jpg"])

    document = _tagged_html(root, {"2024-01-01T00:00:00": "Viaje"})

    assert '<span class="tag-section-count">1 grupo</span>' in document


def test_html_ends_with_the_untagged_section(tmp_path: Path) -> None:
    root = tmp_path / "fotos"
    _write_photos(root, ["a.jpg", "b.jpg"])

    document = _tagged_html(root, {"2024-06-01T00:00:00": "Familia"})

    assert 'data-drop=""' in document
    assert document.index('data-drop="Familia"') < document.index('data-drop=""')
    assert UNTAGGED_SECTION_TITLE in document


def test_html_puts_the_tag_on_each_card(tmp_path: Path) -> None:
    root = tmp_path / "fotos"
    _write_photos(root, ["a.jpg", "b.jpg"])

    document = _tagged_html(
        root,
        {
            "2024-01-01T00:00:00": "Viaje",
            "2024-06-01T00:00:00": "Familia",
        },
    )

    assert 'data-tag="Viaje"' in document
    assert 'data-tag="Familia"' in document


def test_an_untagged_card_carries_an_empty_tag(tmp_path: Path) -> None:
    root = tmp_path / "fotos"
    _write_photos(root, ["a.jpg", "b.jpg"])

    document = _tagged_html(root, {"2024-01-01T00:00:00": "Viaje"})

    assert 'data-tag=""' in document


def test_html_without_tags_keeps_the_single_grid(tmp_path: Path) -> None:
    from fotos_plus.viewer import render_html

    root = tmp_path / "fotos"
    _write_photos(root, ["a.jpg", "b.jpg"])
    result = suggestions(
        trips=[
            trip("2024-01-01T00:00:00", "2024-01-02T00:00:00"),
            trip("2024-06-01T00:00:00", "2024-06-02T00:00:00"),
        ]
    )
    photos = [
        photo("a.jpg", "2024-01-01T10:00:00"),
        photo("b.jpg", "2024-06-01T10:00:00"),
    ]
    groups = assign_groups(photos, result)

    document = render_html(groups, str(root))

    assert document.count('<section class="tag-section"') == 0
    assert document.count('<div class="grid">') == 1
    assert document.count('<article class="card"') == 2


def test_the_drift_notice_mentions_tags_not_only_labels(tmp_path: Path) -> None:
    from fotos_plus.labels import LabelResolution
    from fotos_plus.viewer import render_html

    root = tmp_path / "fotos"
    _write_photos(root, ["a.jpg"])
    groups = assign_groups(
        [photo("a.jpg", "2024-01-01T10:00:00")],
        suggestions(trips=[trip("2024-01-01T00:00:00", "2024-01-02T00:00:00")]),
    )
    # un nombre resuelto, un tag resuelto y un tag que quedo sin grupo
    drift = LabelResolution(
        labels={"2024-01-01T00:00:00": "Navidad"},
        tags={"2024-01-01T00:00:00": "Familia"},
        unresolved_tags=["2030-01-01T00:00:00"],
    )

    document = render_html(groups, str(root), drift=drift)

    assert "nombres y tags" in document
    assert "Siguen guardados" in document
    # 1 nombre + 1 tag resueltos + 1 sin grupo
    assert "1 de 3" in document


def test_the_tag_selector_offers_the_catalog(tmp_path: Path) -> None:
    root = tmp_path / "fotos"
    _write_photos(root, ["a.jpg", "b.jpg"])

    document = _tagged_html(
        root,
        {"2024-01-01T00:00:00": "Viaje"},
        catalog=["Viaje", "Familia"],
        token="t0ken",
    )

    assert f'list="{TAG_CATALOG_ID}"' in document
    assert '<option value="Familia">' in document


def test_the_tag_selector_shows_the_current_tag(tmp_path: Path) -> None:
    root = tmp_path / "fotos"
    _write_photos(root, ["a.jpg", "b.jpg"])

    document = _tagged_html(root, {"2024-01-01T00:00:00": "Familia"}, token="t0ken")

    assert 'value="Familia"' in document
    assert "Quitar tag" in document


def test_an_untagged_card_has_no_remove_button(tmp_path: Path) -> None:
    root = tmp_path / "fotos"
    _write_photos(root, ["a.jpg", "b.jpg"])

    document = _tagged_html(root, {"2024-01-01T00:00:00": "Familia"}, token="t0ken")

    # la segunda tarjeta no tiene tag, asi que no hay nada que quitar
    assert document.count("Quitar tag") == 1


def test_the_catalog_is_emitted_once_for_the_whole_document(tmp_path: Path) -> None:
    root = tmp_path / "fotos"
    _write_photos(root, ["a.jpg", "b.jpg"])

    document = _tagged_html(
        root,
        {
            "2024-01-01T00:00:00": "Familia",
            "2024-06-01T00:00:00": "Viaje",
        },
        token="t0ken",
    )

    assert document.count(f'<datalist id="{TAG_CATALOG_ID}">') == 1


def test_the_catalog_includes_tags_that_still_have_cards(tmp_path: Path) -> None:
    root = tmp_path / "fotos"
    _write_photos(root, ["a.jpg", "b.jpg"])

    # "Viaje" no esta en el catalogo pero una tarjeta lo tiene
    document = _tagged_html(
        root,
        {"2024-06-01T00:00:00": "Viaje"},
        catalog=["Familia"],
        token="t0ken",
    )

    assert '<option value="Familia">' in document
    assert '<option value="Viaje">' in document


# --- Arrastre y solo lectura ---


def test_the_editable_page_makes_cards_draggable(tmp_path: Path) -> None:
    root = tmp_path / "fotos"
    _write_photos(root, ["a.jpg", "b.jpg"])

    document = _tagged_html(root, {"2024-01-01T00:00:00": "Viaje"}, token="t0ken")

    assert 'card.setAttribute("draggable", "true")' in document
    assert "dragstart" in document


def test_the_editable_page_wires_the_three_drop_targets(tmp_path: Path) -> None:
    root = tmp_path / "fotos"
    _write_photos(root, ["a.jpg", "b.jpg"])

    document = _tagged_html(root, {"2024-01-01T00:00:00": "Viaje"}, token="t0ken")

    # tarjeta, seccion y el "Sin tag" se resuelven con el mismo manejador
    assert 'card.getAttribute("data-tag") || ""' in document
    assert 'seccion.getAttribute("data-drop") || ""' in document
    assert 'if (tagDestino)' in document


def test_the_selector_refuses_an_empty_tag_without_calling_the_server(tmp_path: Path) -> None:
    root = tmp_path / "fotos"
    _write_photos(root, ["a.jpg", "b.jpg"])

    document = _tagged_html(root, {"2024-01-01T00:00:00": "Viaje"}, token="t0ken")

    # un tag vacio avisa y no se manda: quitarlo es clear_tag, no set_tag con ""
    assert "Un tag no puede estar vacio" in document
    assert "if (!texto)" in document


def test_a_rejected_tag_leaves_the_card_untouched(tmp_path: Path) -> None:
    root = tmp_path / "fotos"
    _write_photos(root, ["a.jpg", "b.jpg"])

    document = _tagged_html(root, {"2024-01-01T00:00:00": "Viaje"}, token="t0ken")

    # el DOM no se toca hasta que el servidor confirma, y recien ahi se recarga
    assert "mostrarErrorTag" in document
    assert "window.location.reload()" in document


def test_the_read_only_export_has_no_drag_or_tag_controls(tmp_path: Path) -> None:
    root = tmp_path / "fotos"
    _write_photos(root, ["a.jpg", "b.jpg"])

    document = _tagged_html(root, {"2024-01-01T00:00:00": "Viaje"})

    # El script de edicion no viaja: sin el no hay arrastre ni selector, porque las
    # tarjetas no reciben el atributo draggable que el CSS de arrastre espera.
    assert "dragstart" not in document
    assert "set_tag" not in document
    assert "clear_tag" not in document
    assert "Quitar tag" not in document
    assert f'<datalist id="{TAG_CATALOG_ID}">' not in document
    assert "<script>" not in document
    # pero las secciones si se ven
    assert '<section class="tag-section"' in document
    assert 'data-tag="Viaje"' in document
    assert "solo lectura" in document
