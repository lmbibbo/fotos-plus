# Tasks

## 1. Build photo-set card descriptors

- [x] 1.1 Add a photo-set card model/helper in `fotos_plus/viewer.py` that turns the marked set and each non-empty bucket into a card descriptor with title, photos, count, date range, and a synthetic browse key; verify with unit tests in `tests/test_viewer.py`.
- [x] 1.2 Order the descriptors as Marcadas first and buckets in catalogue order, skipping empty buckets; verify the order and empty-set behavior with tests.
- [x] 1.3 Compute counts from the actual set and dates from the earliest/latest known capture dates, including photos without a date; verify with tests that include an undated marked photo and a multi-date bucket.

## 2. Render photo cards on the landing page

- [x] 2.1 Replace the flat photo-section rendering path with photo cards that reuse the group-card shell and thumbnail helper; verify the viewer output contains one `Marcadas` card and one card per non-empty bucket, with no flat photo cards.
- [x] 2.2 Show at most five thumbnails per photo card, all thumbnails when the set is smaller, and the correct photo count and date range; verify with tests for small sets, large sets, and undated photos.
- [x] 2.3 Keep photo cards out of the group-axes data: no country, group label editor, tag editor, or group section counts; verify with tests that the existing group cards and tag sections are unchanged.
- [x] 2.4 Update the README description of the home order and card presentation; verify the documented order matches the generated page.

## 3. Open the full set from a served photo card

- [x] 3.1 Extend the server's resolved card map to include the marked and bucket photo cards under their synthetic keys; verify with tests that `group_for("marcadas")` and `group_for("cubo:<name>")` resolve to the correct photo list.
- [x] 3.2 Update `GET /api/photos` to return the existing JSON shape for a photo card, with the card title and photos in browse order; verify with server tests for marked, bucket, empty, and special-character bucket names.
- [x] 3.3 Render the served `Ver fotos` control on photo cards and keep it out of the export; verify with tests that the button carries the synthetic key and that the export has no such control.
- [x] 3.4 Update the README served-browser notes to describe opening a photo card; verify the documented behavior matches the endpoint and grid flow.

## 4. Keep photo cards out of group drag-and-drop

- [x] 4.1 Restrict the card drag/drop JavaScript to real group cards, so photo cards cannot start a drag and cannot receive a group card; verify with tests that the selector excludes photo cards.
- [x] 4.2 Preserve the existing rejection message when a group card is dropped on the photo-card area, and preserve group-tag drag behavior; verify with tests that no mark, bucket, or group tag changes.
- [x] 4.3 Add a regression test for a photo card that is neither draggable nor a drop target; verify it fails before the fix and passes after it.

## 5. Export parity and integration

- [x] 5.1 Remove the old flat photo-section path and the 300-photo bound, and render the same photo cards in the exported HTML without browse, picker, or drag controls; verify with export tests for marked and bucket cards.
- [x] 5.2 Update the README note about the old 300-photo sections to describe the five-thumbnail card preview; verify the README no longer promises the removed behavior.
- [x] 5.3 Run `pytest` and verify the full suite passes, including the new viewer, server, drag, and export tests.
- [x] 5.4 Run `openspec validate --all --strict` and verify all changes and specs validate.
- [x] 5.5 Generate a served page from a library with marks and buckets and verify manually that each set appears as one card, `Ver fotos` opens the full set, and dragging a group card is rejected.

## 6. Keep previews working and honest

- [x] 6.1 Resolve the library folder as the index folder when it is a directory, otherwise the suggestions folder, and report the missing folder when neither is a directory; verify in `tests/test_viewer.py` and `tests/test_server.py`.
- [x] 6.2 Give photo-set cards a kind-aware empty state: keep the real count and state that previews could not be produced, without the group-only "falls into another group" note; verify for a marked card and a bucket card.
- [x] 6.3 Show a placeholder in the served grid for a photo whose thumbnail cannot be served, and keep selecting the cell opening the browser; verify with a server test.
- [x] 6.4 Run `pytest` and `openspec validate --all --strict`.
