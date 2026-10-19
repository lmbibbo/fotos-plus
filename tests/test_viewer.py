from __future__ import annotations

import json
import re
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
    render_html,
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
    root: Path,
    tags: dict[str, str],
    catalog=(),
    token: str | None = None,
    photo_tags=(),
    photo_tagged=None,
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
    return render_html(
        groups,
        str(root),
        token=token,
        tag_options=catalog,
        # Sin token el render borra las marcas y no viaja inventario; con token, viaja.
        marked=[],
        photo_tags=photo_tags,
        photo_tagged=photo_tagged,
    )


def _payload_of(document: str) -> dict:
    return json.loads(re.search(r'id="viewer-data">(.*?)</script>', document, re.S).group(1))


# --- 5.1 catalogo y pertenencia en el payload servido -------------------------


def test_the_served_payload_carries_the_bucket_catalogue_and_membership(
    tmp_path: Path,
) -> None:
    root = tmp_path / "fotos"
    _write_photos(root, ["a.jpg", "b.jpg"])

    document = _tagged_html(
        root,
        {"2024-01-01T00:00:00": "Viaje"},
        token="t0ken",
        photo_tags=["Favoritas", "Para imprimir"],
        photo_tagged={"a.jpg": ["Favoritas"], "b.jpg": ["Favoritas", "Para imprimir"]},
    )

    payload = _payload_of(document)
    assert payload["photo_tags"] == ["Favoritas", "Para imprimir"]
    assert payload["photo_tagged"] == {
        "a.jpg": ["Favoritas"],
        "b.jpg": ["Favoritas", "Para imprimir"],
    }


def test_adding_buckets_leaves_every_existing_payload_field_untouched(
    tmp_path: Path,
) -> None:
    root = tmp_path / "fotos"
    _write_photos(root, ["a.jpg"])

    without = _payload_of(_tagged_html(root, {}, token="t0ken"))
    with_buckets = _payload_of(
        _tagged_html(
            root,
            {},
            token="t0ken",
            photo_tags=["Favoritas"],
            photo_tagged={"a.jpg": ["Favoritas"]},
        )
    )

    # Los cubos agregan dos claves y nada mas: los grupos y el modo van iguales.
    assert set(with_buckets) == set(without) | {"photo_tags", "photo_tagged"}
    assert with_buckets["groups"] == without["groups"]
    assert with_buckets["flat"] == without["flat"]
    # Sin cubos, las dos claves viajan vacias y no rompen el script del recorrido.
    assert without["photo_tags"] == []
    assert without["photo_tagged"] == {}


def test_the_export_payload_carries_no_bucket_fields(tmp_path: Path) -> None:
    root = tmp_path / "fotos"
    _write_photos(root, ["a.jpg"])

    # Sin token el documento es el export: no hay donde guardar, asi que no viaja nada.
    document = _tagged_html(
        root,
        {},
        photo_tags=["Favoritas"],
        photo_tagged={"a.jpg": ["Favoritas"]},
    )

    payload = _payload_of(document)
    assert "photo_tags" not in payload
    assert "photo_tagged" not in payload


def test_a_photo_holding_no_bucket_is_left_out_of_the_membership_map(
    tmp_path: Path,
) -> None:
    root = tmp_path / "fotos"
    _write_photos(root, ["a.jpg", "b.jpg"])

    document = _tagged_html(
        root,
        {},
        token="t0ken",
        photo_tags=["Favoritas"],
        photo_tagged={"a.jpg": ["Favoritas"], "b.jpg": []},
    )

    assert _payload_of(document)["photo_tagged"] == {"a.jpg": ["Favoritas"]}


# --- 5.2 el control del selector ----------------------------------------------


def test_the_served_markup_carries_the_bucket_picker(tmp_path: Path) -> None:
    root = tmp_path / "fotos"
    _write_photos(root, ["a.jpg"])

    document = _tagged_html(root, {}, token="t0ken", photo_tags=["Favoritas"])

    assert 'id="photo-browser-buckets"' in document
    assert 'id="photo-browser-bucket-list"' in document
    assert 'id="photo-browser-bucket-add"' in document
    assert 'class="bucket-input"' in document
    # El nombre nuevo se escribe en un input, con el catalogo como sugerencia.
    assert 'list="bucket-catalog"' in document


def test_the_picker_sits_next_to_the_mark_button(tmp_path: Path) -> None:
    root = tmp_path / "fotos"
    _write_photos(root, ["a.jpg"])

    document = _tagged_html(root, {}, token="t0ken")

    # El boton de marcar sigue siendo un solo boton, antes que el selector de cubos.
    assert document.index('id="photo-browser-mark"') < document.index(
        'id="photo-browser-buckets"'
    )
    # Marcar no se vuelve un selector: sigue siendo un boton que se aprieta una vez.
    assert document.count('id="photo-browser-mark"') == 1


def test_the_bucket_catalogue_is_offered_as_a_separate_datalist(tmp_path: Path) -> None:
    root = tmp_path / "fotos"
    _write_photos(root, ["a.jpg"])

    document = _tagged_html(
        root,
        {"2024-01-01T00:00:00": "Viaje"},
        catalog=["Viaje"],
        token="t0ken",
        photo_tags=["Viaje"],
    )

    # El mismo nombre en los dos ejes vive en dos datalists distintos, no en uno mezclado.
    assert f'<option value="Viaje"></option>' in document
    assert (
        document.count(f'<datalist id="{TAG_CATALOG_ID}"><option value="Viaje">') == 1
    )
    assert document.count('<datalist id="bucket-catalog">') == 1
    # El selector de cubos es uno solo en el recorrido; el de tags, uno por tarjeta.
    assert document.count('list="bucket-catalog"') == 1
    assert document.count('class="bucket-input"') == 1


def test_the_picker_is_absent_without_a_server(tmp_path: Path) -> None:
    root = tmp_path / "fotos"
    _write_photos(root, ["a.jpg"])

    document = _tagged_html(root, {}, photo_tags=["Favoritas"])

    assert 'id="photo-browser-buckets"' not in document
    assert "bucket-catalog" not in document


# --- 5.3 y 5.4 el script del selector -----------------------------------------


def _script_of(document: str) -> str:
    match = re.search(r'<script>\n(.*?)</script>', document, re.S)
    assert match, "el documento servido deberia traer el script de edicion"
    return match.group(1)


def test_the_picker_shows_the_photo_membership_and_reposts_on_change(
    tmp_path: Path,
) -> None:
    root = tmp_path / "fotos"
    _write_photos(root, ["a.jpg"])

    document = _tagged_html(root, {}, token="t0ken", photo_tags=["Favoritas"])
    script = _script_of(document)

    # Lee la pertenencia que ya trae la pagina, sin pedirla.
    assert "pintarCubos" in script
    assert 'datos.photo_tagged' in script or "photo_tagged" in script
    # Agregar y quitar van al endpoint con el hash de la foto, no con su ruta.
    assert '"/api/photo-tags"' in script
    assert "foto.sha256" in script
    # Y se repinta al cambiar de foto, sin recargar.
    assert "cubosDe" in script


def test_a_rejected_bucket_edit_reports_the_reason_and_restores_the_server_state(
    tmp_path: Path,
) -> None:
    root = tmp_path / "fotos"
    _write_photos(root, ["a.jpg"])

    document = _tagged_html(root, {}, token="t0ken", photo_tags=["Favoritas"])
    script = _script_of(document)

    # Ante un rechazo se avisa el motivo y se vuelve a pintar lo que el servidor dice,
    # no lo que se habia puesto de entrada.
    assert "datos.buckets" in script
    assert "pintarCubos" in script
    assert 'error || "No se pudo guardar el cubo"' in script


# --- 5.5 la documentacion ------------------------------------------------------


