from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Optional

from .models import INDEX_VERSION, ScanResult, SuggestionsResult

SUGGESTIONS_SUFFIX = "-sugerencias"
EDITION_SUFFIX = "-edicion"
RENDERS_SUFFIX = "-renders"


class IndexVersionError(ValueError):
    pass


def state_dir() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local"
    else:
        base = os.environ.get("XDG_STATE_HOME") or Path.home() / ".local" / "state"
    return Path(base) / "fotos-plus"


def indexes_dir() -> Path:
    return state_dir() / "indexes"


def _root_key(root: Path) -> str:
    normalized = os.path.normcase(os.path.normpath(str(Path(root).resolve())))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def _index_file_name(root: Path) -> str:
    return f"{_root_key(root)}.json"


def _suggestions_file_name(root: Path) -> str:
    return f"{_root_key(root)}{SUGGESTIONS_SUFFIX}.json"


def index_path_for(root: Path, index_dir: Optional[Path] = None) -> Path:
    if index_dir is not None:
        return Path(index_dir) / _index_file_name(root)
    return indexes_dir() / _index_file_name(root)


def suggestions_path_for(root: Path, index_dir: Optional[Path] = None) -> Path:
    if index_dir is not None:
        return Path(index_dir) / _suggestions_file_name(root)
    return indexes_dir() / _suggestions_file_name(root)


def suggestions_path_next_to(index_path: Path) -> Path:
    index_path = Path(index_path)
    return index_path.parent / f"{index_path.stem}{SUGGESTIONS_SUFFIX}.json"


def edicion_path_next_to(index_path: Path) -> Path:
    """Ruta del archivo de edicion contiguo al indice.

    Vive al lado del archivo de sugerencias y es un archivo distinto: lo escribe el
    editor y lo lee el visor, mientras que el de sugerencias solo lo escribe el
    escaneo. Cada archivo tiene un unico escritor.
    """
    index_path = Path(index_path)
    return index_path.parent / f"{index_path.stem}{EDITION_SUFFIX}.json"


def renders_dir_next_to(index_path: Path) -> Path:
    """Directory of screen-sized renders, next to the index.

    It is a directory rather than a file because it holds one render per photo. It sits
    beside the index it was derived from and every entry is named after the photo's content
    hash, not its filename: that way it survives the photo moving folder and cannot go
    stale when the file changes. Everything inside is disposable; deleting it costs the
    time to produce the renders again and nothing else.
    """
    index_path = Path(index_path)
    return index_path.parent / f"{index_path.stem}{RENDERS_SUFFIX}"


def render_path_for(renders_dir: Path, sha256: str) -> Path:
    """Path of the screen render for the photo with that content hash."""
    return Path(renders_dir) / f"{sha256}.jpg"


def poster_path_for(renders_dir: Path, sha256: str) -> Path:
    """Path of the cached poster frame for the video with that content hash."""
    return Path(renders_dir) / f"{sha256}-poster.jpg"


def default_index_path(root: Path) -> Path:
    return index_path_for(root)


def write_json_atomic(payload: dict, path: Path) -> Path:
    """Escribe un JSON de forma atomica.

    Se escribe primero en un temporal del mismo directorio y despues se renombra con
    `os.replace`, que es atomico en el mismo sistema de archivos. Asi una
    interrupcion nunca deja un JSON a medias.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(payload, indent=2, ensure_ascii=False)

    handle, temporary = tempfile.mkstemp(
        dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            stream.write(body)
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise
    return path


def write_index(result: ScanResult, path: Path) -> Path:
    return write_json_atomic(result.to_dict(), path)


def write_suggestions(result: SuggestionsResult, path: Path) -> Path:
    return write_json_atomic(result.to_dict(), path)


def read_index(path: Path) -> ScanResult:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    version = data.get("version")
    if version != INDEX_VERSION:
        raise IndexVersionError(
            f"index version {version!r} is not supported "
            f"(expected {INDEX_VERSION}): rescan the library to rebuild the index"
        )
    return ScanResult.from_dict(data)


def read_suggestions(path: Path) -> SuggestionsResult:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return SuggestionsResult.from_dict(data)
