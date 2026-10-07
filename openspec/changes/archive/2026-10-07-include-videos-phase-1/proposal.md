# Proposal

## Why

Phone libraries mix photos and videos, but the scan ignores every video file, so trips, cards, marks, and buckets silently miss part of the library. Including videos in the scan closes that gap while reusing the date/GPS grouping pipeline that already exists.

## What Changes

Phase 1 (this change). Playback is explicitly out of scope and left for phase 2.

- The scan accepts `.mp4`, `.mov`, and `.3gp` files and records each video with its capture date (from container metadata), GPS position when available, duration, and content hash, exactly like a photo entry.
- Videos with a capture date and position group into trip and period suggestions under the identical rules as photos. Dateless videos follow the existing undated handling.
- Cards and photo sections show videos: a JPEG poster frame when an `ffmpeg` binary is available on the machine, otherwise a generic duration tile. No new pip dependency.
- In the served browser, a video opens on a still (poster) with its duration marked and without playback. The `/render` endpoint keeps serving photos only.
- The static export embeds video posters like photo thumbnails and never embeds video blobs.

## Capabilities

### New Capabilities
None

### Modified Capabilities
- `photo-scanning`: Accept video containers in the scan; record capture date from container metadata plus duration and media kind; report unreadable videos as scan errors without stopping.
- `trip-periods`: Videos participate in trip and period suggestions under the identical date/position rules as photos.
- `photo-viewing`: Cards and photo sections render videos via poster frames (or a duration tile when no decoder exists); the served browser shows a still for videos with no playback in this phase.

## Impact

- `fotos_plus/photos.py`: Video identification, container metadata reader, poster extraction via optional `ffmpeg`.
- `fotos_plus/models.py`: Media kind and duration fields on `Photo`; index version bump.
- `fotos_plus/viewer.py`: Video tiles in cards, sections, export, and served browser still.
- `fotos_plus/scanner.py`, `fotos_plus/grouping.py`: No logic changes expected (they consume the unified fields); covered by new tests.
- `tests/`: New scan, grouping, and viewer tests; fixture videos (tiny synthetic containers).
- Photo marking and bucket tagging work unchanged (they key on content hash).
