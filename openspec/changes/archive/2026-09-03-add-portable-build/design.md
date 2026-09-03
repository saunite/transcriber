## Context

`add-tauri-gui` produced a real, working NSIS installer (`Transcriber_0.1.0_x64-setup.exe`, cross-compiled via Docker, installs per-user with no admin prompt — see its tasks.md section 7). While using that build to verify things, two gaps surfaced:

1. The install/uninstall ceremony (registry entries, Start Menu shortcut, uninstaller) is more than the current dev/test loop needs. The raw `cargo tauri build` output already contains everything needed to run — `transcriber-gui.exe`, `transcriber-sidecar.exe`, `WebView2Loader.dll` — just missing the model resources next to it.
2. More importantly: `TranscriptionEngine.__init__` calls `WhisperModel(model_size, ...)` with a bare model name (e.g. `"base"`), which faster-whisper resolves via its own Hugging Face cache/download logic — **not** via the model files staged at `src-tauri/resources/model/` for bundling. Testing "worked" only because the dev machine already had `base` cached from earlier unrelated work. A real end user's machine has no such cache, so today's build would silently try to download the model from the internet on first use, defeating the explicit "offline first run" requirement.

## Goals / Non-Goals

**Goals:**
- A portable, no-installer build: extract a folder/zip anywhere, run `transcriber-gui.exe`, no admin, no registry footprint.
- The sidecar actually loads the model from wherever it's bundled (portable folder or installed location), not from a network/cache lookup, in both packaging forms.
- Verify the fix in a way that isn't masked by this dev machine's pre-existing model cache.

**Non-Goals:**
- Removing or replacing the NSIS installer — it stays for a future real release.
- Changing the model itself, or supporting multiple bundled models — still just `base`.
- Auto-update/versioning for the portable build.

## Decisions

### 1. Model path: explicit override, not environment-variable convention
`TranscriptionEngine.__init__` gains an optional `model_path` parameter; when set, it's passed to `WhisperModel(model_path, ...)` directly (faster-whisper accepts a local directory path in place of a model name). `transcriber.py` gains a `--model-path <dir>` CLI flag. When absent, behavior is unchanged (bare model name, faster-whisper's normal cache resolution) — this keeps the existing CLI/tests working exactly as before for anyone not running from a bundled build.

The GUI side (`src-tauri/src/sidecar.rs`) computes the bundled model directory relative to its own executable location (using Tauri's path-resolution APIs, which work the same whether running from an installed location or a portable folder) and always passes `--model-path` when spawning the sidecar — so the GUI path never depends on the ambient HF cache, portable or installed.

**Alternative considered**: set `HF_HOME`/`HUGGINGFACE_HUB_CACHE` env vars to point at the bundled directory instead of a new flag. Rejected — it works by exploiting cache-directory conventions rather than saying what's actually happening, and would silently break if faster-whisper's caching internals change. An explicit path parameter is a one-line, direct fix.

### 2. Portable build: assemble from existing outputs, no new bundler config
No new Tauri bundle target — `cargo tauri build` already isn't required to produce something runnable; the pre-bundle `target/<triple>/release/` output already has the exe/sidecar/DLL. A small assembly script copies those three files plus `src-tauri/resources/model/` into an output folder (and optionally zips it). This reuses 100% of the existing build pipeline (`build_sidecar.py`, `fetch_sidecar_resources.py`, `cargo tauri build`) — it's purely an assembly step after them, not a new build path.

**Alternative considered**: a dedicated Tauri "portable" bundle target. Tauri doesn't have first-class support for this on Windows (NSIS/MSI are the options), so this would mean fighting the bundler rather than just copying files that are already sitting there.

### 3. Verifying the offline-load fix despite the dev machine's warm cache
Point `HF_HOME` (or equivalent) at an empty temp directory for one test run, so faster-whisper's normal cache-lookup path is guaranteed to miss, and confirm the app still loads the model successfully (proving it's reading from the bundled path, not silently falling back to a download that happens to succeed because of network access). This is a test-time trick, not a product change.

## Risks / Trade-offs

- **[Risk]** A portable folder has no uninstaller and no upgrade mechanism — a user has to know to delete the old folder when replacing it with a new version. **Mitigation**: none needed now; this is explicitly a dev/test-loop convenience, not the release artifact end users get (that's still the NSIS installer, and later possibly an updater).
- **[Risk]** If `--model-path` is set but the model files are missing/corrupted (e.g. someone copies a portable folder incompletely), the error from faster-whisper may be less clear than a normal "downloading..." flow. **Mitigation**: keep it in scope for this change to surface a clear error if the model directory doesn't exist before even constructing `WhisperModel`, rather than relying on faster-whisper's own error message.

## Open Questions

- Should the portable folder also include a `README.txt` pointing at `--setup-help`/`--list-devices` equivalents for GUI users, or is that unnecessary since the GUI is meant to replace needing the CLI at all? Leaning toward not needed for now.
