# Proposal

## Why

Marked photos and bucketed photos are the only home items rendered as loose photo grids. Every trip, period, and unclassified group uses a card with a title, count, preview, and browsing action. That mismatch makes the marked and bucket sections look like raw search results instead of curated sets.

## What Changes

- Replace each flat photo section with one card:
  - a single "Marcadas" card when at least one photo is marked;
  - one card per bucket that holds at least one photo.
- Each card shows the set name, the number of photos, an optional date range, and up to five thumbnails, matching the group-card preview.
- In served mode, the card offers "Ver fotos", which opens the existing photo grid/browser with every photo in the set in browse order.
- The cards appear after the group cards and group sections: the Marcadas card first, then bucket cards in catalogue order. An empty bucket produces no card; no marks produce no Marcadas card.
- The cards are a second view over photos that already belong to groups. They do not change group membership, group counts, labels, tags, or the fact that a photo can appear in several sets.
- The exported HTML presents the same cards read-only. It shows five thumbnails per card and offers no browse control, exactly as group cards do.
- A photo-set card always reports the real number of photos in its set. When a thumbnail cannot be produced it says so and never claims the photos fall into another group, because that explanation only fits a declared group card.
- The viewer resolves the library folder from the index; when that folder is unavailable it uses the folder the paired suggestions file declares, and when neither is available it reports the problem instead of drawing cards with no previews.
- Photo-set cards are not draggable and are not drop targets for group tags.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `photo-marking`: marked photos are presented as a card instead of a flat photo section.
- `photo-viewing`: bucket sections, the photo-section bound, both-axes behavior, opening a photo, drag rejection, and export presentation change to card presentation.

## Impact

- `fotos_plus/viewer.py`: photo section construction, card rendering, library-folder resolution, the photo-card empty state, browser references, drag setup, and export rendering.
- `fotos_plus/server.py`: resolve synthetic collection references for the served "Ver fotos" action and serve media against the folder the page used.
- Viewer, export, drag, server, and preview-failure tests.
- `openspec/specs/photo-marking/spec.md` and `openspec/specs/photo-viewing/spec.md` after archiving.
- Exported HTML no longer embeds up to 300 photos per marked or bucket section; it shows five previews per card. This is a deliberate consistency tradeoff, matching group cards.

## Rollback Plan

Revert the change commit and restore the previous `photo-marking` and `photo-viewing` requirements. The edition file format does not change, so existing marks and bucket assignments remain intact; no data migration or cleanup is required.
