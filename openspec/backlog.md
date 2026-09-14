# Backlog: parked work

**Do not start any item here without an explicit go-ahead from the user.** These were deliberately parked on 2026-09-13 so they are not forgotten. When one is picked up, it goes through `/opsx:propose` (or the relevant open change) and is removed from this list.

## Waiting on a Windows session

Nothing. Every Windows check was completed on 2026-09-14.

Verified since this list was written, so removed: `02-add-release-pipeline-windows` 4.1–4.5 (per-user install and uninstall with no admin prompt, portable app, CLI offline, and the launcher's `wmic` fix), `fix-live-stop-orphans-engine` 5.3 (stop kills the sidecar on Windows), the published `.deb` requires `libasound2` (run 34765219343), and a `workflow_dispatch` run creates no release (`01-add-release-pipeline` 3.4).

## Parked changes (each needs a proposal)

- **Consistent window decorations on Linux.** The `.rpm`/`.deb` run as native Wayland clients and GTK draws its own title bar. The AppImage's `AppRun` hook forces `GDK_BACKEND=x11`, so KWin draws the Breeze title bar instead. Measured under X11: `_NET_FRAME_EXTENTS = 0, 0, 30, 0`, no `_GTK_FRAME_EXTENTS`; the button layout comes from `kwinrc`'s `ButtonsOnLeft=HXIA`. The user prefers the AppImage look. Likely approach: set `GDK_BACKEND=x11` at the top of `main()` in `src-tauri/src/main.rs`, before `tauri::Builder` (edition 2021, so no `unsafe`). Tauri 2.9.3 exposes no deb/rpm `desktopTemplate`. Trade-offs: XWayland scaling and HiDPI, screen-share and clipboard behaviour. It would also sidestep the Wayland crash the hook exists for (tauri-apps/tauri#8541).
- **An hour's gap between GUI and engine timestamps.** In one session the GUI marked the start as `08:43:28` and named the file `transcript_20260913_084328.txt`, while the engine's own transcript lines were stamped `07:43`/`07:44`. Not investigated. Suspect the JS and Python sides disagree on timezone or DST handling.
- **The File view never shows a file run's transcript.** `desktop-gui`'s "Drop a video file" scenario promises "the resulting transcript" in the GUI, but file mode writes segments only to the output file and prints none to stdout, so `sidecar.rs` emits no `transcript-line` events and the File view stays empty. Found while planning `add-automated-local-tests`. Its GUI tests deliberately do not assert on this in either direction, so neither the gap nor a fix is enshrined.
- **Live session shows "Capturing" before the engine is listening.** Found on Windows, 2026-09-14. The SYS/MIC indicators switch to "Capturing" as soon as `start_live_session` resolves, because `renderPens()` treats every non-idle state as capturing, including `loaded` (`src/main.js`). The status also moves to "Listening — no speech yet" on the first `sidecar-log` line of any kind, including model-loading output. The engine already prints `Listening... (Ctrl+C to stop)` once capture really starts (`transcriber.py`), so the likely fix is to wait for that line before showing either. Not platform-specific: the same JS runs everywhere.
- **The real release.** Publish a non-draft release, delete the test drafts and tags, and decide the version.

## Known limits, accepted for now

- **`.deb` live capture is not tested on real Debian/Ubuntu hardware.** It passes CI install checks in containers, which have no audio. Low risk (those distributions share the build host's ALSA layout), but unproven.
- **macOS artifacts are untested on real hardware.** `03-add-release-pipeline-macos` is complete in CI (runs 34856241319 and 34859698393), but there is no Mac. The README's call for testers covers opening the app, file transcription, `--coreaudio-tap`, and a downloaded copy's Gatekeeper behaviour.
- **macOS stop behaviour is untested.** It uses the same Unix path as Linux (`pgrep -P` instead of `/proc`).
- **The AppImage device-visibility anomaly was never root-caused.** One AppImage run auto-detected `hw:0,0` while every local run of the same binary saw zero inputs. Not reproduced since the libasound fix. Worth a look only if it recurs.

## Minor

- **Dead link in README** (line ~173): it points at `openspec/changes/drop-ffmpeg-dependency/`, which was archived to `openspec/changes/archive/2026-09-08-drop-ffmpeg-dependency/`.
