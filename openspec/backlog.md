# Backlog: parked work

**Do not start any item here without an explicit go-ahead from the user.** These were deliberately parked on 2026-09-13 so they are not forgotten. When one is picked up, it goes through `/opsx:propose` (or the relevant open change) and is removed from this list.

## Waiting on a Windows session

Nothing. Every Windows check was completed on 2026-09-14.

Verified since this list was written, so removed: `02-add-release-pipeline-windows` 4.1–4.5 (per-user install and uninstall with no admin prompt, portable app, CLI offline, and the launcher's `wmic` fix), `fix-live-stop-orphans-engine` 5.3 (stop kills the sidecar on Windows), the published `.deb` requires `libasound2` (run 34765219343), and a `workflow_dispatch` run creates no release (`01-add-release-pipeline` 3.4).

## Parked changes (each needs a proposal)

- **Consistent window decorations on Linux.** The `.rpm`/`.deb` run as native Wayland clients and GTK draws its own title bar. The AppImage's `AppRun` hook forces `GDK_BACKEND=x11`, so KWin draws the Breeze title bar instead. Measured under X11: `_NET_FRAME_EXTENTS = 0, 0, 30, 0`, no `_GTK_FRAME_EXTENTS`; the button layout comes from `kwinrc`'s `ButtonsOnLeft=HXIA`. The user prefers the AppImage look. Likely approach: set `GDK_BACKEND=x11` at the top of `main()` in `src-tauri/src/main.rs`, before `tauri::Builder` (edition 2021, so no `unsafe`). Tauri 2.9.3 exposes no deb/rpm `desktopTemplate`. Trade-offs: XWayland scaling and HiDPI, screen-share and clipboard behaviour. It would also sidestep the Wayland crash the hook exists for (tauri-apps/tauri#8541).
- **An hour's gap between GUI and engine timestamps.** In one session the GUI marked the start as `08:43:28` and named the file `transcript_20260913_084328.txt`, while the engine's own transcript lines were stamped `07:43`/`07:44`. Not investigated. Suspect the JS and Python sides disagree on timezone or DST handling.
- **The File view never shows a file run's transcript.** `desktop-gui`'s "Drop a video file" scenario promises "the resulting transcript" in the GUI, but file mode writes segments only to the output file and prints none to stdout, so `sidecar.rs` emits no `transcript-line` events and the File view stays empty. Found while planning `add-automated-local-tests`. Its GUI tests deliberately do not assert on this in either direction, so neither the gap nor a fix is enshrined.
- **Logic audit follow-ups (2026-09-15).** A read-through of every product module against its specs, comments and UI promises. Cluster A (engine liveness) is the open change `fix-engine-liveness`. The rest were read in the code but not reproduced. Each cluster should become one change that starts with a test failing today.
  - **B. Lines and charts routed to the wrong place** (frontend only; test with the fake bridge):
    - **B1:** `startNextFile` sets `currentFlow = "file"` and clears the File chart *before* the shell refuses a drop during a live session, and nothing resets it. All later live lines land on the File chart, and Live shows "stalled".
    - **B2:** `startLiveSession` clears the previous live chart before a start that can be refused.
  - **C. The time axis is not true scale** (needs a design decision: stamp lines at speech time, i.e. base plus offset):
    - **C1:** `--actual-time` stamps are the moment a line is *printed*, after inference. All segments of a chunk share one stamp, and SYS (10 s) and MIC (5 s) chunks lag differently.
    - **C2:** the 1 s chunk overlap is transcribed twice, repeating words, and `time_offset` advances by the full chunk including the overlap. Relative stamps drift +1 s per chunk, or +20 % on MIC.
    - **C3:** `relayout()` measures gaps from hidden lines under Show/Find, and an out-of-order line moves `previous` backwards, inflating the next gap.
    - **C4:** `formatDuration` rounds to "59 min 60 s" and "1 h 60 min".
  - **D. CLI, launchers and edges:**
    - **D1:** `transcribe_live_simple` with an explicit `--audio-device` runs inference inside PortAudio's callback (overflow, dropped audio), and its silence `KeyboardInterrupt` is raised on the callback thread, so auto-stop never stops.
    - **D2:** `win-start-transcription.bat`'s `"%~1:~0,1%"` isn't valid cmd syntax, so a flags-only call takes the first flag as the name prefix.
    - **D3:** `transcribe_file.bat` hard-codes `--language en`.
    - **D4:** the launchers run `transcriber.py` by relative path, and pass `--model base`, so `--model-path` gets labelled base.
    - **D5:** `withFreshTimestamp` splits on the last `.` of the whole path (`/home/a.b/transcript` goes to the wrong folder).
    - **D6:** the WASAPI default-loopback match is a substring test, and Linux keeps recording the old sink's monitor after the default output changes.
    - **D7:** the stall hint's copy says "raising and lowering the pens", but no such control exists.
  - **Only skimmed** (not audited in depth): `macos_capture.py` and its Swift helper (no hardware), and `build_portable.py`.
- **The real release, and the checks that can only run after it.** Nothing is published yet: the only release and tag are the draft `v0.1.0` (checked 2026-09-15). Grouped here on 2026-09-15.
  1. **Decide the version and re-tag.** The draft `v0.1.0` and its tag point at `3d17f94`, which predates the PyAV pin (`av==18.1.0`) and the re-derived `SOURCE-PROVENANCE.txt` (archived `refresh-source-provenance-for-pyav`). Its artifacts and its notes' provenance link are stale, so don't publish that draft.
     - Delete it with `gh release delete v0.1.0 --cleanup-tag`.
     - Fast-forward `main` to `dev`.
     - Set the chosen version in `tauri.conf.json`, `Cargo.toml` and `Cargo.lock`, then tag, per README "Releasing". The workflow's preflight checks the version fields, the PyAV pin and every provenance link.
  2. **Try one artifact from the new draft, then publish it** (README "Releasing" step 4).
  3. **`add-manual-update-check` 4.3, the "update available" path against the real API.** Build a temporary debug app whose `tauri.conf.json` version is lower than the published one (e.g. `0.0.1`), or wait for the next release. Clicking **Check for updates** must show the newer version, and **Open download page** must open `https://github.com/saunite/transcriber/releases/latest` in the browser. Record the method in its archive, `openspec/changes/archive/2026-09-15-add-manual-update-check/tasks.md`.
  4. **Expect the e2e online verdict to change.** Once a release is published, `tests/test_e2e_linux.py`'s `update check online` reads "You're up to date (…)" instead of "No releases published yet". The scenario accepts either, so this is only a sanity check. Note that some VPNs drop GitHub's 140.82.112.0/22 range, and the scenario then prints `SKIP`.
  5. **Point macOS testers at the published artifacts.** The README's call for testers (see "Known limits": macOS artifacts and stop behaviour are untested) needs a public download to link to.

## Known limits, accepted for now

- **WASAPI capture only mixes 2-channel output to mono.** `WASAPICapture.capture_stream` opens the loopback at the device's `maxInputChannels` and reshapes only when that is 2 (`wasapi_capture.py`). A 5.1 or 7.1 output device would feed interleaved samples straight to transcription as if they were mono. Found during the ponytail audit on 2026-09-14 and deliberately left out of `01-merge-dual-capture-paths`. The likely fix is `reshape(-1, CHANNELS).mean(axis=1)` for any channel count.
- **`.deb` live capture is not tested on real Debian/Ubuntu hardware.** It passes CI install checks in containers, which have no audio. Low risk (those distributions share the build host's ALSA layout), but unproven.
- **macOS artifacts are untested on real hardware.** `03-add-release-pipeline-macos` is complete in CI (runs 34856241319 and 34859698393), but there is no Mac. The README's call for testers covers opening the app, file transcription, `--coreaudio-tap`, and a downloaded copy's Gatekeeper behaviour.
- **macOS stop behaviour is untested.** It uses the same Unix path as Linux (`pgrep -P` instead of `/proc`).
- **The AppImage device-visibility anomaly was never root-caused.** One AppImage run auto-detected `hw:0,0` while every local run of the same binary saw zero inputs. Not reproduced since the libasound fix. Worth a look only if it recurs.

## Minor

- **Dead link in README** (line ~173): it points at `openspec/changes/drop-ffmpeg-dependency/`, which was archived to `openspec/changes/archive/2026-09-08-drop-ffmpeg-dependency/`.
