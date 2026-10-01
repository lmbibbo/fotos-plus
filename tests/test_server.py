from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from fotos_plus.index import (
    edicion_path_next_to,
    read_index,
    write_index,
    write_suggestions,
    suggestions_path_next_to,
)
from fotos_plus.labels import EDITION_VERSION, read_edicion
from fotos_plus.models import (
    LOCATION_KNOWN,
    LOCATION_UNKNOWN,
    STATUS_SUGGESTED,
    PeriodSuggestion,
    Photo,
    ScanResult,
    SuggestionsResult,
    TripLocation,
    TripSuggestion,
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


def build_index(tmp_path: Path, scanned_at: str = "2026-01-01T00:00:00") -> Path:
    """Indice minimo con un viaje y un periodo, con fotos reales en disco."""
    from tests.conftest import make_sized_image

    root = tmp_path / "fotos"
    make_sized_image(root / "a.jpg")
    make_sized_image(root / "b.jpg")

    photos = [
        Photo(
            relative_path="a.jpg",
            name="a.jpg",
            extension=".jpg",
            size_bytes=1,
            sha256="a",
            captured_at="2024-05-02T10:00:00",
            latitude=-41.13,
            longitude=-71.31,
        ),
        Photo(
            relative_path="b.jpg",
            name="b.jpg",
            extension=".jpg",
            size_bytes=1,
            sha256="b",
            captured_at="2024-08-02T10:00:00",
        ),
    ]
    index_path = tmp_path / "indice.json"
    write_index(ScanResult(root=str(root), scanned_at=scanned_at, photos=photos), index_path)
    write_suggestions(
        SuggestionsResult(
            root=str(root),
            scanned_at=scanned_at,
            trips=[trip("2024-05-01T00:00:00", "2024-05-05T00:00:00")],
            periods=[period("2024-08-01T00:00:00", "2024-08-05T00:00:00")],
        ),
        suggestions_path_next_to(index_path),
    )
    return index_path


@pytest.fixture
def serving(tmp_path: Path):
    """Arranca el servidor en un hilo y lo cierra al terminar el test."""
    from fotos_plus.server import start_edit_server

    started: list = []

    def factory(index_path: Path, port: int | None = None):
        server, actual, token = start_edit_server(index_path, port=port)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        started.append((server, thread))
        return f"http://127.0.0.1:{actual}", token

    yield factory

    for server, thread in started:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def get(url: str, token: str, host: str = "127.0.0.1"):
    request = urllib.request.Request(url, headers={"Host": host})
    request.add_header("X-Fotos-Plus-Token", token)
    try:
        with urllib.request.urlopen(request, timeout=10) as respuesta:
            return respuesta.status, respuesta.read().decode("utf-8"), dict(respuesta.headers)
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode("utf-8"), dict(error.headers)


def post(url: str, token: str, body: dict, headers: dict | None = None):
    headers = dict(headers or {})
    headers.setdefault("Content-Type", "application/json")
    headers.setdefault("X-Fotos-Plus-Token", token)
    data = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=10) as respuesta:
            return respuesta.status, json.loads(respuesta.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read().decode("utf-8"))


# --- 4.1 arranque y export estatico --------------------------------------------


def test_server_only_listens_on_loopback(tmp_path: Path, serving) -> None:
    index_path = build_index(tmp_path)
    url, token = serving(index_path)

    status, body, _ = get(url + "/", token)

    assert status == 200
    assert "Viajes y periodos sugeridos" in body


def test_the_static_html_is_written_before_serving(tmp_path: Path) -> None:
    """El modo servidor no reemplaza al export: el HTML sigue existiendo."""
    from fotos_plus.cli import main

    index_path = build_index(tmp_path)
    expected = index_path.with_suffix(".html")
    assert not expected.exists()

    # se genera el export con el camino normal, que es el que escribe el archivo
    code = main(["view", str(index_path)])

    assert code == 0
    assert expected.is_file()
    assert "solo-lectura" in expected.read_text(encoding="utf-8")


# --- 4.2 loopback y Host -------------------------------------------------------


def test_a_non_loopback_host_is_rejected(tmp_path: Path, serving) -> None:
    index_path = build_index(tmp_path)
    url, token = serving(index_path)

    status, body, _ = get(url + "/", token, host="192.168.1.50")

    assert status == 400
    assert "Host no permitido" in body