def test_the_readme_describes_the_picker_next_to_mark() -> None:
    readme = (Path(__file__).resolve().parents[1] / "README.md").read_text(
        encoding="utf-8"
    )

    assert "Marcar" in readme
    assert re.search(r"[Cc]ubo", readme)


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


# --- 4.2 el inventario solo viaja en la pagina servida ------------------------


def _embedded_payload(document: str) -> dict:
    return json.loads(re.search(r'id="viewer-data">(.*?)</script>', document, re.S).group(1))


def test_the_served_payload_carries_the_reference_of_every_group(tmp_path: Path) -> None:
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

    document = render_html(groups, str(root), token="secreto", marked=[])
    data = _embedded_payload(document)

    assert [g["browse_key"] for g in data["groups"]] == [
        "2024-01-01T00:00:00",
        "2024-07-01T00:00:00",
    ]


def test_the_served_payload_carries_the_mark_count_of_every_group(tmp_path: Path) -> None:
    from fotos_plus.viewer import render_html

    root = tmp_path / "fotos"
    _write_photos(root, ["a.jpg", "b.jpg", "c.jpg"])
    marked = [photo("b.jpg", "2024-07-01T00:00:00").sha256]
    groups = assign_groups(
        [
            photo("a.jpg", "2024-01-01T00:00:00"),
            photo("b.jpg", "2024-07-01T00:00:00"),
            photo("c.jpg", "2024-07-02T00:00:00"),
        ],
        suggestions(
            trips=[trip("2024-01-01T00:00:00", "2024-01-02T00:00:00")],
            periods=[period("2024-07-01T00:00:00", "2024-07-02T00:00:00")],
        ),
    )

    document = render_html(groups, str(root), token="secreto", marked=marked)
    data = _embedded_payload(document)

    counts = {g["browse_key"]: g["marked_count"] for g in data["groups"]}
    assert counts == {"2024-01-01T00:00:00": 0, "2024-07-01T00:00:00": 1}


def test_the_exported_payload_carries_no_inventory(tmp_path: Path) -> None:
    """El export no tiene a quien preguntar, asi que no lleva referencias ni marcas."""
    from fotos_plus.viewer import render_html

    root = tmp_path / "fotos"
    _write_photos(root, ["a.jpg"])
    groups = assign_groups(
        [photo("a.jpg", "2024-01-01T00:00:00")],
        suggestions(trips=[trip("2024-01-01T00:00:00", "2024-01-02T00:00:00")]),
    )

    document = render_html(groups, str(root))
    data = _embedded_payload(document)

    assert all("browse_key" not in g for g in data["groups"])
    assert all("marked_count" not in g for g in data["groups"])


def test_passing_marks_without_a_token_still_exports_no_inventory(tmp_path: Path) -> None:
    from fotos_plus.viewer import render_html

    root = tmp_path / "fotos"
    _write_photos(root, ["a.jpg"])
    groups = assign_groups(
        [photo("a.jpg", "2024-01-01T00:00:00")],
        suggestions(trips=[trip("2024-01-01T00:00:00", "2024-01-02T00:00:00")]),
    )

    document = render_html(groups, str(root), token=None, marked=["x" * 64])
    data = _embedded_payload(document)

    assert all("browse_key" not in g for g in data["groups"])


def test_the_unclassified_group_gets_a_reserved_reference() -> None:
    """El grupo de fotos sin clasificar tambien se puede recorrer."""
    from fotos_plus.viewer import UNCLASSIFIED_GROUP_KEY

    groups = assign_groups(
        [photo("suelta.jpg", "2024-03-01T00:00:00")],
        suggestions(trips=[trip("2024-01-01T00:00:00", "2024-01-02T00:00:00")]),
    )

    orphans = [g for g in groups if g.kind == "orphan"]
    assert len(orphans) == 1
    assert orphans[0].key is None
    assert orphans[0].browse_key == UNCLASSIFIED_GROUP_KEY


def test_a_served_photo_list_does_not_grow_the_page(tmp_path: Path) -> None:
    """Las fotos sueltas no se embeben: se piden por grupo."""
    from fotos_plus.viewer import render_html

    root = tmp_path / "fotos"
    names = [f"{i:03}.jpg" for i in range(40)]
    _write_photos(root, names)
    groups = assign_groups(
        [photo(n, "2024-01-01T00:00:00") for n in names],
        suggestions(trips=[trip("2024-01-01T00:00:00", "2024-01-02T00:00:00")]),
    )

    document = render_html(groups, str(root), token="secreto", marked=[])
    payload = re.search(r'id="viewer-data">(.*?)</script>', document, re.S).group(1)

    for name in names:
        assert name not in payload


# --- 5. recorrido de fotos a pantalla completa --------------------------------


def _browser_html(root: Path, names: list[str], token: str | None = "t0ken") -> str:
    return render_html(
        assign_groups(
            [photo(n, "2024-01-01T00:00:00") for n in names],
            suggestions(trips=[trip("2024-01-01T00:00:00", "2024-01-02T00:00:00")]),
        ),
        str(root),
        token=token,
        marked=[],
    )


def test_a_card_with_photos_offers_the_browser(tmp_path: Path) -> None:
    root = tmp_path / "fotos"
    _write_photos(root, ["a.jpg"])

    document = _browser_html(root, ["a.jpg"])

    assert '<button type="button" class="browse-open"' in document
    assert 'data-browse-key="2024-01-01T00:00:00"' in document


def test_a_card_with_no_photos_has_no_browser_button(tmp_path: Path) -> None:
    """Un grupo declarado que se quedo sin fotos no ofrece un recorrido vacio."""
    root = tmp_path / "fotos"
    _write_photos(root, [])
    groups = assign_groups(
        [],
        suggestions(trips=[trip("2024-01-01T00:00:00", "2024-01-02T00:00:00")]),
    )

    document = render_html(groups, str(root), token="t0ken", marked=[])

    assert '<button type="button" class="browse-open"' not in document
    assert 'id="photo-browser"' in document


def test_the_unclassified_group_offers_the_browser(tmp_path: Path) -> None:
    root = tmp_path / "fotos"
    _write_photos(root, ["suelta.jpg"])
    groups = assign_groups(
        [photo("suelta.jpg", "2024-03-01T00:00:00")],
        suggestions(trips=[trip("2024-01-01T00:00:00", "2024-01-02T00:00:00")]),
    )

    document = render_html(groups, str(root), token="t0ken", marked=[])

    assert 'data-browse-key="sin-clasificar"' in document


def test_the_browser_is_hidden_until_it_opens(tmp_path: Path) -> None:
    root = tmp_path / "fotos"
    _write_photos(root, ["a.jpg"])

    document = _browser_html(root, ["a.jpg"])

    assert '<div class="browser" id="photo-browser"' in document
    assert 'data-token="t0ken"' in document
    assert re.search(r'id="photo-browser"[^>]*\shidden', document)


def test_the_browser_shows_its_place_inside_the_group(tmp_path: Path) -> None:
    root = tmp_path / "fotos"
    _write_photos(root, ["a.jpg", "b.jpg"])

    document = _browser_html(root, ["a.jpg", "b.jpg"])

    assert 'id="photo-browser-position"' in document
    assert '(indice + 1) + " de " + lista.length' in document


def _sentencia(document: str, patron: str) -> str:
    """Una sentencia del script tal cual la ve el navegador."""
    found = re.findall(patron, document, re.DOTALL)
    assert len(found) == 1, f"se esperaba una sola sentencia, hay {len(found)}"
    return found[0]


def _fecha_declaration(document: str) -> str:
    return _sentencia(document, r"var fecha =.*?;")


def _position_assignment(document: str) -> str:
    return _sentencia(document, r"posicion\.textContent =.*?;")


