## ADDED Requirements

### Requirement: Chart search counts the matching lines the user can see
When the user searches the chart, the system SHALL show a count of the transcript lines that contain the search text, are shown by the current source filter, and belong to the chart currently displayed (live or file). Lines hidden by the source filter, and lines in the chart that is not displayed, SHALL NOT be counted. The count SHALL update when the search text, the source filter, or the displayed chart changes, and when new transcript lines arrive. With no search text, no count SHALL be shown.

#### Scenario: Source filter hides some matches
- **WHEN** the live chart has one system-audio line and one microphone line containing "budget", the source filter shows system audio only, and the user searches for "budget"
- **THEN** one line is shown highlighted and the count reads "1 line"

#### Scenario: Matches in the chart that is not displayed
- **WHEN** the file chart contains a line with "budget", the live chart is displayed with no line containing "budget", and the user searches for "budget"
- **THEN** the count reads "0 lines"

#### Scenario: Switching charts updates the count
- **WHEN** a search is active and the user switches from the live chart to the file chart
- **THEN** the count reflects the matching visible lines of the file chart

#### Scenario: Search cleared
- **WHEN** the user clears the search text
- **THEN** no count is shown
