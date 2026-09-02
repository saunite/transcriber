## Why

The app currently ships two ways: an NSIS installer (`add-tauri-gui` task 7.1) and a portable folder assembled by `build_portable.ps1` (`add-portable-build`), with `.deb` also listed as a bundle target. That is three packaging forms to build, test, and document for a tool that has one job.

The installer earns none of its cost here. It exists to give a Start Menu entry, an uninstaller, and registry state — for an app that is one executable plus a model directory, needs no admin (it already installs per-user), and has no updater wired up. Meanwhile it doubles the release matrix and adds an install step between a user and a transcript.

The decision is to keep exactly one artifact per OS, downloadable and runnable with no install step.

## What Changes

- **Drop the installer bundle targets.** `tauri.conf.json`'s `bundle.targets` goes from `["nsis", "appimage", "deb"]` to the portable-artifact targets only. `bundle.windows.nsis` config is removed.
- **One artifact per OS**, each the platform's idiomatic no-install form:
  - **Linux**: `.AppImage` — a genuine single executable file. Already a configured target; this is free.
  - **macOS**: `Transcriber.app` in a `.zip` — a `.app` is a directory, but Finder treats it as one draggable object. A bare single-file Mach-O GUI binary has no `Info.plist`, no icon, no bundle identifier, and behaves badly under Gatekeeper. Zipped `.app` is the portable form on macOS.
  - **Windows**: a `.zip` of the portable folder. Tauri offers no single-file portable target on Windows, and the payload (a ~150MB frozen sidecar plus a ~145MB model) cannot live inside the exe without a self-extractor — see design.md for why that option was rejected.
- **`build_portable.ps1` → `build_portable.py`.** The current assembler is PowerShell-only, so it cannot produce the Linux or macOS artifact. Rewritten as one Python script (Python is already required to build the sidecar) covering all three platforms and emitting the zip. The `.ps1` is deleted.
- **Docker and CI produce portable artifacts only.** `nsis` comes out of `docker/tauri-build.Dockerfile`; `docker/build.ps1` and `.github/workflows/build-gui.yml` stop building and uploading installer bundles.
- **macOS enters the build matrix** as a real target producing the zipped `.app`. Live capture stays gated there (`add-macos-capture` is still open) — the artifact exists and file transcription works, matching the existing "graceful macOS degradation" requirement.
- **No console window on launch.** `src-tauri/src/main.rs` is missing the `windows_subsystem = "windows"` attribute, so the Windows executable is built as a console-subsystem binary and opens a black console window alongside the app. One line fixes it. Verified as a real gap, not a suspicion — see design.md.
- Out of scope: an auto-updater, code signing/notarization, and switching the frozen sidecar to PyInstaller `--onedir` — see design.md Non-Goals.

## Capabilities

### Modified Capabilities
- `desktop-gui` (from the in-flight `add-tauri-gui` / `add-portable-build` changes): packaging is now a single no-install artifact per platform rather than an installer plus an optional portable folder; the requirement that the portable build exists "alongside the installer" is superseded. Also gains an explicit requirement that launching the artifact shows no console/terminal window on any platform.

## Impact

- **Changed**: `src-tauri/tauri.conf.json` (`bundle.targets`, remove `bundle.windows.nsis`), `src-tauri/src/main.rs` (one attribute line), `docker/tauri-build.Dockerfile` (drop the `nsis` package), `docker/build.ps1`, `.github/workflows/build-gui.yml`, `README.md`.
- **Deleted**: `build_portable.ps1`.
- **New**: `build_portable.py` (cross-platform assembler, replaces the above).
- **Unchanged**: all Python engine code, all Rust code. `sidecar.rs`'s `resolve_model_dir()` already resolves via Tauri's `resource_dir()`, which works identically for installed, portable-folder, AppImage, and `.app` layouts — that is exactly what `add-portable-build` fixed, and nothing here disturbs it.
- **What is given up**: no Start Menu / Applications entry, no uninstaller, no file associations, and no in-place update path. Tauri's updater plugin supports AppImage and `.app` but not a loose Windows folder, so wiring an updater later means either reintroducing a Windows installer or building a bespoke updater. Accepted deliberately — see design.md.
- **Not changed**: unsigned-binary warnings. SmartScreen on Windows and Gatekeeper on macOS trigger on the portable artifact exactly as they did on the installer. Removing installers neither helps nor hurts here.

## Ordering

**Apply `drop-ffmpeg-dependency` first.** A portable artifact is supposed to run with nothing else installed, and until that change lands, a user who drops an `.mp4` on this one hits a hard "ffmpeg is not installed" failure (`add-tauri-gui` task 2.6 is still open). Shipping the portable artifact first would ship something that is portable in name only. The two changes also both touch the `desktop-gui` "Fully offline first run" requirement, which cites a bundled ffmpeg binary — doing ffmpeg first means one rewrite of that text instead of two.
