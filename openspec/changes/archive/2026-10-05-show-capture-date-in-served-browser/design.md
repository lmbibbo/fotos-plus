# Design

## Context

See `proposal.md` for motivation.

The state that shapes this approach:

- A group is a trip or a period, never a single day. `assign_groups` in
  `fotos_plus/viewer.py` puts each photo in the trip or period whose date interval
  contains it, so a group spans as many days as the trip did.
- `Photo.captured_at` is an optional ISO timestamp string, read from EXIF at scan
  time (`exif-datetime-original` or `exif-datetime`). There is no filesystem or
  filename fallback, so a present date always came from the file itself.
- The served page is a full-screen browser that displays **one photo at a time**.
  `mostrar(indiceNuevo)` is the only function that writes the position element, and
  it already assigns `posicion.textContent = (indice + 1) + " de " + lista.length`.
- The initial HTML payload for a group card deliberately carries no per-photo data.
  Its docstring states that loose photos are not included and are requested per
  group, because the previous design inlined every thumbnail and produced a 544 MB
  document. That decision must not be undone here.
- `_group_thumbs` returns a list of bare base64 strings and discards the `Photo`
  objects, so the static export has no per-photo data available without changing
  that function's return type.
- The document declares `<meta charset="utf-8">` and the card meta line joins its
  items with U+00B7 MIDDLE DOT (`viewer.py:414`), which is the established separator
  in this viewer's visual language.

## Goals / Non-Goals

**Goals:**

- Show the capture date of the photo currently on screen in the served browser.
- Leave the request count, the document size, and the initial payload untouched.
- Keep the served photo list the single source of per-photo metadata for the client.

**Non-Goals:**

- Per-photo place. The only granularity available is country, resolved through a
  9.8 MB polygon dataset in `fotos_plus/places.py`; showing it per photo would need
  either that dataset in the serve path or a change to the index format. See
  `proposal.md`.
- Any change to the static HTML export, to `_group_thumbs`, or to `_photo_card`.
- Distinguishing `exif-datetime-original` from `exif-datetime` in the UI.
- Showing the time of day. The stored value carries it; the display does not use it.

## Decisions

**D1 - Extend the existing position line instead of adding an element.**

The position element already exists, already carries per-photo context, and is
written in exactly one place. Appending the date to it needs no new markup and no
new stylesheet rule, which matters in a viewer that emits one inline document.

The result reads `3 de 12 · 2024-03-14`, reusing the U+00B7 separator that already
joins the card meta items, so the separator is consistent across the document.

Alternative considered: a sibling `<span class="fecha">` next to the position.
Rejected — it adds markup, a CSS rule, and a second thing to keep in sync on every
navigation, for no observable gain.

**D2 - Pass `captured_at` through the existing `/api/photos` response.**

The server holds the `Photo` objects and the client holds nothing. The per-group
request already returns `ref`, `sha256`, and `marked` for every photo; adding
`captured_at` is one key in that dict.

Alternative considered: embed a per-photo date map in the initial HTML payload, so
the client would need no extra data. Rejected — that payload was deliberately kept
free of per-photo entries, and widening it works against the decision that removed
the 544 MB document.

**D3 - Send the raw timestamp and truncate in the client.**

The server sends `photo.captured_at` unchanged and `mostrar()` slices the first ten
characters for display. This matches the existing convention of truncating ISO
strings for presentation (`group.first_captured_at[:10]` on the card), and it keeps
the full precision in the payload so a later change could show the time or a fuller
tooltip without another server round.

Alternative considered: send a pre-sliced `YYYY-MM-DD`. Rejected — it bakes
presentation into the API and forecloses showing more precision later.

**D4 - Omit the date when the photo has none.**

`captured_at` is optional. When it is absent the position line is assigned exactly
as it is today, so an undated photo degrades to current behavior with no placeholder
and no layout shift.

Alternative considered: render "sin fecha". Rejected as noise on a line whose job
is position.

**D5 - Pass the whole optional value, never a substitute.**

The key is present in the payload for every photo, with a null value when the date
is unknown, rather than being omitted. Keeping the key stable means the client
reads one property unconditionally.

## Flow

The only path that changes is the one that fills the position line.

```
user        browser JS            server (ThreadingHTTPServer)
  |              |                        |
  | click card   |                        |
  |------------->|                        |
  |              | GET /api/photos?group= |
  |              |------------------------>|
  |              |                         | group = group_for(key)
  |              |                         | sorted(group.photos, _photo_sort_key)
  |              |                         | per photo: ref, sha256, marked,
  |              |                         |           captured_at   <-- added
  |              |<------------------------| 200 JSON
  |              |                         |
  |              | lista = datos.photos    |
  |              | mostrar(0)              |
  |              |   posicion.textContent  |
  |              |     = "1 de 12 · 2024-03-14"
  |              |   GET /render?ref=...   (unchanged)
  |<-------------|  photo on screen
```

`mostrar()` remains the single writer of the position line, so the date cannot go
stale relative to the photo: every navigation, pointer, or keyboard step re-enters
it and reassigns the whole string.

## Risks / Trade-offs

- **Payload grows by one ISO timestamp per photo** → the value is roughly 25
  characters, so a 500-photo group adds about 12 KB of JSON to a response that is
  already requested deliberately and lazily. Sending a pre-sliced date would halve
  that; D3 chose flexibility over the bytes, and the trade is acceptable at this
  size.
- **The date shown can still be wrong for scanned film** → `exif-datetime` records
  digitization, so a scan of 1985 negatives carries today's date. This is a property
  of the index, not of the viewer, and the viewer now surfaces it more visibly.
  Accepted: showing nothing would be worse, and correcting EXIF provenance is out
  of scope.
- **The exact-equality assertion on the served photo list in `tests/test_server.py`
  fails** → intended. It is a canary that the payload shape moved, and it is updated
  in the same change.
- **Client-side truncation trusts the stored format** → if `captured_at` were ever
  stored in another format, the slice would misbehave. Every existing display of
  these timestamps already slices the same way, so this introduces no new assumption.

## Migration Plan

None. The change adds a response field and modifies one assignment. No stored data
is written, no index needs rebuilding, and no rescan is required: existing indexes
already carry `captured_at`.

Rollback is a revert of the two code edits, the payload assertion, and the new
tests. The old client ignores the added field, so a server rollback during a deploy
window is safe in both directions.

## Open Questions

None. The remaining choices — served mode only, ISO form, omission over placeholder
— are settled in the specs, and none of them can be reopened without changing the
requirements.
