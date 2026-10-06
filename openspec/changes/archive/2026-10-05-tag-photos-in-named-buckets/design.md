# Design

## Context

See `proposal.md` - Why for the motivation. What follows is only the current state that constrains
the approach.

The edition file is the single writer-owned store for everything the user curates. At version 3 it
holds four fields: `labels` keyed by group key, an ordered `tags` catalogue, `tagged` mapping a
group key to one tag, and `marked` as a flat list of content hashes. Two rules govern every edit:
each operation reconstructs the whole file field by field, and reading never rewrites. Versions 1
and 2 stay readable and are migrated in memory, so bumping `EDITION_VERSION` and widening
`SUPPORTED_EDITIONS` is the established way to extend this file.

Groups are keyed by their earliest timestamp, which is unique and is what the viewer already sorts
by. That is the identity for labels and group tags, and it is why the specification can reject an
ambiguous or dangling group reference.

Photos are keyed by content hash. That is the identity for marks, and it is what lets a mark survive
a rescan, a move and a rename.

The landing page is a `Section` list whose `groups` field holds whole `Group` cards, and
`group_sections` derives those sections from `tagged`. A card renders up to `THUMBNAILS_PER_GROUP`
thumbnails as inline base64. Rendering scale has bitten this project before: inlining 2000px renders
produced a 544 MB document, which is why the page is grouped and why full-screen renders are served
lazily from `/render` rather than inlined.

The served browser is one overlay that walks a flat ordered list of photos and holds the Mark
toggle. Its payload is a JSON blob emitted once into the document. The server exposes
`GET /api/photos`, `POST /api/labels` and `POST /api/marks`, all guarded by a token, a loopback
host check and a JSON content-type check.

`_flat_card` already renders a single loose photo with its capture date, and `.card.flat` already
styles it. It is currently reachable only when there are no suggestions at all, so the primitive
this change needs already exists and is already tested.

## Goals / Non-Goals

Goals:

- Add a second organisation axis at photo granularity without weakening the first one at group
  granularity.
- Keep the fast mark path fast. A curation pass must not be pushed through a picker.
- Stay inside the existing architecture: no new files, no build step, no framework, no new
  dependency.

Non-Goals:

- No action on the photos themselves. Buckets stay an intention, like marks.
- No reordering or renaming of buckets beyond the catalogue order the picker already implies.
- No pagination. See the scale decision below for why this is acceptable now and what it costs.
- No bulk operations across a group. Buckets are assigned to one photo at a time.
- Folding marks into a reserved bucket. That is a separate follow-up; see the decision below.

## Decisions

### Bucket membership is a map of hash to list of names

`photo_tagged: { <sha256>: [<bucket name>, ...] }`, with the value being a list rather than a single
name.

The alternative was `{ <sha256>: <bucket name> }`, which mirrors exactly how `tagged` stores one tag
per group and would have bought a free drag-and-drop gesture.

It was rejected because buckets that overlap are the normal case when curating. A photo tagged
"Favoritas" and "Para imprimir" is ordinary, and a single-name map makes that unrepresentable. The
cost of the list is real but bounded: one place becomes ambiguous, namely how to express "put this
photo in that bucket". Everything else, including section construction and pruning, treats the value
as an opaque set.

Storing the assignment on the photo rather than the reverse map `{ <bucket name>: [<sha>, ...] }`
keeps it symmetrical with `tagged`, keeps a photo's whole membership reachable with one lookup, and
means removing a bucket from a photo cannot leave a dangling entry in another bucket's list.

### The bucket catalogue is separate from the group tag catalogue

A new `photo_tags` list rather than reusing `tags`.

The alternative was sharing `tags`, which would have needed no new field and no new picker list. It
was rejected because the two axes mean different things. A group tag classifies a trip; a bucket
curates individual photos. Sharing one catalogue would let "Familia" appear as a section of group
cards and as a section of loose photos holding entirely different things, and a user could not tell
which axis a name belonged to. It would also make the existing "a new tag is indistinguishable from
an existing one" rule apply across axes, so adding a bucket name would silently be able to collide
with a group tag name.

The cost is a second list to maintain and a second name to type in the picker.

### Marks stay a separate concept with a section of their own

`marked` is untouched and gets its own landing page section.

The alternative was making the mark a reserved bucket, folding `marked` into `photo_tagged` and
retiring the concept. That is cleaner as a model, and it is the reason this was worth writing down
rather than just choosing.

It was rejected on two grounds. First, tempo. The purpose of `photo-marking` is that a curation pass
over a large library produces a durable shortlist, and a pass is fast and repetitive; the mark stays
a single click precisely so that hundreds of photos can be triaged without opening anything. A
bucket is added through a picker. Making the mark a bucket would force the fast path through the
slow control so the two would look uniform, which trades a real ergonomic property for a cosmetic
one. Second, pruning. `prune_marked` already discards hashes absent from the index without
rewriting the file, and bucket assignments need the same rule; keeping the two keyspaces apart means
each has one clear pruning rule instead of one rule that has to serve both.

