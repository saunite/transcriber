## ADDED Requirements

### Requirement: A release's downloads are grouped and explained
Each release's assets SHALL be named so that the download list, which the hosting service sorts alphabetically, groups them by the platform they are for. Each release's notes SHALL carry a table telling a reader which download to take for their platform and what each one is, and SHALL identify any asset that exists only for package managers as such. Asset names SHALL keep the project's case rule: the `.deb` and `.rpm` file names lowercase, the other artifacts capitalised.

#### Scenario: Someone opens the release page
- **WHEN** a visitor opens a published release
- **THEN** the notes above the assets tell them which file to take for their platform, and which files are only for package managers

#### Scenario: The asset list is read top to bottom
- **WHEN** the assets of a release are listed in the order the hosting service shows them
- **THEN** each platform's downloads appear together rather than interleaved with other platforms'

#### Scenario: Package manager files are not mistaken for downloads
- **WHEN** a release carries repository index files for a package manager
- **THEN** the notes say they are for package managers and a visitor does not need them
