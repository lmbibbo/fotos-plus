# Design

## Problem statement recap
The landing page builds photo sections via `photo_sections()`, which appends an untagged photos section ("Sin cubo") holding every photo in no bucket. The requirement now states the landing page MUST NOT present an untagged photos section in any case: photos in no bucket appear in no photo section.

## Solution
Remove the untagged-section block from `photo_sections()` in `fotos_plus/viewer.py` entirely, along with the now-unused `UNTAGGED_PHOTOS_TITLE` constant. The `has_bucket_memberships` early return added earlier becomes dead logic (with no untagged block, an empty membership map already yields no bucket sections from the catalogue loop), so remove it too and let the catalogue loop naturally produce nothing. Update the function docstring and the cap-motivation comment that referenced "Sin cubo". Update `README.md`, which documents the page structure. Marked section, bucket sections, group cards, flat mode, and the served/export payloads are untouched.

## Impact
- `fotos_plus/viewer.py`: Delete the untagged block, the constant, and the obsolete early return.
- `tests/test_viewer.py`: Update tests that expect "Sin cubo" alongside buckets; delete the test whose whole premise was the untagged section's size (generic cap coverage already exists).
- `README.md`: Remove "Sin cubo" from the documented page structure.
- No server/API changes.