def test_the_position_line_carries_the_capture_date_of_the_photo(
    tmp_path: Path,
) -> None:
    """La foto mostrada dice que dia es: el recorrido es de una en una y la fecha no se deduce."""
    root = tmp_path / "fotos"
    _write_photos(root, ["a.jpg"])

    document = _browser_html(root, ["a.jpg"])

    declaracion = _fecha_declaration(document)
    assert "foto.captured_at" in declaracion
    assert ".slice(0, 10)" in declaracion

    asignacion = _position_assignment(document)
    assert '" \\u00b7 " + fecha' in asignacion


def test_a_photo_without_a_capture_date_leaves_the_position_line_alone(
    tmp_path: Path,
) -> None:
    """Sin EXIF la linea queda como estaba: sin fecha y sin un texto que la reemplace."""
    root = tmp_path / "fotos"
    _write_photos(root, ["a.jpg"])

    document = _browser_html(root, ["a.jpg"])

    assert 'foto.captured_at ? foto.captured_at.slice(0, 10) : ""' in _fecha_declaration(
        document
    )
    assert 'fecha ? " \\u00b7 " + fecha : ""' in _position_assignment(document)
    assert "sin fecha" not in document
    assert "Sin fecha" not in document


def test_the_shown_date_follows_the_photo_because_navigation_reassigns_the_line(
    tmp_path: Path,
) -> None:
    """La fecha no puede quedar vieja: la pinta `mostrar`, que es por donde pasa todo salto."""
    root = tmp_path / "fotos"
    _write_photos(root, ["a.jpg", "b.jpg"])

    document = _browser_html(root, ["a.jpg", "b.jpg"])

    mostrar = re.search(
        r"function mostrar\(indiceNuevo\) \{(.*?)\n    \}", document, re.DOTALL
    )
    assert mostrar is not None
    assert "posicion.textContent" in mostrar.group(1)
    assert "foto.captured_at" in mostrar.group(1)

    for salto in (
        "botonPrevio.addEventListener(\"click\", function () { mostrar(indice - 1); });",
        "botonSiguiente.addEventListener(\"click\", function () { mostrar(indice + 1); });",
        "mostrar(indice || 0);",
    ):
        assert salto in document, f"ningun camino de navegacion llama a mostrar: {salto}"


def test_the_browser_asks_the_server_for_the_photo(tmp_path: Path) -> None:
    """La imagen no puede ir en un `src`: el token viaja en un encabezado."""
    root = tmp_path / "fotos"
    _write_photos(root, ["a.jpg"])

    document = _browser_html(root, ["a.jpg"])

    assert 'fetch(rutaFoto, {' in document
    assert 'var rutaFoto = "/render?ref=" + encodeURIComponent(foto.ref);' in document
    assert '"X-Fotos-Plus-Token": token' in document
    assert "URL.createObjectURL(blob)" in document
    assert "URL.revokeObjectURL(urlActual)" in document


def test_the_browser_has_both_directions(tmp_path: Path) -> None:
    root = tmp_path / "fotos"
    _write_photos(root, ["a.jpg", "b.jpg"])

    document = _browser_html(root, ["a.jpg", "b.jpg"])

    assert 'id="photo-browser-prev"' in document
    assert 'id="photo-browser-next"' in document
    assert "mostrar(indice - 1)" in document
    assert "mostrar(indice + 1)" in document


def test_the_browser_stops_at_the_ends_instead_of_wrapping(tmp_path: Path) -> None:
    root = tmp_path / "fotos"
    _write_photos(root, ["a.jpg", "b.jpg"])

    document = _browser_html(root, ["a.jpg", "b.jpg"])

    assert "Math.max(0, Math.min(indiceNuevo, lista.length - 1))" in document


def test_the_browser_binds_the_keyboard_in_both_directions(tmp_path: Path) -> None:
    root = tmp_path / "fotos"
    _write_photos(root, ["a.jpg", "b.jpg"])

    document = _browser_html(root, ["a.jpg", "b.jpg"])

    assert 'evento.key === "ArrowLeft"' in document
    assert 'evento.key === "ArrowRight"' in document


def test_the_browser_leaves_the_keys_alone_while_typing(tmp_path: Path) -> None:
    root = tmp_path / "fotos"
    _write_photos(root, ["a.jpg"])

    document = _browser_html(root, ["a.jpg"])

    assert 'destino.tagName === "INPUT"' in document
    assert 'destino.tagName === "TEXTAREA"' in document
    assert "destino.isContentEditable" in document
    assert "if (escribiendo(evento)) { return; }" in document


def test_the_browser_shows_whether_the_photo_is_marked(tmp_path: Path) -> None:
    root = tmp_path / "fotos"
    _write_photos(root, ["a.jpg"])

    document = _browser_html(root, ["a.jpg"])

    assert 'id="photo-browser-mark"' in document
    assert 'botonMarcar.setAttribute("aria-pressed"' in document
    assert 'foto.marked ? "Quitar la marca" : "Marcar"' in document
    # el estado se vuelve a pintar en cada foto, para que al mover se vea el de esa
    assert "pintarMarca(foto);" in document


def test_the_mark_updates_without_reloading(tmp_path: Path) -> None:
    root = tmp_path / "fotos"
    _write_photos(root, ["a.jpg"])

    document = _browser_html(root, ["a.jpg"])

    assert 'fetch("/api/marks"' in document
    assert 'action: marcada ? "mark" : "unmark"' in document
    assert "foto.marked = datos.marked;" in document
    assert "window.location.reload()" not in document.split("photo-browser")[-1]


def test_closing_the_browser_touches_no_mark(tmp_path: Path) -> None:
    root = tmp_path / "fotos"
    _write_photos(root, ["a.jpg", "b.jpg"])

    document = _browser_html(root, ["a.jpg", "b.jpg"])

    # cerrar solo esconde y suelta la imagen: no manda nada al servidor
    assert "function cerrar()" in document
    assert "browser.hidden = true;" in document
    assert 'evento.key === "Escape"' in document
    cerrar = document.split("function cerrar()")[1].split("}")[0]
    assert "fetch(" not in cerrar
    assert "marcar" not in cerrar.lower()


def test_the_exported_html_has_no_browser(tmp_path: Path) -> None:
    """El export no lleva el recorrido: sin servidor no hay renders que pedir."""
    root = tmp_path / "fotos"
    _write_photos(root, ["a.jpg", "b.jpg"])

    document = _browser_html(root, ["a.jpg", "b.jpg"], token=None)

    assert 'id="photo-browser"' not in document
    assert '<button type="button" class="browse-open"' not in document
    assert "/render?ref=" not in document
    assert "/api/photos" not in document
    assert "/api/marks" not in document
    assert "<script>" not in document


# --- la rejilla de un grupo ------------------------------------------------------


def test_the_grid_is_served_hidden_with_a_back_control(tmp_path: Path) -> None:
    root = tmp_path / "fotos"
    _write_photos(root, ["a.jpg"])

    document = _browser_html(root, ["a.jpg"])

    assert '<section class="group-grid" id="group-grid" hidden>' in document
    assert 'id="group-grid-back"' in document
    assert 'id="group-grid-cells"' in document


def test_the_grid_cells_carry_the_thumb_scale_columns(tmp_path: Path) -> None:
    """Las celdas van a la escala de las miniaturas de las tarjetas, sin recorte."""
    root = tmp_path / "fotos"
    _write_photos(root, ["a.jpg"])

    document = _browser_html(root, ["a.jpg"])

    assert '<div class="grid-cells" id="group-grid-cells">' in document
    assert ".grid-cells { display: grid; gap: 8px;" in document
    assert "grid-template-columns: repeat(auto-fill, minmax(56px, 1fr)); }" in document
    assert ".video-tile" in document
    assert "min-height: 36px;" in document


def test_cells_render_one_lazy_item_in_browse_order(tmp_path: Path) -> None:
    root = tmp_path / "fotos"
    _write_photos(root, ["a.jpg", "b.jpg"])

    document = _browser_html(root, ["a.jpg", "b.jpg"])

    assert "lista.forEach(function (foto, i)" in document
    assert 'boton.setAttribute("data-indice", String(i));' in document
    assert 'img.loading = "lazy";' in document


