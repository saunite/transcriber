## MODIFIED Requirements

### Requirement: Source-provenance directions are verified and attached
Before building a release, the system SHALL check that every concrete source location listed in the project's source-provenance file resolves, and SHALL fail the release if any does not. The system SHALL NOT attach the source-provenance file to a release as a downloadable asset. Instead, every release's notes SHALL include a section, placed before any automatically generated notes, that names the bundled GPL-licensed components and links to the source-provenance file as it exists at that release's tag, so the directions shown always match the release they accompany.

#### Scenario: A source location no longer resolves
- **WHEN** a release tag is pushed and one source URL in the provenance file returns an error
- **THEN** the run fails before any platform build starts, naming the URL that failed

#### Scenario: Provenance accompanies the release
- **WHEN** a draft release is created
- **THEN** its notes begin with a section linking to the source-provenance file at that release's tag, and the file is not among the release's attached assets

#### Scenario: Provenance changes in a later release
- **WHEN** a later release is tagged after the source-provenance file was updated
- **THEN** that release's notes link to the updated file at the new tag, while earlier releases keep linking to the file as it was at their own tags
