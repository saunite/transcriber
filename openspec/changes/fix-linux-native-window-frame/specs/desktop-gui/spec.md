## ADDED Requirements

### Requirement: The Linux window uses the desktop's own frame
On Linux, the application window SHALL be framed the way the user's desktop frames its other windows, and SHALL NOT impose a title bar of its own. Where the window system can draw the frame (as KDE's KWin can), the application SHALL let it, so the frame follows the user's decoration theme, button layout and title bar size. Where it cannot, the window SHALL use the toolkit's standard title bar, which follows the desktop's own button layout setting. The window SHALL stay a native client of the session's display server rather than being moved to a compatibility layer to achieve this.

#### Scenario: KDE Plasma on Wayland
- **WHEN** the installed `.deb` or `.rpm` application is opened on a KDE Plasma Wayland session
- **THEN** its frame is drawn by the window manager, matching the other windows' decoration theme, button positions and title bar height, and it is still a native Wayland window

#### Scenario: A desktop that does not draw frames
- **WHEN** the application is opened on a Wayland session whose window manager does not draw window frames, such as GNOME
- **THEN** the window has the toolkit's standard title bar with close, minimize and maximize controls, arranged by the desktop's button layout setting, and can still be moved, resized, maximized and closed

#### Scenario: The window opens without delay
- **WHEN** the application is started on Linux
- **THEN** the window appears framed from its first frame, with no visible change of frame after it is shown, and opens as quickly as before

### Requirement: Linux names follow one case rule
On Linux, the package name, the package file names of the `.deb` and `.rpm`, and the command that starts the desktop application SHALL be lowercase. Every name the desktop displays or uses to match a running window to its launcher entry SHALL be `Transcriber`: the launcher entry's file name, the window's Wayland application ID, its X11 window class, and the class the launcher entry declares for matching. The AppImage file name SHALL keep the capitalised `Transcriber` form.

#### Scenario: Installing and starting from a terminal
- **WHEN** a user installs the package with `apt` or `dnf` and starts the app from a terminal
- **THEN** the package is named `transcriber` and the command is `transcriber-gui`

#### Scenario: The desktop matches the window to its launcher entry
- **WHEN** the application is running, from the `.deb`, the `.rpm` or the AppImage, on Wayland or X11
- **THEN** the window identifies itself as `Transcriber`, the installed launcher entry is `Transcriber.desktop` and declares the same class, so the desktop matches the window to it by either route

## MODIFIED Requirements

### Requirement: Distributed application carries the project icon
The desktop application SHALL show the project icon (the Transcriber mark on its light-blue background) wherever its platform displays an application icon: launcher and menu entries, the application window and taskbar, the executable and installer on Windows, and the application bundle and disk image on macOS. Every icon size SHALL be rendered down from a source at least as large as that size, never upscaled from a smaller image. On Linux, the window SHALL identify itself to the desktop in a way that matches its installed launcher entry, so the desktop can find the icon for a running window under both Wayland and X11.

#### Scenario: Installed on Linux
- **WHEN** a user installs the `.deb` or `.rpm` and opens the desktop's application launcher
- **THEN** the Transcriber entry shows the project icon, with sizes of at least 256 pixels available to the desktop

#### Scenario: Running window on Linux
- **WHEN** a user opens the installed `.deb` or `.rpm` application on a Wayland session, or the AppImage
- **THEN** the desktop matches the window to the Transcriber launcher entry, and the window's title bar (where the frame shows an icon) and its taskbar entry show the project icon rather than a generic one

#### Scenario: Windows executable and installer
- **WHEN** a Windows user views the application executable or the installer in Explorer
- **THEN** both show the project icon rather than a generic or placeholder icon

#### Scenario: macOS application bundle
- **WHEN** a macOS user views the application bundle in Finder or the Dock
- **THEN** it shows the project icon

#### Scenario: No upscaled sizes
- **WHEN** the application's icon files are generated
- **THEN** each size is derived from a source of at least 1024×1024 pixels
