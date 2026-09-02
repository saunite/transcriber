## Context

Three packaging forms exist today for one app:

```
cargo tauri build
   ├─ target/<triple>/release/          raw output: gui exe, sidecar exe, WebView2Loader.dll
   ├─ bundle/nsis/*-setup.exe           Windows installer   (add-tauri-gui 7.1)
   ├─ bundle/appimage/*.AppImage        Linux, single file
   └─ bundle/deb/*.deb                  Linux installer

build_portable.ps1  ──> dist/portable/Transcriber/   Windows folder, PowerShell-only
```

What is actually in an artifact:

```
transcriber-gui[.exe]        ~10 MB    Tauri shell
WebView2Loader.dll           ~150 KB   Windows only (mingw target)
transcriber-sidecar[.exe]   ~150 MB    PyInstaller --onefile
resources/model/**          ~145 MB    faster-whisper `base`
                            ───────
                            ~305 MB
```

The Tauri shell is ~3% of the artifact. The installer is not what makes this heavy, and removing it does not make it lighter — it removes a step, not bytes. The measured NSIS installer was 259MB (`add-tauri-gui` task 6.3).

## Goals / Non-Goals

**Goals:**
- Exactly one downloadable artifact per OS, runnable with no install step, no admin, no registry writes.
- One assembler script that works on all three platforms.
- Windows, Linux, and macOS artifacts all actually produced by the build pipeline.

**Non-Goals:**
- A literal single *file* on Windows. See Decision 2.
- An auto-updater. There is none today; this change does not add one, and it makes adding one harder on Windows (see Risks).
- Code signing / notarization.
- Switching the sidecar to PyInstaller `--onedir`. Tempting — `add-tauri-gui` task 6.3 measured 9s cold / 6.7s warm sidecar start and attributed it to `--onefile`'s `_MEI*` re-extraction on every launch, and a portable folder makes `--onedir` layout-compatible for free. But Tauri's `externalBin` / `app.shell().sidecar()` expects a *single file*, so `--onedir` means restaging the sidecar as a resource and spawning it by resolved path instead. That is a real change to `sidecar.rs`, not a packaging tweak. Kept out; see Open Questions.
- Removing the Docker cross-build. It stays — it is the only proven Windows build path on the dev machine.

## Decisions

### 1. Linux is an AppImage; macOS is a zipped `.app`

Both are already the platform-native answer to "no installer", and both are just a matter of what is in `bundle.targets`:

- **AppImage** is literally the thing being asked for: one executable file, `chmod +x`, run. Tauri bundles `externalBin` and `resources` into it, and `resource_dir()` resolves inside the mounted image, so `resolve_model_dir()` needs no change. Caveat worth knowing: AppImage needs FUSE, or `--appimage-extract-and-run` on hosts without it.
- **macOS `.app`** is a directory, but it is the unit macOS users drag, and it is what carries `Info.plist`, the icon, and the bundle identifier. A bare Mach-O GUI binary has none of those and behaves badly under Gatekeeper. Zipping it gives one download, one drag. `.dmg` is dropped — it is a mount-then-copy ceremony, i.e. an installer in spirit.

`.deb` is dropped outright: it is an installer with a package manager attached, and AppImage covers the same users better here.

### 2. Windows ships a zip, not a self-extracting exe

There is no single-file portable target for Tauri on Windows, and three separate things block one:

1. **The payload.** Tauri `resources` and `externalBin` are files placed *next to* the exe, not blobs inside it. ~295MB of sidecar and model cannot be embedded without a self-extractor.
2. **`WebView2Loader.dll`.** Tauri v2 statically links this on MSVC targets, but the build here is `x86_64-pc-windows-gnu` (mingw, via Docker — chosen because the Rust toolchain cannot be installed natively on the dev machine, see `add-tauri-gui` tasks.md section 3). Mingw cannot consume the MSVC import library, so the DLL ships as a sibling file. **This needs verifying** rather than assuming — if a build with zero resources still emits the DLL, then even an empty app cannot be one file on this target.
3. Switching to MSVC to fix (2) reopens the toolchain problem the Docker path exists to avoid, and would still leave (1).

**Alternative considered — self-extracting exe** (7-Zip SFX, or `include_bytes!` in the Rust shell). It produces a genuine single file. Rejected: it unpacks ~300MB into `%LOCALAPPDATA%` on first run with no uninstaller, or re-unpacks on every launch. That is an install with the visibility removed — strictly worse than a zip the user can see, move, and delete. It also re-creates the exact `--onefile` extraction cost that task 6.3 flagged as a real startup problem.

**Alternative considered — stop bundling the model** and download `base` on first run. Payload drops to ~160MB and single-file becomes plausible. Rejected: it directly contradicts the `desktop-gui` "Fully offline first run" requirement, which is the reason `add-portable-build` added `--model-path` in the first place. Not renegotiating that requirement inside a packaging change.

So: `.zip` of the folder. One download, one extract, one exe. Honest about what it is.

### 3. One Python assembler, replacing the PowerShell one

`build_portable.ps1` cannot run on Linux or macOS, so it cannot produce two of the three artifacts. Rewriting it in Python costs nothing new — `build_sidecar.py` and `fetch_sidecar_resources.py` already require Python at build time, and `shutil` plus `zipfile` cover everything the `.ps1` did.

Its work is genuinely platform-shaped, and mostly it does *less* than before:
- **Linux**: take the AppImage from `bundle/appimage/`. No assembly at all.
- **macOS**: take `Transcriber.app` from `bundle/macos/`, zip it (with `ditto` if available, to preserve resource forks and signing metadata).
- **Windows**: the existing job — copy the three files from `target/<triple>/release/` plus `resources/model/`, then zip.

