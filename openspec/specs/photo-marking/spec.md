# photo-marking Specification

## Purpose

Lets the user record a binary keep/drop opinion about individual photos, so that a curation pass
over a large library produces a durable shortlist without modifying, moving or deleting anything.

## Requirements

### Requirement: Binary mark per photo

Each photo SHALL carry at most one mark, either marked or unmarked. Marking an unmarked photo and
marking a marked photo again SHALL both be accepted, so that marking and unmarking are symmetric
operations rather than a set-to-true and a separate delete. A photo that has never been visited
SHALL be indistinguishable from one that was marked and then unmarked.

#### Scenario: Marking a photo

- **GIVEN** a served viewer with a photo currently displayed and no mark on it
- **WHEN** the user marks the photo
- **THEN** the photo is stored as marked
- **AND** the displayed photo shows it as marked without requiring a reload

#### Scenario: Unmarking a photo

- **GIVEN** a served viewer with a photo currently displayed that is marked
- **WHEN** the user unmarks the photo
- **THEN** the photo is no longer stored as marked

#### Scenario: A photo viewed and unmarked is not remembered as reviewed

- **GIVEN** a photo that was marked and later unmarked
- **WHEN** the marks are listed for its group
- **THEN** that photo does not appear in the list
- **AND** no separate record of having been reviewed exists for it

### Requirement: Marks are identified by content hash

A mark SHALL reference its photo by the content hash the scanner recorded for it, and never by the
file's path. Marking therefore SHALL survive a rescan and SHALL survive the file being moved or
renamed inside the library root, as long as its content is unchanged. Two files with identical
content SHALL resolve to the same mark.

#### Scenario: A marked photo is moved to another folder

- **GIVEN** a photo that is marked, stored under one relative path
- **WHEN** the photo is moved within the library root and the library is rescanned
- **THEN** the photo at its new path is still reported as marked

#### Scenario: A rescan does not alter marks

- **GIVEN** an edition file holding marks
- **WHEN** the library is rescanned and the suggestions file is replaced
- **THEN** the marks remain in the edition file and still resolve to photos

#### Scenario: Identical content in two locations

- **GIVEN** two files whose content hash is the same
- **WHEN** one of them is marked
- **THEN** the other one is reported as marked as well

### Requirement: Marks are stored in the edition file at the current version

The edition file SHALL declare the current version, which is 4, and SHALL store marks as a flat
list of content hashes, independent of the keys that index labels, tags and buckets. Edition files
at versions 1, 2 and 3 SHALL remain readable and SHALL load with no marks, keeping the labels, tag
catalogue, tag assignments and bucket assignments they already held. Reading an edition file SHALL
NOT by itself rewrite it to a newer version. A mark entry that is not 64 lowercase hexadecimal
characters SHALL be rejected when the file is written.

#### Scenario: A version 3 edition file loads with no marks

- **GIVEN** an edition file at version 3 holding labels, tags, tag assignments and buckets
- **WHEN** the file is read
- **THEN** the labels, tag catalogue, tag assignments and buckets are all preserved
- **AND** the photo list is empty
- **AND** the file on disk still declares version 3

#### Scenario: A version 2 edition file loads with no marks

- **GIVEN** an edition file at version 2 holding labels, tags and tag assignments
- **WHEN** the file is read
- **THEN** the labels, tag catalogue and tag assignments are all preserved
- **AND** the photo list is empty
- **AND** the file on disk still declares version 2

#### Scenario: A version 1 edition file loads with no marks

- **GIVEN** an edition file at version 1 holding only labels
- **WHEN** the file is read
- **THEN** the labels are preserved
- **AND** the photo list is empty

#### Scenario: The first mark upgrades the file

- **GIVEN** an edition file at version 3 with tags already saved
- **WHEN** the user marks a photo and the edit is saved
- **THEN** the file declares version 4
- **AND** it holds the tag catalogue, the tag assignments and the mark

#### Scenario: A malformed mark is rejected on write

- **GIVEN** an edition file being saved
- **WHEN** a mark entry is not 64 lowercase hexadecimal characters
- **THEN** the save is rejected and the reason is reported
- **AND** the edition file is left unchanged

### Requirement: Marks survive unrelated edits to the same file

Saving a label, removing a label, assigning a tag or clearing a tag SHALL NOT add to, remove from or
otherwise alter the stored marks. Those operations live in the same file as the marks and each of
them reconstructs the saved content field by field, so the system SHALL carry the marks through
every one of them unchanged.

#### Scenario: Saving a label keeps the marks

- **GIVEN** an edition file holding marks and no label for some group
- **WHEN** the user saves a label for that group
- **THEN** the marks are still stored
- **AND** the saved label is stored

#### Scenario: Removing a label keeps the marks

- **GIVEN** an edition file holding marks and a label
- **WHEN** the user removes that label
- **THEN** the marks are still stored

#### Scenario: Assigning a tag keeps the marks

