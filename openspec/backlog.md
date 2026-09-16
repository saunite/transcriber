# Backlog: parked work

**Do not start any item here without an explicit go-ahead from the user.** These were deliberately parked on 2026-09-13 so they are not forgotten. When one is picked up, it goes through `/opsx:propose` (or the relevant open change) and is removed from this list.

## Waiting on a Windows session

Nothing. Every Windows check was completed on 2026-09-14.

Verified since this list was written, so removed: `02-add-release-pipeline-windows` 4.1–4.5 (per-user install and uninstall with no admin prompt, portable app, CLI offline, and the launcher's `wmic` fix), `fix-live-stop-orphans-engine` 5.3 (stop kills the sidecar on Windows), the published `.deb` requires `libasound2` (run 34765219343), and a `workflow_dispatch` run creates no release (`01-add-release-pipeline` 3.4).

## Parked changes (each needs a proposal)

- **Consistent window decorations on Linux.** The `.rpm`/`.deb` run as native Wayland clients and GTK draws its own title bar. The AppImage's `AppRun` hook forces `GDK_BACKEND=x11`, so KWin draws the Breeze title bar instead. Measured under X11: `_NET_FRAME_EXTENTS = 0, 0, 30, 0`, no `_GTK_FRAME_EXTENTS`; the button layout comes from `kwinrc`'s `ButtonsOnLeft=HXIA`. The user prefers the AppImage look. Likely approach: set `GDK_BACKEND=x11` at the top of `main()` in `src-tauri/src/main.rs`, before `tauri::Builder` (edition 2021, so no `unsafe`). Tauri 2.9.3 exposes no deb/rpm `desktopTemplate`. Trade-offs: XWayland scaling and HiDPI, screen-share and clipboard behaviour. It would also sidestep the Wayland crash the hook exists for (tauri-apps/tauri#8541).
- **An hour's gap between GUI and engine timestamps.** In one session the GUI marked the start as `08:43:28` and named the file `transcript_20260913_084328.txt`, while the engine's own transcript lines were stamped `07:43`/`07:44`. Not investigated. Suspect the JS and Python sides disagree on timezone or DST handling.
- **Windows system audio doesn't follow a default-output change mid-session.** `WASAPICapture` opens the default output's loopback once, at start, so switching output (for example, connecting Bluetooth headphones) leaves the session recording the old device. Linux follows the change on PipeWire (see "Known limits"). The user scoped this out of the logic audit's cluster D on 2026-09-15.
- **Split the model and the engine into their own packages.** The `.deb` and `.rpm` are ~283 MB because the bundled model (142 MB) and the frozen engine (153 MB) sit inside them, so every upgrade costs that much while the application's own code is under a megabyte. Both ecosystems handle split packages natively (`transcriber` depending on `transcriber-model-base` and an engine package), which would make a typical upgrade a few megabytes. Parked by the user on 2026-09-16 while proposing `add-linux-package-repos`; that change makes upgrades routine, which is what makes this worth doing.
- **The real release, and the checks that can only run after it.** Nothing is published yet: the only release and tag are the draft `v0.1.0` (checked 2026-09-15). Grouped here on 2026-09-15.
  1. **Decide the version and re-tag.** The draft `v0.1.0` and its tag point at `3d17f94`, which predates the PyAV pin (`av==18.1.0`) and the re-derived `SOURCE-PROVENANCE.txt` (archived `refresh-source-provenance-for-pyav`). Its artifacts and its notes' provenance link are stale, so don't publish that draft.
     - Delete it with `gh release delete v0.1.0 --cleanup-tag`.
     - Fast-forward `main` to `dev`.
     - Set the chosen version in `tauri.conf.json`, `Cargo.toml` and `Cargo.lock`, then tag, per `docs/building.md`, "Releasing". The workflow's preflight checks the version fields, the PyAV pin and every provenance link.
  2. **Try one artifact from the new draft, then publish it** (`docs/building.md`, "Releasing", step 4).
  3. **`add-manual-update-check` 4.3, the "update available" path against the real API.** Build a temporary debug app whose `tauri.conf.json` version is lower than the published one (e.g. `0.0.1`), or wait for the next release. Clicking **Check for updates** must show the newer version, and **Open download page** must open `https://github.com/saunite/transcriber/releases/latest` in the browser. Record the method in its archive, `openspec/changes/archive/2026-09-15-add-manual-update-check/tasks.md`.
  4. **Expect the e2e online verdict to change.** Once a release is published, `tests/test_e2e_linux.py`'s `update check online` reads "You're up to date (…)" instead of "No releases published yet". The scenario accepts either, so this is only a sanity check. Note that some VPNs drop GitHub's 140.82.112.0/22 range, and the scenario then prints `SKIP`.
  5. **Point macOS testers at the published artifacts.** The README's call for testers (see "Known limits": macOS artifacts and stop behaviour are untested) needs a public download to link to.

## Known limits, accepted for now

- **Linux system audio follows a default-output change only on PipeWire.** The engine records the monitor of the sink that is default when a session starts; WirePlumber's `linking.follow-default-target` (on by default) moves that recording to the new default's monitor. Verified on PipeWire 1.6.8 and WirePlumber 0.5.14 (`02-fix-audit-edges-linux`, 2026-09-15). Untested on PulseAudio proper or with that setting off, where the session would keep recording the old output.
- **WASAPI capture only mixes 2-channel output to mono.** `WASAPICapture.capture_stream` opens the loopback at the device's `maxInputChannels` and reshapes only when that is 2 (`wasapi_capture.py`). A 5.1 or 7.1 output device would feed interleaved samples straight to transcription as if they were mono. Found during the ponytail audit on 2026-09-14 and deliberately left out of `01-merge-dual-capture-paths`. The likely fix is `reshape(-1, CHANNELS).mean(axis=1)` for any channel count.
- **`.deb` live capture is not tested on real Debian/Ubuntu hardware.** It passes CI install checks in containers, which have no audio. Low risk (those distributions share the build host's ALSA layout), but unproven.
- **macOS artifacts are untested on real hardware.** `03-add-release-pipeline-macos` is complete in CI (runs 34856241319 and 34859698393), but there is no Mac. The README's call for testers covers opening the app, file transcription, `--coreaudio-tap`, and a downloaded copy's Gatekeeper behaviour.
- **macOS stop behaviour is untested.** It uses the same Unix path as Linux (`pgrep -P` instead of `/proc`).
- **The AppImage device-visibility anomaly was never root-caused.** One AppImage run auto-detected `hw:0,0` while every local run of the same binary saw zero inputs. Not reproduced since the libasound fix. Worth a look only if it recurs.

## Minor

- **Only skimmed in the 2026-09-15 logic audit** (not audited in depth): `macos_capture.py` and its Swift helper (no hardware), and `build_portable.py`. Every other audit cluster was done (`fix-engine-liveness`, `fix-refused-start-routing`, `fix-true-scale-time-axis`, `01-fix-audit-edges`, `02-fix-audit-edges-linux`, `03-fix-audit-edges-windows`).