def test_localhost_host_is_accepted(tmp_path: Path, serving) -> None:
    index_path = build_index(tmp_path)
    url, token = serving(index_path)

    status, _, _ = get(url + "/", token, host="localhost")

    assert status == 200


# --- 4.3 token -----------------------------------------------------------------


def test_post_without_a_token_is_rejected(tmp_path: Path, serving) -> None:
    index_path = build_index(tmp_path)
    url, token = serving(index_path)

    status, body = post(
        url + "/api/labels",
        "",
        {"action": "set", "key": "2024-05-01T00:00:00", "text": "Bariloche", "token": ""},
    )

    assert status == 403
    assert "token invalido" in body["error"]


def test_post_with_a_wrong_token_is_rejected(tmp_path: Path, serving) -> None:
    index_path = build_index(tmp_path)
    url, token = serving(index_path)

    status, body = post(
        url + "/api/labels",
        token,
        {
            "action": "set",
            "key": "2024-05-01T00:00:00",
            "text": "Bariloche",
            "token": "otro-token",
        },
    )

    assert status == 403
    assert "token invalido" in body["error"]
    assert not edicion_path_next_to(index_path).exists()


# --- 4.4 Content-Type y CORS ---------------------------------------------------


def test_post_without_json_content_type_is_rejected(tmp_path: Path, serving) -> None:
    index_path = build_index(tmp_path)
    url, token = serving(index_path)

    status, body = post(
        url + "/api/labels",
        token,
        {"action": "set", "key": "2024-05-01T00:00:00", "text": "Bariloche", "token": token},
        headers={"Content-Type": "text/plain"},
    )

    assert status == 415
    assert "application/json" in body["error"]


def test_responses_carry_no_cross_origin_headers(tmp_path: Path, serving) -> None:
    index_path = build_index(tmp_path)
    url, token = serving(index_path)

    _, _, headers = get(url + "/", token)

    assert "Access-Control-Allow-Origin" not in headers
    assert "Access-Control-Allow-Methods" not in headers


# --- 4.5 validacion antes de escribir -----------------------------------------


def test_a_valid_label_is_persisted(tmp_path: Path, serving) -> None:
    index_path = build_index(tmp_path)
    url, token = serving(index_path)

    status, body = post(
        url + "/api/labels",
        token,
        {
            "action": "set",
            "key": "2024-05-01T00:00:00",
            "text": "Viaje a Bariloche",
            "token": token,
        },
    )

    assert status == 200
    assert body["ok"] is True
    overlay = read_edicion(edicion_path_next_to(index_path))
    assert overlay.labels == {"2024-05-01T00:00:00": "Viaje a Bariloche"}


def test_an_empty_label_is_rejected_and_nothing_is_written(tmp_path: Path, serving) -> None:
    index_path = build_index(tmp_path)
    url, token = serving(index_path)

    status, body = post(
        url + "/api/labels",
        token,
        {"action": "set", "key": "2024-05-01T00:00:00", "text": "   ", "token": token},
    )

    assert status == 400
    assert "no puede estar vacia" in body["error"]
    assert not edicion_path_next_to(index_path).exists()


def test_a_reference_that_does_not_resolve_is_rejected(tmp_path: Path, serving) -> None:
    index_path = build_index(tmp_path)
    url, token = serving(index_path)

    status, body = post(
        url + "/api/labels",
        token,
        {"action": "set", "key": "2030-01-01T00:00:00", "text": "Perdida", "token": token},
    )

    assert status == 400
    assert "no corresponde a ningun grupo actual" in body["error"]
    assert not edicion_path_next_to(index_path).exists()


def test_a_rejected_edit_leaves_a_previous_edition_untouched(tmp_path: Path, serving) -> None:
    from fotos_plus.labels import LabelOverlay, write_edicion

    index_path = build_index(tmp_path)
    edicion = edicion_path_next_to(index_path)
    write_edicion(
        LabelOverlay(
            based_on_scanned_at="2026-01-01T00:00:00",
            labels={"2024-05-01T00:00:00": "Bariloche"},
        ),
        edicion,
    )
    before = edicion.read_bytes()
    url, token = serving(index_path)

    status, _ = post(
        url + "/api/labels",
        token,
        {"action": "set", "key": "2024-05-01T00:00:00", "text": "", "token": token},
    )

    assert status == 400
    assert edicion.read_bytes() == before


