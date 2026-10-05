# Spec Delta

## MODIFIED Requirements

### Requirement: Browsing the photos of a group in the served viewer

In `--serve` mode the viewer MUST offer, for each group that owns at least one photo, a way to open
a full-screen browser showing that group's photos one at a time. The browser SHALL advance to the
previous and next photo, SHALL be operable from the keyboard for both directions, and SHALL show
which photo of the group is currently displayed and how many the group holds. When the displayed
photo carries a capture date, the browser SHALL also show that date in the `YYYY-MM-DD` form next to
that position. When the displayed photo carries no capture date, the browser SHALL show the position
alone, without a placeholder standing in for the date. Reaching the first or the last photo SHALL
leave the viewer on that photo rather than moving past the ends of the group.

#### Scenario: Opening the browser from a group

- **GIVEN** a running server and a group card that owns photos
- **WHEN** the user opens that group's browser
- **THEN** the browser shows the group's first photo
- **AND** it shows the position within the group and the group's total photo count

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
- **THEN** no browser is opened

#### Scenario: Closing the browser

- **GIVEN** the browser open on a group
- **WHEN** the user closes it
- **THEN** the group cards are shown again
- **AND** no mark is added or removed by opening and closing the browser
