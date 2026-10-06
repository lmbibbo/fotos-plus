# Tasks

## 1. Edition file at version 4

- [x] 1.1 Bump `EDITION_VERSION` to 4 and widen `SUPPORTED_EDITIONS` to include 4; add `photo_tags` and `photo_tagged` to `LabelOverlay` defaulting to empty, and verify a default overlay round-trips through the constructor with both fields present
- [x] 1.2 Read versions 1, 2 and 3 with an empty bucket catalogue and no bucket assignments while preserving labels, tags, tagged and marked, and verify the file on disk still declares its original version after the read
- [x] 1.3 Write version 4 with bucket fields populated; reject a `photo_tagged` key that is not 64 lowercase hex characters and reject a stored bucket name absent from `photo_tags`, verifying the save is refused and the file left unchanged in both cases
- [x] 1.4 Validate bucket names: refuse an empty or whitespace-only name, and treat two names that differ only in case or surrounding whitespace as the same bucket, verified by tests covering both refusals and the identity match
- [x] 1.5 Add a test that a bucket edit on a version 3 file with tags and marks already saved produces a version 4 file holding all of them
- [x] 1.6 Update the README section "DÃ³nde se guardan los nombres" to document version 4, `photo_tags` and `photo_tagged`, keeping the existing Spanish wording for everything already there

## 2. Pruning by content hash

- [x] 2.1 Generalise the existing mark pruning into one helper that resolves a set of content hashes against the scanned index, and route `marked` through it with no behaviour change, verified by the existing photo-marking pruning tests passing untouched
- [x] 2.2 Prune `photo_tagged` through the same helper, and verify a bucket name whose last photo was pruned is still present in `photo_tags` and therefore produces no section
- [x] 2.3 Verify pruning does not rewrite the file, and that a version 4 file whose bucket assignments all resolve keeps every one of them

## 3. Unrelated edits carry the new fields through

- [x] 3.1 Carry `photo_tags` and `photo_tagged` through the label save path unchanged, verified by a test that saves a label on a file holding buckets and asserts both survive
- [x] 3.2 Carry both through the label removal path, verified the same way
- [x] 3.3 Carry both through the group tag assign and clear paths, verified by tests that also assert the group tag change landed
- [x] 3.4 Carry both through the mark and unmark paths, verified by a test that marks a photo and asserts the buckets are still stored
- [x] 3.5 Carry `marked`, `labels`, `tags` and `tagged` through a bucket add and a bucket remove, verified by tests that also assert the membership changed as intended

## 4. Server endpoint for bucket edits

- [x] 4.1 Add `POST /api/photo-tags` applying the same guards `POST /api/labels` and `POST /api/marks` apply: valid token, loopback host and JSON content type; verified by a test that a request missing or falsifying the token is rejected and writes no file
- [x] 4.2 Accept an add: validate the name, resolve the content hash against the index, append the name to the catalogue when it is new and to `photo_tagged[sha]`, and rewrite only the edition file atomically; verified by a test asserting the persisted content
- [x] 4.3 Accept a remove: drop that one name from `photo_tagged[sha]` and leave the photo's other buckets, the catalogue and every unrelated field untouched; verified by a test asserting the photo's remaining membership
- [x] 4.4 Reject with a reason, writing nothing, an empty or whitespace-only name, a content hash that resolves to no photo in the index, and a malformed hash; verified by one test per rejection

## 5. Bucket picker in the served browser

- [x] 5.1 Add the bucket catalogue and each photo's membership to the payload the served document emits, and verify the payload carries them without changing any existing field
- [x] 5.2 Add the picker control to the browser overlay next to the Mark button, rendering one control per catalogue name plus a way to write a new name, verified by asserting the control appears in the served markup
- [x] 5.3 Show the displayed photo's own membership, update it immediately on change without reloading the page, and verify that moving to another photo shows that photo's membership and that a photo in no bucket shows nothing held
- [x] 5.4 Wire add and remove to the endpoint, and on rejection report the reason and restore the membership the server actually holds rather than the optimistic one; verified by a test that forces a rejection and asserts the reverted state
- [x] 5.5 Update the README section "Marcar fotos" and "Recorrer las fotos de un grupo" to describe the picker, its position next to Mark, and that Mark remains a single click

## 6. Photo sections on the landing page

- [x] 6.1 Give `Section` a photo-bearing form alongside its group-bearing form, keeping the group one unchanged, verified by the existing group-labels and photo-viewing tag section tests passing untouched
- [x] 6.2 Implement photo section construction: one section per non-empty bucket in catalogue order, the marked section before them, and the untagged photos section last; verified by a test asserting the section names and their order
- [x] 6.3 Reuse `_flat_card` and `.card.flat` for section photos, and verify a section photo renders as a single photo with its capture date rather than as a group card
- [x] 6.4 Verify no section inlines a render, by asserting section photo markup references thumbnails only and never the `/render` endpoint
- [x] 6.5 Report each section's photo count, verify a catalogue name holding no photo produces no section, and verify a photo in several buckets is listed under each of them
- [x] 6.6 List photos within a section in browse order, and verify a photo with no capture date is still listed and still opens the browser at that photo
- [x] 6.7 Compose the page as group sections, then the marked section, then bucket sections, then the untagged section; verify a library with no tags, no marks and no buckets still renders one flat date-ordered card list with no section heading
- [x] 6.8 Verify buckets do not alter a group card's title, photo count, date range or country, and that a marked or bucketed photo is absent from the marked or bucket section after it is unmarked or unbucketed
- [x] 6.9 Give photo sections no drop target, and verify dragging a group card onto one reports the refusal, stores nothing, and leaves dragging a card onto a group section unchanged
- [x] 6.10 Update the README section "Visualizador" to describe the two axes and their order, and document the 300-photo-per-section bound in "Limitaciones conocidas"

## 7. Static export

- [x] 7.1 Show the marked section and the bucket sections including the untagged one in the exported HTML, verified by a test asserting the section names appear in the exported document
- [x] 7.2 Verify the export contains no picker, no bucket control and no drop target, and that bucket fields do not leak into the export payload the way `marked_count` is withheld today
- [x] 7.3 Verify a bucket assignment whose photo no longer resolves is absent from both the export and the served page, while its catalogue entry survives in both

## 8. Integration

- [x] 8.1 Run the full test suite and confirm it is green
- [x] 8.2 Run `openspec validate --specs --strict` and confirm no spec regressed
- [x] 8.3 Drive a real server end to end: assign a bucket to a photo, confirm the picker reflects it without a reload, confirm the marks section and the bucket sections appear, and confirm the dragged-card refusal, checking the generated markup with node as the existing date change did
- [x] 8.4 Confirm `view` without `--serve` still writes a document that opens standalone with the new sections and no controls
