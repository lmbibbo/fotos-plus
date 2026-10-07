# Tasks

## 1. Model and index version
- [x] 1.1 Add `kind` (default `"photo"`) and `duration_s` (default `None`) to `Photo` in `fotos_plus/models.py`, with backwards-compatible `to_dict`/`from_dict`
- [x] 1.2 Bump `INDEX_VERSION` 1 → 2 with a rescan-required path for old indexes
- [x] 1.3 Unit tests for serialization defaults and the version gate

## 2. Container metadata reader
- [x] 2.1 New box parser for `mvhd`/`mdhd` creation_time (capture date) and timescale duration
- [x] 2.2 Best-effort GPS extraction; `None` position when atoms are absent
- [x] 2.3 Wire the video branch into `identify()` in `fotos_plus/photos.py`; corrupt containers raise `PhotoError`
- [x] 2.4 Scan tests per extension (`.mp4`, `.mov`, `.3gp`), missing date, corrupt file, error entry without stopping

## 3. Grouping parity
- [x] 3.1 Tests proving dated/positioned videos land in the same trip and period suggestions as same-place photos (no `grouping.py` logic change expected)
- [x] 3.2 Tests for undated-video handling matching dateless photos

## 4. Posters and viewer
- [x] 4.1 `make_poster()` via optional system `ffmpeg` with once-per-run detection; generic duration tile fallback
- [x] 4.2 Cards and photo sections render posters/tiles for videos, including the export
- [x] 4.3 Served browser shows the poster still with duration mark and no playback; `/render` refuses video references with a reason
- [x] 4.4 Viewer and server tests, mocking the `ffmpeg` call

## 5. Docs and verify
- [x] 5.1 Update `README.md` (accepted formats, ffmpeg-optional posters, no playback in this phase)
- [x] 5.2 Full `pytest` run and `openspec validate --all --strict`