def test_an_unknown_action_is_rejected(tmp_path: Path, serving) -> None:
    index_path = build_index(tmp_path)
    url, token = serving(index_path)

    status, body = post(
        url + "/api/labels",
        token,
        {"action": "borrar-todo", "key": "2024-05-01T00:00:00", "token": token},
    )

    assert status == 400
    assert "accion desconocida" in body["error"]


# --- 4.6 puerto ocupado --------------------------------------------------------


def test_an_occupied_port_is_reported(tmp_path: Path) -> None:
    import socket

    from fotos_plus.server import EditServerError, start_edit_server

    index_path = build_index(tmp_path)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as occupado:
        occupado.bind(("127.0.0.1", 0))
        occupado.listen(1)
        port = occupado.getsockname()[1]

        with pytest.raises(EditServerError) as caught:
            start_edit_server(index_path, port=port)

    assert "ya esta en uso" in str(caught.value)


# --- 4.7 cierre ordenado -------------------------------------------------------


def test_stopping_the_server_frees_the_port(tmp_path: Path) -> None:
    import socket

    from fotos_plus.server import start_edit_server

    index_path = build_index(tmp_path)
    server, port, _token = start_edit_server(index_path)

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)

    # el puerto vuelve a quedar disponible
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        probe.bind(("127.0.0.1", port))


# --- 5.1 la pagina servida trae los controles ----------------------------------


def test_the_served_page_shows_the_label_in_the_title(tmp_path: Path) -> None:
    from fotos_plus.index import read_suggestions, suggestions_path_next_to
    from fotos_plus.viewer import assign_groups, render_html

    index_path = build_index(tmp_path)
    labels = {"2024-05-01T00:00:00": "Viaje a Bariloche"}
    index = read_index(index_path)
    suggestions = read_suggestions(suggestions_path_next_to(index_path))
    groups = assign_groups(index.photos, suggestions, labels=labels)
    document = render_html(groups, index.root, labels=labels, token="abc")

    assert "Viaje a Bariloche" in document
    assert 'class="label-input"' in document
    assert 'data-mode="editable"' in document
    # el boton de quitar aparece solo si hay etiqueta
    assert 'class="label-remove"' in document


def test_a_group_without_a_label_has_no_remove_button(tmp_path: Path) -> None:
    from fotos_plus.index import read_suggestions, suggestions_path_next_to
    from fotos_plus.viewer import assign_groups, render_html

    index_path = build_index(tmp_path)
    index = read_index(index_path)
    suggestions = read_suggestions(suggestions_path_next_to(index_path))
    groups = assign_groups(index.photos, suggestions, labels={})
    document = render_html(groups, index.root, labels={}, token="abc")

    assert 'data-mode="editable"' in document
    assert 'class="label-remove"' not in document


def test_the_static_export_carries_no_editing_controls(tmp_path: Path) -> None:
    from fotos_plus.index import read_suggestions, suggestions_path_next_to
    from fotos_plus.viewer import assign_groups, render_html

    index_path = build_index(tmp_path)
    index = read_index(index_path)
    suggestions = read_suggestions(suggestions_path_next_to(index_path))
    groups = assign_groups(index.photos, suggestions, labels={})
    document = render_html(groups, index.root)

    assert 'data-mode="solo-lectura"' in document
    assert "solo lectura" in document
    assert "fetch(" not in document
    assert 'class="label-input"' not in document


# --- 5.2 flujo de guardado completo --------------------------------------------


def test_saving_a_label_through_the_server_shows_it_on_the_next_load(tmp_path: Path, serving) -> None:
    index_path = build_index(tmp_path)
    url, token = serving(index_path)

    status, body = post(
        url + "/api/labels",
        token,
        {
            "action": "set",
            "key": "2024-05-01T00:00:00",
            "text": "Viaje a Bariloche",
            "kind": "trip",
            "token": token,
        },
    )
    assert status == 200
    # el servidor responde el titulo que quedo, para actualizar la pagina sin recargar
    assert body["title"] == "Viaje a Bariloche"

    status, document, _ = get(url + "/", token)
    assert status == 200
    assert "Viaje a Bariloche" in document


# --- 5.3 quitar etiqueta es una accion separada --------------------------------


