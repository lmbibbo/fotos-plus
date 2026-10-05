# Tasks

## 1. Serve the capture date with each photo

- [x] 1.1 Add `captured_at` to every photo dict in the `/api/photos` response in `fotos_plus/server.py`, passing `photo.captured_at` unchanged, and update the exact-dict assertion in `tests/test_server.py` that compares the served photo list so it includes the new key. Verify: the updated assertion passes and the change is confined to that one dict.
- [x] 1.2 Add tests in `tests/test_server.py` asserting that a photo carrying a capture date serves its ISO timestamp and that a photo without one serves `null` rather than omitting the key. Verify: both new tests pass.

## 2. Render the date on the position line

- [x] 2.1 Extend the `posicion.textContent` assignment inside `mostrar()` in `fotos_plus/viewer.py` to append U+00B7 MIDDLE DOT and the first ten characters of `foto.captured_at`, leaving the assigned string untouched when `captured_at` is absent. Verify: no new element and no new CSS rule were introduced, and the served document still declares `charset=utf-8`.
- [x] 2.2 Add tests in `tests/test_viewer.py` covering a dated photo (position, separator and ISO date all present), an undated photo (position only, with no placeholder text), and navigation onto a photo with a different date (the shown date follows the photo now displayed). Verify: all three new tests pass.

## 3. Confirm the surfaces out of scope did not move

- [x] 3.1 Verify `_group_thumbs` and `_photo_card` in `fotos_plus/viewer.py` are unmodified and that the card meta line still joins its items with U+00B7, so the static export keeps its current shape. Verify: the exported-HTML tests pass without being edited.
- [x] 3.2 Verify the initial group-card payload still carries no per-photo `captured_at`, preserving the decision that loose photos are requested per group. Verify: the existing payload tests in `tests/test_viewer.py` pass without being edited.

## 4. Integration checks

- [x] 4.1 Run the full pytest suite and verify every test passes.
- [x] 4.2 Run `openspec validate --all --strict` and verify it reports no failures.
- [x] 4.3 Serve an index whose group spans several days and confirm in a browser that the position line shows the ISO date, changes when stepping to the next photo, and omits the date entirely for a photo with no EXIF timestamp.

## 5. Archive and open the pull request

- [ ] 5.1 Commit the implementation and its tests on the `feature/show-capture-date-in-served-browser` branch, never on `main`.
- [ ] 5.2 Run `openspec validate --specs --strict` and verify it passes before archiving.
- [ ] 5.3 Run `openspec archive` on the feature branch, never on `main`, and commit the archive result on that same branch alongside the code.
- [ ] 5.4 Verify every checkbox in the archived `tasks.md` is marked, including the ones completed while archiving, so the archived file reflects the work that was done.
- [ ] 5.5 Push the branch and open a single pull request against `main` with an English description, and verify the PR is open and its checks have run.
