from __future__ import annotations

import json
import re
import threading
import urllib.error
import urllib.parse
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
from fotos_plus.viewer import UNCLASSIFIED_GROUP_KEY


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


def build_index(
    tmp_path: Path,
    scanned_at: str = "2026-01-01T00:00:00",
    shas: tuple[str, str] = ("a", "b"),
    captured_at: tuple[str | None, str | None] = (
        "2024-05-02T10:00:00",
        "2024-08-02T10:00:00",
    ),
) -> Path:
    """Indice minimo con un viaje y un periodo, con fotos reales en disco.

    Los hashes por defecto son cortos porque solo alcanzan para nombrar renders. Los
    tests que necesitan escribir marcas pasan hashes de verdad, que es lo que el formato exige.
    Las fechas por defecto dejan cada foto en su grupo. Un `None` las saca de cualquier
    intervalo y las manda al grupo sin clasificar.
    """
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
                sha256=shas[0],
                captured_at=captured_at[0],
                latitude=-41.13,
                longitude=-71.31,
            ),
            Photo(
                relative_path="b.jpg",
                name="b.jpg",
                extension=".jpg",
                size_bytes=1,
                sha256=shas[1],
                captured_at=captured_at[1],
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

# --- 3. render de pantalla de una foto ----------------------------------------


def fetch_render(url: str, token: str, reference: str, headers: dict | None = None):
    quoted = urllib.parse.quote(reference, safe="")
    all_headers = {"X-Fotos-Plus-Token": token}
    all_headers.update(headers or {})
    request = urllib.request.Request(f"{url}/render?ref={quoted}", headers=all_headers)
    try:
        with urllib.request.urlopen(request, timeout=10) as respuesta:
            return respuesta.status, respuesta.read(), dict(respuesta.headers)
    except urllib.error.HTTPError as error:
        return error.code, error.read(), dict(error.headers)


def test_an_unknown_get_path_is_still_not_found(tmp_path: Path, serving) -> None:
    index_path = build_index(tmp_path)
    url, token = serving(index_path)

    status, _, _ = get(f"{url}/nada", token)

    assert status == 404


def test_a_render_is_served_as_a_jpeg(tmp_path: Path, serving) -> None:
    index_path = build_index(tmp_path)
    url, token = serving(index_path)

    status, data, headers = fetch_render(url, token, "a.jpg")

    assert status == 200
    assert headers["Content-Type"] == "image/jpeg"
    assert headers["Content-Length"] == str(len(data))
    assert data[:2] == b"\xff\xd8"


def test_a_render_never_exceeds_the_cap(tmp_path: Path, serving) -> None:
    from io import BytesIO

    from PIL import Image as pil_image

    from fotos_plus.photos import RENDER_SIZE

    index_path = build_index(tmp_path)
    url, token = serving(index_path)

    _, data, _ = fetch_render(url, token, "a.jpg")

    with pil_image.open(BytesIO(data)) as rendered:
        assert max(rendered.size) <= RENDER_SIZE


def test_the_second_render_is_not_produced_again(tmp_path: Path, serving) -> None:
    """La segunda peticion sale del render guardado."""
    index_path = build_index(tmp_path)
    url, token = serving(index_path)

    first = fetch_render(url, token, "a.jpg")[1]
    second = fetch_render(url, token, "a.jpg")[1]

    assert first == second
    stored = index_path.parent / "indice-renders"
    assert [p.name for p in stored.iterdir()] == ["a.jpg"]


def test_a_render_without_the_token_is_refused(tmp_path: Path, serving) -> None:
    from fotos_plus.server import start_edit_server

    index_path = build_index(tmp_path)
    url, token = serving(index_path)

    status, data, _ = fetch_render(url, token, "a.jpg", headers={"X-Fotos-Plus-Token": "nope"})

    assert status == 403
    assert data[:2] != b"\xff\xd8"


def test_a_render_with_no_token_at_all_is_refused(tmp_path: Path, serving) -> None:
    index_path = build_index(tmp_path)
    url, token = serving(index_path)
    quoted = urllib.parse.quote("a.jpg", safe="")
    request = urllib.request.Request(f"{url}/render?ref={quoted}", headers={"Host": "127.0.0.1"})
    try:
        with urllib.request.urlopen(request, timeout=10) as respuesta:
            status, data = respuesta.status, respuesta.read()
    except urllib.error.HTTPError as error:
        status, data = error.code, error.read()

    assert status == 403
    assert data[:2] != b"\xff\xd8"


def test_a_render_from_a_cross_origin_page_is_refused(tmp_path: Path, serving) -> None:
    """Un `<img>` de otra pagina no puede leer fotos de este servidor."""
    index_path = build_index(tmp_path)
    url, token = serving(index_path)

    status, data, _ = fetch_render(
        url, token, "a.jpg", headers={"Sec-Fetch-Site": "cross-site"}
    )

    assert status == 403
    assert data[:2] != b"\xff\xd8"


def test_a_render_from_a_sibling_site_is_refused(tmp_path: Path, serving) -> None:
    index_path = build_index(tmp_path)
    url, token = serving(index_path)

    status, _, _ = fetch_render(
        url, token, "a.jpg", headers={"Sec-Fetch-Site": "same-site"}
    )

    assert status == 403


def test_a_same_origin_render_is_allowed(tmp_path: Path, serving) -> None:
    index_path = build_index(tmp_path)
    url, token = serving(index_path)

    status, _, _ = fetch_render(
        url, token, "a.jpg", headers={"Sec-Fetch-Site": "same-origin"}
    )

    assert status == 200


def test_a_render_with_no_reference_is_refused(tmp_path: Path, serving) -> None:
    index_path = build_index(tmp_path)
    url, token = serving(index_path)

    request = urllib.request.Request(
        f"{url}/render", headers={"X-Fotos-Plus-Token": token}
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as respuesta:
            status = respuesta.status
    except urllib.error.HTTPError as error:
        status = error.code

    assert status == 400


def test_a_reference_that_is_not_in_the_index_is_refused(tmp_path: Path, serving) -> None:
    index_path = build_index(tmp_path)
    url, token = serving(index_path)

    status, _, _ = fetch_render(url, token, "no-existe.jpg")

    assert status == 404


@pytest.mark.parametrize(
    "malicious",
    [
        "../../../Windows/win.ini",
        "..\\..\\..\\Windows\\win.ini",
        "C:\\Windows\\win.ini",
        "/etc/passwd",
        "fotos/../../secreto.jpg",
    ],
)
def test_a_reference_escaping_the_root_is_refused(
    tmp_path: Path, serving, malicious: str
) -> None:
    """Ninguna de estas referencias llega al disco: no estan en el indice."""
    index_path = build_index(tmp_path)
    url, token = serving(index_path)

    status, data, _ = fetch_render(url, token, malicious)

    assert status == 404
    assert b"MZ" not in data[:64]


def test_a_render_does_not_write_into_the_library(tmp_path: Path, serving) -> None:
    """El unico lugar que crece es el cache, al lado del indice."""
    from tests.conftest import make_sized_image

    index_path = build_index(tmp_path)
    url, token = serving(index_path)
    root = tmp_path / "fotos"
    before = sorted(p.name for p in root.iterdir())

    fetch_render(url, token, "a.jpg")

    assert sorted(p.name for p in root.iterdir()) == before
    assert (tmp_path / "indice-renders").is_dir()


def test_two_requests_for_the_same_reference_return_the_same_bytes(
    tmp_path: Path, serving
) -> None:
    """La resolucion queda cacheada en el servidor, no se vuelve a recorrer el indice."""
    index_path = build_index(tmp_path)
    url, token = serving(index_path)

    first = fetch_render(url, token, "b.jpg")
    second = fetch_render(url, token, "b.jpg")

    assert first[0] == 200
    assert first[1] == second[1]


def test_a_render_of_a_photo_that_vanished_is_reported(tmp_path: Path, serving) -> None:
    """La foto desaparece entre el escaneo y la peticion: se informa, no se cuelga."""
    index_path = build_index(tmp_path)
    url, token = serving(index_path)
    (tmp_path / "fotos" / "b.jpg").unlink()

    status, _, _ = fetch_render(url, token, "b.jpg")

    assert status == 422


# --- 4. inventario de fotos de un grupo ---------------------------------------


def fetch_photos(url: str, token: str, group: str, headers: dict | None = None):
    all_headers = {"X-Fotos-Plus-Token": token}
    all_headers.update(headers or {})
    quoted = urllib.parse.quote(group, safe="")
    request = urllib.request.Request(f"{url}/api/photos?group={quoted}", headers=all_headers)
    try:
        with urllib.request.urlopen(request, timeout=10) as respuesta:
            return respuesta.status, json.loads(respuesta.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read().decode("utf-8"))


def test_the_photo_list_of_a_group_comes_back_in_order(tmp_path: Path, serving) -> None:
    index_path = build_index(tmp_path)
    url, token = serving(index_path)

    status, data = fetch_photos(url, token, "2024-05-01T00:00:00")

    assert status == 200
    assert data["photos"] == [
        {
            "ref": "a.jpg",
            "sha256": "a",
            "marked": False,
            "captured_at": "2024-05-02T10:00:00",
        },
    ]


def test_the_photo_list_carries_the_capture_date_of_each_photo(
    tmp_path: Path, serving
) -> None:
    """El visor necesita el dia de cada foto para pintar la linea de posicion."""
    index_path = build_index(tmp_path)
    url, token = serving(index_path)

    status, data = fetch_photos(url, token, "2024-05-01T00:00:00")

    assert status == 200
    assert data["photos"][0]["captured_at"] == "2024-05-02T10:00:00"


def test_a_photo_without_a_capture_date_serves_null_instead_of_dropping_the_key(
    tmp_path: Path, serving
) -> None:
    """La clave se manda siempre: el cliente lee una sola propiedad sin comprobar nada."""
    index_path = build_index(tmp_path, captured_at=(None, "2024-08-02T10:00:00"))
    url, token = serving(index_path)

    status, data = fetch_photos(url, token, UNCLASSIFIED_GROUP_KEY)

    assert status == 200
    assert [photo["ref"] for photo in data["photos"]] == ["a.jpg"]
    assert "captured_at" in data["photos"][0]
    assert data["photos"][0]["captured_at"] is None


def test_the_photo_list_carries_the_content_hash_of_each_photo(
    tmp_path: Path, serving
) -> None:
    index_path = build_index(tmp_path)
    url, token = serving(index_path)

    _, data = fetch_photos(url, token, "2024-08-01T00:00:00")

    assert data["photos"][0]["sha256"] == "b"


def test_the_photo_list_reports_the_mark_state_of_each_photo(
    tmp_path: Path, serving
) -> None:
    from fotos_plus.labels import LabelOverlay, write_edicion

    index_path = build_index(tmp_path, shas=("a" * 64, "b" * 64))
    write_edicion(LabelOverlay(marked=["a" * 64]), edicion_path_next_to(index_path))
    url, token = serving(index_path)

    _, data = fetch_photos(url, token, "2024-05-01T00:00:00")

    assert data["photos"][0]["marked"] is True
    assert data["marked_count"] == 1


def test_the_group_photos_are_the_ones_the_cards_show(tmp_path: Path, serving) -> None:
    """El endpoint agrupa igual que las tarjetas, no con otra cuenta."""
    index_path = build_index(tmp_path)
    url, token = serving(index_path)
    _, page, _ = get(url, token)
    data = json.loads(page.split('id="viewer-data">')[1].split("</script>")[0])

    _, listing = fetch_photos(url, token, "2024-05-01T00:00:00")

    entry = next(g for g in data["groups"] if g["browse_key"] == "2024-05-01T00:00:00")
    assert entry["photo_count"] == len(listing["photos"])


def test_an_unknown_group_is_refused(tmp_path: Path, serving) -> None:
    index_path = build_index(tmp_path)
    url, token = serving(index_path)

    status, data = fetch_photos(url, token, "no-existe")

    assert status == 404
    assert data["error"]


def test_the_photo_list_without_a_token_is_refused(tmp_path: Path, serving) -> None:
    index_path = build_index(tmp_path)
    url, token = serving(index_path)

    status, _ = fetch_photos(url, token, "2024-05-01T00:00:00", headers={
        "X-Fotos-Plus-Token": "nope"
    })

    assert status == 403


def test_the_photo_list_without_a_group_is_refused(tmp_path: Path, serving) -> None:
    index_path = build_index(tmp_path)
    url, token = serving(index_path)

    request = urllib.request.Request(
        f"{url}/api/photos", headers={"X-Fotos-Plus-Token": token}
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as respuesta:
            status = respuesta.status
    except urllib.error.HTTPError as error:
        status = error.code

    assert status == 400


def test_a_group_that_repeats_its_reference_is_refused(tmp_path: Path) -> None:
    """Dos grupos con la misma clave no se distinguen: no se muestra uno cualquiera."""
    from fotos_plus.server import _LabelServer
    from fotos_plus.viewer import Group

    group = Group(
        title="Uno",
        kind="trip",
        photo_count=1,
        first_captured_at=None,
        last_captured_at=None,
        key="misma",
        photos=[],
    )
    twin = Group(
        title="Dos",
        kind="trip",
        photo_count=1,
        first_captured_at=None,
        last_captured_at=None,
        key="misma",
        photos=[],
    )
    server = _LabelServer.__new__(_LabelServer)
    server._group_map = None
    server._groups = [group, twin]
    server._resolution = object()

    assert server.group_for("misma") is None


# --- 6. marcar y desmarcar la foto mostrada ------------------------------------


def mark(
    url: str,
    token: str,
    action: str,
    reference: str,
    host: str = "127.0.0.1",
    headers: dict | None = None,
    content_type: str = "application/json",
):
    all_headers = {"X-Fotos-Plus-Token": token}
    all_headers.update(headers or {})
    if content_type is not None:
        all_headers["Content-Type"] = content_type
    body = {"action": action, "ref": reference, "token": token}
    data = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        f"{url}/api/marks", data=data, headers={**all_headers, "Host": host}, method="POST"
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as respuesta:
            return respuesta.status, json.loads(respuesta.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read().decode("utf-8"))


def marked_index(tmp_path: Path) -> Path:
    return build_index(tmp_path, shas=("a" * 64, "b" * 64))


def test_a_mark_is_saved_and_confirmed(tmp_path: Path, serving) -> None:
    index_path = marked_index(tmp_path)
    url, token = serving(index_path)

    status, data = mark(url, token, "mark", "a.jpg")

    assert status == 200
    assert data["marked"] is True
    assert read_edicion(edicion_path_next_to(index_path)).marked == ["a" * 64]


def test_unmarking_removes_the_mark_again(tmp_path: Path, serving) -> None:
    index_path = marked_index(tmp_path)
    url, token = serving(index_path)
    mark(url, token, "mark", "a.jpg")

    status, data = mark(url, token, "unmark", "a.jpg")

    assert status == 200
    assert data["marked"] is False
    assert read_edicion(edicion_path_next_to(index_path)).marked == []


def test_marking_the_same_photo_twice_does_not_duplicate_it(
    tmp_path: Path, serving
) -> None:
    index_path = marked_index(tmp_path)
    url, token = serving(index_path)

    mark(url, token, "mark", "a.jpg")
    mark(url, token, "mark", "a.jpg")

    assert read_edicion(edicion_path_next_to(index_path)).marked == ["a" * 64]


def test_marking_writes_only_the_edition_file(tmp_path: Path, serving) -> None:
    """Las fotos no se tocan: marcar solo reescribe el archivo de edicion."""
    index_path = marked_index(tmp_path)
    root = tmp_path / "fotos"
    photos_before = {p.name: p.read_bytes() for p in root.iterdir()}
    listing_before = sorted(p.name for p in tmp_path.iterdir())
    index_before = index_path.read_bytes()

    url, token = serving(index_path)
    mark(url, token, "mark", "a.jpg")

    assert {p.name: p.read_bytes() for p in root.iterdir()} == photos_before
    assert index_path.read_bytes() == index_before
    assert sorted(p.name for p in tmp_path.iterdir()) == sorted(
        listing_before + ["indice-edicion.json"]
    )


def test_marking_survives_the_labels_already_in_the_file(tmp_path: Path, serving) -> None:
    from fotos_plus.labels import LabelOverlay, write_edicion
    from fotos_plus.index import read_suggestions

    index_path = marked_index(tmp_path)
    overlay = LabelOverlay(labels={"2024-05-01T00:00:00": "Viaje"})
    write_edicion(overlay, edicion_path_next_to(index_path))
    url, token = serving(index_path)

    mark(url, token, "mark", "a.jpg")

    saved = read_edicion(edicion_path_next_to(index_path))
    assert saved.marked == ["a" * 64]
    assert saved.labels["2024-05-01T00:00:00"] == "Viaje"


def test_a_mark_with_no_token_is_refused(tmp_path: Path, serving) -> None:
    index_path = marked_index(tmp_path)
    url, token = serving(index_path)

    status, _ = mark(url, token, "mark", "a.jpg", headers={"X-Fotos-Plus-Token": "nope"})

    assert status == 403
    assert not edicion_path_next_to(index_path).exists()


def test_a_mark_from_another_host_is_refused(tmp_path: Path, serving) -> None:
    index_path = marked_index(tmp_path)
    url, token = serving(index_path)

    status, data = mark(url, token, "mark", "a.jpg", host="ejemplo.com")

    assert status == 400
    assert data["error"]
    assert not edicion_path_next_to(index_path).exists()


def test_a_mark_without_a_json_content_type_is_refused(tmp_path: Path, serving) -> None:
    index_path = marked_index(tmp_path)
    url, token = serving(index_path)

    status, data = mark(url, token, "mark", "a.jpg", content_type="text/plain")

    assert status == 415
    assert data["error"]
    assert not edicion_path_next_to(index_path).exists()


def test_a_mark_of_a_reference_outside_the_index_is_refused(
    tmp_path: Path, serving
) -> None:
    index_path = marked_index(tmp_path)
    url, token = serving(index_path)

    status, data = mark(url, token, "mark", "../../Windows/win.ini")

    assert status == 404
    assert data["error"]
    assert not edicion_path_next_to(index_path).exists()


def test_an_unknown_mark_action_is_refused(tmp_path: Path, serving) -> None:
    index_path = marked_index(tmp_path)
    url, token = serving(index_path)

    status, data = mark(url, token, "borrar", "a.jpg")

    assert status == 400
    assert data["error"]


def test_a_mark_without_a_reference_is_refused(tmp_path: Path, serving) -> None:
    index_path = marked_index(tmp_path)
    url, token = serving(index_path)

    status, data = post(f"{url}/api/marks", token, {"action": "mark", "token": token})

    assert status == 400
    assert data["error"]


def test_a_post_to_an_unknown_path_is_still_not_found(tmp_path: Path, serving) -> None:
    index_path = marked_index(tmp_path)
    url, token = serving(index_path)

    status, data = post(f"{url}/api/otros", token, {"token": token})

    assert status == 404


def test_a_reopened_browser_shows_the_mark_that_was_just_saved(
    tmp_path: Path, serving
) -> None:
    """La pagina se reconstruye al marcar: la cuenta del grupo queda al dia."""
    index_path = marked_index(tmp_path)
    url, token = serving(index_path)

    _, before, _ = get(url, token)
    mark(url, token, "mark", "a.jpg")
    _, after, _ = get(url, token)

    def count(document: str) -> int:
        data = json.loads(
            re.search(r'id="viewer-data">(.*?)</script>', document, re.S).group(1)
        )
        entry = next(g for g in data["groups"] if g["browse_key"] == "2024-05-01T00:00:00")
        return entry["marked_count"]

    assert count(before) == 0
    assert count(after) == 1


def test_a_reopened_browser_reports_the_new_mark_state(tmp_path: Path, serving) -> None:
    index_path = marked_index(tmp_path)
    url, token = serving(index_path)
    mark(url, token, "mark", "a.jpg")

    _, listing = fetch_photos(url, token, "2024-05-01T00:00:00")

    assert listing["photos"][0]["marked"] is True
    assert listing["marked_count"] == 1
