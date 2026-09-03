## 1. Mark source tasks as moved

- [ ] 1.1 In `openspec/changes/remove-installer-packaging/tasks.md`, mark tasks 2.6, 4.2, 4.3, 5.1, and the Windows portion of 5.4 as `[x]` with a "Superseded — moved to `05-remove-installer-packaging-windows`" note, following the existing convention used at that file's task 6.4

## 2. Windows verification (moved from `remove-installer-packaging`)

- [ ] 2.1 (was 2.6) Run `build_portable.py` on Windows against a `03-add-wsl-windows-build`-produced release dir, extract the produced zip to a fresh path, run it, and confirm it transcribes
- [ ] 2.2 (was 4.2) Double-click `transcriber-gui.exe` from Explorer and confirm the app window appears with no console window before, beside, or behind it
- [ ] 2.3 (was 4.3) Start a live session and a file transcription and confirm no console window flashes when the sidecar spawns
- [ ] 2.4 (was 5.1) Extract the zip on a machine that has never had the app installed, run `transcriber-gui.exe`, confirm no admin prompt, no registry writes, and a working transcription
- [ ] 2.5 (was 5.4, Windows portion) Confirm the Windows zip leaves no state outside its own folder — deleting the folder is a complete uninstall (note any WebView2 cache location found, matching the pattern `remove-installer-packaging` task 5.4 already documented for Linux/WebKitGTK)
