## Purpose

Let people who installed the Linux packages receive new versions through their own package manager, from repositories the project publishes with each release, without weakening what they can verify about what gets installed.

## ADDED Requirements

### Requirement: Published releases are installable as package repositories
The project SHALL publish, for each released version, repository metadata that lets Debian-family and RPM-family package managers install and upgrade the application from that release. The packages themselves SHALL remain the release's own downloadable assets rather than being copied to a second location.

#### Scenario: Upgrading through the package manager
- **WHEN** a user has the application installed from the `.deb` or `.rpm` with the project's repository registered, and a newer version is published
- **THEN** their package manager offers that version, and upgrading installs it without visiting the download page

#### Scenario: A draft or unpublished release
- **WHEN** a release exists but has not been published
- **THEN** the repositories continue to describe the most recently published version, and no user is offered the unpublished one

### Requirement: Repository contents are signed and verifiable
Repository metadata SHALL be signed, and each package manager SHALL be configured to verify that signature before trusting anything the repository describes. The metadata SHALL carry a checksum for every package it lists, so a package that does not match is refused. The public key SHALL be installed by the application's own package, and its fingerprint SHALL be documented so a user can confirm what they trust.

#### Scenario: Tampered repository index
- **WHEN** the repository's index no longer matches its signature, or is signed by a key the user does not have
- **THEN** the package manager refuses the repository and installs nothing from it

#### Scenario: Package does not match the index
- **WHEN** a package downloaded from the repository does not match the checksum the signed index records
- **THEN** the package manager refuses to install it

#### Scenario: Checking what is trusted
- **WHEN** a user wants to know which key their machine now trusts for this project
- **THEN** the documentation names the key's fingerprint and where the key file was installed, so they can compare it against their system

### Requirement: Installing the package registers the repository
The `.deb` and `.rpm` SHALL install the repository definition and its signing key, so that upgrades are offered without the user configuring anything. Where the package manager requires a user to confirm trusting the key before it will use the repository, that confirmation SHALL be asked once, SHALL identify the key by its fingerprint, and SHALL NOT recur. Removing the package SHALL leave no repository definition behind that would keep pointing the package manager at this project.

#### Scenario: First install from a downloaded package
- **WHEN** a user installs the downloaded `.deb` or `.rpm`
- **THEN** the repository and its key are registered, and their package manager offers later versions from then on

#### Scenario: Confirming the key the first time
- **WHEN** a user's package manager verifies repository metadata against keys it holds itself, and this project's key is not yet among them
- **THEN** the first upgrade asks the user once to accept the key, showing its fingerprint, and later upgrades proceed without asking

#### Scenario: Removing the application
- **WHEN** a user removes the application through their package manager, purging it where that distinction exists
- **THEN** the repository definition is gone, and their package manager no longer refers to this project

### Requirement: A user's changes to the repository file are kept
The installed repository definition SHALL be treated as a configuration file by the package manager: a user's edits SHALL survive an upgrade, with any newer version placed alongside it under the package manager's usual name, while an unedited file SHALL be updated in place. A user who disables the repository SHALL stay disabled across upgrades.

#### Scenario: The user disables automatic updates
- **WHEN** a user disables the repository by editing the installed file, and later upgrades the application
- **THEN** their edit is still in effect after the upgrade, and the version shipped with the new package is left beside it rather than replacing it

#### Scenario: The repository definition changes between versions
- **WHEN** the project changes the repository definition and the user has not edited theirs
- **THEN** the upgrade replaces it with the new one, without a prompt
