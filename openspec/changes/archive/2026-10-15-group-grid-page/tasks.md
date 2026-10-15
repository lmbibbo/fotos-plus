# Tasks

## 1. Grid section
- [x] 1.1 Add a hidden grid container plus a back-to-cards control to the served landing page; give the cells their own dense thumb-scale grid CSS (natural aspect, shrunken duration-tile min-height)
- [x] 1.2 Render one lazy cell per group item in browse order: `/thumb` URLs for photos, `/poster` URLs for videos (query token), duration tile where no poster exists

## 2. `/thumb` endpoint
- [x] 2.1 Add `cached_thumb` to `photos.py`, keyed by content hash like `cached_render`/`cached_poster`
- [x] 2.2 Serve `/thumb` from `server.py` with the same token, loopback-host, and index-resolution guards as `/render`; refuse video references with a reason

## 3. Click-through to the browser
- [x] 3.1 Extend `abrir(clave)` with an optional start index defaulting to 0
- [x] 3.2 "Ver fotos" swaps the cards for the grid; cell clicks open the existing browser at the clicked index; closing returns to the grid; arrows, marks, buckets unchanged

## 4. Tests
- [x] 4.1 Viewer tests: cell count and order, thumb URL shapes, duration tiles, start-index opening, click-through index, close-to-grid, back-to-cards, export untouched
- [x] 4.2 Server tests: `/thumb` guards (token, loopback host), index refusal, video refusal, lazy cache reuse

## 5. Docs and verify
- [x] 5.1 Update `README.md` browse flow (grid view between button and browser)
- [x] 5.2 Full `pytest` run and `openspec validate --all --strict`
