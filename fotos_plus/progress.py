from __future__ import annotations

import os
import time
from typing import IO, Optional

REFRESH_EVERY = 25
REFRESH_SECONDS = 0.5
RECENT_SAMPLE_WINDOW = 50


def progress_enabled(stream: IO[str]) -> bool:
    if os.environ.get("FOTOS_PLUS_NO_PROGRESS") == "1":
        return False
    try:
        return bool(stream.isatty())
    except (AttributeError, ValueError):
        return False


def format_duration(seconds: Optional[float]) -> str:
    if seconds is None:
        return "--"
    total = int(round(seconds))
    if total < 0:
        return "--"
    if total < 60:
        return f"{total}s"
    if total < 3600:
        return f"{total // 60}m {total % 60:02d}s"
    return f"{total // 3600}h {(total % 3600) // 60:02d}m"


def format_progress(processed: int, total: int, rate: Optional[float], eta: Optional[float]) -> str:
    percentage = int(processed * 100 / total) if total else 100
    rate_text = f"{rate:.1f} fotos/s" if rate else "-- fotos/s"
    remaining_text = format_duration(eta) if eta is not None else "?"
    return (
        f"Escaneando... {processed}/{total} ({percentage}%)"
        f" - {rate_text} - faltan {remaining_text}"
    )


class ProgressReporter:
    def __init__(self, stream: IO[str]) -> None:
        self._stream = stream
        self._started = time.monotonic()
        self._samples: list[tuple[float, int]] = []
        self._last_shown = 0.0
        self._last_processed = 0
        self._last_line: Optional[str] = None
        self._total = 0
        self._completed = False
        self._width = 0

    def __call__(self, processed: int, total: int) -> None:
        if total <= 0:
            return
        now = time.monotonic()
        self._total = total
        self._samples.append((now, processed))
        if len(self._samples) > RECENT_SAMPLE_WINDOW:
            self._samples.pop(0)

        is_last = processed >= total
        due = processed - self._last_processed >= REFRESH_EVERY
        late = now - self._last_shown >= REFRESH_SECONDS
        if not (is_last or due or late):
            return

        self._last_shown = now
        self._last_processed = processed
        if is_last:
            self._completed = True
        self._render(self._format(processed, total, now))

    def finish(self) -> None:
        if self._total <= 0 or self._last_line is None:
            return
        if not self._completed:
            self._write(self._format(self._total, self._total, time.monotonic()))
        self._stream.write("\n")
        self._stream.flush()

    def _format(self, processed: int, total: int, now: float) -> str:
        elapsed = now - self._started
        rate = processed / elapsed if processed and elapsed >= 0.001 else None
        eta = None
        if processed < total and len(self._samples) >= 2:
            first_time, first_processed = self._samples[0]
            window = now - first_time
            if window >= 0.001 and processed > first_processed:
                window_rate = (processed - first_processed) / window
                eta = (total - processed) / window_rate
        return format_progress(processed, total, rate, eta)

    def _render(self, line: str) -> None:
        self._last_line = line
        self._write(line)

    def _write(self, line: str) -> None:
        # Se rellena con espacios hasta el ancho ya usado para que una linea mas
        # corta no deje restos de la anterior.
        self._width = max(self._width, len(line))
        self._stream.write(f"\r{line.ljust(self._width)}")
        self._stream.flush()
