# Design

## Grid: inline section in the landing page, one new media endpoint

A separate `/group` page cannot reuse the existing browser without duplicating the
overlay, the viewer script, and the mark/bucket wiring into a second secured page, so
the grid lives inline in the landing page instead. The "Ver fotos" button flow becomes:
fetch the item list from `/api/photos` (as `abrir` already does), render one cell per
item into a grid container in browse order, hide the cards view, show the grid. Selecting
a cell opens the existing full-screen overlay at that index. Closing the overlay returns
to the grid; a small "back" control on the grid returns to the group cards.

## Dense thumb-scale cells

Cells show a thumb at the same scale as the thumbnails on the group cards (about 55 px
wide): the cells container uses its own `repeat(auto-fill, minmax(56px, 1fr))` with an
8 px gap instead of the cards' 320 px columns, so a whole group reads as a contact
sheet — roughly 21 cells per row on a desktop width — instead of a page of large
images. Thumbs keep their natural aspect (`height: auto`), like every other thumb in
the viewer; no cropping. The duration tile for no-poster videos shrinks its `min-height`
so it stays inside the small cells.

## `/thumb`: the grid's photo endpoint

At this display size the `/render` payload (2000 px, up to about 450 KB) is roughly 30x
what a cell needs, and one screen of dense lazy cells would still pull tens of
megabytes. Cells therefore load photos from a new `/thumb?ref=...&token=...` endpoint
mirroring `/poster`: the same random token as a query parameter (labels cannot set
headers), the same loopback host check, and the same index resolution — a caller-supplied
reference is never used directly to read a filesystem path. It reuses `make_thumbnail`
(200 px, quality 70), the same bytes the export embeds, and stores results through a new
`cached_thumb`, keyed by content hash like `cached_render`/`cached_poster` and equally
disposable. Video cells keep `/poster`, which already produces thumbnail-scale frames.
`loading="lazy"` stays; a full grid of thumbs weighs a couple of megabytes at worst.

The static export is untouched — the "Ver fotos" button only exists on served pages.

## Tests

Viewer tests: grid renders one cell per item in browse order, photo cells use `/thumb`
URLs and video cells `/poster` URLs (query token), no-poster videos get duration tiles,
`abrir` accepts a start index, clicking a cell opens the browser at that index, closing
returns to the grid, back control returns to the cards, export unchanged.
Server tests: `/thumb` refuses requests without the valid token and from non-loopback
hosts, refuses references the index does not contain and video references; the first
request produces and stores a thumb, the second reuses the stored one. `/api/photos`,
`/render`, and `/poster` behavior is already covered.
