# Proposal

## Why

The viewer can name and classify groups, but it cannot show you what is inside one. Each card
embeds five 200px thumbnails, so in the reference library (5059 photos across 66 groups) only 330
of 5059 photos are visible at all. Everything else is a number in a card.

That makes "keep the ones worth keeping" impossible to carry out, which is the selection step the
user actually needs before any cleanup work can happen. Marking is the cheap and reversible half of
that work: it records an opinion and touches nothing on disk. Acting on those opinions -- deleting,
moving, collecting -- is a separate concern with a very different risk profile, and it is
deliberately left for a later change.

## What Changes

- Add a full-screen photo browser overlay, available per group, in `--serve` mode only. It shows
  the group's photos one at a time, navigable by keyboard.
- Add a served endpoint that returns a screen-sized render of a single photo (longest edge capped
  at 2000px). Renders are produced lazily on first request and cached on disk.
- Key the render cache by the photo's `sha256`, so a changed file cannot serve a stale render and a
  moved file keeps its cached render.
- Require the existing random token on the new endpoint, and resolve every request through the
  scanned index rather than through a client-supplied filesystem path.
- Bump the edition file from version 2 to version 3 and add a flat `marked` list of `sha256` values.
- Let the user mark and unmark the current photo from the browser overlay, one binary state per
  photo.
- Drop marks whose `sha256` no longer appears in the index when the edition file is loaded.

Deliberately out of scope:

- **No action is taken on marked photos.** No deletion, no moving, no collecting, no export of the
  selection. A later change decides that, and it can do so knowing the marks are already curated.
- **No subgroups.** Group membership keeps being derived from date ranges on every view. A
  subgroup model needs persisted explicit membership, its own keys and reconciliation after a
  rescan; it is a much larger change and this one does not need it.
- **No tri-state.** Marks are marked/unmarked only. A photo the user looked at and rejected is
  indistinguishable from one they never reached. Sequential browsing makes the next unmarked photo
  the pending one, which covers the gap well enough for this step.
- **No zoom to the original.** 2000px is enough to judge a photo. The reference library has photos
  up to 8160x6144 (13.77 MB), which is not a fluid browsing experience.
- **No change to the static export.** It stays self-contained, five thumbnails per card, ~2 MB, no
  editing controls. The pasarela is useless there because the browser blocks `file://` subresources
  loaded from an `http://` page.

## Capabilities

### New Capabilities

- `photo-marking`: recording a binary keep/drop opinion about individual photos, persisted by
  content hash so it survives file moves and rescans, and preserved across unrelated edits to the
  same file.

### Modified Capabilities

- `photo-viewing`: adds browsing a group's photos in the served viewer -- the overlay, its keyboard
  navigation, the screen-sized render endpoint with its token and index-resolution guarantees, the
  lazy sha256-keyed render cache, and the explicit statement that the static export gains none of it.

`group-labels` is **not** modified. Its requirement that the edition file declare a version and
accept earlier versions already covers a v2 to v3 bump, and it does not claim the file carries only
labels and tags. The docstring in `labels.py` and the capability name now understate the file's
contents; that drift is recorded in `design.md` rather than fixed here.

## Impact

- `fotos_plus/labels.py`: edition version 2 to 3, new `marked` field, its validator, migration from
  v1 and v2, and orphan pruning on load. Every overlay constructor that re-lists fields by hand
  (`set_label`, `remove_label`, `set_tag`, `clear_tag`) must carry `marked` through, and a miss
  there silently destroys marks or tags. This is the highest-risk part of the change and needs a
  dedicated test.
- `fotos_plus/server.py`: new authenticated GET route, its handler, and caching of resolved photos.
- `fotos_plus/photos.py`: a screen-sized render helper next to the existing thumbnail helper.
- `fotos_plus/viewer.py`: the overlay, keyboard navigation, and the extra viewer payload.
- New render-cache location, writable and disposable, derived from the index path.
- No new runtime dependency. Pillow is already required for thumbnails.
- No change to the static export path or to the scanner.

### Rollback plan

The pasarela, the endpoint and the cache are all additive and can be dropped by reverting the code;
no index, suggestions file or photo is touched by this change.

The edition file is the one asymmetric case, and it is a real hazard:

- Once a mark is saved, the file declares version 3. The previous release's reader accepts only
  versions 1 and 2, so after a code revert `view` **reports the version as unsupported instead of
  loading the file**. This is expected and is not data loss, but it does mean a reverted checkout
  cannot open that library until the file is restored.
- Full return to version 2 therefore means either restoring a pre-change copy of the file, or
  hand-removing the `marked` array and setting `version` back to 2 -- which discards the marks by
  definition. There is no way to keep the marks under version 2.
- Mitigation for rollout: back up `<index>-edicion.json` before the first mark is written. With
  that backup, any rollback is a file restore.

### Known issue recorded by this change

The project instructions ask for these artifacts in English, while all four current specs and all
eight archived changes are written in Spanish. The deltas in this change are therefore in English
and, once archived, will sit next to Spanish requirements inside `photo-viewing.spec.md`. A
translation pass over the existing specs is needed at some point and is not part of this change.