The `resources/model` relative layout the current script produces must be preserved exactly; `resolve_model_dir()` in `sidecar.rs` depends on it.

### 4. `bundle.targets` needs verifying, not guessing

Setting `"targets": ["appimage", "app"]` means a Windows build matches no target. Whether `cargo tauri build` treats that as a no-op (still emitting `target/<triple>/release/`, which is all the Windows path needs) or as an error is not something to assume — `add-tauri-gui` task 3.2 already recorded that Tauri's build script hard-errors on an empty resource glob rather than ignoring it, so it is not forgiving here by default.

Two candidate shapes, decided by testing (task 1.2):
- `"targets": ["appimage", "app"]` and let the Windows build produce no bundle, or
- pass `--bundles` explicitly per platform from the build scripts and leave the config minimal.

### 5. No console window on launch — one missing attribute on Windows

Double-clicking the artifact must open the app and nothing else. Three places on Windows can produce a stray console window; two are already fine and one is a real defect.

**The GUI executable itself — broken today.** `src-tauri/src/main.rs` starts straight at `mod sidecar;` with no `windows_subsystem` attribute:

```
$ grep -rn "windows_subsystem" src-tauri/
   (no matches)
```

Rust `bin` crates default to the **console subsystem** on Windows, so the linker marks the exe as a console app and Windows allocates a console window for it on launch — a black window beside the app, and for a user double-clicking a portable exe, before it. Tauri's own project template carries the attribute for exactly this reason; this `main.rs` was hand-written (see its "UNVERIFIED: written without a working Rust/Cargo toolchain" header) and never got it. `add-tauri-gui` task 7.3 launched the installed app and screenshotted the UI, but a console window is easy not to mention when you are looking at whether the UI rendered.

The fix is the standard template line, as the file's first line:

```rust
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]
```

`not(debug_assertions)` keeps the console in dev builds. No downside here: nothing in `main.rs` or `sidecar.rs` writes to stdout (`grep -n "println!\|eprintln!" src-tauri/src/*.rs` returns nothing), so no logging is lost — sidecar output already flows to the webview as `sidecar-log` events.

**The sidecar spawn — already correct.** The frozen sidecar is a console-subsystem exe (PyInstaller's default; `build_sidecar.py` passes no `--noconsole`), so spawning it naively would flash a console every time a session starts. It does not, because `tauri-plugin-shell` sets the flag unconditionally. Verified against the pinned version in `Cargo.lock` (2.3.6):

```rust
// tauri-plugin-shell-2.3.6/src/process/mod.rs:160-173
pub(crate) fn new<S: AsRef<OsStr>>(program: S) -> Self {
    let mut command = StdCommand::new(program);
    command.stdout(Stdio::piped());
    ...
    #[cfg(windows)]
    command.creation_flags(CREATE_NO_WINDOW);
```

`new_sidecar()` delegates to `new()`, so every sidecar spawn in `sidecar.rs` gets it. **No change needed, and importantly: do not "fix" this by rebuilding the sidecar with PyInstaller `--noconsole`** — that would make the sidecar a GUI-subsystem binary, which breaks running it directly from a terminal for debugging, for no gain.

**Grandchild processes — fixed by the other change.** `transcriber.py`'s two ffmpeg merge calls use plain `subprocess.run` with no creation flags, from a sidecar that itself has no console. Windows allocates a *new* console for a console-subsystem child in that situation, so those would flash a window mid-session. `drop-ffmpeg-dependency` deletes both call sites, which is one more reason to apply it first. After it lands, the sidecar spawns no external processes at all.

**Linux and macOS need no fix.** ELF binaries have no console-subsystem concept; an AppImage launched from a file manager runs via its bundled `.desktop` entry, which must have `Terminal=false` (Tauri's default — verify, do not assume). On macOS, double-clicking a `.app` never opens Terminal; double-clicking a *bare* Mach-O executable does — which is one more reason the macOS artifact is a `.app` and not a loose binary (Decision 1).

## Risks / Trade-offs

- **[Risk]** **No update path on Windows.** Tauri's updater plugin supports AppImage and `.app`; a loose folder has nothing to update in place. If an updater is wanted later, Windows needs either a reintroduced installer or a bespoke mechanism. **Mitigation**: none taken. There is no updater today, and the honest position is that this trade is being made knowingly rather than discovered later.
- **[Risk]** No uninstaller means an abandoned 300MB folder if a user forgets it. **Mitigation**: accepted; it is one visible folder, which is more discoverable than the `%LOCALAPPDATA%` state an installer or self-extractor would leave.
- **[Risk]** The macOS artifact is newly in the matrix and has never been built. PyInstaller does not cross-compile, so the sidecar must be frozen on a macOS runner, and `add-macos-capture` is still open. **Mitigation**: it ships gated (file transcription only), which is already the specified behavior. Treat the first CI run as the actual test, the way `add-tauri-gui` task 7.2 did.
- **[Trade-off]** Users who *wanted* a Start Menu shortcut now make their own. For a tool launched a few times a week, acceptable.

## Open Questions

- Should the Windows zip carry a short `README.txt` (what to run, that the folder is self-contained, that deleting it is the uninstall)? `add-portable-build` leaned no. With the installer gone this is the only artifact a Windows user gets, which tilts it toward yes.
- Follow-up, not this change: revisit PyInstaller `--onedir` for the 6.7-9s sidecar cold start. The portable layout makes it viable; `externalBin` is what blocks it. Worth its own change once the packaging here is settled.
- Does the mingw target emit `WebView2Loader.dll` unconditionally (Decision 2, point 2)? Worth confirming during task 1.2 — it does not change the outcome, but it changes whether "one file on Windows" was ever reachable at all.
