# Spec Delta

## MODIFIED Requirements

### Requirement: Photo bucket sections on the landing page

When at least one photo belongs to a bucket, the landing page MUST present one card for each
bucket that holds at least one photo. Each card MUST show the bucket name, the number of photos it
holds, the earliest and latest capture dates when known, and at most five thumbnails from the
bucket, using the same card presentation as a group card. If the bucket has fewer than five
photos, the card MUST show all of them. The card MUST NOT show a country and MUST NOT offer group
label or tag controls, because a bucket is not a group. A bucket in the catalogue that holds no
photo MUST NOT produce a card. Photos that belong to no bucket MUST NOT appear in any photo card.

The marked card, when present, MUST appear before the bucket cards. The bucket cards MUST appear
after the group cards and group sections, in the order the bucket catalogue lists them. In the
served viewer, each bucket card MUST offer a control that opens the full bucket in the photo grid.
The photos in a bucket MUST be ordered by the same order the photos are browsed in.

#### Scenario: One section per bucket

- **GIVEN** an edition file that places two photos in "Favoritas" and one photo in "Para imprimir"
- **WHEN** the landing page is generated
- **THEN** a "Favoritas" card reporting two photos and a "Para imprimir" card reporting one appear
- **AND** each card shows at most five thumbnails

#### Scenario: A photo may appear in more than one section

- **GIVEN** a photo that belongs to both "Favoritas" and "Para imprimir"
- **WHEN** the landing page is generated
- **THEN** the photo appears in the "Favoritas" card
- **AND** the photo also appears in the "Para imprimir" card

#### Scenario: Photos in no bucket get their own section

- **GIVEN** an edition file that places one photo in "Favoritas" and leaves every other photo in no bucket
- **WHEN** the landing page is generated
- **THEN** the "Favoritas" card appears
- **AND** no card appears for the photos in no bucket

#### Scenario: An empty bucket produces no section

- **GIVEN** a bucket catalogue holding "Favoritas" and "Para imprimir"
- **WHEN** no photo belongs to "Para imprimir" and the landing page is generated
- **THEN** a "Favoritas" card appears
- **AND** no "Para imprimir" card appears

#### Scenario: No buckets means no photo sections

- **GIVEN** an edition file in which no photo belongs to any bucket
- **WHEN** the landing page is generated
- **THEN** no bucket card and no untagged photos card appear

#### Scenario: Bucket sections follow the group sections

- **GIVEN** an edition file that assigns a group tag to one group, marks one photo and places two photos in "Favoritas"
- **WHEN** the landing page is generated
- **THEN** the group sections appear first
- **AND** the "Marcadas" card appears after them
- **AND** the "Favoritas" card appears after the "Marcadas" card

#### Scenario: A bucket with more than five photos shows a bounded preview

- **GIVEN** an edition file that places twelve photos in "Favoritas"
- **WHEN** the landing page is generated
- **THEN** the "Favoritas" card reports twelve photos
- **AND** it shows exactly five thumbnails

#### Scenario: Opening a bucket card shows the full bucket

- **GIVEN** a served viewer and a "Favoritas" bucket holding twelve photos
- **WHEN** the user activates the control that opens the bucket
- **THEN** the photo grid lists all twelve photos
- **AND** it lists them in the order the photos are browsed in

### Requirement: Both axes coexist on one page

The landing page MUST present the group cards and group sections together with the marked and
bucket cards, in a single page, with the group cards and group sections first. A library with no
group tags, no marks and no buckets MUST be presented exactly as it is before this change: one
flat list of group cards ordered by date. Adding buckets or marks MUST NOT change how any group
card is titled, how many photos it reports, or which group it belongs to. A marked or bucketed
photo MUST remain in its group card as well as appearing in the photo cards that contain it.

#### Scenario: The two axes on one page

- **GIVEN** an edition file that assigns the group tag "Familia" to one group and places two photos in "Favoritas"
- **WHEN** the landing page is generated
- **THEN** a "Familia" section holding that group's card and a "Favoritas" card both appear in the same document
- **AND** the "Familia" section appears before the "Favoritas" card

#### Scenario: A library with neither tags nor marks is unchanged

- **GIVEN** an edition file holding no group tags, no marks and no buckets
- **WHEN** the landing page is generated
- **THEN** the cards appear in a single list ordered by date
- **AND** no section heading appears

#### Scenario: Buckets do not alter the group cards

- **GIVEN** a group card reporting a photo count, a date range and a country
- **WHEN** two of its photos are placed in a bucket
- **THEN** the card still reports the same photo count, date range and country
- **AND** the card is still in the same group

#### Scenario: A marked or bucketed photo remains in its group card

- **GIVEN** a photo that belongs to a group, is marked, and is placed in a bucket
- **WHEN** the landing page is generated
- **THEN** the photo still belongs to the same group card
- **AND** it also appears in the "Marcadas" card
- **AND** it also appears in the bucket card

### Requirement: Photos in the viewer open at the photo itself

A photo shown in the photo grid opened from a marked or bucket card MUST open the served browser
at that photo when the user selects it, so that a photo reached from a bucket is immediately
bucketed and markable. A photo with no capture date MUST still be reachable this way, and MUST NOT
be excluded from any photo card or its grid because its date is unknown.

#### Scenario: Selecting a photo opens the browser at it

- **GIVEN** a served viewer and a photo listed in the "Favoritas" bucket card
- **WHEN** the user opens the card's photo grid and selects that photo
- **THEN** the browser opens showing that photo
- **AND** the picker shows the buckets that photo belongs to

