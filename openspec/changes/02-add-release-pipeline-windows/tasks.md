## 1. Config and launchers

- [ ] 1.1 Add `bundle.windows.nsis.installMode: "currentUser"` to `src-tauri/tauri.conf.json`. Verify that the installer built in 2.3 installs under `%LOCALAPPDATA%` (checked in 4.1).
- [ ] 1.2 In `win-start-transcription.bat`, prefer `%~dp0transcriber.exe` when present, building the printed and executed `CMD` from the same variable (design.md Decision 4). Verify on Windows: from an extracted CLI zip it prints and runs the `transcriber.exe …` command; from the checkout it still prints `python transcriber.py …`.
- [ ] 1.3 Give `transcribe_file.bat` the same fallback in place of its hard-coded `.venv\Scripts\python.exe transcriber.py`. Verify that it transcribes a file from an extracted CLI zip with no Python on `PATH`.

## 2. Windows leg in `release.yml`

- [ ] 2.1 Set up the toolchain on `windows-latest`: `rustup default stable-x86_64-pc-windows-gnu`, `rustup target add x86_64-pc-windows-gnu`, and mingw-w64 on `PATH` (design.md Decision 1). Verify in the run log that `rustc -vV` reports `host: x86_64-pc-windows-gnu` and that `x86_64-w64-mingw32-gcc --version` succeeds.
- [ ] 2.2 Set up Python 3.14 with a venv containing `requirements.txt` and `pyinstaller`. Run `build_sidecar.py`, stage the result as `src-tauri/binaries/transcriber-sidecar-x86_64-pc-windows-gnu.exe`, run `fetch_sidecar_resources.py`, then run the smoke test from `01`. Verify that the smoke-test step passes in the run log.
- [ ] 2.3 Run `npx --yes @tauri-apps/cli@<pinned> build --target x86_64-pc-windows-gnu --bundles nsis`, then `build_portable.py --target x86_64-pc-windows-gnu`, and upload the setup exe, the portable zip, and the CLI zip (release on tag runs, artifact on dispatch runs). Verify with a `workflow_dispatch` run that all three are downloadable.
- [ ] 2.4 Confirm that `WebView2Loader.dll` ends up in the installed app directory (design.md Decision 3). Check by extracting the NSIS installer with 7-Zip, or during the install in 4.1. If it's missing, add it for Windows builds and re-run.

## 3. Documentation

- [ ] 3.1 Fill in README's Windows download subsection: the setup exe (per-user, no admin rights, uninstall from Windows settings), the portable zip (extract and run; deleting the folder uninstalls), the CLI zip (`transcriber.exe`, the launchers, and the bundled model), and the unsigned-file SmartScreen prompt ("More info → Run anyway"). Verify each described file name against a real run's outputs.

## 4. Real-hardware verification

- [ ] 4.1 From a **standard (non-admin)** Windows account, run the CI-built installer. Confirm there's no UAC prompt, the install lands under that user's profile, the Start Menu launch shows no console window, and both a live session and an offline file transcription work.
- [ ] 4.2 Uninstall through Windows settings. Confirm the app files and the Start Menu entry are gone with no admin prompt, apart from the WebView2 cache already documented in `05` task 2.5.
- [ ] 4.3 (moved from `05-remove-installer-packaging-windows` task 2.4) On a machine that has never had the app, extract the **CI-built** portable zip, run `transcriber-gui.exe`, and confirm there's no admin prompt and a transcription works. This needs a genuinely clean machine: another PC or a cloud VM (design.md Decision 5).
- [ ] 4.4 Extract the CLI zip and run `transcriber.exe --file <clip>` with the network disconnected. It must transcribe with the bundled model. Then run `win-start-transcription.bat` and confirm a live session starts from the bundled exe.
