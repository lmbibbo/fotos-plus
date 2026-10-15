# Spec Delta

## ADDED Requirements

### Requirement: Serving a thumbnail for the grid

The served viewer MUST obtain a grid cell's photo from an endpoint that returns a
thumbnail-scale render — the same size and quality as the thumbnails embedded in the
cards — so that a screenful of cells stays light even when the group holds hundreds of
photos. The endpoint MUST serve only photos that the scanned index contains, and MUST
refuse video references with a reason: grid video cells are shown through their posters
instead.

#### Scenario: Requesting the thumbnail of a photo

- **GIVEN** a running server and a photo in the index
- **WHEN** the grid requests that photo's thumbnail
- **THEN** it receives an image at thumbnail scale rather than the screen render
- **AND** the bytes are far smaller than the render of the same photo

#### Scenario: A thumbnail is produced once and stored

- **GIVEN** a photo with no stored thumbnail
- **WHEN** its thumbnail is requested twice
- **THEN** the second request returns the stored thumbnail instead of reprocessing the original

#### Scenario: A photo that is not in the index

- **GIVEN** a running server
- **WHEN** a thumbnail is requested for something the index does not contain
- **THEN** the request is refused with a reason
- **AND** no file outside the library root is served

#### Scenario: A video reference is refused

- **GIVEN** a video recorded in the scanned index
- **WHEN** its reference is requested from the thumbnail endpoint
- **THEN** the endpoint refuses it with a reason
- **AND** the grid shows that video through its poster

## MODIFIED Requirements

### Requirement: Browsing the photos of a group in the served viewer

In `--serve` mode the viewer MUST offer, for each group that owns at least one photo, a way to open
a grid page showing every photo and video of that group, each with a thumb at the scale the group
cards use. Selecting an element of the grid MUST open the full-screen browser at that item. The
browser SHALL advance to the previous and next photo, SHALL be operable from the keyboard for both
directions, and SHALL show which photo of the group is currently displayed and how many the group
holds. When the displayed photo carries a capture date, the browser SHALL also show that date in
the `YYYY-MM-DD` form next to that position. When the displayed photo carries no capture date, the
browser SHALL show the position alone, without a placeholder standing in for the date. Reaching the
first or the last photo SHALL leave the viewer on that photo rather than moving past the ends of
the group.

#### Scenario: Opening the browser from a group

- **GIVEN** a running server and a group card that owns photos
- **WHEN** the user follows that group's "Ver fotos" action
- **THEN** a grid page opens showing a thumb for every photo and video of the group
- **AND** it shows the position within the group and the group's total photo count

#### Scenario: Opening the browser on the selected element

- **GIVEN** the grid page of a group open in the browser
- **WHEN** the user selects one of its elements
- **THEN** the full-screen browser opens at that item rather than at the first one
- **AND** it shows the position within the group and the group's total photo count

#### Scenario: Grid thumbs at the card-thumbnail scale

- **GIVEN** a running server and a group that owns photos
- **WHEN** the grid page of that group opens
- **THEN** every cell shows a thumb at the same scale as the thumbnails on the group cards
- **AND** a group of many photos reads as a dense contact sheet rather than a page of large images

#### Scenario: A displayed photo that carries a capture date

- **GIVEN** the browser open on a photo whose capture date is known
- **WHEN** the browser displays that photo
- **THEN** it shows that capture date next to the position within the group
- **AND** the date is rendered in the `YYYY-MM-DD` form

#### Scenario: A displayed photo with no capture date

- **GIVEN** the browser open on a photo that carries no capture date
- **WHEN** the browser displays that photo
- **THEN** it shows the position within the group and the group's total photo count
- **AND** it shows neither a date nor a placeholder where the date would have been

#### Scenario: The shown date follows the displayed photo

- **GIVEN** the browser open on a group whose photos carry different capture dates
- **WHEN** the user moves to the next photo
- **THEN** the shown date is that of the photo now displayed rather than the one left behind

#### Scenario: Moving between photos

- **GIVEN** the browser open on a group of more than one photo
- **WHEN** the user requests the next photo
- **THEN** the browser shows the following photo of that group

#### Scenario: Moving with the keyboard

- **GIVEN** the browser open on a photo
- **WHEN** the user presses the next-photo key
- **THEN** the browser advances one photo without needing a pointer

#### Scenario: The last photo of the group

- **GIVEN** the browser open on the last photo of a group
- **WHEN** the user requests the next photo
- **THEN** the browser still shows that last photo

#### Scenario: A group that owns no photos

- **GIVEN** a group card reporting that it owns no photos
- **WHEN** the viewer offers a way to browse that group
- **THEN** no grid page is opened

#### Scenario: Closing the browser

- **GIVEN** the browser open on a group
- **WHEN** the user closes it
- **THEN** the grid page that opened it is shown again
- **AND** no mark is added or removed by opening and closing the browser

### Requirement: The media endpoints require the token and resolve through the index

The render and thumbnail endpoints MUST require the same random token the served page
already carries, and MUST refuse a request whose host header is not a loopback address,
matching the guarantees already required of edits. Both endpoints MUST accept a photo
reference that names a photo in the index and MUST resolve it through the index, so that
a caller-supplied value is never used directly to read or write a filesystem path. A
reference that the index does not contain MUST be refused with a reason.

#### Scenario: Request without the valid token

- **GIVEN** a running server
- **WHEN** a render is requested with no token or an incorrect token
- **THEN** the server refuses the request
- **AND** no image bytes are returned

#### Scenario: Request from a host that is not loopback

- **GIVEN** a running server
- **WHEN** a render is requested with a host header that is not a loopback address
- **THEN** the server refuses the request

#### Scenario: A reference that escapes the library root

- **GIVEN** a running server
- **WHEN** a render is requested with a reference that climbs out of the library root
- **THEN** the server refuses the request
- **AND** no file outside the library root is returned

#### Scenario: A reference that is not a photo in the index

- **GIVEN** a running server
- **WHEN** a render is requested for a reference the index does not contain
- **THEN** the server refuses the request and reports that the reference does not resolve

## RENAMED Requirements

- FROM: `### Requirement: The render endpoint requires the token and resolves through the index`
- TO: `### Requirement: The media endpoints require the token and resolve through the index`
