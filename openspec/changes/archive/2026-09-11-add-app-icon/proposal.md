## Why

The app ships a 32×32 placeholder icon (`src-tauri/icons/icon.png` and `icon.ico`, one size each), so launchers, taskbars and installers show it blurry or not at all. The user has drawn a real icon, `resources/transcriber-icon-light-blue-bg.png`, and wants it used everywhere an icon can be set.

That file is the right design, but at 64×64 it's too small to be the source. Platform icon sets go up to 256 px (Windows `.ico`), 512 px (Linux HiDPI), and 1024 px (macOS `.icns`), and a 64 px source upscaled by Tauri's generator comes out visibly soft. The same mark exists at full resolution in `resources/src/transcriber-icon-full-size.xcf` (805×802), so a proper 1024×1024 master can be exported from it.

## What Changes

- **A 1024×1024 master icon, `resources/transcriber-icon-1024.png`,** exported from the full-size `.xcf`: square, cropped close to the mark, on the same light-blue background (rgb 186, 244, 255) as the user's 64 px file. The export command is documented, so the master can be regenerated when the `.xcf` changes.
- **App icons regenerated from the master** with `cargo tauri icon`: 32, 64, 128, 256 and 512 px PNGs, a multi-size `.ico` (16 to 256 px), and an `.icns`. `bundle.icon` lists them, so they reach every Tauri artifact: the Linux menu entry and window icon (AppImage, `.deb`, `.rpm`), the Windows executable and the NSIS installer, and the macOS `.app` and `.dmg`. The generator's Android, iOS and Windows Store outputs are dropped, since this app ships none of those.
- **The standalone CLI binary gets the icon on Windows and macOS** (PyInstaller `--icon`), so `transcriber.exe` stops showing the generic Python icon. Linux executables have no embedded icon.
- **The README shows the icon** in its header, and gains a short "Updating the icon" note.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `desktop-gui`: adds the requirement that the distributed app shows the project icon wherever its platform displays one, rendered without upscaling.

## Impact

- **New**: `resources/transcriber-icon-1024.png`.
- **Replaced**: `src-tauri/icons/`, which goes from 2 placeholder files to the generated desktop set.
- **Changed**:
  - `src-tauri/tauri.conf.json`: the `bundle.icon` list.
  - `build_sidecar.py`: `--icon` on Windows and macOS.
  - `README.md`.
- **Unchanged**: the user's `resources/*.png` and `.xcf` files, which stay as the design sources.
- **Out of scope**: a simplified small-size variant for 16–32 px, an in-app logo (the UI follows `DESIGN.md`, so that's a separate design decision), a macOS-style rounded-rectangle shape, and GitHub's social preview image, which is set by hand in the repository settings. See design.md.
- **Verification**: Linux is checked on the next release tag run and on the Fedora/KDE machine. The Windows and macOS icons ride along with `02`/`03`, which own those builds.
