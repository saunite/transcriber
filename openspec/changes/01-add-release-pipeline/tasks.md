## 1. Standalone CLI and bundled model

- [x] 1.1 In `transcriber.py`, default `--model-path` to `<dir of sys.executable>/model` when frozen, when `--model` is `base`, and when `model.bin` exists there (design.md Decision 6). Add one small `test_bundled_model_default.py`, run the same way as the existing `test_*.py` files, covering three cases: frozen with a bundled model resolves to it; frozen with `--model small` doesn't; not frozen doesn't.
- [x] 1.2 Extend `build_portable.py` so each run also assembles the CLI archive (design.md Decision 5): the renamed sidecar, `model/` without `.cache/`, the platform's launcher script(s) from a per-platform mapping, and the notice files. Output `.zip` on Windows and `.tar.gz` elsewhere, and add version and platform to every output file name. Verify with a local Linux build: `tar tzf` shows the expected layout, including `model/LICENSE.txt`; and after `tar xzf`, both `transcriber` and the launcher are executable.

  **Verified locally 2026-09-11** with a freshly frozen sidecar (PyInstaller 6.22.2, Python 3.14.7). `tar tvzf` shows `transcriber` and `linux-start-transcription.sh` as `-rwxr-xr-x`, plus `model/` (with `LICENSE.txt`, no `.cache/`) and all three notice files. The extracted `./transcriber --file silence.wav`, run with `HF_HOME` empty, `HF_HUB_OFFLINE=1`, and an unreachable proxy, logged `Loading base model from …/transcriber-cli_0.1.0_linux-x64/model`, exited 0, and wrote the transcript. That also confirms 1.1 inside a real frozen binary.

  **Pre-existing bug found, not caused by this change:** after a successful `--file` run, the frozen sidecar prints a `pyi_rth_multiprocessing` traceback (`ModuleNotFoundError: No module named '_socket'`, or `'array'`; it varies) while shutting down. The Sep 4 sidecar staged in `src-tauri/binaries/` prints the same one, so it predates this change. Exit code and output are unaffected, so the smoke test (exit 0 plus output file) still passes. It does violate `linux-sidecar-build`'s "no resource_tracker traceback" scenario, so it needs its own change. Unverified guess: a multiprocessing helper process, possibly started through tqdm's lock under Python 3.14's new default start method, re-runs the binary after the parent has begun deleting its extraction directory.
- [x] 1.3 In `linux-start-transcription.sh`, prefer `./transcriber` next to the script when present (design.md Decision 11). Verify two things: from an extracted CLI archive, the printed command starts with the bundled binary's path; from the checkout, it still starts with the Python interpreter.

## 2. Tauri config

- [ ] 2.1 Add `bundle.linux.rpm.depends` with shared-library capabilities, checked against `ldd` output for the built `transcriber-gui` (design.md Decision 4). Verify that `rpm -qpR` on the built `.rpm` lists them.

## 3. Release workflow

- [ ] 3.1 Create `.github/workflows/release.yml`, triggered on `v*` tags and `workflow_dispatch`, with `contents: write`. It needs a preflight job that does three things: fail when the tag version (without the `v`) differs from the version in `tauri.conf.json` or `Cargo.toml`; check the provenance URLs (design.md Decision 10); and create the draft release with `SOURCE-PROVENANCE.txt` attached. Verify by pushing the throwaway tag `v0.0.0-mismatch`: the run fails in preflight with both versions named, and no release appears. Then delete the tag.
- [ ] 3.2 Add the Linux leg on `ubuntu-22.04`:
  - install the system packages from the README, Python 3.14, and the venv with `requirements-linux.txt` and `pyinstaller`
  - freeze the sidecar and stage it under its target-triple name, then run `fetch_sidecar_resources.py`
  - run the smoke test (design.md Decision 7)
  - run `NO_STRIP=1 npx --yes @tauri-apps/cli@<pinned> build --bundles appimage,deb,rpm`, then `build_portable.py`
  - upload with `gh release upload` on tag runs, or `actions/upload-artifact` on dispatch runs

  Verify with a `workflow_dispatch` run that finishes green, with the AppImage, `.deb`, `.rpm`, and CLI `.tar.gz` downloadable from it.
- [ ] 3.3 Add the container install checks (design.md Decision 8). Verify that all five distro installs pass in the run log, then break one dependency name on purpose in a scratch run and confirm the leg fails.
- [ ] 3.4 Verify that a `workflow_dispatch` run creates no release: `gh release list` is unchanged afterwards.

## 4. Documentation

- [ ] 4.1 Rewrite README's "Download and run" section. It should explain portable vs. installer vs. CLI, give Linux instructions for the AppImage, `.deb` (`sudo apt install ./…deb`), and `.rpm` (`sudo dnf install ./…rpm` or `sudo zypper install ./…rpm`), and cover CLI archive usage, including that the bundled `base` model works offline and other sizes download on first use. Leave the Windows and macOS subsections to `02`/`03`, but keep a placeholder line for each so the section reads completely.
- [ ] 4.2 Add a README "Releasing" section: bump `version` in `tauri.conf.json` and `Cargo.toml`, and commit the `Cargo.lock` change; merge to `main`; `git tag vX.Y.Z && git push origin vX.Y.Z`; review the draft; publish. Update "Before publishing a release": step 1 is now automatic in preflight, and step 2 (re-derive provenance after a PyAV version change) stays manual. Verify by reading every README command against the workflow file.

## 5. End-to-end verification (Linux, real hardware)

- [ ] 5.1 Push `v0.1.0` and confirm that a draft release appears with the Linux artifacts and `SOURCE-PROVENANCE.txt`, and that it isn't publicly visible.
- [ ] 5.2 On the Fedora 44 development machine, install the `.rpm` with `dnf`, launch from the application menu (no terminal window), and run a file transcription with the network disabled. Then remove it with `dnf` and confirm the app and its menu entry are gone.
- [ ] 5.3 Download the AppImage from the draft, `chmod +x` it, run it, and transcribe a file.
- [ ] 5.4 Extract the CLI `.tar.gz` and run `./transcriber --file <clip>` with the network cut off (for example `unshare -rn`). It must transcribe with the bundled model. Also confirm that `./linux-start-transcription.sh` prints the bundled-binary command.
- [ ] 5.5 Either keep `v0.1.0` as the first real release (publish it once `02` and `03` legs have been added and re-run) or delete it with `gh release delete v0.1.0 --cleanup-tag`. Record which was done here.
