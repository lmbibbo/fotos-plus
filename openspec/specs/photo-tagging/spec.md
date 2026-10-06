# photo-tagging Specification

## Purpose

Lets the user place individual photos into any number of user-defined named buckets, so that a
curation result over individual photos stays browsable and survives rescans, independently of the
tags that classify whole groups.

## Requirements

### Requirement: Bucket catalogue of user-defined names

The edition file MUST store an ordered catalogue of bucket names defined by the user, and the
viewer MUST offer choosing a bucket from that catalogue or writing a new one. A new name MUST be
added to the catalogue when the edit is saved. Two catalogue entries MUST NOT differ only in letter
case or in surrounding whitespace, and a name that is empty or made only of whitespace MUST NOT be
stored. An empty bucket name offered in the catalogue MUST NOT produce a bucket section.

#### Scenario: Choosing a bucket from the catalogue

- **GIVEN** a bucket catalogue holding the names "Favoritas" and "Para imprimir"
- **WHEN** the user assigns "Favoritas" to a photo
- **THEN** the photo belongs to the bucket "Favoritas"
- **AND** the catalogue does not change

#### Scenario: Writing a new bucket name

- **GIVEN** a bucket catalogue holding only "Favoritas"
- **WHEN** the user writes "Para collage" as a bucket for a photo and saves it
- **THEN** the photo belongs to the bucket "Para collage"
- **AND** "Para collage" is available in the catalogue for other photos

#### Scenario: A new name is recognised as an existing bucket

- **GIVEN** a bucket catalogue holding "Favoritas"
- **WHEN** the user creates the bucket "  favoritas  "
- **THEN** the system recognises it as the bucket that already exists
- **AND** the catalogue does not gain a second entry that differs only in case or whitespace

#### Scenario: An empty bucket name is rejected

- **GIVEN** a photo that belongs to "Favoritas"
- **WHEN** the user submits an empty bucket name, or one made only of spaces, for that photo
- **THEN** the system rejects the operation and reports that a bucket name cannot be empty
- **AND** the photo keeps the buckets it already belonged to

### Requirement: A photo can belong to several buckets

A photo MUST be able to belong to any number of buckets at the same time, and bucket membership
MUST NOT be exclusive. Adding a bucket to a photo that already has buckets MUST keep the existing
ones. Removing one bucket MUST leave the photo's other buckets in place, and MUST leave the photo
itself present in the library. A photo that belongs to no bucket MUST remain a normal photo of its
group and MUST still be browsable there.

#### Scenario: Adding a second bucket keeps the first

- **GIVEN** a photo that belongs only to the bucket "Favoritas"
- **WHEN** the user adds the bucket "Para imprimir" to it
- **THEN** the photo belongs to both "Favoritas" and "Para imprimir"

#### Scenario: Removing one bucket keeps the others

- **GIVEN** a photo that belongs to "Favoritas" and "Para imprimir"
- **WHEN** the user removes "Para imprimir" from it
- **THEN** the photo still belongs to "Favoritas"
- **AND** the photo is no longer reported under "Para imprimir"

#### Scenario: A photo can belong to no bucket

- **GIVEN** a photo that belongs to "Favoritas"
- **WHEN** the user removes that bucket from it
- **THEN** the photo belongs to no bucket
- **AND** the photo is still browsable in its group as before

### Requirement: Bucket membership is identified by content hash

A bucket assignment MUST reference its photo by the content hash the scanner recorded for it, and
never by the file's path. Bucket membership SHALL therefore survive a rescan and SHALL survive the
file being moved or renamed inside the library root, as long as its content is unchanged. Two files
with identical content SHALL resolve to the same bucket membership.

#### Scenario: A bucketed photo is moved to another folder

- **GIVEN** a photo that belongs to "Favoritas", stored under one relative path
- **WHEN** the photo is moved within the library root and the library is rescanned
- **THEN** the photo at its new path is still reported under "Favoritas"

#### Scenario: A rescan does not alter bucket membership

- **GIVEN** an edition file holding bucket assignments
- **WHEN** the library is rescanned and the suggestions file is replaced
- **THEN** the bucket assignments remain in the edition file and still resolve to photos

#### Scenario: Identical content in two locations

- **GIVEN** two files whose content hash is the same
- **WHEN** one of them is placed in a bucket
- **THEN** the other one is reported in that bucket as well

