from __future__ import annotations

import http.server
import json
import secrets
import socket
import string
from pathlib import Path
from typing import Optional
from urllib.parse import parse_qs, urlsplit

from .index import (
    edicion_path_next_to,
    render_path_for,
    renders_dir_next_to,
    suggestions_path_next_to,
)
from .labels import (
    LabelError,
    LabelOverlay,
    bucket_photo,
    clear_tag,
    derived_title,
    mark_photo,
    prune_marked,
    prune_photo_tagged,
    read_edicion,
    remove_label,
    resolve_labels,
    set_label,
    set_tag,
    unbucket_photo,
    unmark_photo,
    write_edicion,
)
from .index import read_index, read_suggestions
from .photos import PhotoError, cached_render
from .viewer import _photo_sort_key, assign_groups, render_html


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


def _is_cross_origin(headers) -> bool:
    """Whether the browser says the request came from somewhere other than this server.

    The server deliberately sends no CORS headers, which stops a foreign page from reading
    a response. That protection does not cover `<img>`, which renders cross-origin without
    asking. Once a route returns photo bytes, any page the user visits while the server is
    running could otherwise embed a photo from it. The browser tells us which case this is
    in `Sec-Fetch-Site`, and a genuine same-origin request never sends `cross-site`.
    """
    return headers.get("Sec-Fetch-Site", "") in {"cross-site", "same-site"}


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

    def _send_image(self, status: int, image_bytes: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "image/jpeg")
        self.send_header("Content-Length", str(len(image_bytes)))
        self.end_headers()
        self.wfile.write(image_bytes)

    def log_message(self, format: str, *args) -> None:
        # No logueamos ruido al stdout del comando
        return

    def do_GET(self) -> None:
        host = self.headers.get("Host", "")
        if not _is_loopback(host):
            self._send_json(400, {"error": "Host no permitido"})
            return
        server = self.server
        split = urlsplit(self.path)
        path = split.path
        if path == "/" or path == "":
            html_bytes = server.build_page()
            self._send_html(200, html_bytes)
            return
        if path == "/render":
            self._serve_render(parse_qs(split.query))
            return
        if path == "/api/photos":
            self._serve_photos(parse_qs(split.query))
            return
        self._send_json(404, {"error": "no encontrado"})

    def _serve_render(self, query: dict[str, list[str]]) -> None:
        """Sirve el render de pantalla de una foto del indice.

        La referencia que llega nunca se usa como ruta del sistema de archivos: se busca
        en el indice y de ahi salen tanto el archivo original como el nombre del render.
        Una referencia que el indice no tiene no llega a tocar el disco, asi que un
        `../` o una ruta absoluta no tienen por donde entrar.
        """
        server = self.server

        if self.headers.get("X-Fotos-Plus-Token") != server.token:
            self._send_json(403, {"error": "token invalido"})
            return

        if _is_cross_origin(self.headers):
            self._send_json(403, {"error": "peticion de otro origen rechazada"})
            return

        values = query.get("ref") or []
        if len(values) != 1:
            self._send_json(400, {"error": "falta la referencia de la foto"})
            return

        photo = server.photo_for(values[0])
        if photo is None:
            self._send_json(404, {"error": "la referencia no corresponde a ninguna foto"})
            return

        source = server.root / photo.relative_path
        try:
            data = cached_render(source, photo.sha256, server.render_path(photo.sha256))
        except PhotoError as error:
            self._send_json(422, {"error": f"no se pudo preparar la foto: {error}"})
            return
        except OSError as error:
            self._send_json(500, {"error": f"no se pudo leer la foto: {error}"})
            return
        self._send_image(200, data)

    def _serve_photos(self, query: dict[str, list[str]]) -> None:
        """La lista de fotos de un grupo, para que el visor pueda recorrerlo.

        Va en su propio endpoint y no en la pagina porque son cinco mil fotos: la pagina
        tiene que abrir rapido y las listas se piden solo cuando alguien abre un grupo.
        """
        server = self.server

        if self.headers.get("X-Fotos-Plus-Token") != server.token:
            self._send_json(403, {"error": "token invalido"})
            return

        values = query.get("group") or []
        if len(values) != 1:
            self._send_json(400, {"error": "falta la referencia del grupo"})
            return

        group = server.group_for(values[0])
        if group is None:
            self._send_json(404, {"error": "la referencia no corresponde a ningun grupo"})
            return

        marked = set(server.overlay.marked)
        self._send_json(
            200,
            {
                "group": group.browse_key,
                "title": group.title,
                "marked_count": sum(1 for p in group.photos if p.sha256 in marked),
                "photos": [
                    {
                        "ref": photo.relative_path,
                        "sha256": photo.sha256,
                        "marked": photo.sha256 in marked,
                        "captured_at": photo.captured_at,
                    }
                    for photo in sorted(group.photos, key=_photo_sort_key)
                ],
            },
        )

    def do_POST(self) -> None:
        body = self._drain_body()
        if body is None:
            return

        host = self.headers.get("Host", "")
        if not _is_loopback(host):
            self._send_json(400, {"error": "Host no permitido"})
            return

        path = self.path.split("?", 1)[0]
        if path not in ("/api/labels", "/api/marks", "/api/photo-tags"):
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

        if path == "/api/marks":
            self._save_mark(data)
            return

        if path == "/api/photo-tags":
            self._save_bucket(data)
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

    def _save_mark(self, data: dict) -> None:
        """Marca o desmarca la foto mostrada.

        Igual que las etiquetas, la referencia se resuelve por el indice y no se usa
        como ruta: la marca se guarda por el hash de contenido que el escaneo ya le
        calculo. Lo unico que se reescribe es el archivo de edicion; las fotos no se
        tocan, y por eso marcar no puede fallar a mitad de camino por un disco lleno en
        la biblioteca.
        """
        server = self.server

        action = data.get("action")
        if action not in ("mark", "unmark"):
            self._send_json(400, {"error": "accion desconocida"})
            return

        reference = data.get("ref")
        if not isinstance(reference, str):
            self._send_json(400, {"error": "falta la referencia de la foto"})
            return

        photo = server.photo_for(reference)
        if photo is None:
            self._send_json(404, {"error": "la referencia no corresponde a ninguna foto"})
            return

        try:
            if action == "mark":
                updated = mark_photo(server.overlay, photo.sha256)
            else:
                updated = unmark_photo(server.overlay, photo.sha256)
            write_edicion(updated, server.edicion_path)
        except LabelError as error:
            # Rechazo previsto: no se escribe nada y el archivo queda intacto.
            self._send_json(400, {"error": str(error)})
            return
        except OSError as error:
            self._send_json(500, {"error": f"no se pudo escribir: {error}"})
            return

        server.overlay = updated
        # La pagina lleva las marcas de cada grupo, asi que hay que reconstruirla para
        # que un recorrido abierto la vez siguiente ya muestre el estado nuevo.
        server.invalidate_page()
        self._send_json(
            200,
            {
                "ok": True,
                "ref": photo.relative_path,
                "sha256": photo.sha256,
                "marked": photo.sha256 in updated.marked,
            },
        )

    def _save_bucket(self, data: dict) -> None:
        """Agrega o quita un cubo de la foto nombrada por su hash.

        A diferencia de las marcas, que son una sola operacion de ida y vuelta, un cubo se
        agrega o se quita por separado: una foto puede estar en varios a la vez y quitar uno
        no tiene que tocar los demas.

        El hash no se usa como ruta del sistema de archivos: se busca en el indice para
        saber que la foto existe, y lo que se guarda es el hash mismo, asi que la
        pertenencia sobrevive a que la foto se mueva de carpeta. Lo unico que se reescribe es
        el archivo de edicion.
        """
        server = self.server

        action = data.get("action")
        if action not in ("add", "remove"):
            self._send_json(400, {"error": "accion desconocida"})
            return

        sha256 = data.get("sha256")
        name = data.get("bucket")

        if not isinstance(sha256, str) or not isinstance(name, str):
            self._send_json(400, {"error": "falta el hash o el nombre del cubo"})
            return

        try:
            if action == "add":
                updated = bucket_photo(
                    server.overlay,
                    sha256,
                    name,
                    [photo.sha256 for photo in server.index().photos],
                    server.scanned_at,
                )
            else:
                updated = unbucket_photo(server.overlay, sha256, name)
            write_edicion(updated, server.edicion_path)
        except LabelError as error:
            # Rechazo previsto: no se escribe nada y el archivo queda intacto.
            self._send_json(400, {"error": str(error)})
            return
        except OSError as error:
            self._send_json(500, {"error": f"no se pudo escribir: {error}"})
            return

        server.overlay = updated
        # Las secciones de cubos son parte de la pagina, asi que hay que reconstruirla.
        server.invalidate_page()
        self._send_json(
            200,
            {
                "ok": True,
                "sha256": sha256,
                "buckets": updated.buckets_for(str(sha256)),
            },
        )


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
        dev: bool = False,
    ) -> None:
        super().__init__(server_address, handler_class)
        self.index_path = Path(index_path)
        self.token = token
        self.dev = dev
        self.suggestions = suggestions
        self.scanned_at = suggestions.scanned_at
        self.edicion_path = Path(edicion_path)
        self.overlay = overlay
        self._page_cache: Optional[bytes] = None
        self._index_result = None
        self._photo_map: Optional[dict] = None
        self._resolution = None
        self._groups = None
        self._group_map: Optional[dict] = None

    @property
    def root(self) -> Path:
        return Path(self.index().root)

    def index(self):
        """El indice, leido una sola vez mientras el servidor vive.

        El archivo ya se cargo para resolver el servidor y volver a leerlo en cada
        peticion solo produciria decisiones distintas entre las tarjetas y los renders:
        si el indice cambiara a mitad de una sesion, una tarjeta podria describir fotos
        que su render no encuentra. Leyendolo una vez, el servidor es coherente consigo
        mismo.
        """
        if self._index_result is None:
            self._index_result = read_index(self.index_path)
            # Las marcas y los cubos de fotos que el indice ya no tiene no se cuentan para
            # mostrar, pero siguen guardados: si la foto vuelve, la marca y el cubo estan.
            known = [photo.sha256 for photo in self._index_result.photos]
            self.overlay = prune_photo_tagged(prune_marked(self.overlay, known), known)
        return self._index_result

    def photo_for(self, reference: str):
        """La foto del indice que esa referencia nombra, o None si no hay ninguna.

        La referencia solo se usa como clave de este mapa. De la foto resuelta salen el
        archivo original y el nombre del render, y ninguno de los dos depende de lo que
        haya mandado el cliente.
        """
        if self._photo_map is None:
            self._photo_map = {
                photo.relative_path: photo for photo in self.index().photos
            }
        return self._photo_map.get(reference.replace("\\", "/"))

    def render_path(self, sha256: str) -> Path:
        return render_path_for(renders_dir_next_to(self.index_path), sha256)

    def resolve(self):
        """Las etiquetas vigentes y los grupos, calculados una sola vez por sesion.

        La pagina y el endpoint de fotos tienen que contar lo mismo: si uno agrupara con
        una edicion y el otro con otra, una tarjeta podria abrir un grupo con una lista
        que no corresponde. Salen de la misma cuenta.
        """
        if self._resolution is None:
            resolution = resolve_labels(self.overlay, self.suggestions)
            self._resolution = resolution
            self._groups = assign_groups(
                self.index().photos,
                self.suggestions,
                labels=resolution.labels,
                tags=resolution.tags,
            )
        return self._resolution, self._groups

    def group_for(self, reference: str):
        """El grupo que esa referencia nombra, o None si no hay uno solo.

        Dos grupos con la misma referencia no se distinguen, asi que no se elige uno
        cualquiera: se informa, porque un grupo mostrado por error seria peor que uno
        que no se pueda abrir.
        """
        if self._group_map is None:
            grouped: dict = {}
            for group in self.resolve()[1]:
                grouped.setdefault(group.browse_key, []).append(group)
            self._group_map = {
                key: (members[0] if len(members) == 1 else None)
                for key, members in grouped.items()
            }
        return self._group_map.get(reference)

    def invalidate_page(self) -> None:
        """La pagina se vuelve a construir en el proximo request."""
        self._page_cache = None
        self._resolution = None
        self._groups = None
        self._group_map = None

    def build_page(self) -> bytes:
        if self._page_cache is not None and not self.dev:
            return self._page_cache

        result = self.index()
        resolution, groups = self.resolve()
        html = render_html(
            groups,
            result.root,
            flat=False,
            labels=resolution.labels,
            token=self.token,
            drift=resolution,
            tag_options=self.overlay.tags,
            marked=self.overlay.marked,
            photo_tags=self.overlay.photo_tags,
            photo_tagged=self.overlay.photo_tagged,
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
    index_path: Path,
    port: Optional[int] = None,
    bind: str = "127.0.0.1",
    dev: bool = False,
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
        dev=dev,
    )
    return server, port, token