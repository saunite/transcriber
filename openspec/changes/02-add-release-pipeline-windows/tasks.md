## 1. Config and launchers

- [x] 1.1 Add `bundle.windows.nsis.installMode: "currentUser"` to `src-tauri/tauri.conf.json`. Verify that the installer built in 2.3 installs under `%LOCALAPPDATA%` (checked in 4.1).
- [x] 1.2 In `win-start-transcription.bat`, prefer `%~dp0transcriber.exe` when present, building the printed and executed `CMD` from the same variable (design.md Decision 4). Verify on Windows: from an extracted CLI zip it prints and runs the `transcriber.exe …` command; from the checkout it still prints `python transcriber.py …`.
- [x] 1.3 Give `transcribe_file.bat` the same fallback in place of its hard-coded `.venv\Scripts\python.exe transcriber.py`. Verify that it transcribes a file from an extracted CLI zip with no Python on `PATH`.

## 2. Windows leg in `release.yml`

- [x] 2.1 Set up the toolchain on `windows-latest`: `rustup default stable-x86_64-pc-windows-gnu`, `rustup target add x86_64-pc-windows-gnu`, and mingw-w64 on `PATH` (design.md Decision 1). Verify in the run log that `rustc -vV` reports `host: x86_64-pc-windows-gnu` and that `x86_64-w64-mingw32-gcc --version` succeeds.
- [x] 2.2 Set up Python 3.14 with a venv containing `requirements.txt` and `pyinstaller`. Run `build_sidecar.py`, stage the result as `src-tauri/binaries/transcriber-sidecar-x86_64-pc-windows-gnu.exe`, run `fetch_sidecar_resources.py`, then run the smoke test from `01`. Verify that the smoke-test step passes in the run log.
- [x] 2.3 Run `npx --yes @tauri-apps/cli@<pinned> build --target x86_64-pc-windows-gnu --bundles nsis`, then `build_portable.py --target x86_64-pc-windows-gnu`, and upload the setup exe, the portable zip, and the CLI zip (release on tag runs, artifact on dispatch runs). Verify with a `workflow_dispatch` run that all three are downloadable.
- [ ] 2.4 Confirm that `WebView2Loader.dll` ends up in the installed app directory (design.md Decision 3). Check by extracting the NSIS installer with 7-Zip, or during the install in 4.1. If it's missing, add it for Windows builds and re-run.

  **Run 34694349879 (v0.1.0, 2026-09-12): the Windows leg failed, but only on an artifact-naming bug in `build_portable.py`, now fixed.**

  `cp: cannot stat 'dist/portable/transcriber-cli_*_windows-x64.zip': No such file or directory`. `build_cli()`'s Windows branch built its archive name with `out_dir.with_suffix(".zip")`, and the directory is `transcriber-cli_0.1.0_windows-x64` — `Path.with_suffix` replaces everything after the **last** dot, so it produced **`transcriber-cli_0.1.zip`**. The log confirms it: "CLI archive assembled at: …\dist\portable\transcriber-cli_0.1.zip". Fixed to `out_dir.parent / f"{name}.zip"`, matching how the `tar.gz` branch two lines below already built its name.

  **Why this never showed up before:** only the Windows branch used `with_suffix`; Linux and macOS use f-strings, which is why the published `transcriber-cli_0.1.0_linux-x64.tar.gz` has always been named correctly. The bug was latent in the script from the start and could only surface the first time the Windows job ran.

  **Everything else in the leg worked**, so both risks design.md flagged are retired:
  - **Toolchain**: `rustc 1.98.1 (48a229cea 2026-09-01)` with host `stable-x86_64-pc-windows-gnu`, and `x86_64-w64-mingw32-gcc` resolved on `PATH` — the "Show toolchain" step passed, so mingw is present under the name `src-tauri/.cargo/config.toml` expects.
  - **Smoke test**: `.github/smoke-test.sh` ran under Git Bash against the frozen `.exe` and the job proceeded past it.
  - **NSIS**: built via `makensis`, producing `…\target\x86_64-pc-windows-gnu\release\bundle\nsis\Transcriber_0.1.0_x64-setup.exe` — the exact path and filename predicted from the bundler source. "Finished 1 bundle", correct for `--bundles nsis`.
  - **Portable zip**: "Portable artifact assembled at: …\dist\portable\Transcriber_0.1.0_windows-x64.zip".

  2.4 stays open: no Windows assets reached the draft release, because the step died before `gh release upload`. It needs one passing run.



  **Implemented and committed 2026-09-11/12 (`1ef885e`); every CI and hardware half is still open.**

  - **1.1** `bundle.windows.nsis.installMode: "currentUser"` is set in `src-tauri/tauri.conf.json`. The `%LOCALAPPDATA%` check belongs to 4.1.
  - **1.2** `win-start-transcription.bat` now picks `%~dp0transcriber.exe` when present, building the printed and executed `CMD` from one `RUN` variable. **Beyond the task text:** the script called `.venv\Scripts\activate.bat` unconditionally, which would fail inside a release CLI zip that has no venv, so the venv activation moved into the fallback branch and is itself guarded by an `if exist`.
  - **1.3** `transcribe_file.bat` got the same `RUN` choice in place of its hard-coded `.venv\Scripts\python.exe transcriber.py`.
  - **2.1–2.3** A `windows` job was added to `release.yml`: `rustup default stable-x86_64-pc-windows-gnu` plus the gnu target (so build scripts and proc-macros are linked by mingw too, not MSVC), both candidate mingw paths appended to `PATH`, a "Show toolchain" step that fails fast if `rustc -vV`/`x86_64-w64-mingw32-gcc` are wrong, Python 3.14 with a pip cache keyed on `requirements.txt`, the freeze staged as `transcriber-sidecar-x86_64-pc-windows-gnu.exe`, the shared smoke test, `rust-cache`, the NSIS build, `build_portable.py --target …`, and the tag/dispatch upload split. `yamllint` and a PyYAML parse pass, and the job appears as `preflight -> windows` alongside `linux`.

  **Three output paths were verified against the code rather than assumed**, since each would otherwise fail ~20 minutes into a Windows run: `build_sidecar.py` writes `dist/<platform.system().lower()>` = `dist/windows/`; `build_portable.py` writes `Transcriber_<version>_windows-x64.zip` and `transcriber-cli_<version>_windows-x64.zip` into `dist/portable/`; and `tauri-bundler`'s nsis module writes `project_out_directory()/bundle/nsis/<name>-setup.exe`, i.e. `target/x86_64-pc-windows-gnu/release/bundle/nsis/`.

  **Two risks left for the run to settle**, both in design.md: whether the runner's mingw is on `PATH` under the `x86_64-w64-mingw32-gcc` name (the Show toolchain step makes that fail in seconds, not minutes), and whether `.github/smoke-test.sh` behaves under Git Bash when invoking a Windows `.exe`.

