## ADDED Requirements

### Requirement: Distributed application carries the project icon
The desktop application SHALL show the project icon (the Transcriber mark on its light-blue background) wherever its platform displays an application icon: launcher and menu entries, the application window and taskbar, the executable and installer on Windows, and the application bundle and disk image on macOS. Every icon size SHALL be rendered down from a source at least as large as that size, never upscaled from a smaller image.

#### Scenario: Installed on Linux
- **WHEN** a user installs the `.deb` or `.rpm` and opens the desktop's application launcher
- **THEN** the Transcriber entry shows the project icon, with sizes of at least 256 pixels available to the desktop

#### Scenario: Windows executable and installer
- **WHEN** a Windows user views the application executable or the installer in Explorer
- **THEN** both show the project icon rather than a generic or placeholder icon

#### Scenario: macOS application bundle
- **WHEN** a macOS user views the application bundle in Finder or the Dock
- **THEN** it shows the project icon

#### Scenario: No upscaled sizes
- **WHEN** the application's icon files are generated
- **THEN** each size is derived from a source of at least 1024×1024 pixels
