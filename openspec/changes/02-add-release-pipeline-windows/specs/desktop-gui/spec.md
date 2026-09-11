## ADDED Requirements

### Requirement: Windows installer installs per user without administrator rights
The Windows installer SHALL install the application into the current user's own profile without requesting administrator privileges and without writing machine-wide registry keys. It SHALL create a Start Menu entry and an uninstaller, and uninstalling SHALL remove the installed application files and the Start Menu entry.

#### Scenario: Install from a standard user account
- **WHEN** a user without administrator rights runs the installer
- **THEN** installation completes with no administrator (UAC) prompt, and the application is installed under that user's profile

#### Scenario: Launch after install
- **WHEN** the user starts the application from the Start Menu entry the installer created
- **THEN** the application opens and can complete a file transcription with no network access

#### Scenario: Uninstall
- **WHEN** the user uninstalls the application through Windows' installed-apps settings or the uninstaller
- **THEN** the installed application files and the Start Menu entry are removed, with no administrator prompt
