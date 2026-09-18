# Tasks

## 1. Implementation

- [x] 1.1 Add `src-tauri/tauri.linux.conf.json` repeating the `app.windows` entry from `tauri.conf.json` with `"visible": false`, and a test that fails when the two entries differ in anything but `visible`. Verify the test passes, then change a width in one file and verify it fails.
- [x] 1.2 Add `packaging/transcriber.desktop` reproducing today's desktop file with `StartupWMClass=Transcriber`, and name it in `bundle.linux.deb.desktopTemplate` and `bundle.linux.rpm.desktopTemplate` in `src-tauri/tauri.conf.json`. Verify the built `.deb` and `.rpm` install `/usr/share/applications/Transcriber.desktop` with `StartupWMClass=Transcriber` and the other lines unchanged (`Comment`, `Exec=transcriber-gui`, `Icon=transcriber-gui`, `Name=Transcriber`).
- [ ] 1.3 Add `gtk = "0.18"` under `[target.'cfg(target_os = "linux")'.dependencies]` in `src-tauri/Cargo.toml`. In `src-tauri/src/main.rs`, under `#[cfg(target_os = "linux")]`: call `glib::set_prgname(Some("Transcriber"))` at the top of `main()` (through the gtk crate's `glib` re-export), and in the `setup` hook get the main window, call `gtk_window()?.set_titlebar(None::<&gtk::Widget>)`, then `show()`. Verify `cargo test` passes, `Cargo.lock` gains no new crate version, and the Windows cross-build (`cargo tauri build --target x86_64-pc-windows-gnu`, per `docs/building.md`) still compiles. The Tauri CLI must be installed first (`docs/building.md`).

- [x] 1.4 Stop CI lowercasing the AppImage: in `.github/workflows/release.yml`, rename only `out/Transcriber*.deb` and `out/Transcriber*.rpm`, and change the README's Linux table to `Transcriber_<version>_amd64.AppImage`. Verify with a dry run of the loop on the four Linux file names.

  **Done 2026-09-18.** A dry run on `Transcriber_0.1.0_amd64.AppImage`, `Transcriber_0.1.0_amd64.deb`, `Transcriber-0.1.0-1.x86_64.rpm` and `transcriber-cli_0.1.0_linux-x64.tar.gz` leaves the AppImage capitalised and gives `transcriber_0.1.0_amd64.deb` and `transcriber-0.1.0-1.x86_64.rpm`. The install-test step afterwards globs `/p/*.deb` and `/p/*.rpm`, so it's unaffected. The first real check is task 1.3's workflow run.

## 2. Verification on KDE Plasma (Wayland)

- [x] 2.1 Build the `.rpm` and install it. Run it with `WAYLAND_DEBUG=1` and verify:
  - the log shows `request_mode(2)` (server-side) and no `set_window_geometry` shadow offsets;
  - `set_app_id("Transcriber")`;
  - KWin reports `desktopFileName=Transcriber`, using the KWin-script-over-D-Bus query from this change's investigation.

  **Done 2026-09-18, with the built release binary run directly** (`src-tauri/target/release/transcriber-gui`, the same binary the `.rpm` packages); installing the `.rpm` needs `sudo`. Log: `request_mode(2)`, answered with `mode(2)` three times; `set_window_geometry(0, 0, 900, 640)`, down from `(24, 21, 900, 640)` with shadow offsets; `set_app_id("Transcriber")`. KWin: `resourceClass=Transcriber desktopFileName=Transcriber`. The built `.deb`, `.rpm` and AppImage all carry `StartupWMClass=Transcriber` (checked in task 1.2), so the AppImage does use the `deb` template and no `build_portable.py` rewrite is needed. While testing this, a window that was already visible also switched to server-side decoration when its header bar was removed, but at 948×688 instead of 900×640. That keeps design.md Decision 2 (start hidden) as the right call.

- [x] 2.2 Screenshot the window and compare it with the one taken on 2026-09-18. Verify:
  - a Breeze frame about 30px tall, with buttons on the left per `ButtonsOnLeft=HXIA`;
  - the project icon in the frame's menu button;
  - the project icon on the taskbar entry.

  Also check that moving, resizing from each edge, maximizing, minimizing and closing all work.

  **Done 2026-09-18,** release binary, KDE Plasma 6.7 Wayland, screen unlocked:
  - **Frame:** KWin's Breeze decoration, 27px, with close, minimize and maximize on the left per `ButtonsOnLeft=HXIA`, and the project icon in the menu button on the right. The 2026-09-18 "before" capture had tao's ~52px header bar, buttons on the right and no icon.
  - **Taskbar:** the project icon, in the icon task manager on the top panel.
  - **Window operations,** driven through KWin, with geometry read back after each settled:
    - moving works;
    - resizing to 1100×760 works;
    - asking for 300×200 is held at the 640×480 minimum (640×507 including the frame);
    - maximizing fills the work area (1745×963), and restoring works;
    - minimizing and unminimizing work;
    - closing exits the app.
  - **A wrong turn, recorded so it isn't repeated:** screenshots taken while the session was locked show the frame but a blank page. That's because WebKit doesn't paint while the session is locked. The installed v0.1.0 showed the same blank page, so it isn't a regression.

- [x] 2.3 Build the AppImage (`build_portable.py`) and verify:
  - its `usr/share/applications/Transcriber.desktop` says `StartupWMClass=Transcriber` (extract with `--appimage-extract 'usr/share/applications/*'`). If it doesn't, have `build_portable.py` rewrite that line when it repacks, and re-verify;
  - its window class is `Transcriber` (`xprop -name Transcriber WM_CLASS`);
  - the project icon shows on its title bar and taskbar under X11;
  - the file is still named `Transcriber_<version>_amd64.AppImage`.

  **Done 2026-09-18,** except the published file name. The repacked AppImage (`build_portable.py`) has `StartupWMClass=Transcriber` in its desktop file. Under X11 its window class is `"Transcriber", "Transcriber"` and `_NET_FRAME_EXTENTS = 0, 0, 30, 0` (KWin's frame). Its title bar and taskbar entry both show the project icon. The frame now matches the `.rpm`'s. **The file name:** the local build is `Transcriber_0.1.0_amd64.AppImage`. CI used to lowercase it, and v0.1.0 was published as `transcriber_0.1.0_amd64.AppImage`. Told this, the user kept the capitalised name, and task 1.4 stops CI renaming it.

- [x] 2.4 Time from launch to first visible frame, before and after, over five launches each. Verify the median hasn't grown by more than 100 ms.

  **Done 2026-09-18,** unlocked, alternating the installed v0.1.0 and the new build, five launches each. The measure is from the first Wayland message to the first buffer attached to the window. Before: 306, 260, 283, 293, 259 ms (median 283). After: 202, 187, 190, 188, 212 ms (median 190), so the first frame arrives about 90 ms sooner, because GTK no longer renders a header bar and shadow first. This is the window's first frame, not WebKit's first paint of the page. An earlier baseline, taken while the session was locked, was discarded.

## 3. Verification where the window manager doesn't draw frames

- [ ] 3.1 Start a nested GNOME Shell or Mutter session (`gnome-shell --devkit` or `mutter --nested`, whichever this version supports) and open the app inside it. Verify GTK's standard titlebar appears with close, minimize and maximize, and that move, resize, maximize and close work. If no nested session can be started, record GNOME as untested in this task, with the reason, rather than checking it off.

  **Partly verified, 2026-09-18, so left open.** GNOME Shell 50 / Mutter 50 can't run nested here: `--nested` is gone and `--devkit` needs `mutter-devkit`, which isn't installed. The app did run inside a headless GNOME Shell (`--headless --virtual-monitor 1280x800`, on its own D-Bus session):
  - **Verified:** GNOME offered no server-side decoration protocol, and GTK drew its own frame: `set_window_geometry(24, 21, 900, 677)`, a 37px standard titlebar with shadow margins, against tao's ~52px header bar. The app ID was `Transcriber`.
  - **Not verified:** the titlebar's buttons and move, resize, maximize and close under GNOME. GNOME Shell refuses screenshots from any client but its own tool ("Screenshot is not allowed"). `GTK_CSD=1` can't show the fallback on KDE either, because GTK on Wayland ignores it and still takes KWin's frame.

## 4. Suites and design record

- [ ] 4.1 Run `.venv/bin/python run_tests.py` with `TRANSCRIBER_TEST_SPEECH` set, and verify every suite passes, including `tests/test_e2e_linux.py` with no skips.
- [x] 4.2 Impeccable verify-only pass on the `src-index-html` surface, per DESIGN.md:
  - light and dark screenshots at 900x640 and at the 640x480 minimum, confirming the page itself is unchanged under the new frame;
  - a finish review by the `impeccable-finish-reviewer` agent, with its verdict recorded here;
  - one `detect.mjs` run (no page files change; note it if it ran degraded);
  - a DESIGN.md note that on Linux the window frame is the desktop's own and not part of the design.

  **Done 2026-09-18.** Impeccable, Operate mode, verify-only, with context loaded via `context.mjs --target src/index.html`.
  - **Captures:** the real window on KDE Wayland, driven through tauri-driver with a throwaway data directory, in dark and light at 900×640 and 640×480. The page area measured exactly those sizes, with no horizontal overflow.
  - **Reviewer:** the `impeccable-finish-reviewer` agent returned **Verdict: ship**, with no material fixes. The title block meets the thinner frame cleanly at both sizes and in both themes. Rail, chart and engine log are unchanged, and the page gains about 22px of height. In Light the dark KWin frame over the light panel is the desktop's decoration following the desktop's colour scheme, which the existing "Resolved theme applies to native window chrome" requirement already accepts. The frame's title and the page's "TRANSCRIBER" lettering were paired the same way under the old header bar, so they stay.
  - **Detector:** `detect.mjs` on `src/index.html` and `src/style.css` ran **degraded** (its HTML parser modules are unavailable). It reported 16 findings, 15 off-ramp font sizes and 1 radius, all in files this change doesn't touch (`git diff HEAD -- src/` is empty), so none were introduced here.
  - **DESIGN.md:** the Layout section now says the window frame is not part of the design. On Linux it's the desktop's own, with the user's button layout and the desktop's colour scheme, and the title block begins directly under it.

- [x] 4.3 Remove "Consistent window decorations on Linux" from `openspec/backlog.md`. Verify with `grep -n "window decorations" openspec/backlog.md`.
- [x] 4.4 Run `openspec validate fix-linux-native-window-frame --strict` and verify it passes.