def test_photo_cells_ask_for_thumbs_and_video_cells_for_posters(tmp_path: Path) -> None:
    root = tmp_path / "fotos"
    _write_photos(root, ["a.jpg"])

    document = _browser_html(root, ["a.jpg"])

    assert 'img.src = urlMedio(esVideo ? "/poster" : "/thumb", foto.ref);' in document
    assert '"/render", foto.ref' not in document


def test_a_video_cell_falls_back_to_the_duration_tile(tmp_path: Path) -> None:
    root = tmp_path / "fotos"
    _write_photos(root, ["a.jpg"])

    document = _browser_html(root, ["a.jpg"])

    assert 'ficha.className = esVideo ? "video-tile" : "thumb-tile";' in document
    assert 'ficha.textContent = esVideo ? fichaVideo(foto) : "Sin miniatura";' in document
    assert "boton.replaceChild(ficha, img)" in document


def test_a_photo_cell_falls_back_to_a_placeholder(tmp_path: Path) -> None:
    """Una miniatura que el servidor no puede servir no queda como imagen rota."""
    root = tmp_path / "fotos"
    _write_photos(root, ["a.jpg"])

    document = _browser_html(root, ["a.jpg"])

    # El manejador de error ya no esta atado solo al video: tambien cubre la foto.
    assert 'var esVideo = foto.kind === "video";' in document
    assert 'img.addEventListener("error", function () {' in document
    assert '"thumb-tile"' in document
    assert '"Sin miniatura"' in document
    assert ".thumb-tile" in document


def test_clicking_a_cell_opens_the_browser_at_that_index(tmp_path: Path) -> None:
    root = tmp_path / "fotos"
    _write_photos(root, ["a.jpg", "b.jpg"])

    document = _browser_html(root, ["a.jpg", "b.jpg"])

    assert "function abrir(clave, indice)" in document
    assert "mostrar(indice || 0);" in document
    assert 'boton.addEventListener("click", function () { abrir(claveActual, i); });' in document


def test_closing_returns_to_the_grid_and_the_back_control_to_the_cards(
    tmp_path: Path,
) -> None:
    root = tmp_path / "fotos"
    _write_photos(root, ["a.jpg"])

    document = _browser_html(root, ["a.jpg"])

    cerrar = _sentencia(document, r"function cerrar\(\) \{.*?\n    \}")
    assert "rejilla.hidden = false" in cerrar
    assert "tarjetas.hidden = false" in cerrar
    volver = _sentencia(document, r"function volverTarjetas\(\) \{.*?\n    \}")
    assert "rejilla.hidden = true" in volver
    assert "tarjetas.hidden = false" in volver


def test_the_export_has_no_grid(tmp_path: Path) -> None:
    """Sin servidor no hay lista ni miniaturas que pedir: el export no lleva rejilla."""
    root = tmp_path / "fotos"
    _write_photos(root, ["a.jpg"])

    document = _browser_html(root, ["a.jpg"], token=None)

    assert '<section class="group-grid"' not in document
    assert "/thumb" not in document
    assert "/poster" not in document


# --- 6.1 y 6.2 tarjetas de fotos ----------------------------------------------


def _sections_html(tmp_path: Path, **kwargs) -> str:
    from fotos_plus.viewer import render_html

    root = tmp_path / "fotos"
    _write_photos(root, ["a.jpg", "b.jpg"])
    groups = assign_groups(
        [photo("a.jpg", "2024-01-01T10:00:00"), photo("b.jpg", "2024-06-01T10:00:00")],
        suggestions(
            trips=[
                trip("2024-01-01T00:00:00", "2024-01-02T00:00:00"),
                trip("2024-06-01T00:00:00", "2024-06-02T00:00:00"),
            ]
        ),
    )
    return render_html(groups, str(root), token="t0ken", **kwargs)


def _photo_card(document: str, title: str) -> str:
    """El articulo de la tarjeta de fotos con ese titulo."""
    heading = f"<h2>{title}</h2>"
    start = document.index(heading)
    start = document.rfind('<article class="card photo-card"', 0, start)
    end = document.index("</article>", start)
    return document[start:end]


def test_photo_cards_come_out_marked_then_buckets() -> None:
    from fotos_plus.viewer import (
        MARKED_COLLECTION_KEY,
        MARKED_SECTION_TITLE,
        bucket_collection_key,
        photo_cards,
    )

    a = photo("a.jpg", "2024-01-01T10:00:00")
    b = photo("b.jpg", "2024-06-01T10:00:00")
    c = photo("c.jpg", "2024-09-01T10:00:00")

    cards = photo_cards(
        [a, b, c],
        marked=[b.sha256],
        photo_tags=["Favoritas", "Para imprimir"],
        photo_tagged={a.sha256: ["Favoritas"], b.sha256: ["Para imprimir"]},
    )

    assert [card.title for card in cards] == [
        MARKED_SECTION_TITLE,
        "Favoritas",
        "Para imprimir",
    ]
    assert cards[0].collection_key == MARKED_COLLECTION_KEY
    assert cards[1].browse_key == bucket_collection_key("Favoritas")
    assert cards[0].key is None
    assert cards[0].country is None


def test_bucket_cards_follow_the_catalogue_order_not_the_date_order() -> None:
    from fotos_plus.viewer import photo_cards

    a = photo("a.jpg", "2024-01-01T10:00:00")
    b = photo("b.jpg", "2024-06-01T10:00:00")

    cards = photo_cards(
        [a, b],
        photo_tags=["Zeta", "Alfa"],
        photo_tagged={"a.jpg": ["Alfa"], "b.jpg": ["Zeta"]},
    )

    # El orden es el del catalogo, no el de la fecha de cada foto.
    assert [card.title for card in cards] == ["Zeta", "Alfa"]


def test_a_catalogue_name_holding_no_photo_gets_no_card() -> None:
    from fotos_plus.viewer import photo_cards

    a = photo("a.jpg", "2024-01-01T10:00:00")

    cards = photo_cards(
        [a], photo_tags=["Favoritas", "Vacio"], photo_tagged={"a.jpg": ["Favoritas"]}
    )

    assert [card.title for card in cards] == ["Favoritas"]


def test_a_photo_in_several_buckets_appears_in_each_card() -> None:
    from fotos_plus.viewer import photo_cards

    a = photo("a.jpg", "2024-01-01T10:00:00")

    cards = photo_cards(
        [a],
        photo_tags=["Favoritas", "Para imprimir"],
        photo_tagged={"a.jpg": ["Favoritas", "Para imprimir"]},
    )

    assert [card.title for card in cards] == ["Favoritas", "Para imprimir"]
    assert all(card.photos == [a] for card in cards)


def test_a_marked_photo_with_a_bucket_appears_in_both_cards() -> None:
    from fotos_plus.viewer import photo_cards

    a = photo("a.jpg", "2024-01-01T10:00:00")

    cards = photo_cards(
        [a],
        marked=[a.sha256],
        photo_tags=["Favoritas"],
        photo_tagged={"a.jpg": ["Favoritas"]},
    )

    assert [card.title for card in cards] == ["Marcadas", "Favoritas"]
    assert all(card.photos == [a] for card in cards)


def test_no_photo_at_all_gets_no_photo_cards() -> None:
    from fotos_plus.viewer import photo_cards

    assert photo_cards([], marked=["a.jpg"], photo_tags=["Favoritas"]) == []


