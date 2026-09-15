## ADDED Requirements

### Requirement: Users can check for a newer release on demand
The application SHALL offer a control that checks whether a newer release of the application has been published, and SHALL contact the network for that check only when the user activates the control. It SHALL NOT check automatically, in the background, or at startup. Apart from this user-initiated check, the application SHALL make no network request. The result SHALL tell the user one of: that they are up to date, which newer version is available, that no release has been published yet, or that the check could not be completed. When a newer version is available, the application SHALL offer to open the project's own releases page in the user's browser, and SHALL NOT open any location supplied by the network.

#### Scenario: A newer release exists
- **WHEN** the user checks for updates and the newest published release has a higher version than the running application
- **THEN** the application reports that version as available and offers to open the project's releases page

#### Scenario: Already on the newest release
- **WHEN** the user checks for updates and the newest published release is the same as or older than the running application
- **THEN** the application reports that it is up to date, naming the running version

#### Scenario: No release published yet
- **WHEN** the user checks for updates and the project has no published release
- **THEN** the application reports that no release has been published yet

#### Scenario: The check cannot complete
- **WHEN** the user checks for updates with no network access, or the release host does not answer or answers unexpectedly
- **THEN** the application reports that it could not check for updates, without an error dialog, and every other feature keeps working

#### Scenario: No check without the user
- **WHEN** the application starts and is used for transcription without the user activating the update check
- **THEN** the application makes no network request
