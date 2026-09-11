## Why

`remove-installer-packaging` is 21/28 tasks done; all 7 open tasks require either Windows or macOS hardware to verify, blocking the change's archive even though its general and Linux work is complete and verified. Per `01-adopt-platform-split-requirements`, this change takes over the Windows-only outstanding verification so `remove-installer-packaging` can archive its general/Linux scope independently. This change performs no new implementation — the `desktop-gui` spec delta (single no-install artifact, no console window) was already written by `remove-installer-packaging` and is unchanged; this change only completes verification for the Windows platform, now also updated to run via `03-add-wsl-windows-build`'s WSL build path instead of `docker/build.ps1`.

## What Changes

- Complete `remove-installer-packaging` tasks 2.6, 4.2, 4.3, 5.1, and the Windows portion of 5.4 (all currently `[ ]`, requiring Windows hardware) using an artifact built via `03-add-wsl-windows-build`'s WSL-native path.
- No code or spec changes beyond what those verification tasks might surface as real bugs (tracked as they're found, same as `remove-installer-packaging` itself did for its own verification tasks).
- `remove-installer-packaging`'s own `tasks.md` is annotated marking these tasks as superseded/moved here, following the existing "superseded by" convention already used in that file (task 6.4).

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
(none — `desktop-gui`'s delta was already authored by `remove-installer-packaging`; this change verifies it for Windows, it does not change its text)

This change sets `skip_specs: true` in `.openspec.yaml`: it is pure verification of already-specified behavior, not a behavior change.

## Impact

- **Affected**: `openspec/changes/remove-installer-packaging/tasks.md` (annotation only), potentially `src-tauri/src/main.rs` or `build_portable.py` if verification surfaces a real Windows-only bug (unknown until run).
- **Depends on**: `03-add-wsl-windows-build` for the artifact to verify against.