def test_removing_a_label_drops_the_entry(tmp_path: Path, serving) -> None:
    index_path = build_index(tmp_path)
    url, token = serving(index_path)

    post(
        url + "/api/labels",
        token,
        {"action": "set", "key": "2024-05-01T00:00:00", "text": "Bariloche", "token": token},
    )

    status, body = post(
        url + "/api/labels",
        token,
        {"action": "remove", "key": "2024-05-01T00:00:00", "token": token},
    )

    assert status == 200
    assert read_edicion(edicion_path_next_to(index_path)).labels == {}
    # el servidor devuelve el titulo derivado para que la tarjeta vuelva a su nombre
    assert body["title"] == "Argentina"


def test_removing_a_label_that_does_not_exist_is_rejected(tmp_path: Path, serving) -> None:
    index_path = build_index(tmp_path)
    url, token = serving(index_path)

    status, body = post(
        url + "/api/labels",
        token,
        {"action": "remove", "key": "2024-05-01T00:00:00", "token": token},
    )

    assert status == 400
    assert "no tiene etiqueta para quitar" in body["error"]


# --- 5.4 el cliente no envia una etiqueta vacia --------------------------------


def test_the_client_script_refuses_to_send_an_empty_label() -> None:
    from fotos_plus.viewer import EDIT_SCRIPT

    assert "if (!texto)" in EDIT_SCRIPT
    assert "Una etiqueta no puede estar vacia" in EDIT_SCRIPT


def test_the_static_export_has_no_client_script_at_all(tmp_path: Path) -> None:
    """El export no lleva el script de edicion: sin servidor no hay donde guardar."""
    from fotos_plus.index import read_suggestions, suggestions_path_next_to
    from fotos_plus.viewer import assign_groups, render_html

    index_path = build_index(tmp_path)
    index = read_index(index_path)
    suggestions = read_suggestions(suggestions_path_next_to(index_path))
    groups = assign_groups(index.photos, suggestions, labels={})
    document = render_html(groups, index.root)

    assert "fetch(" not in document
    # la hoja de estilos si menciona las clases, pero no hay ningun formulario
    assert "<form" not in document
    assert 'class="label-input"' not in document


def test_no_edition_file_is_created_by_exporting(tmp_path: Path) -> None:
    from fotos_plus.cli import main

    index_path = build_index(tmp_path)
    edicion = edicion_path_next_to(index_path)
    assert not edicion.exists()

    main(["view", str(index_path)])

    assert not edicion.exists()


def test_a_label_survives_a_rescan(tmp_path: Path) -> None:
    """Un rescaneo posterior no borra el archivo de edicion."""
    from fotos_plus.labels import LabelOverlay, write_edicion

    index_path = build_index(tmp_path)
    edicion = edicion_path_next_to(index_path)
    write_edicion(
        LabelOverlay(
            based_on_scanned_at="2026-01-01T00:00:00",
            labels={"2024-05-01T00:00:00": "Bariloche"},
        ),
        edicion,
    )

    # el escaneo reescribe sugerencias e indice, nunca el archivo de edicion
    write_index(read_index(index_path), index_path)
    write_suggestions(
        SuggestionsResult(
            root=str(tmp_path / "fotos"),
            scanned_at="2026-06-01T00:00:00",
            trips=[trip("2024-05-01T00:00:00", "2024-05-05T00:00:00")],
            periods=[period("2024-08-01T00:00:00", "2024-08-05T00:00:00")],
        ),
        suggestions_path_next_to(index_path),
    )

    assert read_edicion(edicion).labels == {"2024-05-01T00:00:00": "Bariloche"}


def test_drift_is_reported_when_the_scan_moved_on(tmp_path: Path, serving) -> None:
    from fotos_plus.labels import LabelOverlay, write_edicion

    index_path = build_index(tmp_path, scanned_at="2026-06-01T00:00:00")
    write_edicion(
        LabelOverlay(
            based_on_scanned_at="2026-01-01T00:00:00",
            labels={"2024-05-01T00:00:00": "Bariloche"},
        ),
        edicion_path_next_to(index_path),
    )
    url, token = serving(index_path)

    _, document, _ = get(url + "/", token)

    assert "El escaneo se rehizo" in document


# --- Tags por el servidor --------------------------------------------------------


def test_a_valid_tag_is_persisted_and_added_to_the_catalog(tmp_path: Path, serving) -> None:
    index_path = build_index(tmp_path)
    url, token = serving(index_path)

    status, body = post(
        url + "/api/labels",
        token,
        {
            "action": "set_tag",
            "key": "2024-05-01T00:00:00",
            "tag": "Familia",
            "token": token,
        },
    )

    assert status == 200
    assert body["ok"] is True
    overlay = read_edicion(edicion_path_next_to(index_path))
    assert overlay.tags == ["Familia"]
    assert overlay.tagged == {"2024-05-01T00:00:00": "Familia"}