def test_an_undated_photo_still_gets_a_card_and_follows_browse_order() -> None:
    from fotos_plus.viewer import _photo_sort_key, photo_cards

    con_fecha = photo("a.jpg", "2024-01-01T10:00:00")
    sin_fecha = photo("b.jpg", None)

    cards = photo_cards(
        [sin_fecha, con_fecha],
        photo_tags=["Favoritas"],
        photo_tagged={"a.jpg": ["Favoritas"], "b.jpg": ["Favoritas"]},
    )

    # No se descarta por no tener fecha: aparece, y en el mismo orden que el recorrido.
    assert cards[0].photos == [sin_fecha, con_fecha]
    assert cards[0].photos == sorted([sin_fecha, con_fecha], key=_photo_sort_key)
    assert cards[0].first_captured_at == "2024-01-01T10:00:00"
    assert cards[0].last_captured_at == "2024-01-01T10:00:00"


def test_card_count_and_dates_come_from_the_actual_photos() -> None:
    from fotos_plus.viewer import photo_cards

    a = photo("a.jpg", "2024-01-01T10:00:00")
    b = photo("b.jpg", "2024-06-01T10:00:00")
    sin_fecha = photo("c.jpg", None)

    cards = photo_cards(
        [a, b, sin_fecha],
        photo_tags=["Favoritas"],
        photo_tagged={
            "a.jpg": ["Favoritas"],
            "b.jpg": ["Favoritas"],
            "c.jpg": ["Favoritas"],
        },
    )

    assert cards[0].photo_count == 3
    assert len(cards[0].photos) == 3
    assert cards[0].first_captured_at == "2024-01-01T10:00:00"
    assert cards[0].last_captured_at == "2024-06-01T10:00:00"


def test_a_bucket_with_no_resolvable_photo_gets_no_card() -> None:
    from fotos_plus.viewer import photo_cards

    a = photo("a.jpg", "2024-01-01T10:00:00")

    cards = photo_cards(
        [a],
        photo_tags=["Favoritas", "Para imprimir"],
        photo_tagged={"a.jpg": ["Favoritas"], "zz.jpg": ["Para imprimir"]},
    )

    assert [card.title for card in cards] == ["Favoritas"]


def test_a_bucket_name_with_spaces_gets_a_reserved_browse_key() -> None:
    from fotos_plus.viewer import bucket_collection_key, photo_cards

    a = photo("a.jpg", "2024-01-01T10:00:00")

    cards = photo_cards(
        [a],
        photo_tags=["Para imprimir"],
        photo_tagged={"a.jpg": ["Para imprimir"]},
    )

    assert cards[0].browse_key == bucket_collection_key("Para imprimir")
    assert cards[0].browse_key == "cubo:Para imprimir"


def test_a_photo_set_renders_as_a_card_not_a_flat_photo(tmp_path: Path) -> None:
    document = _sections_html(
        tmp_path, photo_tags=["Favoritas"], photo_tagged={"a.jpg": ["Favoritas"]}
    )

    assert '<section class="photo-section">' in document
    seccion = document.split('<section class="photo-section">', 1)[1].split(
        "</section>", 1
    )[0]
    assert '<article class="card photo-card">' in seccion
    assert "card flat" not in seccion

    card = _photo_card(document, "Favoritas")
    assert '<p class="meta">1 foto' in card
    assert "data-key" not in card
    assert "data-tag" not in card
    assert 'class="label-form"' not in card
    assert 'class="tag-controls"' not in card


def test_the_photo_card_reuses_embedded_thumbnails(tmp_path: Path) -> None:
    document = _sections_html(
        tmp_path, photo_tags=["Favoritas"], photo_tagged={"a.jpg": ["Favoritas"]}
    )

    seccion = document.split('<section class="photo-section">', 1)[1].split(
        "</section>", 1
    )[0]
    assert "base64," in seccion
    assert "/render" not in seccion
    assert "/thumb" not in seccion


def test_a_photo_card_reports_its_count_and_date_range(tmp_path: Path) -> None:
    document = _sections_html(
        tmp_path,
        photo_tags=["Favoritas"],
        photo_tagged={"a.jpg": ["Favoritas"], "b.jpg": ["Favoritas"]},
    )

    card = _photo_card(document, "Favoritas")
    assert '<p class="meta">2 fotos · 2024-01-01 – 2024-06-01</p>' in card


def test_a_photo_card_with_no_known_date_omits_the_date_range(tmp_path: Path) -> None:
    from fotos_plus.viewer import render_html

    root = tmp_path / "fotos"
    _write_photos(root, ["a.jpg"])
    groups = assign_groups(
        [photo("a.jpg", None)],
        suggestions(trips=[trip("2024-01-01T00:00:00", "2024-01-02T00:00:00")]),
    )
    document = render_html(
        groups,
        str(root),
        token="t0ken",
        photo_tags=["Favoritas"],
        photo_tagged={"a.jpg": ["Favoritas"]},
    )

    card = _photo_card(document, "Favoritas")
    assert '<p class="meta">1 foto</p>' in card


def test_a_photo_card_shows_five_thumbnails(monkeypatch) -> None:
    from fotos_plus import viewer

    monkeypatch.setattr(viewer, "_thumbnail_b64", lambda photo, root: "mini")
    fotos = [
        photo(f"f{i}.jpg", f"2024-01-01T{i // 60:02d}:{i % 60:02d}:00")
        for i in range(12)
    ]
    cards = viewer.photo_cards(
        fotos,
        photo_tags=["Favoritas"],
        photo_tagged={foto.sha256: ["Favoritas"] for foto in fotos},
    )

    html = viewer._group_card(cards[0], Path("C:/fotos"), {}, token="t0ken")

    assert html.count('class="thumb"') == 5
    assert "12 fotos" in html


def test_a_small_photo_card_shows_all_its_thumbnails(monkeypatch) -> None:
    from fotos_plus import viewer

    monkeypatch.setattr(viewer, "_thumbnail_b64", lambda photo, root: "mini")
    fotos = [photo("a.jpg", "2024-01-01T10:00:00"), photo("b.jpg", "2024-06-01T10:00:00")]
    cards = viewer.photo_cards(
        fotos,
        photo_tags=["Favoritas"],
        photo_tagged={foto.sha256: ["Favoritas"] for foto in fotos},
    )

    html = viewer._group_card(cards[0], Path("C:/fotos"), {}, token="t0ken")

    assert html.count('class="thumb"') == 2


def test_a_served_photo_card_offers_its_reserved_browse_key(tmp_path: Path) -> None:
    document = _sections_html(
        tmp_path,
        marked=["a.jpg"],
        photo_tags=["Favoritas"],
        photo_tagged={"b.jpg": ["Favoritas"]},
    )

    marcadas = _photo_card(document, "Marcadas")
    favoritas = _photo_card(document, "Favoritas")
    assert 'data-browse-key="marcadas"' in marcadas
    assert 'data-browse-key="cubo:Favoritas"' in favoritas
    assert "Ver fotos" in marcadas
    assert "Ver fotos" in favoritas


def test_the_page_goes_groups_then_marked_then_buckets(tmp_path: Path) -> None:
    document = _sections_html(
        tmp_path,
        marked=["a.jpg"],
        photo_tags=["Favoritas"],
        photo_tagged={"b.jpg": ["Favoritas"]},
    )

    # Este documento no trae tags, asi que las tarjetas de grupo van en la grilla simple.
    grid = document.index('<div class="grid">')
    fotos = document.index('<section class="photo-section">')
    assert grid < fotos
    # Y entre las tarjetas de fotos: marcadas, despues cubos. Sin cubo no existe.
    marcadas = document.index("<h2>Marcadas</h2>")
    favoritas = document.index("<h2>Favoritas</h2>")
    assert marcadas < favoritas
    assert "<h2>Sin cubo</h2>" not in document


def test_a_library_with_nothing_to_regroup_keeps_the_single_flat_grid(
    tmp_path: Path,
) -> None:
    document = _sections_html(tmp_path)

    assert '<section class="photo-section">' not in document
    assert '<section class="tag-section"' not in document
    assert document.count('<article class="card"') == 2
    assert "Marcadas" not in document
    assert "Sin cubo" not in document


# --- 6.8 los cubos no tocan las tarjetas de grupo ------------------------------


