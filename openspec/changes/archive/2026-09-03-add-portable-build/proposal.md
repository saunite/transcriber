## Why

Two gaps surfaced while testing the `add-tauri-gui` change's first real Windows build: (1) an installer is more than the current dev/test loop needs — a portable, extract-and-run build is simpler and sufficient while the GUI is still being verified, with the installer remaining valuable later for an actual end-user release; (2) more importantly, the bundled `base` model isn't actually wired up — `transcription_engine.py` calls `WhisperModel("base", ...)` by bare name, which faster-whisper resolves through its own Hugging Face cache, not through the model files staged at `src-tauri/resources/model/` for bundling. This went unnoticed in testing only because the dev machine happened to already have `base` cached from earlier work. On a real end-user machine, the bundled model would sit unused and the app would try to download from the internet on first use — directly breaking the explicit "bundle the model, offline first run" requirement `add-tauri-gui` was built around.

## What Changes

- `transcription_engine.py` / `TranscriptionEngine.__init__` accepts an explicit local model directory and uses it instead of falling back to faster-whisper's bare-name (Hugging Face cache) resolution, when one is provided. `transcriber.py` gains a way to pass this through (e.g. `--model-path`), and the GUI sidecar wiring in `src-tauri/src/sidecar.rs` passes the bundled resources path automatically.
- New portable build output: the raw `cargo tauri build` output (`transcriber-gui.exe`, `transcriber-sidecar.exe`, `WebView2Loader.dll`) plus the staged model resources, assembled into a self-contained folder/zip with no installer, no admin, no registry entries — extract and run.
- `build_sidecar.py`/`fetch_sidecar_resources.py` unaffected; this change only adds an assembly step after the existing build steps, plus the model-path fix upstream of both the CLI and the GUI.
- NSIS installer output (`add-tauri-gui`) is unaffected and remains available for a later real release; this change doesn't remove it.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `transcription`: "Control model, device, and compute settings" gains the ability to load the model from an explicit local directory, bypassing network/cache resolution when provided.
- `desktop-gui` (from the not-yet-archived `add-tauri-gui` change — this extends that in-flight capability rather than an already-merged one): adds portable-build packaging and wires the sidecar to pass its bundled model path explicitly instead of relying on the bare model name.

## Impact

- **Changed code**: `transcription_engine.py` (model resolution), `transcriber.py` (new flag), `src-tauri/src/sidecar.rs` (pass bundled model path to spawned sidecar commands).
- **New code**: a small assembly script producing the portable folder/zip from existing build outputs.
- **Unaffected**: `build_sidecar.py`, `fetch_sidecar_resources.py`, the NSIS installer path, Docker cross-build setup.
- **Testing**: this is the first change where the *correctness* of offline model loading can actually be verified (previously masked by the dev machine's pre-existing HF cache) — verification should include confirming the fix on a machine/cache-state where `base` isn't already present, or by pointing `HF_HOME`/the cache at an empty directory.
