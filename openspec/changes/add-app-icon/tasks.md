## 1. Master icon

- [x] 1.1 Export `resources/transcriber-icon-1024.png` from `resources/src/transcriber-icon-full-size.xcf` with design.md Decision 1's command. Verify with `identify` that it is 1024x1024 and opaque, with a corner pixel of `srgba(186,244,255,1)`. Then look at it next to `resources/transcriber-icon-light-blue-bg.png`: same mark and colors, only sharper.

  **The first export was wrong and got ticked by mistake.** Without `-compose over`, ImageMagick's XCF reader leaves `Compose: None` on the flattened image, and `-extent` then paints a solid light-blue square with no mark (1 colour, 497 bytes). That still passes the size, opacity and corner-colour checks, and I skipped the "look at it" step. It was caught at 2.1: the generated `.icns` came out at only 12,651 bytes, and its 1024 px entry had 1 colour. Fixed by adding `-compose over` (design.md Decision 1 and README updated). **Re-verified 2026-09-11:** 1024x1024, opaque, corner `srgba(186,244,255,1)`, 1,096 colours, 61,553 bytes. `compare -metric AE` against the two-step reference export is 0, and viewing it shows the full mark, crisp, on the light-blue background. Lesson for this task: check the colour count or look at the image; size, opacity and corner colour can't tell a blank image from a real one.

## 2. Application icons

- [x] 2.1 Run `cargo tauri icon resources/transcriber-icon-1024.png` to replace `src-tauri/icons/`, then delete `android/`, `ios/`, `Square*Logo.png` and `StoreLogo.png` (design.md Decision 2). Verify that `file src-tauri/icons/*` lists exactly `32x32.png`, `64x64.png`, `128x128.png`, `128x128@2x.png` (256), `icon.png` (512), `icon.ico`, and `icon.icns`, and that `identify src-tauri/icons/icon.ico` reports 16 through 256 px.
- [x] 2.2 Set `bundle.icon` in `src-tauri/tauri.conf.json` to design.md Decision 2's list. Verify with `cargo check` in `src-tauri/`, which runs Tauri's build script, validates every listed icon path, and embeds the icons.
- [ ] 2.3 Linux end to end, with the next release tag run's packages:
  - `rpm -qpl` on the `.rpm` lists `transcriber-gui.png` under the `hicolor` 32x32, 128x128, 256x256 and 512x512 directories.
  - On the Fedora/KDE machine, the installed app shows the icon in the application launcher, the window, and the taskbar.

  **Expected: a `cargo tauri dev` run shows KDE's generic Wayland "W" icon (seen by the user 2026-09-11).** Under Wayland, an app can't set its own window icon. KDE looks up the window's app_id in the installed `.desktop` files and takes the icon from there. Tauri 2.11 sets no app_id unless `app.enableGtkAppId` is on (`tauri-2.11.5/src/app.rs`, around line 2280), so GTK falls back to the program name, `transcriber-gui`. The packaged `Transcriber.desktop` has `StartupWMClass=transcriber-gui` and `Icon=transcriber-gui`, so the *installed* app should match and show the icon; a dev run has no installed entry to match. If the installed app still shows "W", the next step is `app.enableGtkAppId` plus a desktop entry named after the identifier.

## 3. CLI binary icon

- [x] 3.1 In `build_sidecar.py`, pass `--icon src-tauri/icons/icon.ico` on Windows and `--icon src-tauri/icons/icon.icns` on macOS, and nothing on Linux (design.md Decision 3). Verify that the Linux freeze still succeeds unchanged (`.venv/bin/python build_sidecar.py`, exit 0). The Windows check happens during `02`'s hardware verification: `transcriber.exe` and `transcriber-gui.exe` show the mark in Explorer, and so does the setup exe. The macOS check is on `03`'s testers list.

## 4. README

- [x] 4.1 Add the centered header image (design.md Decision 4) and a short "Updating the icon" note under "Building it yourself", with the export command and the `cargo tauri icon` plus cleanup step. Verify that the image path resolves (`test -f resources/transcriber-icon-1024.png`), and that it renders at the top of the README on GitHub after the next push.

  **Verified 2026-09-11 after pushing `dev` (`94e0404`):** `raw.githubusercontent.com/saunite/transcriber/dev/resources/transcriber-icon-1024.png` returns HTTP 200, a 1024x1024 PNG with 1,096 colours (the real icon, not the blank first export). The README's first line on `dev` is the centered header `<img>` that uses it, and the relative path resolves on GitHub.