def _group_cards(document: str) -> list[str]:
    """Las tarjetas de grupo, sin las tarjetas de fotos ni la grilla plana."""
    return re.findall(r'<article class="card"(?![^>]*\bflat\b).*?</article>', document, re.S)


def test_buckets_leave_a_group_card_alone(tmp_path: Path) -> None:
    sin_cubos = _sections_html(tmp_path)
    con_cubos = _sections_html(
        tmp_path,
        photo_tags=["Favoritas"],
        photo_tagged={"a.jpg": ["Favoritas"], "b.jpg": ["Favoritas"]},
    )

    assert _group_cards(con_cubos) == _group_cards(sin_cubos)
    assert _group_cards(con_cubos) != []


def test_a_mark_leaves_the_group_card_alone(tmp_path: Path) -> None:
    sin_marcas = _sections_html(tmp_path)
    con_marcas = _sections_html(tmp_path, marked=["a.jpg"])

    assert _group_cards(con_marcas) == _group_cards(sin_marcas)


def test_a_bucketed_photo_disappears_from_the_card_when_unbucketed(
    tmp_path: Path,
) -> None:
    root = tmp_path / "fotos"
    _write_photos(root, ["a.jpg", "b.jpg"])
    from fotos_plus.viewer import render_html

    def documento(photo_tagged):
        groups = assign_groups(
            [photo("a.jpg", "2024-01-01T10:00:00"), photo("b.jpg", "2024-06-01T10:00:00")],
            suggestions(trips=[trip("2024-01-01T00:00:00", "2024-01-02T00:00:00")]),
        )
        return render_html(
            groups,
            str(root),
            token="t0ken",
            photo_tags=["Favoritas"],
            photo_tagged=photo_tagged,
        )

    bucketed = documento({"a.jpg": ["Favoritas"]})
    unbucketed = documento({"b.jpg": ["Favoritas"]})

    # a estaba en Favoritas y sale de esa tarjeta; b entra en su lugar.
    favoritas_bucketed = _photo_card(bucketed, "Favoritas")
    favoritas_unbucketed = _photo_card(unbucketed, "Favoritas")
    assert 'alt="a.jpg"' in favoritas_bucketed
    assert 'alt="b.jpg"' not in favoritas_bucketed
    assert 'alt="b.jpg"' in favoritas_unbucketed
    assert 'alt="a.jpg"' not in favoritas_unbucketed
    assert "Sin cubo" not in unbucketed


# --- 6.9 las tarjetas de fotos no son destino de arrastre ---------------------


def test_a_photo_card_is_not_a_drop_target(tmp_path: Path) -> None:
    document = _sections_html(
        tmp_path, photo_tags=["Favoritas"], photo_tagged={"a.jpg": ["Favoritas"]}
    )

    seccion = document.split('<section class="photo-section">', 1)[1].split(
        "</section>", 1
    )[0]
    # Sin `data-drop` no hay zona de destino: soltar ahi no tiene a quien leer un tag.
    assert "data-drop" not in seccion
    assert "data-key" not in _photo_card(document, "Favoritas")


def test_the_drop_script_ignores_photo_cards(tmp_path: Path) -> None:
    document = _sections_html(
        tmp_path, photo_tags=["Favoritas"], photo_tagged={"a.jpg": ["Favoritas"]}
    )

    # El arrastre se engancha a las tarjetas de grupo (las que tienen `data-key`), y a
    # `.photo-section` solo para rechazar el gesto.
    assert 'querySelectorAll(".card[data-key]")' in document
    assert 'querySelectorAll(".card")' not in document
    assert 'querySelectorAll(".photo-section")' in document
    # El rechazo avisa el motivo y no guarda nada: no llama a `soltar` ni a `postTag`.
    rechazo = document.split('querySelectorAll(".photo-section")', 1)[1].split("});", 1)[0]
    assert 'dropEffect = "none"' in rechazo
    assert "postTag" not in rechazo
    assert "soltar(" not in rechazo


def test_a_photo_card_is_not_draggable(tmp_path: Path) -> None:
    document = _sections_html(
        tmp_path, photo_tags=["Favoritas"], photo_tagged={"a.jpg": ["Favoritas"]}
    )

    card = _photo_card(document, "Favoritas")
    assert "<article class=\"card photo-card\">" in card
    assert "draggable" not in card
    assert "data-key" not in card


def test_a_group_section_is_still_a_drop_target(tmp_path: Path) -> None:
    from fotos_plus.viewer import render_html

    root = tmp_path / "fotos"
    _write_photos(root, ["a.jpg", "b.jpg"])
    groups = assign_groups(
        [photo("a.jpg", "2024-01-01T10:00:00"), photo("b.jpg", "2024-06-01T10:00:00")],
        suggestions(
            trips=[
                trip("2024-01-01T00:00:00", "2024-01-02T00:00:00"),
                trip("2024-06-01T00:00:00", "2024-06-02T00:00:00"),
            ]
        ),
        tags={"2024-01-01T00:00:00": "Viaje", "2024-06-01T00:00:00": "Familia"},
    )

    document = render_html(groups, str(root), token="t0ken")

    # Los tags siguen armando secciones con `data-drop`: el arrastre no se toca.
    assert document.count('<section class="tag-section" data-drop=') == 2


def test_the_refusal_message_says_photo_sets_are_not_a_destination(
    tmp_path: Path,
) -> None:
    document = _sections_html(
        tmp_path, photo_tags=["Favoritas"], photo_tagged={"a.jpg": ["Favoritas"]}
    )

    rechazo = document.split('querySelectorAll(".photo-section")', 1)[1]
    assert "Las marcas y los cubos nombran fotos, no viajes" in rechazo


# --- 7 el export estatico ------------------------------------------------------


A_SHA = "a" * 64
B_SHA = "b" * 64
GONE_SHA = "f" * 64


