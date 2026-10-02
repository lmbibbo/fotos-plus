# Design

## Context

See `proposal.md` for motivation. The facts below are what shape the approach.

**The viewer payload carries no photos.** `_payload()` in `fotos_plus/viewer.py` emits per group only
`title`, `kind`, `photo_count`, `first_captured_at`, `last_captured_at` and `country`. The browser
has no idea which photos belong to a group, so the photo inventory has to be sent before any browsing
is possible. Adding every photo's `relative_path` costs about 203 KB of JSON for the reference
library; adding `sha256` as well would cost about 572 KB.

**Originals are too large to display.** Measured on the reference library: median original 3.09 MB,
largest 13.77 MB, 8160x6144, whole library 15.9 GB. A longest-edge-capped render collapses that:
2000px renders measured 31 KB, 332 KB and 457 KB for originals of 0.4 MB, 3.1 MB and 13.8 MB. The
render's size stops depending on the original's size, which is the point. Producing one render takes
roughly 150-300 ms for the largest photo.

**`sha256` is already computed for every photo and already stable.** `sha256_file()` runs during
every scan (`photos.py:161`) and is stored on every `Photo`. In the reference library all 5059 photos
carry one. That means content identity needs no new computation, and marks and renders can both be
keyed by it.

**`do_GET` currently serves exactly one route.** `server.py:88-99` answers `/` with the cached page and
404s everything else. The server already binds loopback only and rejects non-loopback `Host` headers.

**The export must stay self-contained.** Browsers refuse `file://` subresources loaded into an
`http://` page, so a `file://` image reference would work in the exported file and be blocked in the
served page. Any browsing feature therefore has to be served-mode-only unless the bytes are embedded,
and embedding 15.9 GB is impossible.

**The edition file reconstructs itself field by field.** `set_label`, `remove_label`, `set_tag` and
`clear_tag` in `labels.py` each build a fresh `LabelOverlay` by explicitly naming every field. Adding
a field to that dataclass means touching all four, and missing one drops the field silently.

## Goals / Non-Goals

**Goals:**

- The browser learns the photo inventory for a group cheaply, and only when it needs it.
- A displayed image whose cost does not scale with the original file, and whose first-request cost is
  paid once per photo rather than once per group.
- A mark identity that survives rescans and file moves without new bookkeeping.
- Closing the cross-origin image-read hole before the new route exists, not after.
- No risk to the user's library: the change writes at most the edition file and a disposable cache.

**Non-Goals:**

- No action on marked photos. See `proposal.md` - that is a separate change.
- No change to grouping, to the scanner, or to the export. Group membership stays derived on every
  view; sub-group membership would need persisted explicit membership and its own keys.
- No tri-state and no rejection reason. Binary only, as decided.
- No full-resolution zoom and no preloading of the whole group.

## Decisions

### D1. The render cap is 2000px on the longest edge

**Chosen.** 2000px fills a typical desktop viewport at device pixel ratio 2 and stays large enough to
judge sharpness, focus and framing.

**Alternatives.** 1600px is cheaper to produce and adequate for a 1080p screen, but is visibly soft on
a high-density display. Serving originals was rejected: a decoded 8160x6144 image occupies on the
order of 200 MB of memory in the browser, and stepping through 47 of them is not a fluid experience
regardless of loopback bandwidth.

### D2. Renders are produced lazily, one photo at a time, and cached by content hash

**Chosen.** A request for a render that is not cached produces one render, stores it under the
photo's `sha256`, and returns it. Later requests serve the stored file.

**Alternatives.** Generating the whole group on open costs about 14 seconds for a 47-photo group
before anything appears, which is worse than the status quo. Keeping a bounded in-memory LRU was
rejected because the cache must survive across sessions to be worth anything. Eagerly embedding
thumbnails for all groups is what already pushed the export to 2 MB; scaling that to every photo in
every group is not viable.

**Consequence.** The first pass over a group pays roughly 150-300 ms per photo, which is invisible
because one photo is displayed at a time. Every later visit is a plain file read.