#### Scenario: A photo without a capture date is still listed

- **GIVEN** a photo with no capture date that belongs to "Favoritas"
- **WHEN** the landing page is generated
- **THEN** the photo is part of the "Favoritas" card and its full bucket
- **AND** selecting it in the photo grid opens the browser at that photo

### Requirement: Dragging does not assign buckets

Dragging a group card onto a marked or bucket card MUST NOT assign any bucket to any photo, and the
viewer MUST report that photo cards do not accept a dragged card, because a photo may belong to
several buckets at once and a drag cannot express which of them is meant. Photo cards MUST NOT be
draggable and MUST NOT offer a drop target for group cards. This MUST NOT change what dragging a
card onto a group section does.

#### Scenario: A card dropped on a photo section is refused

- **GIVEN** a running server and a group card with no group tag
- **WHEN** the user drags that card onto the "Favoritas" card
- **THEN** the viewer reports that photo cards do not accept a dragged card
- **AND** no bucket assignment is stored

#### Scenario: Photo sections offer no drop target

- **GIVEN** a running server and a landing page with a "Favoritas" card
- **WHEN** the page reports what can be dragged onto
- **THEN** the photo cards are not among the drop targets

#### Scenario: Photo cards are not draggable

- **GIVEN** a served landing page with a "Marcadas" card and a "Favoritas" card
- **WHEN** the user tries to drag either photo card
- **THEN** no drag starts
- **AND** no group tag or bucket assignment changes

#### Scenario: Dragging a card onto a group section is unaffected

- **GIVEN** a served landing page with a group card with no tag and a group section "Familia"
- **WHEN** the user drags the card onto the "Familia" section
- **THEN** the group's tag assignment is stored as before

### Requirement: The exported HTML shows the photo sections read-only

The exported HTML MUST present the marked and bucket cards. It MUST NOT present a flat photo
section or an untagged photos card. It MUST NOT offer any control that opens the served browser,
changes a bucket assignment, or creates a bucket name. The exported document MUST contain no
bucket picker and no drop target, exactly as it contains no tag editor.

#### Scenario: Sections in the export

- **GIVEN** an edition file that marks two photos and places one photo in "Favoritas"
- **WHEN** the exported HTML is generated with `view` and no `--serve`
- **THEN** the "Marcadas" and "Favoritas" cards appear in the export
- **AND** each card shows at most five thumbnails
- **AND** no flat photo section appears

#### Scenario: The export has no bucket controls

- **GIVEN** an exported HTML document that shows a bucket card
- **WHEN** the document is inspected
- **THEN** it offers no control to change a bucket assignment or to write a new bucket name

#### Scenario: The export has no picker

- **GIVEN** an exported HTML document
- **WHEN** the document is inspected
- **THEN** it contains no bucket picker for any photo

#### Scenario: The export has no browsing control

- **GIVEN** an exported HTML document that shows a marked or bucket card
- **WHEN** it is opened in a browser
- **THEN** no control that opens the served browser is offered

## ADDED Requirements

### Requirement: An unavailable library folder is resolved or reported

The viewer and the served endpoints MUST resolve photo files against the library folder the index
declares. When that folder is not available, they MUST resolve them against the folder the paired
suggestions file declares, so an index whose own folder is missing still shows previews. When
neither folder is available, the viewer MUST report that the library folder could not be found and
MUST NOT present the photo sets as empty.

#### Scenario: The folder the index declares is unavailable

- **GIVEN** an index whose declared folder no longer exists and a paired suggestions file whose declared folder does exist
- **WHEN** the landing page is generated
- **THEN** the cards show thumbnails from the folder the suggestions file declares

#### Scenario: Neither declared folder is available

- **GIVEN** an index and a paired suggestions file whose declared folders do not exist
- **WHEN** the landing page is generated
- **THEN** the document reports that the library folder could not be found
- **AND** the missing previews are not explained as photos belonging to another group

### Requirement: Photo-set previews fail without the group explanation

A photo-set card that cannot produce its thumbnails MUST keep reporting the real number of photos in
the set and MUST state that its previews could not be produced. It MUST NOT state that the photos
fall into another group, because that explanation only fits a declared group card. The served grid
MUST show a placeholder for a photo whose thumbnail cannot be served, and selecting that cell MUST
still open the browser, which reports its own failure when the full render cannot be produced.

#### Scenario: A bucket whose previews cannot be produced

- **GIVEN** a bucket whose photo files cannot be read
- **WHEN** the landing page is generated
- **THEN** the bucket card reports the number of photos it holds
- **AND** it states that its previews could not be produced
- **AND** it does not say the photos fall into another group

#### Scenario: A grid cell whose thumbnail cannot be served

- **GIVEN** a served viewer and a bucket whose photo thumbnail cannot be produced
- **WHEN** the user opens the bucket's grid
- **THEN** the cell for that photo shows a placeholder instead of a broken image
- **AND** selecting the cell still opens the browser at that photo

## REMOVED Requirements

### Requirement: A photo section draws a bounded number of photos

**Reason**: The flat photo section is replaced by a photo-set card whose preview is bounded to at
most five thumbnails, so the old 300-photo section no longer exists.

**Migration**: The marked and bucket cards are now the only landing-page presentation for those
sets. The served viewer opens the full set in the photo grid; the exported HTML shows the
five-thumbnail card and no flat photo section.