- **GIVEN** an edition file holding marks
- **WHEN** the user assigns a tag to a group
- **THEN** the marks are still stored
- **AND** the tag assignment is stored

#### Scenario: Clearing a tag keeps the marks

- **GIVEN** an edition file holding marks and a tag assignment
- **WHEN** the user clears that tag
- **THEN** the marks are still stored

### Requirement: Marks without a photo are pruned when read

When an edition file is read against a scanned index, marks whose content hash does not appear in
that index SHALL be discarded, and marks that do appear SHALL be kept. Pruning SHALL happen on read
and SHALL NOT rewrite the file, so an unresolved mark is still available if the photo later returns.

#### Scenario: A marked photo leaves the library

- **GIVEN** an edition file holding a mark for a photo
- **WHEN** the photo is deleted from disk and the library is rescanned
- **THEN** that mark is not reported among the marks for any group

#### Scenario: Pruning does not rewrite the file

- **GIVEN** an edition file holding a mark for a photo that no longer exists
- **WHEN** the file is read
- **THEN** the file on disk still contains the mark
- **AND** the file is only rewritten on the next saved edit

#### Scenario: Everything still resolves

- **GIVEN** an edition file whose marks all match photos in the index
- **WHEN** the file is read
- **THEN** every mark is kept

### Requirement: Marking performs no action on photos

The system SHALL NOT delete, move, rename, copy or modify any photo as a consequence of a mark, and
SHALL NOT do so on server startup or on the next scan either. A mark is a record of an intention
only. Any operation that acts on marked photos SHALL be the subject of a separate change.

#### Scenario: Marking does not touch the library

- **GIVEN** a served viewer and a library of photos
- **WHEN** the user marks and then unmarks a photo
- **THEN** every photo in the library is unchanged on disk

#### Scenario: Restarting the server does not act on marks

- **GIVEN** an edition file holding marks and a running server
- **WHEN** the server is started again
- **THEN** no photo is deleted, moved or modified

#### Scenario: Rescanning does not act on marks

- **GIVEN** an edition file holding marks
- **WHEN** the library is rescanned
- **THEN** no photo is deleted, moved or modified

### Requirement: Marked state is visible for the displayed photo

While a photo is displayed in the served viewer, the viewer SHALL show whether that photo is marked
and SHALL update that indication as soon as the user toggles it, without reloading the page. Moving
to another photo SHALL show that photo's own state, so a marked photo is recognisable while
browsing past it.

#### Scenario: The indication matches the displayed photo

- **GIVEN** a group in which one photo is marked and another is not
- **WHEN** the user moves from the marked photo to the unmarked one
- **THEN** the viewer shows the second photo as unmarked

#### Scenario: Toggling updates the indication immediately

- **GIVEN** an unmarked photo displayed in the viewer
- **WHEN** the user marks it
- **THEN** the viewer shows it as marked without reloading the page

### Requirement: Marks are browsable as their own section

The landing page MUST present the marked photos in a section of their own, separate from the group
sections and from the photo bucket sections, so that the shortlist a curation pass produces can be
looked at after the pass is over. That section MUST list the photos themselves rather than the
groups they belong to, MUST order them by the same order the photos are browsed in, and MUST report
how many photos it holds. A library with no marks MUST NOT produce that section. The section MUST
NOT be editable by dragging anything onto it, and dragging a group card onto it MUST NOT change any
mark, because a mark is not a bucket and the two are not interchangeable.

The marks section MUST appear in the exported HTML as well as in the served viewer. This is the
first place a mark is visible outside the served browser, and it MUST NOT make the export editable:
the section there is read-only, exactly as the rest of the export is.

#### Scenario: The marked photos get a section

- **GIVEN** a library in which three photos are marked and the rest are not
- **WHEN** the landing page is generated
- **THEN** a section for marked photos appears, listing those three photos
- **AND** it reports that it holds three photos

#### Scenario: Marked photos keep their browse order

- **GIVEN** a library in which two marked photos sit in the same group, one captured earlier
- **WHEN** the landing page is generated
- **THEN** the earlier one is listed before the later one in the marked photos section

#### Scenario: No marks means no section

- **GIVEN** an edition file holding no marks
- **WHEN** the landing page is generated
- **THEN** no marked photos section appears

#### Scenario: A card dragged onto the marked section changes nothing

- **GIVEN** a running server and a group card with no bucket assigned
- **WHEN** the user drags that card onto the marked photos section
- **THEN** the card's group tag is unchanged
- **AND** the stored marks are unchanged

#### Scenario: The marks section is visible in the export

- **GIVEN** an edition file holding marks
- **WHEN** the exported HTML is generated with `view` and no `--serve`
- **THEN** the marked photos section appears in the export
- **AND** it offers no control to change any mark

#### Scenario: Unmarking removes the photo from the section

- **GIVEN** a marked photo that appears in the marked photos section
- **WHEN** the user unmarks it in the served browser
- **THEN** the photo is no longer stored as marked
- **AND** it is not listed in the marked photos section on the next generation of the page
