from __future__ import annotations

import http.server
import json
import secrets
import socket
import string
from pathlib import Path
from typing import Optional

from .index import edicion_path_next_to, suggestions_path_next_to
from .labels import (
    LabelError,
    LabelOverlay,
    clear_tag,
    derived_title,
    read_edicion,
    remove_label,
    resolve_labels,
    set_label,
    set_tag,
    write_edicion,
)
from .index import read_index, read_suggestions
from .viewer import assign_groups, render_html


class EditServerError(Exception):
    """Error al arrancar o al operar el servidor de edicion."""


def _is_loopback(host: str) -> bool:
    if not host:
        return False
    h = host.strip().lower()
    if h == "localhost" or h == "127.0.0.1" or h == "::1" or h == "[::1]":
        return True
    if h.startswith("127.0."):
        return True
    return False


class _LabelHandler(http.server.BaseHTTPRequestHandler):
    server_version = "FotosPlus/0.1"

    MAX_BODY_BYTES = 64 * 1024

    def _drain_body(self) -> Optional[bytes]:
        """Lee el cuerpo del POST una sola vez, antes de responder nada.

        Leerlo siempre, incluso cuando la peticion se va a rechazar, evita que el
        cliente siga escribiendo sobre una conexion que el servidor ya cerro: en
        Windows eso aborta la conexion y el cliente se queda sin respuesta en vez de
        recibir el motivo del rechazo.
        """
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._send_json(400, {"error": "Content-Length invalido"})
            return None
        if length > self.MAX_BODY_BYTES:
            self._send_json(413, {"error": "El cuerpo es demasiado grande"})
            return None
        if length <= 0:
            return b""
        return self.rfile.read(length)

    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        # Sin cabeceras CORS: no permitimos acceso desde otro origen
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, status: int, html_bytes: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(html_bytes)))
        self.end_headers()
        self.wfile.write(html_bytes)

    def log_message(self, format: str, *args) -> None:
        # No logueamos ruido al stdout del comando
        return

    def do_GET(self) -> None:
        host = self.headers.get("Host", "")
        if not _is_loopback(host):
            self._send_json(400, {"error": "Host no permitido"})
            return
        server = self.server
        path = self.path.split("?", 1)[0]
        if path == "/" or path == "":
            html_bytes = server.build_page()
            self._send_html(200, html_bytes)
            return
        self._send_json(404, {"error": "no encontrado"})

    def do_POST(self) -> None:
        body = self._drain_body()
        if body is None:
            return

        host = self.headers.get("Host", "")
        if not _is_loopback(host):
            self._send_json(400, {"error": "Host no permitido"})
            return

        path = self.path.split("?", 1)[0]
        if path != "/api/labels":
            self._send_json(404, {"error": "no encontrado"})
            return

        content_type = self.headers.get("Content-Type", "")
        if "application/json" not in content_type:
            self._send_json(415, {"error": "Content-Type debe ser application/json"})
            return

        server = self.server
        token = server.token
        try:
            data = json.loads(body.decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as error:
            self._send_json(400, {"error": f"JSON invalido: {error}"})
            return
        if not isinstance(data, dict):
            self._send_json(400, {"error": "El cuerpo tiene que ser un objeto"})
            return

        # El token viaja en el cuerpo y tambien como encabezado: el encabezado
        # obliga a que el navegador haga preflight, que es lo que corta el
        # cross-origin. El token del cuerpo es la comprobacion real.
        sent = self.headers.get("X-Fotos-Plus-Token")
        if sent != token or data.get("token") != token:
            self._send_json(403, {"error": "token invalido"})
            return

        action = data.get("action") or "set"
        key = data.get("key", data.get("first_captured_at"))
        text = data.get("text", data.get("label"))
        tag = data.get("tag")

        try:
            overlay = server.overlay
            if action == "remove":
                updated = remove_label(overlay, key)
            elif action == "set":
                updated = set_label(
                    overlay, server.suggestions, key, text, server.scanned_at
                )
            elif action == "set_tag":
                updated = set_tag(overlay, server.suggestions, key, tag, server.scanned_at)
            elif action == "clear_tag":
                updated = clear_tag(overlay, key)
            else:
                self._send_json(400, {"error": "accion desconocida"})
                return
            write_edicion(updated, server.edicion_path)
        except LabelError as error:
            # Rechazo previsto: no se escribe nada y el archivo queda intacto.
            self._send_json(400, {"error": str(error)})
            return
        except OSError as error:
            self._send_json(500, {"error": f"no se pudo escribir: {error}"})
            return

        server.overlay = updated
        server.invalidate_page()
        title = updated.title_for(key) or derived_title(
            data.get("kind", "trip"), str(key), server.suggestions
        )
        self._send_json(200, {"ok": True, "title": title})


class _LabelServer(http.server.HTTPServer):
    def __init__(
        self,
        server_address: tuple[str, int],
        handler_class,
        index_path: Path,
        token: str,
        suggestions,
        edicion_path: Path,
        overlay: LabelOverlay,
    ) -> None:
        super().__init__(server_address, handler_class)
        self.index_path = Path(index_path)
        self.token = token
        self.suggestions = suggestions
        self.scanned_at = suggestions.scanned_at
        self.edicion_path = Path(edicion_path)
        self.overlay = overlay
        self._page_cache: Optional[bytes] = None

    def invalidate_page(self) -> None:
        """La pagina se vuelve a construir en el proximo request."""
        self._page_cache = None

    def build_page(self) -> bytes:
        if self._page_cache is not None:
            return self._page_cache

        result = read_index(self.index_path)
        resolution = resolve_labels(self.overlay, self.suggestions)
        groups = assign_groups(
            result.photos,
            self.suggestions,
            labels=resolution.labels,
            tags=resolution.tags,
        )
        html = render_html(
            groups,
            result.root,
            flat=False,
            labels=resolution.labels,
            token=self.token,
            drift=resolution,
            tag_options=self.overlay.tags,
        )
        self._page_cache = html.encode("utf-8")
        return self._page_cache


def _find_free_port(start: int = 8000, end: int = 9000) -> int:
    for port in range(start, end):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise EditServerError("No hay puertos libres en el rango 8000-8999")


def _random_token() -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(32))


def start_edit_server(
    index_path: Path, port: Optional[int] = None, bind: str = "127.0.0.1"
) -> tuple["_LabelServer", int, str]:
    """Arranca el servidor de edicion en loopback.

    Devuelve (servidor, puerto, token). El servidor deja de escuchar cuando se cierra
    con shutdown().
    """
    index_path = Path(index_path)
    if not index_path.is_file():
        raise EditServerError(f"No existe el indice: {index_path}")

    if bind != "127.0.0.1":
        raise EditServerError("El servidor solo puede escucharse en loopback")

    suggestions_path = suggestions_path_next_to(index_path)
    if not suggestions_path.is_file():
        raise EditServerError(
            f"No existe el archivo de sugerencias contiguo a {index_path}"
        )

    suggestions = read_suggestions(suggestions_path)
    edicion_path = edicion_path_next_to(index_path)
    overlay = read_edicion(edicion_path)

    if port is not None:
        # Se comprueba antes de construir el servidor para que un puerto ocupado
        # falle sin dejar un servidor a medio hacer.
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                probe.bind((bind, port))
            except OSError as error:
                raise EditServerError(
                    f"El puerto {port} ya esta en uso: {error}"
                ) from error
    else:
        port = _find_free_port()

    token = _random_token()
    server = _LabelServer(
        (bind, port),
        _LabelHandler,
        index_path,
        token,
        suggestions,
        edicion_path,
        overlay,
    )
    return server, port, token