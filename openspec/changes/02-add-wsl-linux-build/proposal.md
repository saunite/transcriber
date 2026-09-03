## Why

All development is moving onto a Linux/WSL machine, and the Docker cross-compile container (`docker/tauri-build.Dockerfile`, `docker/build.ps1`) exists solely to work around a Windows-host execution-policy block on Rust toolchain binaries (`docker/tauri-build.Dockerfile:5`). WSL runs Linux binaries natively, so that workaround's reason for existing is gone: `cargo`/`rustc`/`tauri-cli` can run directly in WSL with no container. This change establishes the native Linux build path the container's `cargo tauri build` (no `--target`) leg currently provides, so the container can be removed later (`04-remove-ci-and-container-builds`) without losing the ability to build a Linux artifact.

## What Changes

- Document/script the native Linux Tauri build toolchain for WSL: the same system packages the CI `ubuntu-latest` job and the Dockerfile already install (`libwebkit2gtk-4.1-dev`, `libgtk-3-dev`, `libayatana-appindicator3-dev`, `librsvg2-dev`, `libssl-dev`, `patchelf`, `build-essential`, `pkg-config`), plus `rustup` and `cargo install tauri-cli`. No Node.js/npm — the frontend is static files (`src-tauri/tauri.conf.json`'s `frontendDist` points at `../src` with no `beforeBuildCommand`); CI's `setup-node` step was unused.
- Set `CARGO_TARGET_DIR` to a path on the WSL VM's own ext4 filesystem (not under the repo checkout, which may be Windows-mounted `/mnt/c/...` DrvFs) so `cargo`'s incremental-compilation file I/O isn't slowed by crossing the Windows/Linux filesystem boundary — the same problem `fix-docker-build-filesystem` solved for the container, generalized to a non-container WSL build.
- Fix `build_portable.py`'s `_release_dir()` to resolve against `CARGO_TARGET_DIR` when set, instead of hardcoding `src-tauri/target`.
- Run `cargo tauri build` natively (no `--target`) from WSL to produce the Linux `.AppImage`, then `python build_portable.py` to assemble it into `dist/portable/`.

## Capabilities

### New Capabilities
- `wsl-linux-build`: native (containerless) build of the Linux desktop artifact from a WSL environment.

### Modified Capabilities
(none — `docker-build`'s requirements are retired in `04-remove-ci-and-container-builds`, once this change proves the replacement works)

## Impact

- **New**: WSL toolchain setup (documented in README and/or a setup script — see tasks), no new source files required beyond the `build_portable.py` fix.
- **Changed**: `build_portable.py` (`_release_dir()` honors `CARGO_TARGET_DIR`).
- **Unaffected**: `docker/`, `.github/workflows/` (removed in `04`, after this change and `03` both prove their replacements work), all Python/Rust application code.
