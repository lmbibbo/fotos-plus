# Proposal

## Why

When a library has many photos with no bucket, the landing page shows a large untagged photos section ("Sin cubo") at the end. That section can grow to include the entire library and make the served page very large, contradicting the intent of bounding photo sections to keep the document affordable. The home view should show only deliberate groupings (group sections, the marked section, bucket sections) and never the leftover "Sin cubo" section.

## What Changes

- **BREAKING**: The landing page will no longer present an untagged photos section ("Sin cubo") in any case. Photos that belong to no bucket appear in no photo section on the home view; they remain reachable through the group cards and the photo browser.
- Bucket sections still appear only for buckets that hold at least one photo, in catalogue order, after the group sections.
- The behavior for marked photos, group cards, and flat mode remains unchanged.

## Capabilities

### New Capabilities
None

### Modified Capabilities
- photo-viewing: Remove the untagged photos section from the landing page entirely. Update the photo bucket sections requirement (no "section of their own" for photos in no bucket) and the photo section bound requirement (its motivation and scenarios no longer reference the untagged section).

## Impact

- `fotos_plus/viewer.py`: Remove the untagged photos section from `photo_sections()` and drop the now-unused `UNTAGGED_PHOTOS_TITLE` constant.
- `tests/test_viewer.py`: Update tests that expect the untagged photos section alongside buckets; delete the test whose whole premise was the untagged section's size.
- `README.md`: Update the documented page structure that lists the `Sin cubo` section.
- No server API changes; the change affects only the rendered HTML structure for the landing page.
