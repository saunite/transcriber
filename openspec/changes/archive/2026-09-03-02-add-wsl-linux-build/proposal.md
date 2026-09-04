## Why

All development is moving onto a Linux/WSL machine, and the Docker cross-compile container (`docker/tauri-build.Dockerfile`, `docker/build.ps1`) exists solely to work around a Windows-host execution-policy block on Rust toolchain binaries (`docker/tauri-build.Dockerfile:5`). WSL runs Linux binaries natively, so that workaround's reason for existing is gone: `cargo`/`rustc`/`tauri-cli` can run directly in WSL with no container. This change establishes the native Linux build path the container's `cargo tauri build` (no `--target`) leg currently provides, so the container can be removed later (`04-remove-ci-and-container-builds`) without losing the ability to build a Linux artifact.

## What Changes

- Document/script the native Linux Tauri build toolchain for WSL: the same system packages the CI `ubuntu-latest` job and the Dockerfile already install (`libwebkit2gtk-4.1-dev`, `libgtk-3-dev`, `libayatana-appindicator3-dev`, `librsvg2-dev`, `libssl-dev`, `patchelf`, `build-essential`, `pkg-config`), plus `rustup` and `cargo install tauri-cli`. No Node.js/npm — the frontend is static files (`src-tauri/tauri.conf.json`'s `frontendDist` points at `../src` with no `beforeBuildCommand`); CI's `setup-node` step was unused.
- Relocate cargo's `target/` directory to a path on the WSL VM's own ext4 filesystem, via a persistent `~/.cargo/config.toml` (`build.target-dir`) — not just a per-shell `CARGO_TARGET_DIR` export, which silently falls back to the slow path if a shell forgets to set it — so `cargo`'s incremental-compilation file I/O isn't slowed by crossing the Windows/Linux filesystem boundary.
- **Relocate the repository checkout itself off any Windows-mounted path** (e.g. `/mnt/c/...` under WSL) onto a native filesystem (e.g. `~/repos/<name>`). Discovered mid-implementation, confirmed by a live WSL notification: relocating `target/` alone is insufficient — cargo still reads source files and Tauri still writes `src-tauri/gen/` at wherever the checkout lives, on every build, regardless of `target/`'s location.
- Fix `build_portable.py`'s `_release_dir()` to resolve the real build output location by querying `cargo metadata` directly, rather than re-checking only the `CARGO_TARGET_DIR` env var — authoritative regardless of whether cargo's target dir came from the env var, `~/.cargo/config.toml`, or its own default.
- Run `cargo tauri build` natively (no `--target`) from WSL to produce the Linux `.AppImage`, then `python build_portable.py` to assemble it into `dist/portable/`. Verified for real: **3m40.5s** build time, working AppImage, real file transcription through the bundled sidecar.

## Capabilities

### New Capabilities
- `wsl-linux-build`: native (containerless) build of the Linux desktop artifact from a WSL environment.

### Modified Capabilities
(none — `docker-build`'s requirements are retired in `04-remove-ci-and-container-builds`, once this change proves the replacement works)

## Impact

- **New**: WSL toolchain setup (documented in README), a machine-local `~/.cargo/config.toml` (not repo-tracked), `.gitignore` entry for `.venv-linux/` (the Linux-native venv used to freeze the sidecar for smoke-testing).
- **Changed**: `build_portable.py` (`_release_dir()` now queries `cargo metadata` instead of only checking `CARGO_TARGET_DIR`), `README.md` (WSL build section, including the checkout-location note above).
- **Moved**: the repository checkout itself, from a Windows-mounted path to a native-filesystem path — a one-time relocation for this development machine, not a repo-content change. `git status`/`git log` verified identical before and after.
- **Unaffected**: `docker/`, `.github/workflows/` (removed in `04`, after this change and `03` both prove their replacements work), all Python/Rust application code.