def _export_with(tmp_path: Path, **edicion) -> str:
    """Genera el HTML exportado con un archivo de edicion dado.

    Las fotos llevan hash de verdad porque el archivo de edicion los valida al
    escribirse: un nombre de archivo no serviria como hash.
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
    a = photo("a.jpg", "2024-01-01T10:00:00")
    b = photo("b.jpg", "2024-07-01T10:00:00")
    a.sha256 = A_SHA
    b.sha256 = B_SHA
    photos = [a, b]
    index_path = tmp_path / "indice.json"
    write_index(
        ScanResult(root=str(root), scanned_at="2026-01-01T00:00:00", photos=photos),
        index_path,
    )
    write_suggestions(
        suggestions(
            trips=[trip("2024-01-01T00:00:00", "2024-01-02T00:00:00")],
            periods=[period("2024-07-01T00:00:00", "2024-07-02T00:00:00")],
        ),
        suggestions_path_next_to(index_path),
    )
    write_edicion(
        LabelOverlay(based_on_scanned_at="2026-01-01T00:00:00", **edicion),
        edicion_path_next_to(index_path),
    )
    document, _ = build_view(index_path)
    return document


def test_the_export_shows_the_marked_and_bucket_cards(tmp_path: Path) -> None:
    document = _export_with(
        tmp_path,
        marked=[A_SHA],
        photo_tags=["Favoritas"],
        photo_tagged={A_SHA: ["Favoritas"]},
    )

    assert "<h2>Marcadas</h2>" in document
    assert "<h2>Favoritas</h2>" in document
    assert 'class="card photo-card"' in document
    # La foto sin cubo no sale en ninguna tarjeta de fotos.
    assert "<h2>Sin cubo</h2>" not in document


def test_the_export_shows_the_bucket_card_next_to_the_marked_one(
    tmp_path: Path,
) -> None:
    document = _export_with(
        tmp_path,
        marked=[A_SHA],
        photo_tags=["Favoritas"],
        photo_tagged={A_SHA: ["Favoritas"]},
    )

    assert document.index("<h2>Marcadas</h2>") < document.index("<h2>Favoritas</h2>")
    assert "<h2>Sin cubo</h2>" not in document


def test_the_export_shows_no_untagged_card_when_no_buckets_at_all(
    tmp_path: Path,
) -> None:
    document = _export_with(tmp_path, marked=[A_SHA])

    assert "<h2>Marcadas</h2>" in document
    # No untagged card when there are no buckets at all
    assert "<h2>Sin cubo</h2>" not in document


def test_the_export_has_no_picker_and_no_bucket_controls(tmp_path: Path) -> None:
    document = _export_with(
        tmp_path, photo_tags=["Favoritas"], photo_tagged={A_SHA: ["Favoritas"]}
    )

    assert 'id="photo-browser-buckets"' not in document
    assert "bucket-catalog" not in document
    assert "bucket-toggle" not in document
    assert "bucket-input" not in document
    assert 'class="bucket-add"' not in document


def test_the_export_has_no_drop_target_on_its_photo_cards(tmp_path: Path) -> None:
    document = _export_with(
        tmp_path, photo_tags=["Favoritas"], photo_tagged={A_SHA: ["Favoritas"]}
    )

    seccion = document.split('<section class="photo-section">', 1)[1].split(
        "</section>", 1
    )[0]
    assert "data-drop" not in seccion
    assert "data-key" not in _photo_card(document, "Favoritas")
    # Sin arrastre tampoco esta el script: el documento no ofrece ningun control.
    assert "<script>" not in document


def test_the_export_photo_card_has_no_browse_control(tmp_path: Path) -> None:
    document = _export_with(
        tmp_path, marked=[A_SHA], photo_tags=["Favoritas"], photo_tagged={A_SHA: ["Favoritas"]}
    )

    assert 'class="browse-open"' not in document
    assert "data-browse-key" not in document


def test_the_export_payload_withholds_the_bucket_inventory(tmp_path: Path) -> None:
    document = _export_with(
        tmp_path,
        marked=[A_SHA],
        photo_tags=["Favoritas"],
        photo_tagged={A_SHA: ["Favoritas"]},
    )

    payload = json.loads(re.search(r'id="viewer-data">(.*?)</script>', document, re.S).group(1))
    # Igual que las marcas, los cubos no viajan en el export: se muestran y no se
    # embeben.
    assert "photo_tags" not in payload
    assert "photo_tagged" not in payload
    assert "marked_count" not in payload["groups"][0]
    assert "browse_key" not in payload["groups"][0]


def test_a_bucket_whose_photo_is_gone_is_absent_but_its_name_survives(
    tmp_path: Path,
) -> None:
    # GONE_SHA no esta en el indice: se escaneo antes y se borro despues.
    document = _export_with(
        tmp_path,
        photo_tags=["Favoritas", "Para imprimir"],
        photo_tagged={A_SHA: ["Favoritas"], GONE_SHA: ["Para imprimir"]},
    )

    # El nombre sigue en el archivo, asi que el selector lo ofrece, pero la foto no se
    # muestra en ninguna tarjeta y su cubo queda vacio: sin tarjeta que le poner.
    assert "<h2>Para imprimir</h2>" not in document
    card = _photo_card(document, "Favoritas")
    assert 'alt="a.jpg"' in card
    assert card.count('class="thumb"') == 1
    # Y la de Favoritas sale con la foto que si existe.
    assert "<h2>Favoritas</h2>" in document


def test_the_served_page_also_leaves_out_a_bucket_whose_photo_is_gone(
    tmp_path: Path,
) -> None:
    document = _sections_html(
        tmp_path,
        photo_tags=["Favoritas"],
        photo_tagged={"a.jpg": ["Favoritas"], "zz.jpg": ["Favoritas"]},
    )

    # La foto que no existe no se muestra; la que si, sigue en su tarjeta, y la tarjeta
    # cuenta solo esa.
    card = _photo_card(document, "Favoritas")
    assert card.count('class="thumb"') == 1
    assert '<p class="meta">1 foto' in card


def test_the_served_page_keeps_the_name_of_a_bucket_with_no_resolvable_photo(
    tmp_path: Path,
) -> None:
    document = _sections_html(
        tmp_path,
        photo_tags=["Para imprimir"],
        photo_tagged={"zz.jpg": ["Para imprimir"]},
    )

    # El nombre sobrevive en el payload para poder volver a elegirlo, aunque hoy no
    # tenga ninguna foto que mostrar.
    payload = json.loads(re.search(r'id="viewer-data">(.*?)</script>', document, re.S).group(1))
    assert payload["photo_tags"] == ["Para imprimir"]



def test_the_photo_browser_can_scroll_to_the_bucket_controls() -> None:
    """Los controles de cubo tienen que poder alcanzarse, no quedar fuera de pantalla.

    El overlay es `position: fixed` con la imagen a 78vh: sin `overflow` los controles de
    cubo quedaban debajo del viewport y no habia forma de llegar a ellos.
    """
    from fotos_plus.viewer import CSS

    assert re.search(r"\.browser\s*\{[^}]*overflow-y:\s*auto", CSS)
    # Y la imagen tiene que dejarles lugar: a 78vh no sobra espacio para nada mas.
    assert "max-height: 78vh" not in CSS


# --- videos phase 1: posters, tiles, stills ------------------------------------


def video_item(name: str, captured_at: str | None, duration_s: float | None = 12.5):
    item = photo(name, captured_at)
    item.extension = ".mp4"
    item.kind = "video"
    item.duration_s = duration_s
    return item


def _video_group_html(tmp_path: Path, token: str | None = "t0ken", **kwargs) -> str:
    from tests.test_video import make_video

    root = tmp_path / "fotos"
    _write_photos(root, ["a.jpg"])
    make_video(root / "clip.mp4", captured_at="2024-01-01T10:00:00")
    groups = assign_groups(
        [
            photo("a.jpg", "2024-01-01T10:00:00"),
            video_item("clip.mp4", "2024-01-01T10:00:00"),
        ],
        suggestions(
            trips=[trip("2024-01-01T00:00:00", "2024-01-02T00:00:00")],
        ),
    )
    from fotos_plus.viewer import render_html

    return render_html(groups, str(root), token=token, **kwargs)


def test_a_video_card_shows_its_poster_with_duration(tmp_path: Path, monkeypatch) -> None:
    import fotos_plus.viewer

    monkeypatch.setattr(fotos_plus.viewer, "make_poster", lambda path: b"\xff\xd8poster")

    document = _video_group_html(tmp_path)

    assert "video-thumb" in document
    assert "0:12" in document


def test_a_video_without_decoder_gets_a_duration_tile(tmp_path: Path, monkeypatch) -> None:
    import fotos_plus.viewer
    from fotos_plus.photos import PhotoError

    def boom(path):
        raise PhotoError("no video decoder available")

    monkeypatch.setattr(fotos_plus.viewer, "make_poster", boom)

    document = _video_group_html(tmp_path)

    assert "video-tile" in document
    assert "Video 0:12" in document
    # The tile is not a photo thumbnail: only the real photo renders a thumb img.
    assert document.count('<img class="thumb"') == 1


def test_a_video_card_is_distinguishable_from_a_photo_card(tmp_path: Path, monkeypatch) -> None:
    import fotos_plus.viewer

    monkeypatch.setattr(fotos_plus.viewer, "make_poster", lambda path: b"\xff\xd8poster")

    document = _video_group_html(tmp_path)

    assert 'class="thumb"' in document
    assert 'class="video-thumb"' in document


def test_the_browser_plays_videos_with_native_controls(tmp_path: Path) -> None:
    from fotos_plus.viewer import EDIT_SCRIPT

    root = tmp_path / "fotos"
    _write_photos(root, ["a.jpg"])

    document = _browser_html(root, ["a.jpg"])

    assert 'id="photo-browser-video"' in document
    assert "<video" in document
    assert "controls" in document
    assert 'foto.kind === "video"' in EDIT_SCRIPT
    assert "/video" in EDIT_SCRIPT
    assert "video.poster" in EDIT_SCRIPT
    assert "duration_s" in EDIT_SCRIPT
    assert "soltarVideo" in EDIT_SCRIPT
    assert "video.pause()" in EDIT_SCRIPT
    # The video branch attempts playback after the source, and the handler swallows
    # every rejection: a refusal leaves the poster still, an interrupted attempt is
    # already handled by navigation.
    assert re.search(
        r'video\.src = "/video" \+ medio;.*?video\.play\(\)\.catch\(function \(\) \{\}\);',
        EDIT_SCRIPT,
        re.DOTALL,
    )
    assert "Videos show a still without playback" not in EDIT_SCRIPT


def test_arriving_at_a_video_plays_it_and_leaving_still_stops_it_first(
    tmp_path: Path,
) -> None:
    from fotos_plus.viewer import EDIT_SCRIPT

    root = tmp_path / "fotos"
    _write_photos(root, ["a.jpg", "b.jpg"])

    document = _browser_html(root, ["a.jpg", "b.jpg"])

    mostrar = re.search(
        r"function mostrar\(indiceNuevo\) \{(.*?)\n    \}", document, re.DOTALL
    )
    assert mostrar is not None
    cuerpo = mostrar.group(1)
    assert cuerpo.index("soltarVideo();") < cuerpo.index('video.src = "/video" + medio;')
    assert cuerpo.index('video.src = "/video" + medio;') < cuerpo.index("video.play()")

    soltar = re.search(r"function soltarVideo\(\) \{(.*?)\n    \}", document, re.DOTALL)
    assert soltar is not None
    cuerpo_soltar = soltar.group(1)
    assert cuerpo_soltar.index("video.pause();") < cuerpo_soltar.index(
        'video.removeAttribute("src");'
    )
    assert cuerpo_soltar.index("video.pause();") < cuerpo_soltar.index(
        'video.removeAttribute("poster");'
    )
    assert "video.play()" in EDIT_SCRIPT


def test_the_export_embeds_video_posters_and_no_blobs(tmp_path: Path, monkeypatch) -> None:
    import fotos_plus.viewer

    monkeypatch.setattr(fotos_plus.viewer, "make_poster", lambda path: b"\xff\xd8poster")

    document = _video_group_html(tmp_path, token=None)

    assert "video-thumb" in document
    assert "<video" not in document


# --- 6. la carpeta de fotos y las miniaturas que no se pueden preparar ----------


def test_resolve_library_root_prefers_the_index_folder(tmp_path: Path) -> None:
    from fotos_plus.viewer import resolve_library_root

    index_folder = tmp_path / "indice"
    suggestions_folder = tmp_path / "sugerencias"
    index_folder.mkdir()
    suggestions_folder.mkdir()

    assert (
        resolve_library_root(str(index_folder), str(suggestions_folder)) == index_folder
    )


def test_resolve_library_root_falls_back_to_the_suggestions_folder(tmp_path: Path) -> None:
    from fotos_plus.viewer import resolve_library_root

    missing = tmp_path / "desconectada"
    suggestions_folder = tmp_path / "sugerencias"
    suggestions_folder.mkdir()

    assert resolve_library_root(str(missing), str(suggestions_folder)) == suggestions_folder


def test_resolve_library_root_reports_when_no_folder_exists(tmp_path: Path) -> None:
    from fotos_plus.viewer import LibraryRootError, resolve_library_root

    with pytest.raises(LibraryRootError):
        resolve_library_root(str(tmp_path / "a"), str(tmp_path / "b"))


def test_build_view_falls_back_to_the_suggestions_folder(tmp_path: Path) -> None:
    from fotos_plus.index import suggestions_path_next_to, write_index, write_suggestions
    from fotos_plus.models import ScanResult, SuggestionsResult
    from fotos_plus.viewer import build_view

    root = tmp_path / "fotos"
    _write_photos(root, ["a.jpg"])
    index_path = tmp_path / "indice.json"
    write_index(
        ScanResult(
            root=str(tmp_path / "desconectada"),
            scanned_at="2026-01-01T00:00:00",
            photos=[photo("a.jpg", "2024-01-01T00:00:00")],
        ),
        index_path,
    )
    write_suggestions(
        SuggestionsResult(
            root=str(root),
            scanned_at="2026-01-01T00:00:00",
            trips=[trip("2024-01-01T00:00:00", "2024-01-02T00:00:00")],
        ),
        suggestions_path_next_to(index_path),
    )

    document, flat = build_view(index_path)

    assert flat is False
    # La miniatura se pudo preparar con la carpeta que declaran las sugerencias.
    assert 'class="thumb"' in document


def test_build_view_reports_a_missing_library_folder(tmp_path: Path) -> None:
    from fotos_plus.index import suggestions_path_next_to, write_index, write_suggestions
    from fotos_plus.models import ScanResult, SuggestionsResult
    from fotos_plus.viewer import LibraryRootError, build_view

    index_path = tmp_path / "indice.json"
    write_index(
        ScanResult(root=str(tmp_path / "a"), scanned_at="2026-01-01T00:00:00", photos=[]),
        index_path,
    )
    write_suggestions(
        SuggestionsResult(root=str(tmp_path / "b"), scanned_at="2026-01-01T00:00:00"),
        suggestions_path_next_to(index_path),
    )

    with pytest.raises(LibraryRootError):
        build_view(index_path)


def test_a_marked_card_without_previews_does_not_mention_another_group(
    tmp_path: Path, monkeypatch
) -> None:
    from fotos_plus import viewer

    monkeypatch.setattr(viewer, "_thumbnail_b64", lambda foto, root: None)
    groups = assign_groups(
        [photo("a.jpg", "2024-01-01T10:00:00")],
        suggestions(trips=[trip("2024-01-01T00:00:00", "2024-01-02T00:00:00")]),
    )

    document = render_html(groups, str(tmp_path / "fotos"), token="t0ken", marked=["a.jpg"])

    card = _photo_card(document, "Marcadas")
    assert "1 foto" in card
    assert "No se pudieron preparar las miniaturas." in card
    assert "otro grupo" not in card


def test_a_bucket_card_without_previews_keeps_its_count(
    tmp_path: Path, monkeypatch
) -> None:
    from fotos_plus import viewer

    monkeypatch.setattr(viewer, "_thumbnail_b64", lambda foto, root: None)
    groups = assign_groups(
        [photo("a.jpg", "2024-01-01T10:00:00")],
        suggestions(trips=[trip("2024-01-01T00:00:00", "2024-01-02T00:00:00")]),
    )

    document = render_html(
        groups,
        str(tmp_path / "fotos"),
        token="t0ken",
        photo_tags=["Favoritas"],
        photo_tagged={"a.jpg": ["Favoritas"]},
    )

    card = _photo_card(document, "Favoritas")
    assert "1 foto" in card
    assert "No se pudieron preparar las miniaturas." in card
    assert "otro grupo" not in card


def test_a_group_card_without_previews_keeps_the_group_note(monkeypatch) -> None:
    """La nota de grupo sigue siendo la de grupo; el cambio solo toca las de fotos."""
    from fotos_plus import viewer
    from fotos_plus.viewer import Group

    monkeypatch.setattr(viewer, "_thumbnail_b64", lambda foto, root: None)
    group = Group(
        title="Periodo",
        kind="period",
        photo_count=0,
        first_captured_at="2024-01-01T00:00:00",
        last_captured_at="2024-01-02T00:00:00",
        photos=[],
        key="2024-01-01T00:00:00",
    )

    html = viewer._group_card(group, Path("C:/fotos"), {}, token="t0ken")

    assert "Sin fotos propias: caen en otro grupo." in html
    assert "No se pudieron preparar las miniaturas." not in html
