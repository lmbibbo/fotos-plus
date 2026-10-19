# Design

## Context

`mostrar()` in `fotos_plus/viewer.py` is the single path that shows an item in the served
browser: it is reached from a click on a grid cell (through `abrir()` after the `/api/photos`
fetch) and from the arrow keys and the prev/next buttons. It already
branches on `foto.kind` — a video gets `video.poster` and `video.src` set (token as a query
parameter), a photo gets a blob URL on the `<img>`. `soltarVideo()` pauses the element and
clears `src`/`poster` whenever navigation moves away or the browser closes. The `<video>`
element carries `controls`, and there is no `play()` call anywhere today.

Browser policy is the external constraint: Chromium and Firefox allow playback with sound
once the user has interacted with the document, and every arrival at a video happens in the
same document — the click or key that opened the browser is the interaction. Safari may
refuse. See proposal.md for motivation and the spec delta for the contract.

## Goals / Non-Goals

**Goals:**
- Playback starts on every arrival at a video, with no press on the play control.
- A refusal degrades to exactly today's state: poster still plus native controls, no error
  banner, no change of item.
- Rapid navigation cannot leave audio playing over the wrong item or pile up unhandled
  promise rejections in the console.

**Non-Goals:**
- Guaranteeing autoplay — the browser policy has the final word.
- Muted autoplay, or unmuting on the first interaction.
- Any server, endpoint, export, index, or scan change.
- Persisting a user preference for autoplay.

## Decisions

**1. Attempt playback with `video.play()` right after the source is set, and swallow
refusals.** `play()` returns a promise; the rejection handler ignores `NotAllowedError`
(policy refusal — the poster stays) and `AbortError` (the element was re-sourced or paused
by `soltarVideo()` before the attempt settled). Any other rejection is ignored too: the
native controls are the standing fallback, and an error banner over a video that simply did
not start would be noise — the spec forbids reporting an error.
Alternatives considered: the `autoplay` attribute, which is evaluated at element-parse time
with no user activation behind it and is therefore refused more often than a `play()` call
made after the click; muted autoplay, which is always allowed but starts silent, and
unmuting later needs a gesture of its own.

**2. Attempt on every arrival, not only on deliberate opens.** `mostrar()` is the one path
for both cases, so attempting there costs one line and no state. Threading an "explicit
open" flag would buy quiet during fast arrow sweeps at the price of a distinction no
scenario depends on; the pause inside `soltarVideo()` already bounds a sweep, since each
video plays only while it is the displayed item.

**3. The attempt belongs in the video branch of `mostrar()`, immediately after the source
assignment.** A photo arrival runs `soltarVideo()` and never reaches the attempt, and a
video arrival always does: one code path, no listeners to install or clean up.

Arrival at a video through the arrow keys:

```text
  keydown ArrowRight
        |
        v
   mostrar(i + 1) ---> soltarVideo() ---> pause(); src cleared; load()
        |                                   (an in-flight play() rejects with
        |                                    AbortError here, and is swallowed)
        v
   foto.kind === "video"
        |
        +--> video.poster = "/poster?ref=..&token=.."
        +--> video.src    = "/video?ref=..&token=.."
        +--> video.play() ---+--> allowed    --> plays; native controls show pause
        |                    |
        |                    +--> refused    --> poster stays, controls ready,
        |                         (NotAllowedError)   no error reported
        v
   photo branch: /render -> blob -> img.src   (unchanged)
```

## Risks / Trade-offs

- [Safari may refuse playback without a gesture inside the task] → the poster fallback is
  exactly the pre-change behavior, so nothing is lost and nothing errors.
- [Fast arrow sweeps start and stop many videos] → each attempt is bounded by the next
  `soltarVideo()` pause, and interrupted attempts reject with `AbortError`, which is
  swallowed. Sound can pulse during a sweep; that is the visible cost of playback on arrow
  arrival, which is what this change asks for.
- [A `play()` promise settling after the element was re-sourced] → an attempt interrupted
  before playback begins rejects with `AbortError`, which the handler swallows; an attempt
  that settled first is paused by `soltarVideo()`. Either way a late settlement cannot
  restart a video that navigation already left.
- [`mostrar()` still carries the stale phase-1 comment "Videos show a still without
  playback in this phase", which the code above it contradicts] → corrected as a task of
  this change.

## Migration Plan

Single commit on the feature branch, archived and merged through the usual PR flow;
rollback is a revert (see proposal.md - Rollback plan).

## Open Questions

None.
