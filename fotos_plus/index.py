from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Optional

from .models import ScanResult, SuggestionsResult

SUGGESTIONS_SUFFIX = "-sugerencias"


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


def default_index_path(root: Path) -> Path:
    return index_path_for(root)


def _write_json_atomic(payload: dict, path: Path) -> Path:
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
    return _write_json_atomic(result.to_dict(), path)


def write_suggestions(result: SuggestionsResult, path: Path) -> Path:
    return _write_json_atomic(result.to_dict(), path)


def read_index(path: Path) -> ScanResult:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return ScanResult.from_dict(data)


def read_suggestions(path: Path) -> SuggestionsResult:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return SuggestionsResult.from_dict(data)