def test_an_empty_tag_is_rejected_and_nothing_is_written(tmp_path: Path, serving) -> None:
    index_path = build_index(tmp_path)
    url, token = serving(index_path)

    status, body = post(
        url + "/api/labels",
        token,
        {
            "action": "set_tag",
            "key": "2024-05-01T00:00:00",
            "tag": "   ",
            "token": token,
        },
    )

    assert status == 400
    assert "no puede estar vacio" in body["error"]
    assert not edicion_path_next_to(index_path).exists()


def test_a_tag_on_a_reference_that_does_not_resolve_is_rejected(
    tmp_path: Path, serving
) -> None:
    index_path = build_index(tmp_path)
    url, token = serving(index_path)

    status, body = post(
        url + "/api/labels",
        token,
        {
            "action": "set_tag",
            "key": "2030-01-01T00:00:00",
            "tag": "Familia",
            "token": token,
        },
    )

    assert status == 400
    assert "no corresponde a ningun grupo actual" in body["error"]
    assert not edicion_path_next_to(index_path).exists()


def test_a_tag_post_without_a_token_is_rejected(tmp_path: Path, serving) -> None:
    index_path = build_index(tmp_path)
    url, _ = serving(index_path)

    status, body = post(
        url + "/api/labels",
        "token-inventado",
        {
            "action": "set_tag",
            "key": "2024-05-01T00:00:00",
            "tag": "Familia",
            "token": "token-inventado",
        },
    )

    assert status == 403
    assert "token invalido" in body["error"]
    assert not edicion_path_next_to(index_path).exists()


def test_clearing_a_tag_removes_the_assignment_but_keeps_the_catalog(
    tmp_path: Path, serving
) -> None:
    from fotos_plus.labels import LabelOverlay, write_edicion

    index_path = build_index(tmp_path)
    write_edicion(
        LabelOverlay(
            tags=["Familia"],
            tagged={"2024-05-01T00:00:00": "Familia"},
        ),
        edicion_path_next_to(index_path),
    )
    url, token = serving(index_path)

    status, _ = post(
        url + "/api/labels",
        token,
        {"action": "clear_tag", "key": "2024-05-01T00:00:00", "token": token},
    )

    assert status == 200
    overlay = read_edicion(edicion_path_next_to(index_path))
    assert overlay.tagged == {}
    assert overlay.tags == ["Familia"]


def test_clearing_a_tag_that_is_not_there_is_rejected(tmp_path: Path, serving) -> None:
    index_path = build_index(tmp_path)
    url, token = serving(index_path)

    status, body = post(
        url + "/api/labels",
        token,
        {"action": "clear_tag", "key": "2024-05-01T00:00:00", "token": token},
    )

    assert status == 400
    assert "no tiene tag para quitar" in body["error"]


def test_saving_a_label_through_the_server_keeps_the_tags(tmp_path: Path, serving) -> None:
    index_path = build_index(tmp_path)
    url, token = serving(index_path)
    post(
        url + "/api/labels",
        token,
        {
            "action": "set_tag",
            "key": "2024-05-01T00:00:00",
            "tag": "Familia",
            "token": token,
        },
    )

    status, _ = post(
        url + "/api/labels",
        token,
        {
            "action": "set",
            "key": "2024-05-01T00:00:00",
            "text": "Navidad",
            "token": token,
        },
    )

    assert status == 200
    overlay = read_edicion(edicion_path_next_to(index_path))
    assert overlay.labels == {"2024-05-01T00:00:00": "Navidad"}
    assert overlay.tagged == {"2024-05-01T00:00:00": "Familia"}


def test_the_served_page_carries_the_tags_and_the_catalog(tmp_path: Path, serving) -> None:
    index_path = build_index(tmp_path)
    url, token = serving(index_path)
    post(
        url + "/api/labels",
        token,
        {
            "action": "set_tag",
            "key": "2024-05-01T00:00:00",
            "tag": "Familia",
            "token": token,
        },
    )

    _, document, _ = get(url + "/", token)

    assert 'data-tag="Familia"' in document
    assert '<section class="tag-section"' in document
    assert '<option value="Familia">' in document