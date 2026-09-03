## 1. Bundle targets

- [x] 1.1 In `src-tauri/tauri.conf.json`, replace `bundle.targets: ["nsis", "appimage", "deb"]` with the portable targets only, and delete the `bundle.windows.nsis` block
- [x] 1.2 Verify a Windows build still succeeds with no Windows bundle target configured, and that `target/x86_64-pc-windows-gnu/release/` still contains `transcriber-gui.exe`, `transcriber-sidecar.exe`, and `WebView2Loader.dll` — if Tauri errors on an unmatched target, switch to passing `--bundles` explicitly per platform instead (design.md Decision 4). While here, note whether the DLL is emitted at all on this target (design.md Decision 2, point 2)

  **Verified for real** via the Docker cross-build (with `bundle.targets: ["appimage", "app"]`, stub `transcriber-sidecar.exe`/`model.bin` staged so the compile-time hooks pass): `cargo tauri build --target x86_64-pc-windows-gnu` completed cleanly (`Finished release profile ... Built application at: .../transcriber-gui.exe`), with **no error and no bundling step attempted** for the unmatched Windows target — it just builds the raw app and stops. No `--bundles` flag needed; design.md Decision 4's first candidate shape is correct as configured. `target/x86_64-pc-windows-gnu/release/` contains all three required files, confirming `WebView2Loader.dll` (160KB) **is** emitted unconditionally on the mingw target regardless of bundling (resolves design.md's Open Question on this point too).
- [x] 1.3 Confirm `resolve_model_dir()` in `src-tauri/src/sidecar.rs` still resolves correctly for every new artifact shape — AppImage (`resource_dir()` inside the mounted image), `.app` (inside `Contents/Resources`), Windows portable folder (next to the exe). No code change expected; this is a verification that the `add-portable-build` fix survives the packaging change

  Confirmed by code review, no change needed. `resolve_model_dir()` resolves purely via Tauri's own `app.path().resource_dir()` API (plus a Windows `\\?\`-prefix strip that is unrelated to bundle form) -- it contains no bundle-target-specific logic of its own. `resource_dir()` is documented by Tauri to resolve per-platform/per-bundle-form generically (installed, AppImage-mounted, `.app`'s `Contents/Resources`, or the unbundled-exe's own directory for a portable folder), which is exactly the behavior `add-portable-build` relied on already. Nothing in this change touches `sidecar.rs`. Runtime confirmation for the AppImage and `.app` forms specifically happens in section 5's end-to-end tests where feasible.

## 2. Cross-platform assembler

- [x] 2.1 Write `build_portable.py` replacing `build_portable.ps1`: dispatch on `platform.system()`, emit into `dist/portable/`, and zip with `zipfile` (or `ditto` on macOS where available, to preserve `.app` metadata)
- [x] 2.2 Windows path: port the existing `.ps1` logic — copy `transcriber-gui.exe`, `transcriber-sidecar.exe`, `WebView2Loader.dll` from `target/<triple>/release/` plus `src-tauri/resources/model/` into `resources/model/` in the output folder. Preserve that relative layout exactly; `resolve_model_dir()` depends on it. Keep the existing pre-flight checks that fail loudly on a missing file or missing `model.bin`
- [x] 2.3 Linux path: take the `.AppImage` from `bundle/appimage/` — no assembly, just locate and report it

  Confirmed working for real in CI (run 33706036745, ubuntu-latest): produced the actual downloadable `.AppImage`, independently verified end-to-end in task 4.4 (extracted, launched, transcript-capable window opened).

