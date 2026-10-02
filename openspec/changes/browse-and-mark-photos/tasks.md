# Tasks

## 1. Screen-sized render helper and content-addressed cache

- [x] 1.1 Add a render helper in `fotos_plus/photos.py` that caps the longest edge at 2000px, applies the EXIF orientation before resizing, and returns JPEG bytes; verify with `tests/test_photos.py` that a large fixture produces an image within the cap and an orientation-marked fixture comes back upright.
- [x] 1.2 Add cache path resolution for `<index-base>-renders/<sha256>.jpg`, created on demand; verify with `tests/test_photos.py` that the resolved path is keyed by hash and does not vary with the photo's relative path.
- [x] 1.3 Implement the lazy get-or-produce behaviour: return the stored render when present, otherwise produce and store it; verify with `tests/test_photos.py` that a second call returns the stored bytes without reopening the original.
- [x] 1.4 Verify a changed photo with a new content hash does not reuse the previous render, and that deleting the cache directory only costs time; verify in `tests/test_photos.py`.

## 2. Edition file version 3 with marks

- [x] 2.1 Bump `EDITION_VERSION` to 3, add `marked` to `SUPPORTED_EDITIONS`, and add a `marked` field to `LabelOverlay` defaulting to empty; verify in `tests/test_labels.py` that a v1 and a v2 file both load with an empty mark list and that reading does not rewrite the file on disk.
- [x] 2.2 Add a `_read_marked` validator that accepts only 64 lowercase hexadecimal characters, deduplicates, and rejects anything else; verify in `tests/test_labels.py` that a malformed entry raises and that `write_edicion` refuses to write it.
- [x] 2.3 Extend `to_dict` so a saved file declares version 3 and carries `marked` alongside `labels`, `tags` and `tagged`; verify in `tests/test_labels.py` that saving a mark preserves the existing tags and tag assignments.
- [x] 2.4 Carry `marked` through `set_label`, `remove_label`, `set_tag` and `clear_tag`, which each rebuild the overlay by naming every field explicitly; verify with a dedicated regression test in `tests/test_labels.py` that a saved mark survives each of the four operations individually.
- [x] 2.5 Add `mark_photo` and `unmark_photo` as explicit toggles that return a new overlay without mutating the input; verify in `tests/test_labels.py` that both are symmetric and that marking then unmarking leaves no trace.
- [x] 2.6 Filter marks against the scanned index when the overlay is loaded, dropping hashes the index does not contain, without rewriting the file; verify in `tests/test_labels.py` that an unresolved mark is absent in memory but still present on disk.
- [x] 2.7 Update the `LabelOverlay` docstring and the `labels.py` module docstring so they no longer claim the file holds only labels and tags; verify by re-reading both and confirming they mention marks.

## 3. Authenticated render endpoint

- [x] 3.1 Add a `GET` route serving a render, routed alongside the existing `/` branch in `do_GET`; verify in `tests/test_server.py` that an unknown path still returns 404 and that the new route returns image bytes with a correct content type and length.
- [x] 3.2 Resolve the requested photo reference through the scanned index and derive the render from the resolved content hash, so no caller-supplied string is ever used as a filesystem path; verify in `tests/test_server.py` that a reference absent from the index is refused and that a `../` traversal reference and an absolute path are both refused.
- [x] 3.3 Require the existing random token as a request header so the browser preflights it, reusing the same token source as the edit route; verify in `tests/test_server.py` that a request with no token or a wrong token returns no bytes.
- [x] 3.4 Reject requests whose host header is not a loopback address, and reject requests carrying `Sec-Fetch-Site: cross-site` or `same-site`; verify both rejections in `tests/test_server.py`.
- [x] 3.5 Cache the resolved photo lookup on the server object so repeated requests for the same reference do not re-walk the index; verify in `tests/test_server.py` that two requests for the same reference return equal bytes.

## 4. Photo inventory endpoint for the served viewer

- [x] 4.1 Add an endpoint returning, for one group key, the ordered photo references with their content hashes and current mark state, resolved with the same groups the cards already use; verify in `tests/test_server.py` that an unknown or ambiguous group key is refused with a reason.
- [x] 4.2 Extend the served page payload with the per-group inventory only when serving, leaving the export path untouched; verify in `tests/test_viewer.py` that the served page carries the inventory and that the exported HTML does not.

## 5. Group browser overlay in the served viewer

- [x] 5.1 Add a way to open a full-screen browser from a group card that owns at least one photo, showing position within the group and the group's total; verify in `tests/test_viewer.py` that the control is absent for a group owning no photos.
- [x] 5.2 Render the current photo from the render endpoint and show previous and next controls, staying put at the first and last photo rather than moving past the ends; verify in `tests/test_viewer.py`.
- [x] 5.3 Bind keyboard navigation for both directions, ignoring the keys while a text field has focus; verify in `tests/test_viewer.py`.
- [x] 5.4 Show whether the displayed photo is marked and update the indication immediately on toggle without reloading; verify in `tests/test_viewer.py` that moving between a marked and an unmarked photo shows the matching state.
- [x] 5.5 Close the overlay on dismissal, returning to the group cards without adding or removing any mark; verify in `tests/test_viewer.py`.

## 6. Mark endpoint

- [x] 6.1 Add the endpoint that marks and unmarks the displayed photo, resolving the reference through the index and rewriting only the edition file; verify in `tests/test_server.py` that an accepted mark is persisted and that no other file changes.
- [x] 6.2 Apply the same guarantees as the edit route: valid token, loopback host header, JSON content type, and a reason on refusal; verify each rejection in `tests/test_server.py`.
- [x] 6.3 Rebuild the served page after a mark changes so a reopened browser reflects the new state; verify in `tests/test_server.py`.

## 7. Integration and safety checks

- [x] 7.1 Run the full suite and confirm no existing test regressed, in particular the viewer export tests and the label and tag tests; verify with `pytest` reporting all previously passing tests still passing.
- [x] 7.2 Confirm against the reference library that the export still shows five thumbnails per card and stays self-contained, and that the served page gained the browser; verify by generating both from the reference index and comparing the export's thumbnail count and size.
- [x] 7.3 Confirm no photo in the library root was modified by browsing and marking, including across a server restart and a rescan; verify by hashing the library before and after the exercise.
- [x] 7.4 Update `README.md` to describe the group browser, the marks and the disposable render cache, including that the export is unchanged; verify the documented commands run as written.
- [x] 7.5 Run `openspec validate --specs --strict` and confirm it passes; then commit the code, tests and docs together on the `feature/browse-and-mark-photos` branch, never on `main`.