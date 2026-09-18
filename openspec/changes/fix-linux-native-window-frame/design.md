## Context

See `proposal.md` for why. Measured on KDE Plasma (Wayland), Fedora 44, on 2026-09-18:

- tao 0.35.3 (`src/platform_impl/linux/wayland/header.rs`) calls `WlHeader::setup` for every window when the backend is Wayland. It builds a `GtkHeaderBar` with `decoration_layout("menu:minimize,maximize,close")`, wraps it in an `EventBox`, and calls `window.set_titlebar(...)`. It also wires its own resize handling to that header.
- GTK3 decides between drawing its own frame and letting the compositor draw it when the window is realized. A window with a custom titlebar is always client-decorated. Without one, GTK3 on Wayland uses KDE's `org_kde_kwin_server_decoration` protocol and accepts server-side decorations when the compositor's default mode is server, which KWin's is (`default_mode(2)` in the protocol log).
- GTK3's `set_titlebar` documentation warns that it may not work on a window that is already visible.
- The window sends `xdg_toplevel.set_app_id("transcriber-gui")`. That is GLib's program name, the binary name. Tauri passes no GTK application id. The bundler names the desktop file after `productName`: `Transcriber.desktop`, with `StartupWMClass=transcriber-gui`.
- The window is declared in `src-tauri/tauri.conf.json` with `"visible": true`, so Tauri shows it before the `setup` hook runs.

## Goals / Non-Goals

**Goals:**
- On KDE Wayland, KWin draws the frame: Breeze, the user's button layout, the user's titlebar height.
- On desktops that don't draw frames (GNOME), GTK's standard titlebar, following `gtk-decoration-layout`.
- The desktop matches the running window to `Transcriber.desktop` under Wayland, and still does under X11 for the AppImage.

**Non-Goals:**
- Changing the AppImage's backend. Its `GDK_BACKEND=x11` comes from linuxdeploy's GTK hook. Removing it is a separate question, tied to the crash that hook cites (tauri-apps/tauri#8541).
- Windows and macOS. Nothing there changes.
- A custom, app-drawn frame.

## Decisions

**1. Remove tao's header bar with `set_titlebar(None)` on the GTK window, in the `setup` hook, Linux only.**
Get the window's `gtk::ApplicationWindow` through Tauri's `gtk_window()` and call `set_titlebar(None::<&gtk::Widget>)`, under `#[cfg(target_os = "linux")]`. Done unconditionally on Linux, so under X11 it is a no-op because tao installs no header there. The `gtk` crate becomes a direct Linux-only dependency at the version already in `Cargo.lock` (0.18.2), so the build pulls nothing new.
- *Force `GDK_BACKEND=x11`:* rejected as the fix. It costs XWayland: fractional-scaling blur, screen-share and clipboard through the compatibility layer. The spec now asks for a native client.
- *Our own frame (`decorations: false`):* identical everywhere and native nowhere. It means reimplementing drag, resize, snapping and the window menu, plus a full design pass.
- *Patch or fork tao:* a maintenance burden for a two-line result. Worth an upstream issue instead.

**2. Start the window hidden on Linux only, and show it after removing the header bar.**
GTK fixes the decoration mode when the window is realized, and `set_titlebar` isn't reliable on a visible window. So the window has to start hidden and be shown by the setup hook. That override goes in `src-tauri/tauri.linux.conf.json`, which Tauri merges over the main config on Linux only. Merge-patch replaces arrays whole, so that file repeats the whole `app.windows` entry with `"visible": false`, and the setup hook calls `show()` after `set_titlebar(None)`.
- *`"visible": false` for every platform plus `show()` everywhere:* one config instead of two, but it changes how Windows and macOS open, and neither can be tested here.
- The cost of repeating the entry: the window size and title now live in two files. A test compares the two entries, so they can't drift apart without failing.

**3. One naming rule: lowercase for the package and the command, `Transcriber` for everything the desktop matches on.**
Decided by the user on 2026-09-18. Lowercase stays where Linux convention expects it: the package name `transcriber`, the `.deb`/`.rpm` file names, and the command `/usr/bin/transcriber-gui`, which is typed in terminals and can't become `transcriber` because that is the CLI binary's name. The AppImage file keeps `Transcriber_<version>_amd64.AppImage`. Found while applying: CI's rename loop lowercased every `Transcriber*` artifact, the AppImage included, so v0.1.0 shipped `transcriber_0.1.0_amd64.AppImage`. The user chose the capitalised name on 2026-09-18, so the loop now renames only `*.deb` and `*.rpm`. The three identity names all become `Transcriber`:

| Name | Today | After |
|---|---|---|
| Wayland app ID | `transcriber-gui` | `Transcriber` |
| X11 window class | `transcriber-gui` | `Transcriber` |
| `StartupWMClass=` | `transcriber-gui` | `Transcriber` |
| Desktop file | `Transcriber.desktop` | unchanged |

The first two come from `glib::set_prgname(Some("Transcriber"))` at the top of `main()`, Linux only. GTK uses the program name as both, and only sets it itself if nothing has. The third comes from a desktop file template, `packaging/transcriber.desktop`, named in `bundle.linux.deb.desktopTemplate` and `bundle.linux.rpm.desktopTemplate`. It reproduces today's file (`Categories`, `Comment`, `Exec`, `Icon`, `Name`, `Terminal`, `Type`) with `StartupWMClass=Transcriber`. With all three the same, Wayland matches by file name and X11 by `StartupWMClass`, and both land on `Transcriber.desktop`. So the AppImage's icon can't be lost to a mismatch.
- *`app.enableGTKAppId`:* uses the identifier `com.transcriber.app`, which matches no desktop file.
- *Rename the desktop file to match `transcriber-gui`:* the bundler names it after `productName` and has no setting for the file name. It would also break the rule.
- *A second desktop file named `transcriber-gui.desktop`:* two launcher entries.
- *The icon name `transcriber-gui`* stays. Nobody sees it; it is only looked up from the desktop file's `Icon=`.
- **To verify:** the AppImage's desktop file is identical to the `.rpm`'s today (extracted on 2026-09-18), which suggests the bundler builds both from the same source, but that it honours `deb.desktopTemplate` is unproven. If it doesn't, `build_portable.py`, which already repacks the AppImage, rewrites that one line.

## Risks / Trade-offs

- [GTK may still fix the frame at an earlier stage than the setup hook, even with the window hidden] → Task 2.1 checks the protocol log for `request_mode(2)`. If it doesn't appear, the fallback is creating the window from code in the setup hook, where it can be configured before realizing. That's a larger change, and would need to come back as a design update.
- [Removing tao's header also removes the resize handling tao wired to it] → On KDE, KWin handles resizing. On GNOME, GTK's standard titlebar has its own. Both get checked.
- [A future tao release changes or drops the header bar] → `set_titlebar(None)` is harmless when there is no header, so the fix degrades to a no-op rather than breaking.
- [GNOME can't be tested on real hardware] → Test under a nested GNOME Shell or Mutter session if one starts here (both are installed). If neither does, record GNOME as untested rather than claim it.
- [The window hidden at start could delay its appearance] → `show()` runs in the setup hook, before the event loop's first frame, so it must still appear at once. The e2e suite and a timing check confirm that.
- [The e2e suite drives the window through tauri-driver] → Run the full e2e suite. A hidden window that never shows would fail every scenario.
