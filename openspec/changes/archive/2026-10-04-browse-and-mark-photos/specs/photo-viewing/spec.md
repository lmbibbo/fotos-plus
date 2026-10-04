# Spec Delta

## ADDED Requirements

### Requirement: Browsing the photos of a group in the served viewer

In `--serve` mode the viewer SHALL offer, for each group that owns at least one photo, a way to open
a full-screen browser showing that group's photos one at a time. The browser SHALL advance to the
previous and next photo, SHALL be operable from the keyboard for both directions, and SHALL show
which photo of the group is currently displayed and how many the group holds. Reaching the first or
the last photo SHALL leave the viewer on that photo rather than moving past the ends of the group.

#### Scenario: Opening the browser from a group

- **GIVEN** a running server and a group card that owns photos
- **WHEN** the user opens that group's browser
- **THEN** the browser shows the group's first photo
- **AND** it shows the position within the group and the group's total photo count

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
- **THEN** no browser is opened

#### Scenario: Closing the browser

- **GIVEN** the browser open on a group
- **WHEN** the user closes it
- **THEN** the group cards are shown again
- **AND** no mark is added or removed by opening and closing the browser

### Requirement: Serving a screen-sized render of a single photo

The served viewer SHALL obtain the displayable version of a photo from an endpoint that returns a
render whose longest edge is capped, so that the displayed image does not scale with the size of the
original file. The render SHALL carry the EXIF orientation already applied, so the viewer does not
interpret the orientation tag. The endpoint SHALL serve only photos that the scanned index contains.

#### Scenario: Requesting the displayable version of a photo

- **GIVEN** a running server and a photo in the index
- **WHEN** the viewer requests that photo's displayable version
- **THEN** it receives an image
- **AND** the longest edge of that image is within the cap

#### Scenario: A large original is not served whole

- **GIVEN** a photo whose original file is large
- **WHEN** the viewer requests that photo's displayable version
- **THEN** the bytes returned are far smaller than the original file

#### Scenario: An orientation-marked photo appears upright

- **GIVEN** a photo stored sideways with an orientation mark
- **WHEN** the viewer requests that photo's displayable version
- **THEN** the returned image already has its final orientation applied

#### Scenario: A photo that is not in the index

- **GIVEN** a running server
- **WHEN** a render is requested for something the index does not contain
- **THEN** the request is refused with a reason
- **AND** no file outside the library root is served

### Requirement: The render endpoint requires the token and resolves through the index

The render endpoint SHALL require the same random token the served page already carries, and SHALL
refuse a request whose host header is not a loopback address, matching the guarantees already
required of edits. The endpoint SHALL accept a photo reference that names a photo in the index and
SHALL resolve it through the index, so that a caller-supplied value is never used directly to read
or write a filesystem path. A reference that the index does not contain SHALL be refused with a
reason.

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

### Requirement: Renders are produced lazily and cached by content hash

The displayable version of a photo SHALL be produced the first time it is asked for and stored, so
that asking again returns the stored render without reprocessing the original. The stored render
SHALL be identified by the photo's content hash rather than by its name or path. Asking for a photo
whose content hash has no stored render yet SHALL produce and store one. The stored renders SHALL be
disposable: deleting them costs time on the next request and no data.

#### Scenario: The first request is slower than the second

- **GIVEN** a photo with no stored render
- **WHEN** its displayable version is requested twice
- **THEN** the second request returns the stored render instead of reprocessing the original

#### Scenario: A changed photo gets a new render

- **GIVEN** a photo whose content changed, so its content hash is different
- **WHEN** its displayable version is requested
- **THEN** the render stored for the earlier content is not served
- **AND** a render for the new content is produced and stored

#### Scenario: A moved photo keeps its render

- **GIVEN** a photo that has a stored render, at one path
- **WHEN** the photo is moved and its displayable version is requested at the new path
- **THEN** the stored render for that content is served

#### Scenario: Stored renders can be deleted

- **GIVEN** a photo that has a stored render
- **WHEN** the stored renders are deleted and the displayable version is requested again
- **THEN** the render is produced again from the original photo
- **AND** no information about the library is lost

### Requirement: The static export is unaffected by browsing

The exported HTML SHALL keep showing five thumbnails per card and SHALL stay self-contained. The
export SHALL NOT include the group browser, SHALL NOT request renders, and SHALL NOT offer any
control that depends on the server.

#### Scenario: The export keeps its thumbnails

- **GIVEN** a served session in which renders exist
- **WHEN** the exported HTML is opened from disk with no server running
- **THEN** the cards still show five thumbnails each
- **AND** the page needs no network access to show its content

#### Scenario: The export has no browsing control

- **GIVEN** an exported HTML file
- **WHEN** it is opened in a browser
- **THEN** no control that opens a group's photos is offered