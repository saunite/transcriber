## Why

GitHub Actions CI and the Docker cross-compile container were never a deliberate end goal — they accumulated as workarounds (a Windows execution-policy block, wanting a verified build on a real GitHub runner) that no longer serve a purpose now that all development and building happens directly on a Linux/WSL machine. `02-add-wsl-linux-build` and `03-add-wsl-windows-build` reproduce both platforms' build paths without a container; this change removes the now-redundant CI and container machinery, and the requirements that depended on them, once those replacements are proven.

## What Changes

- Delete `.github/workflows/build-gui.yml` and `.github/` if nothing else remains under it.
- Delete `docker/` (`build.ps1`, `tauri-build.Dockerfile`) and `.dockerignore`.
- **REMOVE** the `docker-build` capability entirely — both its requirements ("Native-filesystem build inside the container", "Only the build output crosses the host/container boundary") describe container mechanics that no longer apply; their intent is carried forward by `wsl-linux-build`/`wsl-windows-build`'s own filesystem requirement, not by a modified version of these.
- **REMOVE** `linux-sidecar-build`'s "CI produces a verified Linux build" requirement — it names `.github/workflows/build-gui.yml` and `ubuntu-latest` directly, both gone. The sibling requirement, "Frozen Linux sidecar runs standalone", is unaffected and stays (it's about the binary's behavior, not how it's built).
- Update `README.md`: replace the Docker-based Windows build instructions (`README.md:28-40` area) with the WSL-native instructions from `02`/`03`.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `docker-build`: capability removed entirely (see What Changes).
- `linux-sidecar-build`: the CI-specific requirement is removed; the sidecar-behavior requirement is unchanged.
- `documentation`: no new requirement, but this change is itself an instance of the existing "README mirrors supported behavior" requirement — the build-instructions rewrite satisfies it, no spec delta needed.

## Impact

- **Deleted**: `.github/workflows/build-gui.yml`, `docker/build.ps1`, `docker/tauri-build.Dockerfile`, `.dockerignore`.
- **Changed**: `README.md` (build instructions section).
- **Unaffected**: all application code, `openspec/specs/linux-sidecar-build`'s standalone-binary requirement, `src-tauri/.cargo/config.toml` (its mingw comment references the Dockerfile in prose only — harmless if slightly stale, not functionally dependent on it).

## Ordering

**Apply after `02` and `03` both land and are verified.** `docker/build.ps1` is, as of today, the only proven build path for both Windows and Linux artifacts. Deleting it first would leave no way to build either platform if the WSL replacements turn out to need further fixes.
