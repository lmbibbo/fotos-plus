# Design

## Metadata reader: hand-rolled box parser, zero new dependencies

`identify()` in `fotos_plus/photos.py` gains a video branch keyed on extension
(`.mp4`, `.mov`, `.3gp`). Pillow cannot open these, so a small new module parses ISO
base-media boxes directly: walk top-level boxes, read `mvhd`/`mdhd` creation_time
(seconds since 1904-01-01, UTC) for the capture date, `tkhd`/`mdhd` timescale math for
duration, and `©xyz`/ timed-metadata GPS atoms on a best-effort basis. Assume UTC when
the container carries no zone, matching how dateless-zone photo dates are stored today.

Unreadable or truncated containers raise `PhotoError` like unreadable images, so the
scanner records a `ScanError` and continues. Videos with no date or no GPS flow into the
existing `None` paths — no new grouping logic.

Assumption recorded: hand-rolled parsing over a new pip dependency, keeping the
single-dependency (`Pillow`) install story. GPS atoms vary most between Android and
iPhone files; date and duration are the reliable fields, GPS is best-effort.

## Model: kind, duration, index version bump

`Photo` in `fotos_plus/models.py` gains `kind: str = "photo"` and
`duration_s: Optional[float] = None`, serialized in `to_dict`/`from_dict` with
backwards-compatible defaults (missing `kind` reads as `"photo"`). `INDEX_VERSION`
bumps 1 → 2; old index files are rejected with the existing version-mismatch path and
require a rescan rather than a migration, since a rescan is cheap and total.

## Posters: optional ffmpeg with a generic fallback

New `make_poster(path)` beside `make_thumbnail`: shell out to a system `ffmpeg`
(`-ss` early in the file, single JPEG frame, scaled like thumbnails). No new pip
dependency. When `ffmpeg` is missing or fails, cards and sections render a generic
duration tile (inline SVG/CSS badge with `MM:SS`) so the layout never breaks. Detection
happens once per `view` run, not per video. Posters are embedded as base64 JPEG data
URIs through the existing thumbnail pipeline, so the 300-photo section bound and the
export's self-contained property hold unchanged.

`_read_metadata`/`make_thumbnail`/`make_render` keep rejecting non-image input as today;
`make_render` and `/render` stay photo-only in this phase.

## Grouping, marks, buckets: no logic changes

`scanner.py` (hash, duplicates, progress) and `grouping.py` (trips/periods from
`captured_at` + `has_position`) consume the unified `Photo` fields and need no logic
changes — videos are just dated/positioned items. Marks, buckets, labels, and the
payload inventory key on `sha256` and work unchanged. The served browser shows the
poster still with a duration mark and no `<video>` element; playback, Range-request
serving, and transcoding are explicitly phase 2.

## Test strategy

Fixture videos must be tiny synthetic containers committed or generated at test time
(hand-built minimal `ftyp`+`mvhd` boxes suffice for metadata tests; poster tests mock
the `ffmpeg` call). Cover: each accepted extension, missing-date container, corrupt
container error path, grouping parity (video lands in the same trip as same-place
photos), card poster vs. fallback tile, browser still without playback, `/render`
refusal for videos, export with posters and no blobs.