### Requirement: Bucket membership is stored in the edition file at version 4

The edition file MUST declare version 4 and MUST store an ordered catalogue of bucket names
together with a map from content hash to the bucket names that photo belongs to. Edition files at
versions 1, 2 and 3 SHALL remain readable: they SHALL load with an empty bucket catalogue and no
bucket assignments, while keeping the labels, tag catalogue, tag assignments and marks they
already held. Reading an edition file SHALL NOT by itself rewrite it to a newer version. A bucket
assignment key that is not 64 lowercase hexadecimal characters SHALL be rejected when the file is
written, and a bucket name stored against a photo SHALL be present in the catalogue.

#### Scenario: A version 3 edition file loads with no buckets

- **GIVEN** an edition file at version 3 holding labels, tags, tag assignments and marks
- **WHEN** the file is read
- **THEN** the labels, tag catalogue, tag assignments and marks are all preserved
- **AND** the bucket catalogue is empty and there are no bucket assignments
- **AND** the file on disk still declares version 3

#### Scenario: A version 2 edition file loads with no buckets and keeps its marks

- **GIVEN** an edition file at version 2 holding labels, tags and tag assignments
- **WHEN** the file is read
- **THEN** the labels, tag catalogue and tag assignments are all preserved
- **AND** there are no bucket assignments

#### Scenario: The first bucket edit upgrades the file

- **GIVEN** an edition file at version 3 with tags and marks already saved
- **WHEN** the user places a photo in a bucket and the edit is saved
- **THEN** the file declares version 4
- **AND** it holds the tag catalogue, the tag assignments, the marks and the bucket assignment

#### Scenario: A malformed bucket assignment is rejected on write

- **GIVEN** an edition file being saved
- **WHEN** a bucket assignment key is not 64 lowercase hexadecimal characters
- **THEN** the save is rejected and the reason is reported
- **AND** the edition file is left unchanged

### Requirement: The bucket catalogue is separate from the group tag catalogue

Bucket names and group tag names MUST be held in separate catalogues, so the same name MAY be used
for both without the two referring to each other. A bucket name MUST NOT create, rename or remove a
group tag, and a group tag MUST NOT create, rename or remove a bucket. Assigning or clearing a
group tag MUST NOT change any bucket assignment, and placing or removing a photo from a bucket MUST
NOT change any group tag.

#### Scenario: The same name on both axes

- **GIVEN** a group tag catalogue holding "Familia" assigned to one group
- **WHEN** the user places a photo in a bucket also named "Familia"
- **THEN** the photo is reported in the photo bucket "Familia"
- **AND** the group keeps its group tag "Familia"
- **AND** neither catalogue gained or lost an entry because of the other

#### Scenario: Clearing a group tag leaves buckets alone

- **GIVEN** a group with the tag "Familia" and a photo in the bucket "Familia"
- **WHEN** the user clears the group tag
- **THEN** the group's tag assignment is gone
- **AND** the photo is still reported in the bucket "Familia"

### Requirement: Bucket assignments survive unrelated edits to the same file

Saving a label, removing a label, assigning a group tag or clearing a group tag SHALL NOT add to,
remove from or otherwise alter the stored bucket assignments or the bucket catalogue. Marking and
unmarking a photo SHALL NOT alter any bucket assignment, and adding or removing a bucket from a
photo SHALL NOT alter the stored marks. Those operations live in the same file and each of them
reconstructs the saved content field by field, so the system SHALL carry the bucket fields and the
marks through every one of them unchanged.

#### Scenario: Saving a label keeps the buckets

- **GIVEN** an edition file holding bucket assignments and no label for some group
- **WHEN** the user saves a label for that group
- **THEN** the bucket assignments are still stored
- **AND** the saved label is stored

#### Scenario: Assigning a group tag keeps the buckets

- **GIVEN** an edition file holding bucket assignments
- **WHEN** the user assigns a tag to a group
- **THEN** the bucket assignments are still stored
- **AND** the tag assignment is stored

#### Scenario: Marking keeps the buckets

- **GIVEN** an edition file holding bucket assignments
- **WHEN** the user marks a photo
- **THEN** the bucket assignments are still stored
- **AND** the mark is stored

#### Scenario: Bucketing keeps the marks

