# Design

## Context

See `proposal.md` for the motivation. The current viewer builds marked and bucket sections in
`photo_sections()` and renders them through the flat-photo branch of `_section_html()`. That
branch embeds up to `PHOTOS_PER_SECTION` loose photo cards per set. Group cards already have the
presentation we want: title, count, optional date range, up to five thumbnails, and a served
"Ver fotos" action.

The browser endpoint (`GET /api/photos?group=...`) currently resolves only real group keys.
`server.group_for()` builds that map from `assign_groups()`. The export uses the same renderer with
no token, so it has no browse controls.

The viewer resolves photo files against the library folder recorded in the index. The paired
suggestions file records the same library folder and is generated with it, so it is available even
when the index's own copy is unusable.

Constraints:

- The edition file format and the marks/buckets storage rules do not change.
- The viewer remains one self-contained HTML document with inline CSS/JS.
- Group cards and photo cards must remain independent axes.
- The exported HTML remains read-only.

## Goals / Non-Goals

**Goals:**

- Render one card for the marked set and one card for each non-empty bucket.
- Reuse the group-card shell, thumbnail rules, count, and date-range presentation.
- Keep the served viewer able to open the full set from a photo card.
- Keep previews working when the index's own folder is unavailable, and never present a photo-set card as though its photos belonged to another group.
- Preserve group-card counts, titles, tags, and drag behavior.
- Keep the exported HTML read-only and consistent with group cards.

**Non-Goals:**

- Change how marks or bucket membership are stored.
- Change group assignment, group labels, or group tags.
- Make photo cards editable or draggable.
- Add a new export-only browser or an expandable full grid.
- Change video thumbnail or playback behavior.
- Rewrite the index or rescan the library; resolving the library folder is read-only.

## Decisions

### 1. Use one card descriptor for photo sets

Build a small photo-set view model with the fields the card renderer needs: `title`, `kind`,
`photos`, `first_captured_at`, `last_captured_at`, and a synthetic `browse_key`. The existing
`Group` shape is close, so the implementation can either reuse it with a `collection_key` field or
introduce a sibling dataclass that the card renderer accepts.

Photo cards carry:

- title `"Marcadas"` for the marked set and the bucket name for a bucket;
- count `len(photos)`;
- earliest and latest capture date among the set, omitted when no date is known;
- no country;
- no group key, label editor, or tag editor.

The count comes from the photos actually in the set, not from any suggestion metadata.

Alternative considered: build one card per original trip/period containing marked or bucketed
photos. Rejected because it would duplicate group cards and lose the "Marcadas" / bucket identity
the user wants.

### 2. Build photo cards in the viewer layer and reuse the card renderer

Add a function such as `photo_cards(photos, marked, photo_tags, photo_tagged)` that returns the
cards in display order:

1. the marked card, if any;
2. one card per bucket in catalogue order, skipping empty buckets.

`render_html()` builds the group cards/sections as today, then renders the photo cards in one grid
after them. The cards are not added to `groups`, so group section counts and tag ordering are
unaffected.

The card body reuses `_group_card()` and `_group_thumbs()`: same five-thumbnail limit, same EXIF
orientation handling, same video poster/duration handling. Photo cards get a `photo-card` class so
the page can style and identify them without giving them group semantics.

Alternative considered: keep a section heading for each photo set and put one card under it.
Rejected because the card title would repeat the heading and the result would still look unlike a
normal card grid.

### 3. Use reserved browse keys and resolve them on the server

Use stable synthetic keys:

- `marcadas` for the marked set;
- `cubo:<bucket-name>` for a bucket.

Real group keys are timestamps, so these names cannot collide with a group. Bucket names are sent
through `encodeURIComponent`, so punctuation and spaces are safe in the query string.

`viewer.photo_cards()` is the single source for both the page and the server. The server caches the
photo cards next to the groups in `resolve()` and includes them in the lookup used by
`group_for()`. `GET /api/photos` then returns the same JSON shape for a photo card as for a group:
title, browse key, and the ordered photo list.

Alternative considered: embed every photo set in `viewer-data` and open the grid client-side.
Rejected because it would grow the page and duplicate the existing server-side collection logic.

Sequence for opening a bucket card:

```text
User clicks "Ver fotos" on the "Tucu" card
    |
    v
Browser requests /api/photos?group=cubo%3ATucu
    |
    v
server.group_for("cubo:Tucu")
    |
    +-- group map? no
    +-- photo-card map? yes -> "Tucu" card with its photos
    |
    v
JSON { title: "Tucu", browse_key: "cubo:Tucu", photos: [...] }
    |
    v
Existing grid renders the photos in browse order
    |
    v
Selecting a cell opens the existing photo browser at that photo
```

