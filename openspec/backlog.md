# Backlog: parked work

**Do not start any item here without an explicit go-ahead from the user.** These were deliberately parked on 2026-09-13 so they are not forgotten. When one is picked up, it goes through `/opsx:propose` (or the relevant open change) and is removed from this list.

## Waiting on a Windows session

The Windows packages are built. Download them from the **Artifacts** section of `workflow_dispatch` run 34765219343 (`windows`, 784 MB) while GitHub still keeps them. Both checks fit in one sitting:

- **`fix-live-stop-orphans-engine` 5.3.** Stop a live session on Windows and confirm it reports success and leaves no `transcriber-sidecar.exe` running. The `taskkill /F /T` branch is untouched, but the shared code around it changed.
- **`02-add-release-pipeline-windows` 4.1–4.4.** Install as a non-admin user, uninstall, test on a clean machine, and run the CLI zip offline.

Verified since this list was written, so removed: the published `.deb` requires `libasound2` (its `Depends` is `libasound2, libwebkit2gtk-4.1-0, libgtk-3-0`, run 34765219343), and a `workflow_dispatch` run creates no release (`01-add-release-pipeline` 3.4, now complete).

## Parked changes (each needs a proposal)

- **Consistent window decorations on Linux.** The `.rpm`/`.deb` run as native Wayland clients and GTK draws its own title bar. The AppImage's `AppRun` hook forces `GDK_BACKEND=x11`, so KWin draws the Breeze title bar instead. Measured under X11: `_NET_FRAME_EXTENTS = 0, 0, 30, 0`, no `_GTK_FRAME_EXTENTS`; the button layout comes from `kwinrc`'s `ButtonsOnLeft=HXIA`. The user prefers the AppImage look. Likely approach: set `GDK_BACKEND=x11` at the top of `main()` in `src-tauri/src/main.rs`, before `tauri::Builder` (edition 2021, so no `unsafe`). Tauri 2.9.3 exposes no deb/rpm `desktopTemplate`. Trade-offs: XWayland scaling and HiDPI, screen-share and clipboard behaviour. It would also sidestep the Wayland crash the hook exists for (tauri-apps/tauri#8541).
- **An hour's gap between GUI and engine timestamps.** In one session the GUI marked the start as `08:43:28` and named the file `transcript_20260913_084328.txt`, while the engine's own transcript lines were stamped `07:43`/`07:44`. Not investigated. Suspect the JS and Python sides disagree on timezone or DST handling.
- **macOS release pipeline, in progress.** Change `03-add-release-pipeline-macos` is at 7/8 after run 34856241319 (2026-09-14): the helper is bundled, the app and CLI are ad-hoc signed, the smoke test passes, and the `.dmg` verifies. Left: 2.3, a run confirming the zipped app now unpacks to `Transcriber.app` (fixed with `ditto --keepParent`). Nothing macOS-specific has run on real hardware: there is no Mac.
- **The File view never shows a file run's transcript.** `desktop-gui`'s "Drop a video file" scenario promises "the resulting transcript" in the GUI, but file mode writes segments only to the output file and prints none to stdout, so `sidecar.rs` emits no `transcript-line` events and the File view stays empty. Found while planning `add-automated-local-tests`. Its GUI tests deliberately do not assert on this in either direction, so neither the gap nor a fix is enshrined.
- **The real release.** Publish a non-draft release, delete the test drafts and tags, and decide the version.

## Known limits, accepted for now

- **`.deb` live capture is not tested on real Debian/Ubuntu hardware.** It passes CI install checks in containers, which have no audio. Low risk (those distributions share the build host's ALSA layout), but unproven.
- **macOS stop behaviour is untested.** It uses the same Unix path as Linux (`pgrep -P` instead of `/proc`).
- **The AppImage device-visibility anomaly was never root-caused.** One AppImage run auto-detected `hw:0,0` while every local run of the same binary saw zero inputs. Not reproduced since the libasound fix. Worth a look only if it recurs.

## Minor

- **Dead link in README** (line ~173): it points at `openspec/changes/drop-ffmpeg-dependency/`, which was archived to `openspec/changes/archive/2026-09-08-drop-ffmpeg-dependency/`.
