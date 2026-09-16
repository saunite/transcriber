## MODIFIED Requirements

### Requirement: Project documentation mirrors supported behavior

The project's documentation SHALL be organised as four documents with distinct owners:
- a front page that states what the tool is and how to install and run it, and that describes the licensing of what is shipped;
- a user reference covering every command, flag, requirement file, launcher and platform-specific setup, plus troubleshooting;
- a contributor document covering how a change is proposed, implemented and verified in this project, including running the tests;
- a build document covering the toolchains, the per-platform builds, assets built from source, and releasing.

Each document SHALL accurately describe what the project supports and SHALL be updated, in whichever document owns the subject, whenever a capability's user-facing behaviour changes. The documentation SHALL NOT list prerequisites the tool no longer requires, and SHALL NOT link to material that has moved or been archived.

#### Scenario: New launcher added

- **WHEN** a new launcher script is added to the repo root
- **THEN** the user reference SHALL include it in a "Launchers" section with its usage

#### Scenario: Platform-specific setup documented

- **WHEN** a capability has platform-specific setup
- **THEN** the user reference SHALL document the correct setup per platform, referencing the correct requirements file

#### Scenario: A prerequisite is no longer required

- **WHEN** the tool stops requiring an external prerequisite
- **THEN** the document that named that prerequisite SHALL remove its install instructions rather than leaving them as stale setup steps

#### Scenario: Someone new opens the front page

- **WHEN** a reader opens the front page
- **THEN** it tells them what the tool is, how to install it and how to run it, and points to the user reference, the contributor document and the build document, rather than carrying build, release or full flag reference material itself

#### Scenario: Someone wants to contribute a change

- **WHEN** a reader wants to make a change to the project
- **THEN** the contributor document tells them how changes are proposed and specified, how to run the tests, what is expected of a change that alters the desktop interface, and which branch work lands on

#### Scenario: A document points at moved material

- **WHEN** a document links to a path in the repository that has been archived, renamed or moved
- **THEN** the link SHALL be updated to the current location rather than left pointing at a path that no longer exists
