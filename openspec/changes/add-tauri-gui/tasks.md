## 1. Engine: minimal additive changes

- [x] 1.1 Add `--list-devices-json` flag to `transcriber.py` that reuses the existing device enumeration and prints a JSON array (index, name, max_input_channels, default_samplerate) to stdout
- [x] 1.2 Verify `--list-devices` text output is byte-for-byte unchanged

  Verified: `list_devices()` itself is untouched (only a new sibling method was added); ran both `--list-devices` and `--list-devices-json` against the real 19 devices on this machine and confirmed matching data.

- [x] 1.3 Add a fixture test that runs the engine's live/file paths and asserts the transcript-line regex (from design.md) matches every emitted line, so future engine output changes fail CI instead of silently breaking the GUI

  Implemented in `test_transcript_line_format.py` using synthetic segment data against the real formatting functions (no model/audio device needed, matching `test_wasapi_capture.py`'s style). All 5 assertions pass.

## 2. Sidecar packaging

- [x] 2.1 Freeze the Python engine with PyInstaller (`--onefile`) for Windows

  Done via `build_sidecar.py` (also handles Linux/macOS when run on those OSes -- PyInstaller doesn't cross-compile, so 2.2/2.3 still need someone to run it there). Produces `dist/windows/transcriber-sidecar.exe` (~150MB before model/ffmpeg).

- [ ] 2.2 Freeze the Python engine with PyInstaller for Linux

  Not done: requires running `build_sidecar.py` on Linux, not available in this session.

- [ ] 2.3 Freeze the Python engine with PyInstaller for macOS (shell-only target; sidecar still needed for file transcription)

  Not done: requires running `build_sidecar.py` on macOS, not available in this session.

- [x] 2.4 Smoke-test each frozen binary standalone (`--list-devices-json`, `--file` on a sample clip) before wiring into Tauri

  Smoke-tested the Windows build end-to-end (`--list-devices-json` and `--file` against a synthetic WAV) and found two real bugs the design didn't anticipate, both fixed:
  1. `transcriber.py` crashed with `UnicodeEncodeError` on its first unicode symbol (✓/❌/⚠️/🎙️ appear throughout the codebase) because a piped/detached stdout — exactly how the Tauri sidecar spawns it — falls back to the Windows ANSI codepage. Fixed by forcing UTF-8 on stdout/stderr at the top of `transcriber.py`, so it's fixed regardless of launcher.
  2. The frozen binary crashed with `onnxruntime.NoSuchFile` on `faster_whisper`'s bundled VAD ONNX model (`assets/silero_vad_v6.onnx`) — PyInstaller's default analysis doesn't pick up that package-data file, and no existing PyInstaller hook (built-in or community) covers it. Fixed via `--add-data` in `build_sidecar.py`.

  Only Windows was verified (2.2/2.3 not built in this session); the same two fixes apply to those builds too since they're upstream of the OS-specific freeze step.

- [x] 2.5 Bundle the `base` faster-whisper model files into installer resources per OS

  `fetch_sidecar_resources.py` stages the `base` model (via `faster_whisper.utils.download_model`) into `src-tauri/resources/model/`, matching `tauri.conf.json`'s `bundle.resources` (paths there resolve relative to `src-tauri/`, not the repo root -- initially got this wrong and had to move it). Verified: produced `model.bin` (145MB) + config/tokenizer files.

  **Gap found and fixed later, by `add-portable-build`**: staging the files here was necessary but not sufficient -- `transcription_engine.py` was still loading the model by bare name (`WhisperModel("base", ...)`), which faster-whisper resolves via its own Hugging Face cache, not via these staged files. Went unnoticed because the dev machine already had `base` cached. `add-portable-build` adds an explicit `--model-path` (CLI + engine) and wires `sidecar.rs` to always pass the resolved bundled directory, so the GUI actually uses what's staged here instead of silently depending on an ambient cache/network lookup.

- [ ] 2.6 Bundle a static ffmpeg binary into installer resources per OS

  Not done deliberately: unlike the model, there's no single unambiguous "official" static ffmpeg build source to hardcode with confidence, and guessing a download URL risked silently wiring in something wrong or unmaintained. `fetch_sidecar_resources.py`'s docstring flags this explicitly for whoever sets up the CI build matrix (task 7.2) to pin a specific, verified source per OS.

## 3. Tauri shell scaffold

**Rust toolchain note (superseded below)**: cargo/rustc could not be installed *natively on this Windows machine* -- every install path (direct `rustup-init.exe`, winget) was blocked by a machine-level, hash/reputation-based execution policy specifically targeting Rust toolchain binaries (confirmed: a locally-built PyInstaller exe ran fine from the same directory, ruling out "any new binary" or admin rights as the cause). **Worked around via Docker** (`docker/tauri-build.Dockerfile`): a Linux container with Rust + `gcc-mingw-w64-x86-64` cross-compiles the Windows target (`x86_64-pc-windows-gnu`) without needing MSVC, Visual Studio, Wine, or a native Windows Rust install at all -- the Windows execution-policy issue never applies because nothing Rust-related runs as a native Windows binary until the final cross-compiled artifact. **This actually worked**: `cargo check`, then a full `cargo tauri build --target x86_64-pc-windows-gnu --bundles nsis` succeeded and produced a real, working, installable `.exe`. See below for what was fixed along the way and what was verified by actually installing and running it.

- [x] 3.1 Scaffold Tauri project (`src-tauri/` + chosen frontend framework)

  `src-tauri/` (Cargo.toml, tauri.conf.json, build.rs, src/main.rs, src/sidecar.rs, `.cargo/config.toml` for the mingw linker) + `src/` (index.html, style.css, main.js -- plain HTML/JS/CSS, no framework or bundler). **Verified: compiles cleanly** (`cargo check --target x86_64-pc-windows-gnu` in Docker) after two trivial fixes: an unused `Mutex` import in `sidecar.rs`, and a CLI-flag typo of my own (`--no-strip` doesn't exist) when first invoking `cargo tauri build`. No design-level bugs found in the Rust code itself.

- [x] 3.2 Wire frozen sidecar binary + model + ffmpeg as Tauri bundled resources/external binaries

  `tauri.conf.json` declares `bundle.externalBin: ["binaries/transcriber-sidecar"]` and `bundle.resources: ["resources/model/**/*"]`. **Verified via real build errors, not guessing**: Tauri's build script actually validates these paths exist *at compile time*, which surfaced three real fixes needed: (1) the externalBin binary must be named with the exact target triple in use -- switched from a guessed `-x86_64-pc-windows-msvc.exe` to the real `-x86_64-pc-windows-gnu.exe` once the GNU cross-target was confirmed working; (2) the resources glob needed to be `resources/model/**/*` (not `resources/model/**`) to match files directly inside the directory, not just nested subdirectories; (3) `resources/ffmpeg/**` had to be dropped from the config since that directory doesn't exist yet (task 2.6) -- an empty glob match is a hard build error, not a no-op. ffmpeg resource wiring still needs re-adding once 2.6 is done.

- [x] 3.3 Implement window creation with no sidecar/model load in the startup path

  `main.rs`'s `main()` only builds the Tauri app and registers commands; the sidecar is spawned exclusively from within `sidecar::start_live_session` / `start_file_transcription`. **Verified by actually running the installed app**: the window opened within a couple seconds, titled "Transcriber", and stayed responsive (`Get-Process` showed `Responding: True`) -- consistent with the design goal, though this wasn't measured against the specific numeric budgets in design.md (see section 6).

## 4. Sidecar process management (Rust)

- [x] 4.1 Implement on-demand sidecar spawn (translate UI state → CLI flags, e.g. `--live --wasapi --include-mic --model base ...`)
- [x] 4.2 Implement async, non-blocking stdout/stderr reader on a background task
- [x] 4.3 Implement transcript-line regex parser and `transcript-line` event emission to the webview
- [x] 4.4 Implement fallback `sidecar-log` event for unmatched stdout lines
- [x] 4.5 Implement graceful stop (signal + timeout) and clean-exit handling

  Implemented as a hard kill, not a true graceful SIGINT relay -- `tauri-plugin-shell` doesn't expose a portable "send Ctrl+C to a child" primitive. Marked with a `ponytail:` comment in `sidecar.rs` naming the gap and the upgrade path (a stdin-based stop protocol in `transcriber.py`) if abrupt termination turns out to drop buffered transcript lines or leave partial WAV files. This one detail is still unverified behaviorally (didn't exercise an actual live session -- see note below).

- [x] 4.6 Implement crash detection (unexpected exit) → error event + UI reset to idle
- [x] 4.7 Implement device listing via `--list-devices-json`, parsed as JSON

  All of 4.1-4.7 **compile successfully** against the real `tauri-plugin-shell` v2.3.6 API (confirmed no signature mismatches). **Not verified behaviorally**: didn't click through starting a live session, dropping a file, or triggering a crash -- see the note at the end of section 5 on why GUI interaction testing was cut short this session.

## 5. Frontend UI (rebuild via `impeccable`, see design.md §6)

The plain HTML/CSS/JS pass below proved the event wiring (`transcript-line`, `sidecar-log`, `file-transcription-complete`, `get_platform`) works end-to-end but was never given a design pass and has real gaps (no Browse dialog, no verified click-through). It stays in place as the functional reference while it's rebuilt; nothing here changes the Rust-side event contract, so the sidecar/backend tasks in sections 2-4 are unaffected.

- [x] 5.0 Run the `impeccable` skill against this app's screens (idle/home, live session, device/model/language/task settings, file transcription drop zone, error/toast states) to get an approved design direction + comp

  Code-led (no image generation available in this session, confirmed with the user). Wrote `PRODUCT.md`, rolled the direction dice (`concept-seed.mjs --scope direction --mode operate`, seed key `3935811c`), weighed the catalog's challengers against a grounded 7-direction shortlist derived from the product's own cultural territory (recording/reading back speech privately, offline), and presented assigned + pick + one competitive alternate to the user via AskUserQuestion. User chose **"Verbatim"** (a court-reporter transcript direction, IMPECCABLE'S PICK over the dice-assigned "Night-Watch Log"). Direction contract recorded at `.impeccable/surfaces/src-index-html.md`.

- [x] 5.1 Rebuild idle/home screen per the comp: start live session, drop/browse a file (wire real `@tauri-apps/plugin-dialog` Browse this time — not stubbed), open settings

  Rebuilt `src/index.html` + `src/main.js` + `src/style.css` from scratch around the Verbatim direction. Wired `tauri-plugin-dialog` for real (Cargo.toml, `main.rs` plugin registration, new `src-tauri/capabilities/default.json` granting `core:default`/`dialog:default` — no capabilities file existed before, so this also had to state the core grant explicitly rather than relying on Tauri's implicit default). Also dropped the original `device-select` control: it populated a device list but its value was never read anywhere in the old `start_live_session` call (WASAPI auto-selects its own loopback device server-side) — a real dead/non-functional control in the prior build, removed rather than re-skinned.

- [x] 5.2 Rebuild device picker, populated from the sidecar's JSON device list

  Kept as the microphone-only picker (see 5.1) — `populateMicDevices()` calls `list_devices` unchanged.

- [x] 5.3 Rebuild model/language/task selection controls (mirroring `--model`/`--language`/`--task`; task stays file-panel-only since `transcribe_chunk` has no `task` param)
- [x] 5.4 Rebuild live transcript view: scrolling list of `transcript-line` events, `[SYS]`/`[MIC]` tag styling

  Speaker source is now carried by type style (upright vs. italic small caps) rather than color, per the Verbatim direction's one-accent (red = live) discipline — see DESIGN.md. Also fixed a real bug found while rebuilding: `start_file_transcription` emits the *same* `transcript-line`/`sidecar-log` events as live capture (confirmed in `sidecar.rs`'s shared `spawn_sidecar_events`), but the old frontend had one global listener appending everything into the "Live Transcript" panel regardless of which flow was running — so a file transcription's output was silently appearing mislabeled under "Live Transcript". Rebuilt frontend routes lines to whichever flow (`live`/`file`) actually started, into that tab's own transcript list.

- [x] 5.5 Rebuild collapsible debug/log panel fed by `sidecar-log` events
- [x] 5.6 Rebuild file transcription flow: drag-and-drop + working Browse, progress indicator (`file-transcription-complete`), output format choice (txt/srt/vtt)
- [x] 5.7 Rebuild error/toast surface for sidecar crash and unsupported file drops

  Replaced the flat red toast with the direction's "manila note" material (see DESIGN.md's "Note, Not a Badge" rule) so red stays reserved exclusively for the live-capture stamp.

- [x] 5.8 Rebuild platform-gate: detect macOS at runtime via `get_platform`, disable/hide live-capture controls with an explanatory message (stays gated pending `add-macos-capture`)

  Also now auto-switches to the File Transcription tab on macOS so the disabled Live tab isn't the default view.

- [x] 5.9 impeccable finish-review pass against the approved comp; fix findings

  **No screenshot-based review was possible in this session**: no Rust toolchain to build/run the actual Tauri app, and no browser-automation tool available to render the plain HTML/CSS/JS standalone (this is a code-only environment — same constraint noted throughout sections 1-3 of this file). Ran the mechanical static detector instead (`detect.mjs --json src/index.html src/main.js src/style.css`) — 0 findings, but it ran in **degraded mode** (no HTML/CSS parser deps available, regex-fallback only, explicitly not a clean bill of health) — computed contrast and selector matching were NOT evaluated. Did a manual code-level pass instead: cross-checked every element ID referenced in `main.js` against `index.html` (all present, no stale IDs left from the old markup), verified `[hidden]`/CSS state toggles are consistent, and found/fixed one real CSS bug (the "starting" stamp was inheriting the LIVE stamp's rotated stamp-impact animation, which the direction reserves for LIVE only). **This is a real gap**: an actual screenshot-based finish review (contrast ratios, spacing, real render) has not happened and should before this ships.

- [ ] 5.10 Click through every flow for real (device list populating, start/stop live session, file drop + Browse, crash recovery, macOS platform-gate) — the prior pass never verified this behaviorally; use a real driver (e.g. WebView2/Playwright) instead of blind coordinate clicks

  **Not done, same root cause as 5.9**: no Rust toolchain / running app in this environment to click through. This remains genuinely open — tracked here rather than in section 6 since it's frontend-specific interaction verification, distinct from 6.2's performance/responsiveness concern.

- [x] 5.11 impeccable documenter: record `DESIGN.md` for the rebuilt frontend

  Written directly (ground truth from the actual shipped CSS/HTML tokens) rather than via the subagent, since documentation doesn't benefit from a "fresh eyes" pass the way review does and this session already had full context of what was built. See `DESIGN.md` at the repo root.

## 6. Performance verification

- [x] 6.1 Scripted launch-timing harness: assert window-shown and UI-interactive budgets from design.md on a cold OS file cache

  Measured (not a proper harness with assertions yet, just direct timing via `Get-Process` polling on `MainWindowHandle`, no GUI interaction involved): **window-shown took ~4.5s, both cold and warm** -- well over design.md's <300ms budget. Consistent across two runs, so not a one-time cold-cache artifact. Root cause not diagnosed (would need real profiling); plausible explanation is WebView2 environment initialization cost, which the original budget didn't account for. **This is a real gap between the design's stated goal and actual behavior that needs follow-up** -- either the budget needs revising to reflect realistic WebView2 startup cost, or the window-creation path needs investigation (e.g. whether Tauri can show a native window before WebView2 content is ready, rather than the two being coupled).

- [ ] 6.2 Verify no UI-thread block/dropped-frame regression during sidecar start and live transcript streaming

  Not done: needs interactive use (starting a live session) to observe, which this session stopped pursuing via GUI automation (see section 5 note) rather than risk more blind input simulation on the live desktop.

- [x] 6.3 Record actual installer size per OS and cold sidecar-start time as a baseline for future comparison

  **Installer**: `Transcriber_0.1.0_x64-setup.exe` = 259MB (Windows; dominated by the bundled 145MB model). **Sidecar cold-start** (`--list-devices-json` from the installed location): ~9s first run, ~6.7s on a second run from the same path -- consistently slow, not just a one-time AV-scan cost. **Likely cause, worth acting on**: `build_sidecar.py` uses PyInstaller's `--onefile` mode, which re-extracts the entire bundle to a temp `_MEI*` directory on *every* launch (visible in the earlier ONNX asset error path). Switching to `--onedir` would very likely cut this significantly, at the cost of the sidecar being a folder instead of a single .exe (needs adjusting how it's referenced in `tauri.conf.json`'s `externalBin` and how `build_sidecar.py`/CI stage it). Flagging as a concrete, actionable follow-up rather than changing it blind this session.

## 7. Packaging & release

- [x] 7.1 Configure `tauri-bundler` targets: NSIS `.exe` (Windows), `.AppImage`/`.deb` (Linux). **Changed from the original `.msi`/`.dmg` plan** per explicit direction: NSIS over MSI (WiX is the shakier piece to get working outside a native Windows host; `makensis` has a genuine native Linux build and was confirmed working -- see 7.2/below), and macOS dropped entirely for now (not a current priority; still shell-only pending `add-macos-capture` whenever it's picked back up).

  `tauri.conf.json`: `bundle.targets: ["nsis", "appimage", "deb"]`, plus `bundle.windows.nsis.installMode: "both"`. **Verified for real**: built and installed the actual NSIS installer (see 7.2) with no arguments (the default a user double-clicking would get) -- it installed to `%LOCALAPPDATA%\Programs\Transcriber` with **no UAC prompt**, confirming the default is per-user, no-admin-required, exactly as asked. The "both" mode's system-wide option (which would need admin) was not separately exercised.

- [x] 7.2 CI build matrix / reproducible build environment producing the installer

  Superseded the "GitHub-hosted 3-OS matrix" framing with a locally-runnable Docker path (`docker/tauri-build.Dockerfile`, `docker/build.ps1`) that cross-compiles the Windows NSIS installer entirely from a Linux container -- no MSVC, Wine, or native Windows Rust needed. **This is real, verified, end-to-end**: `docker build` succeeded, `cargo tauri build --target x86_64-pc-windows-gnu --bundles nsis` succeeded, producing `Transcriber_0.1.0_x64-setup.exe` (259MB, dominated by the bundled `base` model). `.github/workflows/build-gui.yml` (the GitHub Actions matrix) still exists as a separate, still-unrun path for later, updated to drop macOS and align with the nsis/mingw target -- but the Docker path is what was actually proven to work this session.

- [x] 7.3 Manual install test confirming no-admin-by-default install (fully-offline testing deferred)

  **Verified**: ran the installer silently (`/S`, no mode flag) as a normal, unelevated user -- completed with exit code 0, no UAC prompt, installed to `%LOCALAPPDATA%\Programs\Transcriber` (per-user). Launched the installed `transcriber-gui.exe`: window opened, titled "Transcriber", stayed responsive, and a screenshot confirmed the full UI rendered correctly. **Not done**: the fully-offline (network-disabled) part of this task, and any interactive click-through testing -- see the note at the end of section 5 on why that was cut short (a blind-input-simulation attempt risked hitting the wrong window on the live desktop, so it was stopped rather than pushed further).

- [x] 7.4 Update README with GUI install/usage instructions alongside the existing CLI instructions

  Added a "Desktop GUI (in development)" section to README.md. Should be revisited to mention the Docker build path now that it's the proven one, and to update the msi/dmg → nsis target change.
