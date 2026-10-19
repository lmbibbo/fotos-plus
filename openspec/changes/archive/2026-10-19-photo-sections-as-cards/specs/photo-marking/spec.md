# Spec Delta

## MODIFIED Requirements

### Requirement: Marks are browsable as their own section

The landing page MUST present the marked photos in a card of their own, separate from the group
cards and from the photo bucket cards, so that the shortlist a curation pass produces can be
looked at after the pass is over. The card MUST show the title "Marcadas", the number of marked
photos, the earliest and latest capture dates when known, and at most five thumbnails from the
marked set, using the same card presentation as a group card. If the set has fewer than five
photos, the card MUST show all of them. The card MUST NOT show a country and MUST NOT offer group
label or tag controls, because a photo set is not a group. The set MUST be ordered by the same
order the photos are browsed in. A library with no marks MUST NOT produce that card.

In the served viewer, the card MUST offer a control that opens the full marked set in the photo
grid, and selecting a photo there MUST open the served browser at that photo. The card MUST NOT be
draggable and MUST NOT be a drop target. Dragging a group card onto it MUST NOT change any mark or
group tag, because a mark is not a bucket and the two are not interchangeable.

The marks card MUST appear in the exported HTML as well as in the served viewer. The exported card
MUST show the same at-most-five-thumbnail preview and MUST NOT offer any control that changes a
mark or opens the served browser; the export remains read-only.

The card MUST report the real number of marked photos even when their thumbnails cannot be
produced. In that case it MUST state that the previews could not be produced and MUST NOT say the
marked photos fall into another group, because that explanation only fits a declared group card.

#### Scenario: The marked photos get a section

- **GIVEN** a library in which three photos are marked and the rest are not
- **WHEN** the landing page is generated
- **THEN** a "Marcadas" card appears
- **AND** it reports that it holds three photos
- **AND** it shows all three thumbnails

#### Scenario: A large marked set shows a bounded preview

- **GIVEN** a library in which twelve photos are marked
- **WHEN** the landing page is generated
- **THEN** the "Marcadas" card reports twelve photos
- **AND** it shows exactly five thumbnails

#### Scenario: Marked photos keep their browse order

- **GIVEN** a library in which two marked photos sit in the same group, one captured earlier
- **WHEN** the landing page is generated
- **THEN** the earlier one is the first thumbnail in the "Marcadas" card
- **AND** the earlier one comes first in the full marked set opened from the card

#### Scenario: No marks means no section

- **GIVEN** an edition file holding no marks
- **WHEN** the landing page is generated
- **THEN** no "Marcadas" card appears

#### Scenario: A card dragged onto the marked section changes nothing

- **GIVEN** a running server and a group card with no bucket assigned
- **WHEN** the user drags that card onto the "Marcadas" card
- **THEN** the card's group tag is unchanged
- **AND** the stored marks are unchanged
- **AND** the viewer reports that photo cards do not accept a dragged card

#### Scenario: The marks section is visible in the export

- **GIVEN** an edition file holding marks
- **WHEN** the exported HTML is generated with `view` and no `--serve`
- **THEN** the "Marcadas" card appears in the export
- **AND** it offers no control to change a mark or open the served browser

#### Scenario: Unmarking removes the photo from the section

- **GIVEN** a marked photo that appears in the "Marcadas" card
- **WHEN** the user unmarks it in the served browser
- **THEN** the photo is no longer stored as marked
- **AND** it is not listed in the "Marcadas" card on the next generation of the page

#### Scenario: A marked set whose thumbnails cannot be produced

- **GIVEN** a library in which a marked photo cannot be read
- **WHEN** the landing page is generated
- **THEN** the "Marcadas" card still reports the number of marked photos
- **AND** it states that its previews could not be produced
- **AND** it does not say the marked photos fall into another group
