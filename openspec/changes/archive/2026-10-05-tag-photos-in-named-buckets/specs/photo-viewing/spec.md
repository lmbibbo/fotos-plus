# Spec Delta

## ADDED Requirements

### Requirement: Photo bucket sections on the landing page

When at least one photo belongs to a bucket, the landing page MUST present a section for each
bucket that holds at least one photo, listing the photos that belong to it. Each such section MUST
show the bucket name and how many photos it holds, and MUST order its photos by the same order the
photos are browsed in. A bucket in the catalogue that holds no photo MUST NOT produce a section. The
photos that belong to no bucket MUST be presented in a section of their own, placed after every
bucket section.

Bucket sections MUST come after the group sections, in the order the bucket catalogue lists them.
When no photo belongs to any bucket, the landing page MUST NOT present any bucket section and MUST
NOT present the untagged photos section.

#### Scenario: One section per bucket

- **GIVEN** an edition file that places two photos in "Favoritas" and one photo in "Para imprimir"
- **WHEN** the landing page is generated
- **THEN** a "Favoritas" section listing two photos and a "Para imprimir" section listing one appear
- **AND** each section reports how many photos it holds

#### Scenario: A photo may appear in more than one section

- **GIVEN** a photo that belongs to both "Favoritas" and "Para imprimir"
- **WHEN** the landing page is generated
- **THEN** the photo is listed under "Favoritas"
- **AND** the photo is also listed under "Para imprimir"

#### Scenario: Photos in no bucket get their own section

- **GIVEN** an edition file that places one photo in "Favoritas" and leaves every other photo in no bucket
- **WHEN** the landing page is generated
- **THEN** the photos in no bucket appear in a section of their own
- **AND** that section appears after the "Favoritas" section

#### Scenario: An empty bucket produces no section

- **GIVEN** a bucket catalogue holding "Favoritas" and "Para imprimir"
- **WHEN** no photo belongs to "Para imprimir" and the landing page is generated
- **THEN** a "Favoritas" section appears
- **AND** no "Para imprimir" section appears

#### Scenario: No buckets means no photo sections

- **GIVEN** an edition file in which no photo belongs to any bucket
- **WHEN** the landing page is generated
- **THEN** no bucket section and no untagged photos section appear

#### Scenario: Bucket sections follow the group sections

- **GIVEN** an edition file that assigns a group tag to one group and places two photos in "Favoritas"
- **WHEN** the landing page is generated
- **THEN** the group sections appear first
- **AND** the bucket sections appear after all of them

### Requirement: A photo section draws a bounded number of photos

A photo section MUST NOT embed more than 300 photos, and its heading MUST report how many photos the
section actually holds. When photos are held back, the section MUST say so and point at the photo
browser, which lists every photo of the group without embedding them. The bound applies to every photo
section, including the marked section and the untagged photos section, and the exported HTML inherits
it.

Bounding the section is what keeps the document from growing with the library. The untagged photos
section is the one that needs it: it holds every photo in no bucket, so it holds the whole library
unless most photos are in buckets. Marking a single photo in a library of 2000 must not turn a page
of 130 KB into one the browser cannot open.

#### Scenario: A section within the bound draws every photo

- **GIVEN** an edition file that places 12 photos in "Favoritas"
- **WHEN** the landing page is generated
- **THEN** all 12 photos are drawn
- **AND** no note about held-back photos appears

#### Scenario: A section over the bound draws only the first 300

- **GIVEN** an edition file that places 500 photos in "Favoritas"
- **WHEN** the landing page is generated
- **THEN** the "Favoritas" heading reports 500 photos
- **AND** at most 300 photos are drawn
- **AND** a note says how many were held back and points at the photo browser

#### Scenario: Marking one photo in a large library keeps the page openable

- **GIVEN** a library of 2000 photos and an edition file that marks exactly one of them
- **WHEN** the landing page is generated
- **THEN** the untagged photos section holds at most 300 drawn photos

### Requirement: Both axes coexist on one page

The landing page MUST present the group sections and the photo sections together, in a single page,
with the group sections first. A library with no group tags and no marks MUST be presented exactly
as it is before this change: one flat list of group cards ordered by date. Adding buckets or marks
MUST NOT change how any group card is titled, how many photos it reports, or which group it belongs
to.

#### Scenario: The two axes on one page

- **GIVEN** an edition file that assigns the group tag "Familia" to one group and places two photos in "Favoritas"
- **WHEN** the landing page is generated
- **THEN** a "Familia" section holding that group's card and a "Favoritas" section holding the two
  photos both appear in the same document
- **AND** the "Familia" section appears before the "Favoritas" section

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

### Requirement: Photos in the viewer open at the photo itself

A photo shown in a photo section MUST open the served browser at that photo when the user selects
it, so that a photo reached from a bucket is immediately bucketed and markable. A photo with no
capture date MUST still be reachable this way, and MUST NOT be excluded from any photo section
because its date is unknown.

#### Scenario: Selecting a photo opens the browser at it

- **GIVEN** a served viewer and a photo listed under the bucket "Favoritas"
- **WHEN** the user selects that photo
- **THEN** the browser opens showing that photo
- **AND** the picker shows the buckets that photo belongs to

#### Scenario: A photo without a capture date is still listed

- **GIVEN** a photo with no capture date that belongs to "Favoritas"
- **WHEN** the landing page is generated
- **THEN** the photo is listed in the "Favoritas" section
- **AND** selecting it opens the browser at that photo

### Requirement: Dragging does not assign buckets

Dragging a group card onto a photo section MUST NOT assign any bucket to any photo, and the viewer
MUST report that photo sections do not accept a dragged card, because a photo may belong to several
buckets at once and a drag cannot express which of them is meant. Photo sections MUST NOT offer a
drop target for group cards. This MUST NOT change what dragging a card onto a group section does.

#### Scenario: A card dropped on a photo section is refused

- **GIVEN** a running server and a group card with no group tag
- **WHEN** the user drags that card onto the "Favoritas" photo section
- **THEN** the viewer reports that photo sections do not accept a dragged card
- **AND** no bucket assignment is stored

#### Scenario: Photo sections offer no drop target

- **GIVEN** a running server and a landing page with a "Favoritas" photo section
- **WHEN** the page reports what can be dragged onto
- **THEN** the photo sections are not among the drop targets

#### Scenario: Dragging a card onto a group section is unaffected

- **GIVEN** a running server and a group card with no group tag
- **WHEN** the user drags that card onto the group section "Familia"
- **THEN** the group's tag assignment is stored as before

### Requirement: The exported HTML shows the photo sections read-only

The exported HTML MUST present the bucket sections and the untagged photos section, and MUST NOT
offer any control that changes a bucket assignment or creates a bucket name. The exported document
MUST contain no bucket picker and no drop target, exactly as it contains no tag editor.

#### Scenario: Sections in the export

- **GIVEN** an edition file that places two photos in "Favoritas"
- **WHEN** the exported HTML is generated with `view` and no `--serve`
- **THEN** a "Favoritas" section listing the two photos appears in the export

#### Scenario: The export has no bucket controls

- **GIVEN** an exported HTML document that shows a bucket section
- **WHEN** the document is inspected
- **THEN** it offers no control to change a bucket assignment or to write a new bucket name

#### Scenario: The export has no picker

- **GIVEN** an exported HTML document
- **WHEN** the document is inspected
- **THEN** it contains no bucket picker for any photo
