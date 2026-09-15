## ADDED Requirements

### Requirement: The application window runs only the application's own code
The application window SHALL enforce a content security policy that allows scripts, styles and other resources only from the application's own bundled files, and network connections only to the application's own inter-process channel. Script that is not part of the bundled application, whether injected into the page or loaded from a remote location, SHALL be refused by the window rather than executed.

#### Scenario: The application works under the policy
- **WHEN** a user opens the application and uses it normally: switching theme, starting and stopping a live session, and transcribing a dropped file
- **THEN** everything works as before, and the window reports no content-security-policy violations

#### Scenario: Injected script is refused
- **WHEN** markup containing an inline script or a reference to a remote script ends up in the application window
- **THEN** the window does not execute that script

#### Scenario: The policy cannot be silently dropped
- **WHEN** the application's configuration no longer sets a content security policy restricting scripts to the application's own code
- **THEN** the automated tests fail
