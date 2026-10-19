# Tasks

## 1. Playback on arrival

- [x] 1.1 In the video branch of `mostrar()`, attempt `video.play()` after `video.src` is
  set, with a rejection handler that swallows every rejection (`NotAllowedError`,
  `AbortError`, and any other the play attempt surfaces) so no unhandled rejection reaches
  the console — verify: the video branch in `EDIT_SCRIPT` contains the play attempt after
  the source assignment and a handler that ignores every rejection
- [x] 1.2 Replace the stale phase-1 comment in `mostrar()` ("Videos show a still without
  playback in this phase") with one describing playback on arrival and the poster
  fallback — verify: the comment no longer claims videos show a still without playback

## 2. Tests

- [x] 2.1 Update `test_the_browser_plays_videos_with_native_controls` to assert the play
  attempt and the swallow-every-rejection handler — verify:
  `pytest tests/test_viewer.py -k browser_plays_videos` passes
- [x] 2.2 Add a viewer test asserting that arriving at a video attempts playback and that
  leaving it still pauses and clears the element first — verify:
  `pytest tests/test_viewer.py` passes for the video group
- [x] 2.3 Keep the export test asserting the document contains no `<video>` element —
  verify: `pytest tests/test_viewer.py -k export` passes

## 3. Docs

- [x] 3.1 Update the `README.md` served-playback note: playback starts on arrival — on
  opening a video and on moving onto one — and falls back to the poster still with native
  controls when the browser refuses — verify: the note reads consistently with the spec
  delta scenarios

## 4. Verify

- [x] 4.1 Full `pytest` run and `openspec validate --all --strict` — verify: every test
  passes and validation reports no failures
- [x] 4.2 Serve a library holding videos and walk through a group: playback starts when
  the browser opens on a video and when an arrow moves onto one, arrows still navigate,
  and leaving a playing video stops it — verify: the walkthrough matches the spec
  scenarios