### D3. The cache is keyed by content hash and lives beside the index

**Chosen.** `<index-base>-renders/<sha256>.jpg`, following the existing `-edicion` and `-sugerencias`
sibling-file convention.

**Alternatives.** A user cache directory under the OS profile was rejected because the render is
derived data that belongs next to the index it was derived from, and the existing convention already
solves locating it. Keying by `relative_path` was rejected because it goes stale when a file moves,
which is the exact case content identity fixes.

**Consequence.** Two files with identical content share one cached render. That is correct rather
than wasteful. The whole directory is disposable and can be deleted at any time.

### D4. The client never names a file on disk

**Chosen.** The browser sends a photo reference. The server looks the reference up in the scanned
index, takes the resulting `sha256`, and reads only `<cache>/<sha256>.jpg` or
`<root>/<relative_path>`. The caller-supplied string is never used as a path component.

**Alternatives.** A `?path=` query parameter validated with `Path.resolve()` and an
`is_relative_to(root)` check is the common approach and is safe when written carefully, but it makes
correctness depend on a validation routine being complete. Resolving through the index makes
traversal unrepresentable: a value that is not in the index does not reach the filesystem at all.

**Consequence.** `../` segments, absolute paths, URL-encoded traversal and symlink games are all
refused by the same lookup miss. Validation is still worth keeping as defence in depth, but it is no
longer load-bearing.

### D5. The render route requires the token, and cross-origin reads are refused

**Chosen.** The route demands the same random token the page carries, supplied as a header so the
browser preflights it, exactly as the edit route already does. Additionally, refuse any request whose
`Sec-Fetch-Site` header is `cross-site` or `same-site`.

**Why.** The server deliberately sends no CORS headers, which prevents a foreign page from *reading* a
response. That protection does not apply to `<img>`, which renders cross-origin without CORS. Today
`do_GET` returns only the page the user is already looking at, so nothing leaks. The moment a route
returns photo bytes, any page the user visits while the server runs could embed
`http://127.0.0.1:<port>/render?...` and display a photo. Requiring the token prevents that, because a
foreign page cannot read it out of the served document.

### D6. The viewer receives photo references only in served mode

**Chosen.** The extra payload is emitted only when the page is being served, not on the export path.

**Alternatives.** Shipping the inventory in the export too would add about 203 KB to a file whose
current selling point is being small, for data the export cannot act on.

### D7. Marks live in the edition file as a flat list of content hashes, at version 3

**Chosen.** `marked: list[str]`, alongside `labels`, `tags` and `tagged`. Version becomes 3, versions 1
and 2 keep loading with an empty list, and reading never rewrites the file.

**Alternatives.** A separate `<index>-marcas.json` file was considered seriously and is conceptually
cleaner, because marks are keyed by content hash while everything else is keyed by group date. It
lost because `labels.py` already has the migration chain, the validator, the atomic writer and the
single-writer rule, and a second user-edited file means a second writer to reason about. The mixed key
space is mild: `marked` is a flat list, not a map, so it never collides with the group-keyed maps.
Cost of `labels.py` as a module name now understating its contents is recorded as accepted debt.

### D8. Orphan marks are dropped in memory on read, not in the file

**Chosen.** On load, marks whose hash is absent from the index are filtered out of the in-memory
overlay. The file is rewritten only when the user next saves an edit.

**Alternatives.** Pruning on write was rejected because it would destroy a mark whose photo is
temporarily missing, for example a drive that is not mounted. Filtering on read keeps the durable
record intact while stopping the viewer from reporting marks that resolve to nothing.

### D9. The 4-setter hazard gets a dedicated test, not a code convention

**Chosen.** A test that saves a mark and then exercises each of `set_label`, `remove_label`,
`set_tag` and `clear_tag`, asserting the marks survive each one.

**Why.** The failure mode is silent. A forgotten field in one constructor produces no error; it just
drops the user's marks the next time they retag a card, and they find out days later. A convention in
a comment does not survive; a test does.

## Flow: browsing a group