### 4. Limit drag behavior to real group cards

The current JS makes every `.card` draggable and a drop target. Photo cards must not participate:
a bucket names photos, not groups, and a mark is not a bucket. The selector changes to only group
cards (for example, `.card[data-key]`), because photo cards intentionally have no group key.

The photo-card grid keeps the existing rejection container/behavior for a group card dragged onto
it: the viewer reports that photo cards do not accept a dragged card and stores nothing.

Alternative considered: add a separate `data-photo-card` flag and skip those cards in JS. Rejected
as an extra state when the presence of a real `data-key` already distinguishes the two card kinds.

### 5. Render the same cards in the export, without browsing

The exported HTML uses the same photo-card markup. Because there is no token, it offers no
"Ver fotos" control, exactly as group cards do. The old flat-photo rendering path and
`PHOTOS_PER_SECTION` bound are removed; the card preview itself is capped at five thumbnails.

This is a deliberate trade-off: the export shows at most five previews per photo set instead of
embedding up to 300 loose photos. The served viewer remains the place to inspect every photo. A
future change can add an expandable export grid if offline access to every photo becomes a
requirement.

### 6. Preserve order and empty-set behavior

Group cards and group sections come first. The photo-card grid follows them, with the marked card
first and bucket cards in catalogue order. A set with no photos produces no card. A photo that
belongs to several buckets appears in each bucket card, and a marked photo appears in the marked
card as well as its group card.

### 7. Resolve the library folder once and reuse it

Resolve the folder as the index folder when it is a directory, otherwise the suggestions folder
when it is a directory. `build_view()` and the server use that resolved folder for cards, renders,
thumbs, posters, and videos, so the page and the media endpoints can never disagree about where the
photos are. When neither is a directory, report a viewer error naming the missing folder instead of
generating a page whose previews silently disappear.

Alternative considered: rewriting the index with the suggestions folder. Rejected because the
viewer must not write scan outputs. Alternative considered: requiring a rescan. Rejected because
the paired suggestions file already carries a usable folder, so the viewer can recover read-only.

### 8. Give photo-set cards their own empty state and the grid a placeholder

The existing "Sin fotos propias: caen en otro grupo." note is only valid for a declared group card:
it explains a group whose photos were assigned to a trip that overrides it. A photo-set card has no
such relationship, so an empty thumbnail row there must say that the previews could not be
produced while keeping the real count. The empty state therefore depends on `collection_key`:
group cards keep the note, photo-set cards get their own message.

The served grid attaches an `error` handler to photo cells too, replacing a broken image with a
placeholder the way video cells already fall back to their duration tile. Selecting the cell still
opens the browser, which reports its own failure when the full render cannot be produced.

Alternative considered: reusing the group note for photo cards. Rejected because it states
something false about where the photos are.

## Risks / Trade-offs

- **Export loses full-set visibility** -> The card is bounded to five thumbnails by design. This
  is documented in the proposal; a separate change can add an expandable export if needed.
- **Synthetic key collisions** -> `marcadas` and `cubo:` are reserved and cannot match timestamp
  group keys. Add tests for a bucket name containing spaces or punctuation.
- **Drag regression** -> Restrict drag setup to cards with a real group key and test that photo
  cards neither start a drag nor accept a drop.
- **Wrong count or date range** -> Compute both from the actual photo set, not from bucket
  metadata, and include photos with no capture date.
- **Photo cards mistaken for groups** -> Give them no group key, no country, no label/tag editor,
  and no draggable behavior.
- **Unavailable or wrong library folder** -> Fall back to the paired suggestions folder and report
  when neither exists; never rewrite the index.
- **Photo-set cards misread as empty group cards** -> A kind-aware empty state keeps the real count
  and avoids the group-only note, covered by tests.

## Migration Plan

No data migration is required. The edition file format is unchanged, and marks/bucket assignments
continue to load as before. Deployment is the normal feature-branch change: update viewer and
server code, update tests and README, run the full pytest suite, validate OpenSpec, archive on the
feature branch, and open a pull request. Rollback is a revert of the change commit; existing marks
and buckets remain intact.

The viewer resolves the library folder read-only: an index folder that is not available falls back
to the paired suggestions folder, and when neither is available the viewer reports it. No index,
suggestions, or edition file is rewritten by this resolution.
