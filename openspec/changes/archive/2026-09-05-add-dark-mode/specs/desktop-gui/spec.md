## ADDED Requirements

### Requirement: Theme defaults to and follows the system setting
The system SHALL resolve the effective theme to the operating system's current light/dark preference when no explicit user theme preference has been stored, and SHALL update the effective theme automatically if the system preference changes while the app is running and no explicit override is set.

#### Scenario: First launch with no stored preference
- **WHEN** a user launches the app for the first time, with no theme preference stored
- **THEN** the app renders in whichever of light or dark matches the operating system's current setting

#### Scenario: System theme changes while the app is open
- **WHEN** a user changes their operating system's theme while the app is running and no explicit in-app theme override is set
- **THEN** the app's rendered theme updates to match the new system setting without requiring a restart

### Requirement: User can override the theme, or return to following the system
The system SHALL let the user explicitly choose Light, Dark, or System from a theme control, and SHALL persist that choice so it survives an app restart until the user changes it again.

#### Scenario: User picks an explicit theme
- **WHEN** a user selects Light or Dark from the theme control
- **THEN** the app immediately renders in that theme regardless of the operating system's setting, and still renders in that theme after the app is restarted

#### Scenario: User returns the control to System
- **WHEN** a user who had previously chosen an explicit theme selects System
- **THEN** the app resumes following the operating system's theme, including any future system theme changes

### Requirement: Resolved theme applies to native window chrome, on a best-effort basis
The system SHALL request the resolved theme (whether system-followed or explicitly overridden) for the application's native window decorations via the platform's window-theming API, not only for the in-page content. Whether the operating system's window chrome actually renders that request is outside the application's control on every platform, and SHALL NOT be required where the platform provides no per-window override.

#### Scenario: Native title bar matches the resolved theme (Windows/macOS)
- **WHEN** the resolved theme is dark, on a platform whose window-theming API supports a genuine per-window override
- **THEN** the operating system-drawn window title bar renders in its dark variant alongside the in-page dark palette, and correspondingly renders in its light variant when the resolved theme is light

#### Scenario: Best-effort request on Linux/GTK
- **WHEN** the resolved theme changes on a Linux desktop environment
- **THEN** the system still issues the platform's theme-request call (GTK's global "prefer dark theme" hint, the only mechanism `tao`/Tauri expose on Linux), but the window chrome's actual appearance follows the desktop environment's own system-wide theme setting rather than this app's request, and this is not treated as a defect