```
browser                          server                      disk
  |                                 |                           |
  |-- click group card ------------>|                           |
  |   (GET /api/photos?group=KEY)   |                           |
  |-------------------------------->|                           |
  |                                 |-- index lookup by key -->|
  |                                 |   (same groups the cards  |
  |                                 |    already resolved)      |
  |                                 |-- reply: ordered          |
  |<--------------------------------|    [ref, sha256, marked]  |
  |                                 |                           |
  |-- open browser, photo 1 -------->|                           |
  |   (GET /render?ref=.. + token)   |                           |
  |-------------------------------->|                           |
  |                                 |-- <cache>/<sha256>.jpg ?  |
  |                                 |        |                  |
  |                                 |     miss                  |
  |                                 |-- render at 2000px ------>| (open original)
  |                                 |-- write <sha256>.jpg ---->| (store)
  |                                 |                           |
  |<--------------------------------| 200 image (31-457 KB)     |
  |                                 |                           |
  |-- press next -------------------->|                           |
  |   (GET /render?ref=.. + token)   |-- cache hit ------------>|
  |<--------------------------------| 200 image, no reprocessing |
  |                                 |                           |
```

The inventory request happens once when the browser opens. Each navigation is one independent render
request, so a slow render delays only its own photo.

## Flow: marking the displayed photo

```
browser                          server                      disk
  |                                 |                           |
  |-- press mark ------------------>|                           |
  |   POST /api/marks               |                           |
  |   {token, ref, marked: true}    |                           |
  |-------------------------------->|                           |
  |                                 |-- resolve ref via index  |
  |                                 |   -> sha256              |
  |                                 |-- overlay.marked.add()   |
  |                                 |-- write_edicion atomically|
  |                                 |   (edition v3) ------->  |
  |<--------------------------------| 200 {marked: true}       |
  |                                 |                           |
  |   update indicator, no reload   |                           |
```

Unmarking is the same flow with the hash removed. Both are explicit toggles; there is no implicit
inverse state to get wrong.

## Risks / Trade-offs

- **A forgotten field in one of the four overlay constructors silently drops marks.** → Dedicated
  regression test per setter; see D9.
- **The render cache can grow without bound.** 2000px renders run 31-457 KB and the reference library
  holds 5059 photos, so a full pass over everything could reach roughly 1.3 GB beside the index.
  → Acceptable because the cache is disposable and per-photo lazy, so it only reaches that size after
  the user has actually looked at every photo. A size cap with eviction is deliberately left out of
  this change; if it matters, it is a separate decision.
- **The first pass over a group is slower than later passes.** → Inherent to lazy generation and
  masked by the fact that one photo is shown at a time. Prefetching neighbours was rejected: it adds
  a concurrency concern to a single-threaded server for a latency nobody perceives.
- **Version 3 makes the edition file unreadable by the previous release.** → Documented in
  `proposal.md` - Rollback plan, with a file backup as the mitigation.
- **Marks do not distinguish "rejected" from "never seen".** → Accepted by decision. Sequential
  browsing makes the next unmarked photo the pending one, so the gap does not cost the user much yet.
- **`labels.py` and `LabelOverlay`'s docstring no longer describe the file's full contents.**
  → Accepted debt, listed in `proposal.md`. Renaming the module is a mechanical follow-up that should
  not ride along with a feature change.

## Migration Plan

1. Land the render helper and cache, with no behaviour change on its own.
2. Land edition version 3 with `marked` defaulting to empty, carried through all four constructors,
   plus the D9 regression test. At this point nothing writes a mark yet, so every existing edition
   file keeps loading and simply gains an empty list on next save.
3. Land the authenticated render route and close the cross-origin read.
4. Land the viewer browser and the mark endpoint.
5. Verify against the reference library: confirm the export is byte-for-byte unchanged in size
   modulo its existing variation, and confirm no photo in the library root is modified.

Rollback strategy is in `proposal.md`. Steps 1 and 3 are additive and independently revertible;
step 2 is the one that changes the file format.