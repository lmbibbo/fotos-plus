# Spec Delta

## MODIFIED Requirements

### Requirement: Photo bucket sections on the landing page

When at least one photo belongs to a bucket, the landing page MUST present a section for each
bucket that holds at least one photo, listing the photos that belong to it. Each such section MUST
show the bucket name and how many photos it holds, and MUST order its photos by the same order the
photos are browsed in. A bucket in the catalogue that holds no photo MUST NOT produce a section.
Photos that belong to no bucket MUST NOT appear in any photo section on the landing page.

Bucket sections MUST come after the group sections, in the order the bucket catalogue lists them.
The landing page MUST NOT present an untagged photos section in any case.

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
- **THEN** the "Favoritas" section appears
- **AND** no section of their own appears for the photos in no bucket: no untagged photos section exists

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
section, including the marked section and the bucket sections, and the exported HTML inherits
it.

Bounding the section is what keeps the document from growing with the library: a bucket holding
hundreds of photos must not turn the page into one the browser cannot open.

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
- **THEN** the marked section appears with that photo
- **AND** no untagged photos section appears

### Requirement: The exported HTML shows the photo sections read-only

The exported HTML MUST present the bucket sections, and MUST NOT present an untagged photos
section. It MUST NOT offer any control that changes a bucket assignment or creates a bucket name.
The exported document MUST contain no bucket picker and no drop target, exactly as it contains
no tag editor.

#### Scenario: Sections in the export

- **GIVEN** an edition file that places two photos in "Favoritas"
- **WHEN** the exported HTML is generated with `view` and no `--serve`
- **THEN** a "Favoritas" section listing the two photos appears in the export
- **AND** no untagged photos section appears

#### Scenario: The export has no bucket controls

- **GIVEN** an exported HTML document that shows a bucket section
- **WHEN** the document is inspected
- **THEN** it offers no control to change a bucket assignment or to write a new bucket name

#### Scenario: The export has no picker

- **GIVEN** an exported HTML document
- **WHEN** the document is inspected
- **THEN** it contains no bucket picker for any photo
