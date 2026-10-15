# Proposal

## Why

The "Ver fotos" button jumps straight into the full-screen browser at the first item, so reaching a specific photo in a large group means stepping through everything before it. An intermediate grid showing every item with a thumb lets the user pick the starting point directly.

## What Changes

- In `--serve` mode, the "Ver fotos" button opens a grid page listing every photo and video of that group, each with a thumb at the same scale as the thumbnails on the group cards — a dense contact sheet (photos from a new `/thumb` endpoint, posters for videos, duration tiles where no decoder exists).
- Selecting an element opens the existing full-screen browser at that item (not at the first one); the browser itself is otherwise unchanged.
- The grid is served-mode only: the button only exists on served pages, and full-group thumbs are fetched per item over authenticated endpoints rather than embedded, so the landing page and the static export are untouched.
- Assumption recorded: thumbs load lazily (`loading="lazy"`) so thousand-item groups don't stampede the server on open.
- Risk recorded: the `video-playback-in-served-browser` change is implemented but not yet archived/synced, so the main spec still describes still-without-playback. This delta is written against the current main-spec text; archive the playback change first, then refresh this delta if its browser requirement touched the same block.

## Capabilities

### New Capabilities
None

### Modified Capabilities
- `photo-viewing`: The group browser gains a thumbnail grid step — "Ver fotos" opens a per-group grid page, and selecting an element opens the existing browser at that item.

## Impact

- `fotos_plus/server.py`: New `/thumb` media route (token, loopback, and index-resolution guards like `/render`); no new page route — the grid is inline in the landing page.
- `fotos_plus/photos.py`: `cached_thumb`, the content-hash thumbnail cache behind `/thumb`, alongside `cached_render`/`cached_poster`.
- `fotos_plus/viewer.py`: Dense grid markup + client script (fetch `/api/photos`, per-item thumbs via `/thumb`/`/poster` URLs with query token, click-through opening the browser at the clicked index).
- `tests/test_server.py`, `tests/test_viewer.py`: `/thumb` guards and cache reuse, grid content and thumb URL shapes, click-through index, export untouched.
- No scan, grouping, mark, bucket, or export changes.
