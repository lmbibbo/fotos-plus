# Spec Delta

## ADDED Requirements

### Requirement: Videos group under the identical date and position rules

Videos with a capture date and a valid position MUST take part in trip suggestions under
the identical distance and ordering rules as photos. Videos with a capture date and no
valid position MUST take part in period suggestions under the identical rules as photos.
Videos without a capture date MUST follow the existing undated handling. Grouping MUST
treat a video timestamp exactly like a photo timestamp: a single instant that orders the
item but never splits a suggestion on its own.

#### Scenario: Dated video joins a trip

- **GIVEN** a video with capture date and valid position taken in the same place as
  dated photos
- **WHEN** the scan builds the suggestions
- **THEN** the video lands in the same trip suggestion as those photos
- **AND** the suggestion counts it like any other item

#### Scenario: Dated video without position joins a period

- **GIVEN** a video with capture date and no valid position
- **WHEN** the scan builds the suggestions
- **THEN** the video lands in a period suggestion under the identical rules as photos

#### Scenario: Undated video follows undated handling

- **GIVEN** a video whose container declares no capture date
- **WHEN** the scan builds the suggestions
- **THEN** the video follows the existing undated handling, exactly like a dateless photo
