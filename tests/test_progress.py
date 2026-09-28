from __future__ import annotations

import io
from pathlib import Path

from fotos_plus import progress
from fotos_plus.progress import (
    ProgressReporter,
    format_duration,
    format_progress,
    progress_enabled,
)
from tests.conftest import make_image


class FakeTTY(io.StringIO):
    def isatty(self) -> bool:
        return True


def test_format_progress_with_known_values() -> None:
    line = format_progress(1200, 4927, 18.3, 202.0)

    assert line == "Escaneando... 1200/4927 (24%) - 18.3 fotos/s - faltan 3m 22s"


def test_format_progress_without_rate_or_remaining() -> None:
    line = format_progress(1, 100, None, None)

    assert "0.0" not in line
    assert line.endswith("-- fotos/s - faltan ?")


def test_format_progress_at_the_end_shows_100_percent() -> None:
    assert "(100%)" in format_progress(50, 50, 5.0, None)


def test_format_duration() -> None:
    assert format_duration(None) == "--"
    assert format_duration(45) == "45s"
    assert format_duration(202) == "3m 22s"
    assert format_duration(3725) == "1h 02m"


def test_progress_enabled_only_for_tty() -> None:
    assert progress_enabled(FakeTTY())
    assert not progress_enabled(io.StringIO())


def test_progress_disabled_by_environment(monkeypatch) -> None:
    monkeypatch.setenv("FOTOS_PLUS_NO_PROGRESS", "1")

    assert not progress_enabled(FakeTTY())


def test_reporter_writes_a_single_line_with_carriage_returns() -> None:
    stream = FakeTTY()
    reporter = ProgressReporter(stream)

    for processed in range(1, 121):
        reporter(processed, 120)
    reporter.finish()

    written = stream.getvalue()
    assert written
    assert written.count("\n") == 1
    assert written.endswith("\n")
    assert written[:-1].count("\n") == 0
    assert "100%)" in written
    assert all(
        line == "" or line.startswith("Escaneando...")
        for line in written.splitlines()
    )


def test_reporter_emits_a_final_complete_line() -> None:
    stream = FakeTTY()
    reporter = ProgressReporter(stream)

    for processed in range(1, 8):
        reporter(processed, 200)
    reporter.finish()

    written = stream.getvalue()
    assert written.rstrip("\n").split("\r")[-1].startswith(
        "Escaneando... 200/200 (100%)"
    )


def test_shorter_line_is_padded_to_erase_the_previous_one(monkeypatch) -> None:
    reloj = [1000.0]
    monkeypatch.setattr(progress.time, "monotonic", lambda: reloj[0])
    stream = FakeTTY()
    reporter = ProgressReporter(stream)

    reporter(900, 1000)
    reloj[0] += 1.0
    reporter(1, 1000)
    reloj[0] += 1.0
    reporter(1000, 1000)

    segments = stream.getvalue().split("\r")
    primera, segunda = segments[1], segments[2]
    assert len(segunda.rstrip()) < len(primera)
    assert len(segunda) == len(primera)
    assert segunda.startswith("Escaneando... 1/1000")
    assert set(segunda[len(segunda.rstrip()) :]) == {" "}


def test_written_lines_never_shrink(monkeypatch) -> None:
    reloj = [1000.0]
    monkeypatch.setattr(progress.time, "monotonic", lambda: reloj[0])
    stream = FakeTTY()
    reporter = ProgressReporter(stream)

    for processed in range(1, 60):
        reloj[0] += 0.6
        reporter(processed, 1000)

    anchos = [len(segmento) for segmento in stream.getvalue().split("\r") if segmento]
    assert anchos == sorted(anchos)


def test_reporter_ignores_zero_total() -> None:
    stream = FakeTTY()
    reporter = ProgressReporter(stream)

    reporter(0, 0)
    reporter.finish()

    assert stream.getvalue() == ""


def test_reporter_shows_first_update_then_throttles() -> None:
    stream = FakeTTY()
    reporter = ProgressReporter(stream)

    for processed in range(1, 6):
        reporter(processed, 1000)

    written = stream.getvalue()
    assert written.count("\r") == 1
    assert written.startswith("\rEscaneando... 1/1000 (0%)")
    assert "-- fotos/s" in written


def test_reporter_prints_every_25_photos() -> None:
    stream = FakeTTY()
    reporter = ProgressReporter(stream)

    for processed in range(1, 60):
        reporter(processed, 1000)

    written = stream.getvalue()
    assert written.count("\r") == 3
    assert "1/1000" in written
    assert "26/1000" in written
    assert "51/1000" in written


def test_scan_reports_progress_over_more_than_25_photos(tmp_path: Path) -> None:
    from fotos_plus.scanner import scan

    for number in range(30):
        make_image(tmp_path / f"foto-{number:03d}.jpg", color="red")
    stream = FakeTTY()
    reporter = ProgressReporter(stream)

    scan(tmp_path, progress=reporter)
    reporter.finish()

    written = stream.getvalue()
    assert written.count("\r") >= 1
    assert "30/30 (100%)" in written
