# Design

## Endpoint: `/video` with single-range support

New handler `_serve_video` in `fotos_plus/server.py`, mirroring `_serve_render` and
`_serve_poster`: token check, cross-origin refusal (loopback is enforced once in
`do_GET` for all routes), index-resolved reference via `photo_for`, kind check
(non-videos refused with a reason). MIME from extension:
`.mp4` → `video/mp4`, `.mov` → `video/quicktime`, `.3gp` → `video/3gpp`, defaulting to
`video/mp4` for anything else the scanner may accept later.

Range parsing: accept `Range: bytes=<start>-<end?>` with optional end and suffix ranges
(`bytes=-N`); clamp satisfiable ranges, answer 206 with `Content-Range` and
`Accept-Ranges: bytes`; answer 416 with `Content-Range: bytes */<size>` past EOF.
Multi-range headers are refused (416 or 400 — decision: 400 with a reason, since the
browser falls back to single ranges). Full responses (no Range) answer 200 with
`Accept-Ranges: bytes` and stream the file in chunks rather than loading multi-GB
originals into memory — use `shutil.copyfileobj` over `wfile` with a 1 MB chunk size.

Assumption recorded: serve originals, no transcoding; loopback bandwidth makes this
free, and the export stays blob-free.

## Browser: `<video>` toggled by kind

`_browser_overlay` gains a `<video controls>` element beside the `<img>`, sharing the
position/status bar, mark button, and bucket controls. `mostrar()` branches on
`foto.kind`: photos keep the `/render` → blob → `<img>` path; videos set
`video.src = "/video?ref=...&token=..."` with `video.poster = "/poster?ref=...&token=..."`,
hide the img, and pause + clear `src` on navigation/close (mirroring `soltarImagen`).
Duration mark logic is unchanged. No autoplay attribute; arrow-key handling is untouched so arrows
keep navigating (confirmed decision).

Media tags cannot set request headers, so the token travels as a `token` query parameter
on `/video` and `/poster` URLs (confirmed decision). Both endpoints accept the header
token or the query token; loopback, cross-origin refusal, and unpredictability are
unchanged, and subresource URLs never land in browser history.

## Tests

Server tests reuse the synthetic-container fixtures: 200/206/416 matrix, guards parity
(token/host/origin/unknown ref), MIME per extension, non-video refusal. Viewer tests
assert the `<video>` element, `controls` attribute, poster wiring, and kind branch in
`EDIT_SCRIPT`; export test gains a no-`<video>` assertion. No scan, grouping, mark, or
bucket changes, so those suites are untouched except where payloads changed (none —
`/api/photos` already carries `kind`/`duration_s`).