- **GIVEN** an edition file holding marks and a photo that belongs to "Favoritas"
- **WHEN** the user adds the bucket "Para imprimir" to that photo
- **THEN** the marks are still stored
- **AND** the photo belongs to both buckets

#### Scenario: Removing a bucket keeps the marks

- **GIVEN** an edition file holding a mark on a photo that belongs to "Favoritas"
- **WHEN** the user removes "Favoritas" from that photo
- **THEN** the mark is still stored

### Requirement: Bucket assignments without a photo are pruned when read

When an edition file is read against a scanned index, bucket assignments whose content hash does
not appear in that index SHALL be discarded, and assignments that do appear SHALL be kept. A
bucket name left with no photos MUST NOT be removed from the catalogue by that pruning. Pruning
SHALL happen on read and SHALL NOT rewrite the file, so an unresolved assignment is still available
if the photo later returns.

#### Scenario: A bucketed photo leaves the library

- **GIVEN** an edition file holding a bucket assignment for a photo
- **WHEN** the photo is deleted from disk and the library is rescanned
- **THEN** that photo is not reported in any bucket

#### Scenario: Pruning does not rewrite the file

- **GIVEN** an edition file holding a bucket assignment for a photo that no longer exists
- **WHEN** the file is read
- **THEN** the file on disk still contains the bucket assignment
- **AND** the file is only rewritten on the next saved edit

#### Scenario: A bucket name survives its last photo

- **GIVEN** a bucket catalogue holding "Para imprimir" with one photo in it
- **WHEN** that photo is deleted from disk and the edition file is read
- **THEN** "Para imprimir" is still in the bucket catalogue
- **AND** it produces no bucket section

#### Scenario: Everything still resolves

- **GIVEN** an edition file whose bucket assignments all match photos in the index
- **WHEN** the file is read
- **THEN** every bucket assignment is kept

### Requirement: Buckets perform no action on photos

The system SHALL NOT delete, move, rename, copy or modify any photo as a consequence of a bucket
assignment, and SHALL NOT do so on server startup or on the next scan either. A bucket assignment
is a record of an intention only. Any operation that acts on bucketed photos SHALL be the subject
of a separate change.

#### Scenario: Bucketing does not touch the library

- **GIVEN** a served viewer and a library of photos
- **WHEN** the user adds a bucket to a photo and then removes it
- **THEN** every photo in the library is unchanged on disk

#### Scenario: Restarting the server does not act on buckets

- **GIVEN** an edition file holding bucket assignments and a running server
- **WHEN** the server is started again
- **THEN** no photo is deleted, moved or modified

#### Scenario: Rescanning does not act on buckets

- **GIVEN** an edition file holding bucket assignments
- **WHEN** the library is rescanned
- **THEN** no photo is deleted, moved or modified

### Requirement: Bucket membership is visible and editable for the displayed photo

While a photo is displayed in the served viewer, the viewer MUST show which buckets that photo
belongs to and MUST offer to add a bucket to it and to remove a bucket from it. The shown membership
MUST reflect the stored assignments as soon as the user changes it, without reloading the page.
Moving to another photo MUST show that photo's own membership, so a bucketed photo is recognisable
while browsing past it. A photo that belongs to no bucket MUST be shown as belonging to none, which
is distinct from a photo the user has not visited yet only in that no bucket is preselected.

#### Scenario: The picker matches the displayed photo

- **GIVEN** a group in which one photo belongs to "Favoritas" and another to no bucket
- **WHEN** the user moves from the first photo to the second
- **THEN** the picker shows "Favoritas" as held for the first photo
- **AND** the picker shows no bucket held for the second

#### Scenario: Adding a bucket updates the picker immediately

- **GIVEN** a photo displayed in the viewer that belongs to no bucket
- **WHEN** the user adds the bucket "Favoritas" to it
- **THEN** the picker shows "Favoritas" as held for that photo without reloading the page

#### Scenario: Removing one bucket leaves the others held

- **GIVEN** a photo displayed in the viewer that belongs to "Favoritas" and "Para imprimir"
- **WHEN** the user removes "Para imprimir" from it
- **THEN** the picker still shows "Favoritas" as held for that photo

#### Scenario: The viewer reports a rejected bucket edit

- **GIVEN** a running server and a photo displayed in the viewer
- **WHEN** the server rejects a bucket edit
- **THEN** the viewer reports the reason
- **AND** the picker shows the membership the photo had before the edit
