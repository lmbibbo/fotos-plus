# Tasks

## 1. Modify viewer logic
- [x] 1.1 Remove the untagged photos section block from `photo_sections()` in `fotos_plus/viewer.py`, plus the now-unused `UNTAGGED_PHOTOS_TITLE` constant and the obsolete `has_bucket_memberships` early return
- [x] 1.2 Update the `photo_sections()` docstring and cap-motivation comment that reference "Sin cubo"

## 2. Update tests
- [x] 2.1 Update tests in `tests/test_viewer.py` that expect "Sin cubo" alongside buckets (order test, page-order test, unbucket test, export tests)
- [x] 2.2 Delete `test_the_cap_is_what_keeps_the_untagged_section_affordable`, whose premise no longer exists (generic cap coverage remains)
- [x] 2.3 Run the viewer tests to confirm they pass

## 3. Update docs
- [x] 3.1 Remove "Sin cubo" from the page structure documented in `README.md`

## 4. Verify
- [x] 4.1 Run all tests to make sure no other behavior is broken
- [x] 4.2 Run `openspec validate --all --strict` and confirm the delta matches the spec