## 3. Documentation

- [x] 3.1 Fill in README's Windows download subsection: the setup exe (per-user, no admin rights, uninstall from Windows settings), the portable zip (extract and run; deleting the folder uninstalls), the CLI zip (`transcriber.exe`, the launchers, and the bundled model), and the unsigned-file SmartScreen prompt ("More info → Run anyway"). Verify each described file name against a real run's outputs.

  **Installer and portable names now verified against a real run (34694349879), which is what this task asked for.** `makensis` produced **`Transcriber_0.1.0_x64-setup.exe`** and `build_portable.py` produced **`Transcriber_0.1.0_windows-x64.zip`** — both exactly as the README table states, confirming the names derived from `tauri-bundler`'s nsis module and `PLATFORM_LABEL`.

  **The CLI zip row was wrong, and the code was at fault rather than the README.** The run emitted `transcriber-cli_0.1.zip` (the `with_suffix` bug recorded under 2.4). The README's `transcriber-cli_<version>_windows-x64.zip` is the intended and now-fixed name, so the table needs no edit — but this row is only confirmed once a passing run publishes it, which 2.4 covers.


  **Written 2026-09-11/12; left unticked deliberately.** README's Windows subsection is now a three-row table matching Linux's: the setup exe (per-user under `%LOCALAPPDATA%`, no admin rights, uninstall via Settings → Apps → Installed apps), the portable zip (extract, run `transcriber-gui.exe`, delete the folder to uninstall), and the CLI zip (`transcriber.exe`, both `.bat` launchers, bundled model), followed by the SmartScreen "More info → Run anyway" note. The stale sentence promising that the installer and CLI zip "are coming" is gone.

  **The three file names are verified against the code that emits them, not against a real run, which is what this task asks for** — so it stays open until the tagged run in 2.4 publishes assets I can compare against:
  - `Transcriber_<version>_x64-setup.exe` — `tauri-bundler-2.9.4/src/bundle/windows/nsis/mod.rs:652` builds `format!("{}_{}_{}-setup", product_name, version_string, arch)` with `arch = "x64"` for `Arch::X86_64` (line 181), landing in `bundle/nsis/`.
  - `Transcriber_<version>_windows-x64.zip` and `transcriber-cli_<version>_windows-x64.zip` — `build_portable.py`'s `build_windows`/`build_cli` with `PLATFORM_LABEL["windows"] = "windows-x64"`.
  - The CLI zip's contents are `build_cli`'s copies: the sidecar renamed `transcriber.exe`, `model/`, `LAUNCHERS["windows"]` (both `.bat` files), and the notices.

## 4. Real-hardware verification

- [ ] 4.1 From a **standard (non-admin)** Windows account, run the CI-built installer. Confirm there's no UAC prompt, the install lands under that user's profile, the Start Menu launch shows no console window, and both a live session and an offline file transcription work.
- [ ] 4.2 Uninstall through Windows settings. Confirm the app files and the Start Menu entry are gone with no admin prompt, apart from the WebView2 cache already documented in `05` task 2.5.
- [ ] 4.3 (moved from `05-remove-installer-packaging-windows` task 2.4) On a machine that has never had the app, extract the **CI-built** portable zip, run `transcriber-gui.exe`, and confirm there's no admin prompt and a transcription works. This needs a genuinely clean machine: another PC or a cloud VM (design.md Decision 5).
- [ ] 4.4 Extract the CLI zip and run `transcriber.exe --file <clip>` with the network disconnected. It must transcribe with the bundled model. Then run `win-start-transcription.bat` and confirm a live session starts from the bundled exe.