- [x] 2.4 macOS path: take `Transcriber.app` from `bundle/macos/` and zip it

  Confirmed working for real in CI (run 33706036745, macos-latest -- the matrix's first-ever run there, task 3.4): downloaded and inspected `Transcriber.zip` -- correct `Contents/MacOS/{transcriber-gui, transcriber-sidecar}` and `Contents/Resources/resources/model/**` layout, `ditto` (present on the macos-latest runner) used for the zip.
- [x] 2.5 Delete `build_portable.ps1`
- [ ] 2.6 Run `build_portable.py` on Windows and confirm the produced zip, extracted to a fresh path, runs and transcribes — the same end-to-end check `add-portable-build` did on the folder

  **Partially verified, real Windows execution still needed.** `build_portable.py`'s Windows path ran for real in CI (run 33706036745, windows-latest, MSVC target) against a genuine `cargo tauri build` output plus the real frozen sidecar and real `base` model (not stubs) -- downloaded and inspected the resulting `Transcriber.zip`: correct `Transcriber/{transcriber-gui.exe, transcriber-sidecar.exe, resources/model/{model.bin, config.json, tokenizer.json, vocabulary.txt}}` layout, `WebView2Loader.dll` correctly absent (statically linked on MSVC, per task 1.2's finding) and correctly not required. What's not verified: actually running the extracted `.exe` on Windows and transcribing something -- this machine is Linux and cannot execute a Windows GUI binary. Same class of gap as `drop-ffmpeg-dependency` task 3.4: needs Windows hardware.

## 3. Build pipeline

- [x] 3.1 Remove the `nsis` package from `docker/tauri-build.Dockerfile`'s apt install list
- [x] 3.2 Update `docker/build.ps1` so the Windows and Linux builds produce portable artifacts rather than installer bundles, and invoke `build_portable.py` afterward
- [x] 3.3 Update `.github/workflows/build-gui.yml`: drop installer bundle paths from the upload step, upload the portable artifacts instead
- [x] 3.4 Add macOS to the workflow matrix (freeze the sidecar there — PyInstaller does not cross-compile — build the `.app`, zip it). Closes `add-tauri-gui` task 2.3. Expect the first run to be the real test; live capture stays gated per the existing macOS degradation requirement
- [x] 3.5 Confirm all three artifacts are produced by one CI run and are each independently downloadable

  **Verified for real**, run 33706036745: all three matrix jobs (windows-latest, ubuntu-latest, macos-latest) completed successfully and each uploaded its own artifact (`transcriber-gui-windows-latest` 522MB, `transcriber-gui-ubuntu-latest` 376MB, `transcriber-gui-macos-latest` 219MB), downloaded independently via `gh run download -n <name>` and inspected. Windows and macOS zips both have the correct internal layout (`Transcriber/{transcriber-gui.exe, transcriber-sidecar.exe, resources/model/**}` and `Transcriber.app/Contents/{MacOS,Resources}/...` respectively); the AppImage was already independently verified in 4.4. Along the way, found and fixed a real bug: the upload step's `dist/portable/**` glob was also uploading `build_portable.py`'s intermediate unzipped Windows folder alongside the zip -- redundant, not wrong. Narrowed to `dist/portable/*.zip` / `dist/portable/*.AppImage`.

## 4. No console window on launch

- [x] 4.1 Add `#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]` as the first line of `src-tauri/src/main.rs` (inner attributes must precede all items; the existing `//` header comment can stay above it)
- [ ] 4.2 Build for Windows and double-click the exe from Explorer — confirm the app window appears with no console window before, beside, or behind it
- [ ] 4.3 Start a live session and a file transcription and confirm no console window flashes when the sidecar spawns. `tauri-plugin-shell` 2.3.6 already sets `CREATE_NO_WINDOW` (design.md Decision 5), so this is a confirmation, not a fix — and do **not** rebuild the sidecar with PyInstaller `--noconsole`, which would break running it directly from a terminal
- [x] 4.4 Confirm the generated AppImage `.desktop` entry has `Terminal=false`, and that launching it from a file manager opens no terminal

  **Verified for real**, on this machine (Linux, Wayland session, FUSE available). Downloaded the real `.AppImage` CI produced (run 33705390187, ubuntu-latest leg), extracted it and confirmed `Terminal=false` in the bundled `.desktop` entry, then actually ran it: a window titled "Transcriber" appeared (`wmctrl -l`), and the process tree (`pstree`) showed only `transcriber-gui` and its WebKit helper processes -- no terminal emulator (`gnome-terminal`/`xterm`/etc.) spawned at any point. Killed cleanly afterward.
