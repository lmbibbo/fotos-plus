# Proposal

## Why

Opening a video in the served browser shows the poster still with native controls, but playback
only starts when the user presses play — once per video. Reviewing a group that holds many videos
means pressing play on every single one, which turns a walk-through into a series of clicks.

## What Changes

- In `--serve` mode, arriving at a video in the group browser starts playback automatically: both
  when the browser opens on a video (a grid cell) and when navigation (arrow keys or the
  prev/next buttons) moves onto one.
- When the browser refuses autoplay under its own policy, the viewer leaves the poster still with
  the native controls in place — exactly today's state — and reports no error.
- Navigation behavior is unchanged: moving off a playing video stops it, arrows keep moving between
  items, and seeking stays in the native controls.
- No server change: `/video` and `/poster` keep serving as they do. The static export is untouched —
  still posters only, no `<video>` element, and no playback surface outside the served browser.

## Capabilities

### New Capabilities
None

### Modified Capabilities
- `photo-viewing`: the served-browser video requirement is renamed from "Videos in the served
  browser show a still without playback" to "Videos in the served browser play automatically on
  arrival"; its behavior changes from "playback MUST start on user action; the viewer MUST NOT
  autoplay videos" to automatic playback on arrival, with the poster still as the fallback when the
  browser refuses.

## Impact

- `fotos_plus/viewer.py`: the video branch of `mostrar()` attempts playback after setting the
  source; `soltarVideo()` already stops it when navigation moves away.
- `tests/test_viewer.py`: the existing video test gains JS-source assertions for the play attempt
  and the handler that swallows a refusal; a new test covers arriving at a video and leaving it;
  the export test still asserts no `<video>` element.
- `README.md`: the note on served-only playback gains the autoplay behavior and its fallback.
- Unchanged: `fotos_plus/server.py`, scanning, the index, marks, buckets, tags, and the export.

## Rollback plan

- Reverting the commit returns the viewer to press-to-play: the `<video>` element, the `/video`
  endpoint, and every guarantee of the previous change keep working, so no data, index, or server
  behavior is at risk.
- The spec requirement returns to user-action playback with the same revert; the archived change
  history keeps both wordings.
- Nothing persisted changes: videos, posters, and renders are stored by content hash and do not
  depend on how playback starts.
