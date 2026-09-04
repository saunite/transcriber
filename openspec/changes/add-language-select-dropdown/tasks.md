## 1. Language picker

- [x] 1.1 Replace `#language-input` (text) with `#language-select` (select) in `src/index.html`
- [x] 1.2 Add `WHISPER_LANGUAGES` + `populateLanguageSelect()` to `src/main.js`, "Auto-detect" (value `""`) first, then all supported languages sorted by name
- [x] 1.3 Update both `invoke()` call sites (`startLiveSession`, `transcribeFile`) to read `els.languageSelect.value || null`

## 2. Verification

- [ ] 2.1 Run the app, confirm the dropdown defaults to "Auto-detect" and lists languages sorted by name
- [ ] 2.2 Start a live session with a specific language selected — confirm `--language <code>` is passed to the sidecar (check the engine log / process args)
- [ ] 2.3 Confirm "Auto-detect" still omits `--language` entirely, matching the old empty-field behavior

## 3. Spec

- [x] 3.1 Add a new `desktop-gui` requirement documenting the language dropdown and its "Auto-detect" default
