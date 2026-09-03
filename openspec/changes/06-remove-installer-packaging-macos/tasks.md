## 1. Mark source tasks as moved

- [ ] 1.1 In `openspec/changes/remove-installer-packaging/tasks.md`, mark tasks 4.5, 5.3, and the macOS portion of 5.4 as `[x]` with a "Superseded — moved to `06-remove-installer-packaging-macos`" note, following the existing convention used at that file's task 6.4

## 2. macOS verification (moved from `remove-installer-packaging`) — PARKED, blocked on hardware/CI

- [ ] 2.1 (was 4.5) Confirm double-clicking `Transcriber.app` in Finder opens no Terminal window
- [ ] 2.2 (was 5.3) Unzip the `.app`, run it, confirm the window opens and file transcription works; record the Gatekeeper prompt for an unsigned build
- [ ] 2.3 (was 5.4, macOS portion) Confirm the macOS `.app` leaves no state outside its own bundle/zip beyond standard WebView cache locations (`~/Library/WebKit/<bundle-id>`, expected — see the Linux equivalent already documented in `remove-installer-packaging` task 5.4) — deleting it is a complete uninstall

## 3. Unblock this change (not started)

- [ ] 3.1 Decide and document a macOS build path once `04-remove-ci-and-container-builds` removes the `macos-latest` CI job (see design.md Open Questions), then resume section 2
