## Why

The language field was a free-text `<input>` with placeholder "auto" — accurate to no visible state in particular (an empty box showing greyed placeholder text reads as "type something," not "auto-detect is active and here's what that means"), and it accepted arbitrary text with no validation against what the bundled faster-whisper model actually supports. Separately explored in this session: whether the engine's actually-detected language could be shown next to the field. Checked, and it doesn't reach the UI in a usable form — file mode's detection only reaches an unparsed line in the debug/engine log, and live mode's `transcribe_chunk` discards the `info` object entirely (`transcription_engine.py`) — so that stays deferred, and this proposal is scoped to only the field itself.

## What Changes

- `src/index.html`: `#language-input` (text) replaced with `#language-select` (select, populated by JS).
- `src/main.js`: a `WHISPER_LANGUAGES` map (faster-whisper's full supported-language table) plus `populateLanguageSelect()`, building an "Auto-detect" option (value `""`) first, then every supported language sorted by name. Both `invoke()` call sites (`startLiveSession`, `transcribeFile`) now read `els.languageSelect.value || null` — the identical null-means-auto-detect contract as before, so nothing on the Rust or Python side changes.

**Deliberately not building**: a "detected language" readout next to the picker (see Why) — tracked as a possible follow-up, not part of this change.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `desktop-gui`: adds one requirement — language selection is a constrained dropdown defaulting to "Auto-detect," not free text.

## Impact

- **Changed**: `src/index.html`, `src/main.js`.
- **Unaffected**: `src-tauri/src/sidecar.rs`, `transcriber.py`, `transcription_engine.py` — the `language` IPC value was already `Option<String>` / `None`-for-auto-detect; the dropdown only changes how that value gets chosen client-side.
