# Backlog: parked work

**Do not start any item here without an explicit go-ahead from the user.** These were deliberately parked on 2026-09-13 so they are not forgotten. When one is picked up, it goes through `/opsx:propose` (or the relevant open change) and is removed from this list.

## Waiting on a tagged CI run

Runs are paused. A new run needs the existing `v0.1.0` draft release and tag deleted, then a re-tag at the current commit. One run covers all three:

- **`fix-live-stop-orphans-engine` 5.3.** On Windows, stop a live session and confirm it reports success and leaves no `transcriber-sidecar.exe` running. The `taskkill /F /T` branch is untouched, but surrounding shared code changed.
- **`02-add-release-pipeline-windows` 4.1–4.4.** Install as a non-admin user, uninstall, test on a clean machine, and run the CLI zip offline. Best done in the same Windows session as the item above.
- **The published `.deb` carries `libasound2`.** `bundle.linux.deb.depends` was added after run 34699748992, so it is proven in config only. Check with `dpkg-deb -f <deb> Depends`.

## Needs a decision first

- **`01-add-release-pipeline` 3.4.** Confirm a manual `workflow_dispatch` run creates no release. GitHub only dispatches from the default branch, and `main` is far behind `dev`, so this needs `dev` pushed to `main` first.

## Parked changes (each needs a proposal)

- **Consistent window decorations on Linux.** The `.rpm`/`.deb` run as native Wayland clients and GTK draws its own title bar. The AppImage's `AppRun` hook forces `GDK_BACKEND=x11`, so KWin draws the Breeze title bar instead. Measured under X11: `_NET_FRAME_EXTENTS = 0, 0, 30, 0`, no `_GTK_FRAME_EXTENTS`; the button layout comes from `kwinrc`'s `ButtonsOnLeft=HXIA`. The user prefers the AppImage look. Likely approach: set `GDK_BACKEND=x11` at the top of `main()` in `src-tauri/src/main.rs`, before `tauri::Builder` (edition 2021, so no `unsafe`). Tauri 2.9.3 exposes no deb/rpm `desktopTemplate`. Trade-offs: XWayland scaling and HiDPI, screen-share and clipboard behaviour. It would also sidestep the Wayland crash the hook exists for (tauri-apps/tauri#8541).
- **An hour's gap between GUI and engine timestamps.** In one session the GUI marked the start as `08:43:28` and named the file `transcript_20260913_084328.txt`, while the engine's own transcript lines were stamped `07:43`/`07:44`. Not investigated. Suspect the JS and Python sides disagree on timezone or DST handling.
- **macOS release pipeline.** Change `03-add-release-pipeline-macos` exists but is not started (0/8). Nothing on macOS has ever been run: there is no Mac.
- **The real release.** Publish a non-draft release, delete the test drafts and tags, and decide the version.

## Known limits, accepted for now

- **`.deb` live capture is not tested on real Debian/Ubuntu hardware.** It passes CI install checks in containers, which have no audio. Low risk (those distributions share the build host's ALSA layout), but unproven.
- **macOS stop behaviour is untested.** It uses the same Unix path as Linux (`pgrep -P` instead of `/proc`).
- **The AppImage device-visibility anomaly was never root-caused.** One AppImage run auto-detected `hw:0,0` while every local run of the same binary saw zero inputs. Not reproduced since the libasound fix. Worth a look only if it recurs.

## Minor

- **Dead link in README** (line ~173): it points at `openspec/changes/drop-ffmpeg-dependency/`, which was archived to `openspec/changes/archive/2026-09-08-drop-ffmpeg-dependency/`.
