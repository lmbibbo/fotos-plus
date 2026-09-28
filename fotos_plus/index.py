from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Optional

from .models import ScanResult


def state_dir() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local"
    else:
        base = os.environ.get("XDG_STATE_HOME") or Path.home() / ".local" / "state"
    return Path(base) / "fotos-plus"


def indexes_dir() -> Path:
    return state_dir() / "indexes"


def default_index_path(root: Path) -> Path:
    normalized = os.path.normcase(os.path.normpath(str(Path(root).resolve())))
    key = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]
    return indexes_dir() / f"{key}.json"


def write_index(result: ScanResult, path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(result.to_dict(), indent=2, ensure_ascii=False)

    handle, temporary = tempfile.mkstemp(
        dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            stream.write(payload)
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise
    return path


def read_index(path: Path) -> ScanResult:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return ScanResult.from_dict(data)