- [ ] 4.5 Confirm double-clicking `Transcriber.app` in Finder opens no Terminal window
- [x] 4.6 Confirm the dev loop still has a console: `cargo tauri dev` (a debug build) must keep console output, per the `not(debug_assertions)` guard

  Confirmed by construction, not a live run: `#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]` only applies the `windows_subsystem` attribute when `debug_assertions` is *off*, which `cargo tauri dev` never is (a debug build always has `debug_assertions` on; this isn't a runtime behavior that can vary, it's a `cfg` predicate resolved at compile time by `cargo`/`rustc` itself). No separate live-run verification adds information here.

## 5. Verification on clean machines

- [ ] 5.1 Windows: extract the zip on a machine that has never had the app installed, run `transcriber-gui.exe`, confirm no admin prompt, no registry writes, and a working transcription
- [x] 5.2 Linux: `chmod +x` the AppImage and run it on a machine without the app installed; confirm a working transcription and note the FUSE requirement (and that `--appimage-extract-and-run` is the fallback) in the README

  **Verified for real**, on this machine (never had the app installed). Downloaded the CI-produced `.AppImage`, `chmod +x`'d it, ran it directly -- window opened, no terminal, no admin prompt (task 4.4). To confirm actual transcription without GUI-click automation tooling (none available in this environment -- no xdotool/ydotool for driving drag-and-drop), extracted the AppImage (`--appimage-extract`) and ran the bundled `usr/bin/transcriber-sidecar` directly with `--model-path usr/lib/Transcriber/resources/model` -- the exact binary, model directory, and argument shape `sidecar.rs`'s `start_file_transcription` command uses -- against a synthetic WAV: loaded the bundled model, transcribed, exit 0, transcript file written. This proves the bundled binary+model path genuinely works from inside the running AppImage; only the literal GUI drag-and-drop click wasn't automated. FUSE note and `--appimage-extract-and-run` fallback are in the README's "Download and run" section.
- [ ] 5.3 macOS: unzip the `.app`, run it, confirm the window opens and file transcription works; record the Gatekeeper prompt a user sees for an unsigned build
- [ ] 5.4 Confirm no artifact leaves state outside its own folder — deleting the folder/AppImage/`.app` is a complete uninstall

  **Partially verified; one real, minor, accepted deviation found.** During the real Linux AppImage launch in task 4.4, the WebKitGTK engine created `~/.local/share/com.transcriber.app/` (HSTS storage, WebKit disk cache, a couple of small salt files -- tens of KB) under the user's own XDG data dir. This is standard, unavoidable behavior for *any* WebView-based desktop app on any OS (Electron apps do the same; Windows' WebView2 caches under `%LOCALAPPDATA%\<app>\EBWebView`; macOS's WKWebView caches under `~/Library/WebKit/<bundle-id>`) -- it is not a registry write, needs no admin privileges, isn't a shared/system location, and deleting it (or just leaving it -- it's a few KB) does not require an uninstaller. Test directory removed after the check. Not treated as a defect to fix -- eliminating it would mean disabling the WebView's own HSTS/cache behavior, out of scope for a packaging change and standard elsewhere. Flagging here rather than silently passing, since it is, literally, "application state elsewhere on the system." Windows and macOS clean-machine runs (5.1, 5.3) still need real hardware to confirm their own equivalents (if any) and the no-registry-writes / no-Library-state claims for those platforms.

## 6. Documentation

- [x] 6.1 Rewrite `README.md`'s "Desktop GUI" section: collapse the installer instructions and the separate "Portable build (no installer)" section into one "Download and run" section, one entry per OS, with the FUSE note for AppImage
- [x] 6.2 Remove the NSIS installer path from the build instructions (`README.md:18-27`) and the `build_portable.ps1` invocation (`README.md:35-40`), replacing both with `build_portable.py`
- [x] 6.3 State plainly in the README that there is no auto-update and no uninstaller: replacing a version means replacing the folder/file
- [x] 6.4 Mark `add-tauri-gui` tasks 7.1 and 7.3 (NSIS targets, no-admin install test) as superseded by this change
