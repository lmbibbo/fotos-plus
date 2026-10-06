# Proposal

## Why

The shortlist produced by marking photos cannot be browsed. A mark is a binary opinion that is only
visible while its photo happens to be on screen in the served browser, so a curation pass over a
few thousand photos ends with a durable record the user has no way to look at, filter or come back
to. Group tags cannot stand in for it either: they classify whole trips, so they cannot express
"these twelve photos", and they cannot span trips.

The user wants several named buckets that individual photos can be placed into, so that a
curation result is navigable the same way the library is.

## What Changes

- Photos can be placed into any number of user-defined named buckets, independently per photo.
- A separate catalogue of photo-bucket names, so bucket names never collide with group tag names.
- The landing page gains photo sections alongside the existing group sections. The page therefore
  carries two axes: trips, and curation.
- The served browser gains a bucket picker next to the existing Mark control, so buckets are
  assigned while looking at a photo.
- The landing page gains a section for marked photos, which makes the existing shortlist visible
  for the first time outside the browser. This is also the first appearance of marks in the static
  export.
- Drag and drop is left exactly as it is for group cards, where dragging means "move". Bucket
  membership is edited with the picker, because membership is not exclusive and a drag gesture
  would be ambiguous.
- The edition file moves to version 4 and grows a `photo_tags` catalogue and a `photo_tagged` map
  keyed by content hash. Marks, labels, group tags and group tag assignments are untouched.

### Deferred: whether marks become a reserved bucket

This change keeps marks as their own concept and gives them their own section. Folding them into a
reserved bucket was considered and not chosen here, for two reasons.

Marking and tagging happen at different speeds. The purpose of `photo-marking` is that "a curation
pass over a large library produces a durable shortlist"; that pass is fast and repetitive, so a
mark stays a single click, while a bucket is added through a picker. Making the mark a bucket would
force the fast path through the slow control in order for the two to look alike in the model.

Pruning would have to serve two mechanisms at once. `prune_marked` already discards hashes absent
from the index without rewriting the file, and bucket assignments keyed by hash need the same rule.
Keeping them in separate keyspaces leaves each one with a single, clear pruning rule.

The cost of this choice is that "Marked" is not editable the way a bucket is. That is deliberate:
it is not a bucket, it is the shortlist. If it later becomes clear that the distinction is not worth
its own section, folding marks into a reserved bucket is a small follow-up delta that would rewrite
`photo-marking` requirements 1, 3 and 4.

## Capabilities

### New Capabilities

- `photo-tagging`: user-defined named buckets that individual photos are placed into, held in the
  edition file beside the group tags, edited from the served browser, and pruned by content hash.

### Modified Capabilities

- `photo-marking`: marks are currently visible only while a photo is displayed and have no landing
  page presence. Add the requirement that marks produce their own section on the landing page and
  appear in the static export. The version requirement is renamed from "at version 3" to "at the
  current version", which is now 4.
- `photo-viewing`: the landing page currently presents only group sections. Add photo sections
  after the group sections, the untagged-photos section, and the bucket picker in the served
  browser. The existing tag section, drag and drop, and read-only export requirements are unchanged.

## Impact

- `fotos_plus/labels.py`: `EDITION_VERSION` becomes 4, `SUPPORTED_EDITIONS` gains 4, and
  `LabelOverlay` gains `photo_tags` and `photo_tagged` alongside the existing fields. Mark pruning
  is generalised so bucket assignments are pruned by the same rule.
- `fotos_plus/viewer.py`: `Section` grows a photo-bearing form alongside its group-bearing form,
  `group_sections` gains a photo counterpart, `_flat_card` is reused for bucket grids, and the
  browser overlay gains the picker control and its payload.
- `fotos_plus/server.py`: `POST /api/photo-tags` for bucket edits, and the photos payload gains
  per-photo bucket names plus a bucket catalogue. The endpoint reuses the existing token, loopback
  host and JSON content-type guards that `POST /api/labels` and `POST /api/marks` already apply.
- `fotos_plus/photos.py`: unchanged. `_flat_card` already renders a loose photo from a thumbnail,
  so no new rendering primitive is needed.
- Tests in `tests/test_labels.py`, `tests/test_server.py` and `tests/test_viewer.py`.

### Scale

Thumbnails are cheap enough for bucket sections to be inline. Measured on a 4032x3024 source with
noise, foliage detail and fine line structure, `make_thumbnail` produces about 5.7 KB at the
existing 200px quality 70, about 7.9 KB of markup per photo once base64 and the card wrapper are
counted. That puts a 400-photo section near 3.1 MB of HTML and a 1200-photo section near 9.2 MB.

This is safe only because bucket sections use thumbnails and not renders. The 544 MB incident that
led to the current grouped design was caused by 2000px renders at about 457 KB each, which is
roughly eighty times heavier per photo. A bucket section must never inline renders. Each photo
section draws at most 300 photos; beyond that the section reports the true count and says how many
were held back, pointing at the photo browser.

## Rollback

The change is additive and revertible by dropping the feature branch, which is the same path as any
other unmerged change here.

For an already-archived change, the ordered steps are:

1. Revert `EDITION_VERSION` to 3 and remove 4 from `SUPPORTED_EDITIONS`. A version 4 file then
   fails to load, so this must land together with the read path change below.
2. Drop `photo_tags` and `photo_tagged` from `LabelOverlay` and stop pruning bucket assignments.
   A version 4 file read by this code keeps only `labels`, `tags`, `tagged` and `marked`.
3. Remove `POST /api/photo-tags` and stop sending bucket fields in the photos payload.
4. Remove the photo sections and the picker from the viewer.

Because versions 1 and 2 remain readable and reading never rewrites the file, no migration is
required to roll back: a version 4 file degrades to its labels, group tags and marks on read, and
the bucket names are lost only when the next saved edit rewrites the file. Marks are never
destroyed by any step above, so the existing shortlist survives a rollback intact.
