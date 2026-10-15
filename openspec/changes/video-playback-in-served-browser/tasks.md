# Tasks

## 1. `/video` endpoint with ranges
- [x] 1.1 Add `_serve_video` in `fotos_plus/server.py` with token, cross-origin, and index-resolution guards mirroring `/render`, plus a kind check refusing non-videos
- [x] 1.2 Single-range parsing (`bytes=<start>-<end?>`, suffix ranges); 200 full with `Accept-Ranges`, 206 slice with `Content-Range`, 416 past EOF, multi-range refused
- [x] 1.3 MIME mapping per container (mp4/quicktime/3gpp); stream file in chunks off `wfile`
- [x] 1.4 Route `/video` in `do_GET`

## 2. Browser playback
- [x] 2.1 Add `<video controls>` to `_browser_overlay`, sharing bar, mark, and bucket controls
- [x] 2.2 Branch `mostrar()` on `foto.kind`: video sets `src`/`poster` and hides `<img>`; pause and clear on navigation/close; photos unchanged
- [x] 2.3 Keep arrow-key navigation untouched (no seek on arrows)

## 3. Tests
- [x] 3.1 Server tests: 200/206/416 matrix, guard parity, MIME per extension, non-video refusal
- [x] 3.2 Viewer tests: `<video>` element with controls and poster wiring, kind branch in `EDIT_SCRIPT`, export has no `<video>`

## 4. Docs and verify
- [x] 4.1 Update `README.md` limitations (playback exists in serve mode; no transcoding; ranges required for seeking)
- [x] 4.2 Full `pytest` run and `openspec validate --all --strict`