The cost is that "Marked" is not editable the way a bucket is, and the page carries two concepts
that a user could reasonably expect to be one. That is stated openly in the photo-marking spec
rather than papered over.

### Dragging stays a move; buckets are edited with a picker

Dragging a group card onto a group section means "move that group to this tag", and that is
unchanged. Photos get no drag target at all.

The alternative was dragging a photo onto a section to add it, which reads naturally but is
ambiguous the moment membership is not exclusive: dropping a photo into "Para imprimir" could mean
add it, move it there from its only bucket, or do nothing because it is already in another one. The
picker resolves this by being explicit, one control per bucket, and it also has to exist anyway
because a bucket name can be written that is not yet in the catalogue.

The cost is that the gesture that works on cards does not work on photos, which is inconsistent and
will be noticed. The photo sections therefore report that they accept no dragged card rather than
silently ignoring the drop.

### Sections are ordered group, then marks, then buckets, then untagged

Group sections keep their existing ordering rule, ascending by the earliest timestamp of the first
card. Bucket sections follow in catalogue order, and the untagged photos section comes last.

Bucket sections are ordered by catalogue order rather than by date because the order is the user's
own, and a user who lists "Favoritas" before "Para imprimir" should see them in that order. This is
deliberately unlike group sections, which are date-ordered because they predate any user ordering of
names.

Placing bucket sections after the group sections keeps the page the user already knows as the first
thing they see, and makes the new axis removable without disturbing the old one.

### Sections render thumbnails, never renders

Every photo in a photo section is a thumbnail. No photo section may inline a 2000px render.

Measured on a 4032x3024 source with per-pixel noise, four thousand foliage clumps and 7px line
structure, `make_thumbnail` yields about 5.7 KB at the existing 200px quality 70, about 7.9 KB of
markup per photo once base64 and the card wrapper are counted. That puts a 400-photo section near
3.1 MB and a 1200-photo section near 9.2 MB.

For contrast, the render that caused the 544 MB document is about 457 KB per photo at 2000px, which
is where the eighty-fold margin comes from. The existing lazy `/render` path and
`RENDER_CACHE` stay the only way a full-sized image reaches the browser.

A photo section draws at most 300 photos, mirroring `THUMBNAILS_PER_GROUP`, which already caps group
cards at 5 thumbnails so their cost does not grow with the library. A photo section has no such
recuperación: each photo is an embedded thumbnail, so without a bound the document grows with the
number of photos in the section. The heading keeps reporting the true count, and a note says how many
photos were held back and points at the photo browser, which already lists every photo of a group
without embedding them. The exported HTML inherits the bound for free because it renders the same
sections.

This bound is not a hypothetical safeguard. Measured against a library of 2000 real-sized photos,
marking a single photo grew the landing page from 130 KB to 42.7 MB and 3.2 s to build, because the
untagged photos section then held the entire library; the browser could not open it. With the bound
the same page is 1.75 MB and opens in well under a second. The untagged section is the reason the
bound has to apply to every photo section and not only to large buckets.

Beyond this change, pagination is still the right answer for a genuinely huge bucket: showing the
first 300 tells the user what is in there, but it does not let them reach photo 301 from the page.
That is a separate change and is not blocked by anything in this one.

### Pruning is generalised, not duplicated

The existing mark pruning becomes one helper that resolves a set of content hashes against the
index and returns the subset present, and both `marked` and `photo_tagged` go through it.

Bucket names are deliberately kept in the catalogue when their last photo is pruned, matching how
`group-labels` keeps unresolved tag assignments for the user to decide on. Dropping the name would
make a pruned assignment silently unrecoverable even if the photo returned.

### Adding a bucket to the displayed photo

The picker sits next to the Mark control in the browser overlay, because that is where the user
already is: looking at one photo, deciding about it. The browser walks a flat ordered list of
photos, so the picker only ever needs the current photo's membership, which is why the payload
carries bucket names per photo rather than a bucket-to-photos index in the client.

```
  user                 browser JS            POST /api/photo-tags      labels.py        edicion.json
   |                       |                          |                     |                 |
   |  clicks "Favoritas"  |                          |                     |                 |
   |---------------------->|                          |                     |                 |
   |                       |  sha, bucket name        |                     |                 |
   |                       |------------------------->|                     |                 |
   |                       |                          |  validate name      |                 |
   |                       |                          |  resolve sha        |                 |
   |                       |                          |-------------------->|                 |
   |                       |                          |                     | add name to      |
   |                       |                          |                     | photo_tags if    |
   |                       |                          |                     | new; append to   |
   |                       |                          |                     | photo_tagged[sha]| 
   |                       |                          |                     |---------------->|
   |                       |                          |                     |                 |
   |                       |                          |                     |  carry marked,   |
   |                       |                          |                     |  labels, tags,   |
   |                       |                          |                     |  tagged through  |
   |                       |                          |                     |  unchanged       |
   |                       |                          |  atomic replace    |                 |
   |                       |                          |<--------------------|                 |
   |                       |  ok + membership         |                     |                 |
   |                       |<-------------------------|                     |                 |
   |  picker updates,     |                          |                     |                 |
   |  no reload           |                          |                     |                 |
   |<----------------------|                          |                     |                 |
```

