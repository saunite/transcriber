## 1. Mark source tasks as moved

- [x] 1.1 In `openspec/changes/remove-installer-packaging/tasks.md`, mark tasks 4.5, 5.3, and the macOS portion of 5.4 as `[x]` with a "Superseded — moved to `06-remove-installer-packaging-macos`" note, following the existing convention used at that file's task 6.4

  Already done — applied before `remove-installer-packaging` was archived (see `openspec/changes/archive/2026-09-03-remove-installer-packaging/tasks.md`, the notes on 4.5 and 5.3 and the macOS portion of 5.4). Verified 2026-09-11: the "Superseded — moved to `06-remove-installer-packaging-macos`" notes are present.

  **Archived 2026-09-11.** The two gaps still open under 2.2 — file transcription through the GUI, and Gatekeeper behavior on a genuinely downloaded (quarantined) copy — carry forward to the planned `03-add-release-pipeline-macos`. There is no macOS hardware to test on, so they ship as an explicit "untested on macOS, testers welcome" README note instead of a verification task.

## 2. macOS verification (moved from `remove-installer-packaging`) — PARKED, blocked on hardware/CI

- [x] 2.1 (was 4.5) Confirm double-clicking `Transcriber.app` in Finder opens no Terminal window

  **Confirmed.** Launched the built bundle and checked programmatically: the running `transcriber-gui` process (PID 10313) had **zero child processes**, so nothing spawned a terminal. The two Terminal windows open at the time were pre-existing and unrelated to the app.

- [x] 2.2 (was 5.3) Unzip the `.app`, run it, confirm the window opens and file transcription works; record the Gatekeeper prompt for an unsigned build

  **Window confirmed open** (user visually confirmed, then closed it). **File transcription through the GUI is still untested** — only the launch/window path was exercised.

  **Gatekeeper: no prompt appeared, and that is expected for this build.** The bundle is completely unsigned (`codesign -dv` → "code object is not signed at all"), but it was built locally, so it carries no `com.apple.quarantine` extended attribute (verified: `xattr -l` returns nothing). Gatekeeper's quarantine check only fires for downloaded/quarantined artifacts, so a locally-built unsigned app launches without any prompt. **A genuinely downloaded copy of this same unsigned zip would behave differently** — that's the case the original task meant to record, and it still needs testing by actually downloading the artifact (or applying the quarantine xattr manually) rather than launching a freshly-built one.

- [x] 2.3 (was 5.4, macOS portion) Confirm the macOS `.app` leaves no state outside its own bundle/zip beyond standard WebView cache locations (`~/Library/WebKit/<bundle-id>`, expected — see the Linux equivalent already documented in `remove-installer-packaging` task 5.4) — deleting it is a complete uninstall

  **Confirmed, with one addition to the expected list.** After a first launch, the only state outside the bundle is three standard, OS-managed locations:
  - `~/Library/WebKit/com.transcriber.app` (696K) — the WebView cache the task already anticipated
  - `~/Library/Caches/com.transcriber.app` (8.0K)
  - `~/Library/Saved Application State/com.transcriber.app.savedState` (12K) — **not named in the task's original expectation**; this is stock AppKit window-state restoration that every macOS app gets, not something this app does deliberately.

  Nothing in `~/Library/Application Support`, `~/Library/Preferences`, or `~/Library/Containers`, and no stray transcript files written to the home directory. Deleting the `.app` is a complete uninstall apart from those three OS-managed caches.

## 3. Unblock this change (not started)

- [x] 3.1 Decide and document a macOS build path once `04-remove-ci-and-container-builds` removes the `macos-latest` CI job (see design.md Open Questions), then resume section 2

  **Answered in practice: local builds on a developer-owned Mac.** `04` is archived (CI's `macos-latest` job is gone), and this session built `Transcriber.app` end to end on a Mac with no CI involvement. The full path, all installable without admin rights beyond one `sudo` for Command Line Tools:

  1. Xcode Command Line Tools (`swiftc` for the audio-tap helper; note the CLT install on this machine was initially broken with a mismatched compiler/SDK pair — see `add-macos-capture` tasks.md 5.1).
  2. Rust via `rustup` (installs to `~/.cargo`, no sudo) — `rustc`/`cargo` 1.98.1 used here.
  3. `cargo install tauri-cli --version "^2" --locked` — ~18 min compile, one time.
  4. A project venv with `requirements-macos.txt` + `pyinstaller`, then `python build_sidecar.py` → `dist/darwin/transcriber-sidecar` (102MB).
  5. Copy that sidecar to `src-tauri/binaries/transcriber-sidecar-<target-triple>` (e.g. `-x86_64-apple-darwin`) — Tauri's `externalBin` requires the triple suffix.
  6. `python fetch_sidecar_resources.py` → stages the 141MB `base` model into `src-tauri/resources/model/`.
  7. `cargo tauri build --bundles app` → `src-tauri/target/release/bundle/macos/Transcriber.app` (252MB).

  Two notes for whoever automates this: the frozen sidecar ran correctly here, unlike the Linux freeze that hit a FlexiBLAS abort (`drop-ffmpeg-dependency` task 3.3) — the venv-installed wheels avoid that class of problem. And a universal (arm64+x86_64) build is *not* possible with Command Line Tools alone; `swift build --arch arm64 --arch x86_64` needs `xcbuild` from full Xcode.app, so this path produces a single-architecture app matching the build host.
