# Spec Delta

## RENAMED Requirements

- FROM: `### Requirement: Videos in the served browser show a still without playback`
- TO: `### Requirement: Videos in the served browser play automatically on arrival`

## MODIFIED Requirements

### Requirement: Videos in the served browser play automatically on arrival

In `--serve` mode, arriving at a video in the group browser MUST start playback with
native browser controls, using its poster still as the pre-playback frame. Playback MUST
start automatically every time the browser arrives at a video — when it opens on one and
when navigation moves onto one. When the browser refuses to start playback under its own
autoplay policy, the viewer MUST leave the poster still in place with the native controls
available, MUST NOT report an error, and MUST NOT move away from the video. Arrow keys MUST
keep moving between items; seeking within a video happens through its native controls. A
`/video` endpoint MUST serve the original file with single-range partial responses under the
same guarantees as `/render` (random token, loopback host, cross-origin refusal,
index-resolved reference). Media-element URLs (`<video src>`, `poster`) carry the token as a
query parameter, since tags cannot set headers; subresource URLs are never stored in browser
history. The `/render` endpoint keeps serving photos only and MUST refuse video references
with a reason. Video blobs MUST never be embedded in the static export; the export shows
video posters exactly like photo thumbnails.

#### Scenario: Browser opened on a video

- **GIVEN** a group holding a video, served with `view --serve`
- **WHEN** the browser opens on that video
- **THEN** a `<video>` element appears with native controls and the poster still
- **AND** playback starts automatically, without a press on the play control

#### Scenario: Navigation moves onto a video

- **GIVEN** the browser open on a photo of a group that also holds a video
- **WHEN** the user presses the arrow key that moves onto that video
- **THEN** playback of the video starts automatically

#### Scenario: The browser refuses to start playback

- **GIVEN** a group holding a video, served with `view --serve`
- **WHEN** the browser arrives at that video and its autoplay policy refuses playback
- **THEN** the poster still stays visible with the native controls available
- **AND** no error is reported and the browser stays on that video

#### Scenario: Moving off a playing video stops it

- **GIVEN** a video playing in the browser
- **WHEN** the user presses the arrow key that moves onto the next item
- **THEN** playback stops before the next item is shown

#### Scenario: Arrow keys keep navigating on a video

- **GIVEN** the browser opened on a video
- **WHEN** the user presses an arrow key
- **THEN** the browser moves to the previous or next item
- **AND** no seek is performed by the viewer

#### Scenario: Video bytes are served with ranges

- **GIVEN** a video recorded in the scanned index
- **WHEN** its reference is requested from the `/video` endpoint without a Range header
- **THEN** the endpoint answers 200 with the full file and `Accept-Ranges: bytes`
- **AND** a request with a single satisfiable byte range answers 206 with that slice
  and a matching `Content-Range`

#### Scenario: Unsatisfiable range is refused

- **GIVEN** a video recorded in the scanned index
- **WHEN** its reference is requested with a byte range past the end of the file
- **THEN** the endpoint answers 416

#### Scenario: Video endpoint keeps the render guarantees

- **GIVEN** the `/video` endpoint
- **WHEN** it is requested without the random token, from a non-loopback host, with a
  cross-site fetch mode, or with a reference the index does not contain
- **THEN** it refuses exactly like `/render` does

#### Scenario: Media tag authenticates with the token in the URL

- **GIVEN** a video recorded in the scanned index
- **WHEN** its reference is requested from `/video` with the token as a query
  parameter and no header token
- **THEN** the endpoint serves the bytes

#### Scenario: Render endpoint refuses a video

- **GIVEN** a video recorded in the scanned index
- **WHEN** its reference is requested from the `/render` endpoint
- **THEN** the endpoint refuses it with a reason instead of serving a render

#### Scenario: Export embeds posters, never video blobs

- **GIVEN** an exported HTML document for a group holding videos
- **WHEN** the document is inspected
- **THEN** video posters appear exactly like photo thumbnails
- **AND** the document embeds no video blob
- **AND** the document contains no `<video>` element