The rejection path is the same shape and ends with a reason and the unchanged membership, so the
picker can revert to what the server actually holds rather than to what it optimistically showed.

### Generating the page with both axes

```
  render_html()      group_sections()   photo_sections()   _flat_card()
       |                    |                   |                 |
       | groups + tagged    |                   |                 |
       |------------------->|                   |                 |
       | Section(group=...) |                   |                 |
       |<-------------------|                   |                 |
       |                                        |                 |
       | photos + photo_tagged + marked         |                 |
       |---------------------------------------->|                 |
       |                    | marked  -> 1 section     |                 |
       |                    | photo_tagged -> 1 per bucket
       |                    | no bucket -> 1 untagged |
       |                    | catalogue order, untagged last
       |                                        |                 |
       |                                        | thumbnail only  |
       |                                        |---------------->|
       |                                        | ~7.9 KB markup  |
       |                                        |<---------------|
       |                                        |                 |
       | group sections, then photo sections    |                 |
       |<---------------------------------------|                 |
```

`Section` grows a second form that holds photos instead of groups. `group_sections` is left alone
so the existing seven `group-labels` scenarios and the `photo-viewing` tag section requirement keep
holding against unchanged code. A page with no marks and no buckets reaches the same single flat
list it reaches today.

## Risks / Trade-offs

- **Two axes on one page is unfamiliar** → Group sections stay first and keep their exact current
  shape, so the page the user knows is untouched above the fold. If the photo sections prove noisy
  they can be dropped without touching group behaviour.
- **A second concept for "I like this photo" invites the question why there are two** → Stated
  explicitly in the photo-marking spec as a deliberate deferral rather than left as an apparent
  inconsistency, and the picker and the Mark button sit next to each other so the difference between
  them is visible where it is used.
- **Dragging works on cards but not on photos** → Photo sections report that they accept no dragged
  card. A silently ignored drop reads as a bug; a reported one reads as a rule.
- **A large bucket produces a large document** → Bounded at 300 drawn photos per section, the same kind
  of bound group cards already use at 5 thumbnails. Measured on 2000 photos: marking one photo grew the
  page from 130 KB to 42.7 MB until the bound was added, after which it is 1.75 MB. Renders stay banned
  from sections, so the failure mode is a note and a truncated list, not an unopenable page. What the
  bound costs: photo 301 of a bucket is reachable from the photo browser, not from the landing page.
- **A photo in several buckets is listed several times, so counts across sections do not sum to the
  library** → This is a property of membership, not a defect. Section counts report their own
  contents and nothing claims they partition the library.
- **Widening the edition file touches every writer** → The existing rule is that each edit
  reconstructs the file field by field, and the photo-marking spec already demands that labels,
  tags and marks be carried through unchanged. Bucket fields are added to that same obligation
  rather than being bolted on, and a test per edit path is what keeps it honest.
- **Hash pruning and buckets interact with the export** → The export reads the same resolution path
  as the served page, so an unresolved assignment is invisible in both and the catalogue entry
  survives in both. Nothing in the export depends on a mark or bucket resolving to a file.

## Migration Plan

1. Widen `EDITION_VERSION` to 4 and `SUPPORTED_EDITIONS` to include it. Add `photo_tags` and
   `photo_tagged` to `LabelOverlay`, defaulting to empty, and accept versions 1 through 3 unchanged.
2. Generalise hash pruning and route `marked` through it with no behaviour change, so the existing
   photo-marking pruning scenarios pass before any bucket code exists.
3. Add the bucket resolution that builds the picker payload, still without any section.
4. Add `POST /api/photo-tags` and the picker in the browser overlay. At this point buckets are
   assignable but not yet browsable.
5. Add photo sections after the group sections, and the marked section before them.
6. Write every new file at version 4 and never rewrite an older file on read, so a user who never
   opens a bucket stays on version 3.

The first two steps are behaviour-preserving on their own and can be shipped alone. Rollback is
covered in `proposal.md` - Rollback; the short version is that no data migration runs in either
direction, and marks are never destroyed.

## Open Questions

- Whether a bucket should ever be renamed in place, propagating to every photo that holds it. The
  catalogue has no rename operation today for group tags either, and this change does not add one,
  so renaming means remove and retag. If it becomes a real need it is a delta on `photo-tagging`
  only and does not disturb this design.

The untagged photos section is specified rather than open. It duplicates the group sections in
aggregate, but it is what makes a bucket removable: without somewhere for a photo to go when its
last bucket is taken away, membership would be awkward to undo. If it later proves to be more noise
than value it can be dropped by removing one requirement and its scenarios, and no other part of
this change notices.
