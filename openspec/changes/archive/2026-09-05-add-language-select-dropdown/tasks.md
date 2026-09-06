## 1. Language picker

- [x] 1.1 Replace `#language-input` (text) with `#language-select` (select) in `src/index.html`
- [x] 1.2 Add `WHISPER_LANGUAGES` + `populateLanguageSelect()` to `src/main.js`, "Auto-detect" (value `""`) first, then all supported languages sorted by name
- [x] 1.3 Update both `invoke()` call sites (`startLiveSession`, `transcribeFile`) to read `els.languageSelect.value || null`

## 2. Verification

- [x] 2.1 Run the app, confirm the dropdown defaults to "Auto-detect" and lists languages sorted by name

  Confirmed two ways: programmatically (extracted `WHISPER_LANGUAGES` from the shipped `main.js` and verified in Node — 100 languages, zero duplicate names, strictly ascending sort) and visually (user screenshot: dropdown open, "Auto-detect" highlighted at top, then Afrikaans/Albanian/Amharic/Arabic/Armenian/Assamese/Azerbaijani/Bashkir/Basque/Belarusian/Bengali in order).
- [x] 2.2 Start a live session with a specific language selected — confirm `--language <code>` is passed to the sidecar (check the engine log / process args)

  **Verified via unit test, not a real live session.** `start_live_session`'s `build_live_session_args` (`src-tauri/src/sidecar.rs`) hardcodes `--wasapi`, which `transcriber.py`'s `_validate_live_capture_platform` rejects on any OS but Windows — so an actual live session through this GUI command cannot run on this (Linux) machine regardless of language selection; that's a pre-existing OS gate, not something this change could newly unblock. Added `passes_language_when_selected`/`omits_language_when_auto_detect` to `sidecar.rs`'s existing `build_live_session_args` unit tests (same pattern as `passes_audio_device_override_when_set`), which do exercise the actual arg-assembly code the live command runs — confirmed `cargo test --bin transcriber-gui sidecar::` passes (7/7). Additionally ran the real sidecar binary through the file-mode path (`transcribeFile`'s other, non-platform-gated call site, same `els.languageSelect.value || null` → `--language` wiring) end-to-end against a synthetic WAV with `--language en`: printed `Language: en`, skipped auto-detection, transcript saved successfully.
- [x] 2.3 Confirm "Auto-detect" still omits `--language` entirely, matching the old empty-field behavior

  Same real end-to-end run repeated without `--language`: printed `Language: auto-detect`, ran Whisper's own language detection (`Detected language: en (probability: 0.59)`), transcript saved successfully. Confirms `null` → omitted flag → old auto-detect behavior, unchanged.

## 3. Spec

- [x] 3.1 Add a new `desktop-gui` requirement documenting the language dropdown and its "Auto-detect" default
