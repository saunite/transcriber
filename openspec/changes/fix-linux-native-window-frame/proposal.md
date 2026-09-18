## Why

On Linux under Wayland, the `.rpm` and `.deb` window doesn't look or behave like the rest of the desktop. On KDE it has a ~52px bar with its buttons on the right, although the user's KDE puts them on the left, and no icon. The AppImage, which runs under XWayland, gets KDE's own Breeze frame. Tests on 2026-09-18 traced both problems to two causes (`openspec/backlog.md`, "Consistent window decorations on Linux"):

- **The frame:** Tauri's windowing library, tao, gives every Wayland window its own `GtkHeaderBar` with a hardcoded button layout. That forces client-side decorations, and the app refuses KWin's three offers to draw the frame.
- **The icon:** the window identifies itself as `transcriber-gui`, but the only installed desktop file is `Transcriber.desktop`. This also breaks the existing requirement that the project icon shows on the application window and taskbar.

## What Changes

- On Linux, remove tao's header bar before the window is first shown. GTK then falls back to its normal behaviour: on KDE, KWin draws the frame (Breeze, the user's button layout, the user's titlebar size); on GNOME, GTK draws its own titlebar, which is native there. The window stays a native Wayland client, with no XWayland.
- Make the window's names consistent with one rule. Lowercase is reserved for the Linux package name (`transcriber`, and the `.deb`/`.rpm` file names) and the command (`transcriber-gui`). Everything the desktop shows or matches on uses `Transcriber`: the desktop file, the Wayland app ID, the X11 window class and the desktop file's `StartupWMClass`. Today the app ID, window class and `StartupWMClass` are `transcriber-gui`, so the Wayland window can't be matched to `Transcriber.desktop`. After the change, all three point at the same desktop file, so the icon is found under Wayland (`.deb`, `.rpm`) and X11 (AppImage) alike. The AppImage file name stays `Transcriber_<version>_amd64.AppImage`.
- Windows and macOS are untouched.
- Remove the "Consistent window decorations on Linux" item from `openspec/backlog.md`, since this change picks it up.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `desktop-gui`:
  - adds a requirement that the Linux window uses the desktop's own frame, following the user's desktop settings;
  - adds a Wayland scenario to "Distributed application carries the project icon", which already requires the icon on the window and taskbar but is not met there today.

## Impact

- `src-tauri/src/main.rs` (Linux-only code in the setup hook).
- A Linux-only config override, `src-tauri/tauri.linux.conf.json`, so the window starts hidden on Linux only.
- `src-tauri/Cargo.toml` (a Linux-only `gtk` dependency, already present transitively at 0.18.2).
- A desktop file template (`packaging/transcriber.desktop`) used through Tauri's `bundle.linux.deb.desktopTemplate` and `bundle.linux.rpm.desktopTemplate`, to set `StartupWMClass=Transcriber`. The AppImage must pick it up too; if the bundler doesn't pass it on, `build_portable.py` (which already repacks the AppImage) patches that one line.
- `DESIGN.md` gets a note that the Linux window frame is the desktop's own.
- No change to the page (`src/`), the engine or the other platforms.
