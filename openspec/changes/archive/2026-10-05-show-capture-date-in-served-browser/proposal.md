# Proposal

## Why

In `--serve` mode the full-screen browser tells the user which photo of a group is
displayed ("3 de 12") but never when that photo was taken. Because a group is a trip
or a period rather than a single day, the date range printed on the group card does
not answer that question: a twenty-day trip shows one range and twenty photos with no
way to tell which day each belongs to.

The data is already available. `Photo.captured_at` is stored in the scanned index and
travels all the way into the group the viewer builds; it is dropped at the boundary
where the served photo list is assembled. This change closes that gap for the surface
where a single photo is on screen and the answer is unambiguous.

## What Changes

- The `/api/photos` endpoint serves `captured_at` for every photo in the requested
  group, alongside the `ref`, `sha256`, and `marked` fields it already returns.
- The served browser appends the capture date of the displayed photo to the position
  line, in the ISO `YYYY-MM-DD` form already used for group date ranges.
- A photo with no capture date leaves the position line exactly as it is today; the
  date is omitted rather than replaced by a placeholder.
- The static HTML export is unchanged. Its five-thumbnail strip repeats a sample of the
  group's earliest photos and the card header already carries the full range, so
  per-thumbnail dates would restate information the card already shows.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `photo-viewing`: the requirement "Browsing the photos of a group in the served
  viewer" gains the capture date of the displayed photo. That requirement already
  governs the position line ("SHALL show which photo of the group is currently
  displayed and how many the group holds"), so this extends existing behavior rather
  than introducing a separate one.

## Impact

**Code**

- `fotos_plus/server.py`: the per-photo dict built for `/api/photos` gains a
  `captured_at` key, passed through from the `Photo` object.
- `fotos_plus/viewer.py`: the inline JS in `mostrar()` extends the text assigned to
  the position element. No new element, no new stylesheet rule, no JS file — the
  viewer emits one self-contained document.

**Tests**

- `tests/test_server.py`: the assertion comparing a served photo list with an exact
  dict gains the new key; a new test covers a photo with and without a capture date.
- `tests/test_viewer.py`: coverage for the position line and for the undated case.

**Not affected**

- The scanned index format is unchanged, so existing indexes keep working and no
  rescan is required.
- No dependency is added. The country dataset and `places.py` are not involved: place
  is deliberately out of scope.
- The static export, `_group_thumbs`, and `_photo_card` are untouched.
- No behavior change for keyboards, marks, or navigation.

**Rollback plan**

The change is additive and confined to one response field and one text assignment.
Reverting the two code edits restores the current behavior exactly; the added
`captured_at` key is ignored by the previous JS. Because the payload gains a key,
the exact-equality assertion in `tests/test_server.py` must be reverted with it, and
the two new tests removed. No stored data is written by this change, so there is
nothing to migrate back and no index to rebuild.
