# Proposal

## Why

Phase 1 gave videos scan, grouping, posters, and a still in the served browser — but opening a video still shows a frozen frame with no way to watch it. Playback is the remaining gap between videos being listed and videos being usable.

## What Changes

- In `--serve` mode, opening a video in the group browser plays it with native browser controls (`<video controls>`), using the poster still as the pre-playback frame.
- A new `/video` endpoint serves the original file with HTTP Range support (single ranges; `Accept-Ranges: bytes`), under the same guarantees as `/render`: random token, loopback host, cross-origin refusal, index-resolved references.
- MIME type follows the container (`.mp4` → `video/mp4`, `.mov` → `video/quicktime`, `.3gp` → `video/3gpp`).
- Arrow keys keep moving between items (confirmed); seeking happens through the native video controls. No autoplay: playback starts on user action.
- Out of scope: transcoding, adaptive streaming, multi-range requests (refused; browsers fall back to single ranges), video blobs in the static export (still forbidden).

## Capabilities

### New Capabilities
None

### Modified Capabilities
- `photo-viewing`: The served browser plays videos via a ranged `/video` endpoint instead of showing a still without playback. The still-without-playback requirement becomes playback with native controls; export and `/render` behavior are unchanged.

## Impact

- `fotos_plus/server.py`: New `/video` endpoint with single-range partial responses; MIME mapping.
- `fotos_plus/viewer.py`: `<video>` element in the browser overlay toggled by item kind; `mostrar()` picks `/video` vs `/render` vs `/poster` (poster as pre-playback frame).
- `tests/test_server.py`, `tests/test_viewer.py`: Range semantics (200/206/416), guards parity with `/render`, JS source assertions, export still blob-free.
- No scan, grouping, mark, or bucket changes.
