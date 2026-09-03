## REMOVED Requirements

### Requirement: CI produces a verified Linux build
**Reason**: `.github/workflows/build-gui.yml` and its `ubuntu-latest` GitHub Actions job — the exact mechanism this requirement names — have been removed. Verification of the Linux build now happens manually via `02-add-wsl-linux-build`'s tasks, run directly on the WSL development machine.
**Migration**: See `openspec/changes/02-add-wsl-linux-build/tasks.md` section 3 for the equivalent manual verification (build, run, transcribe on the WSL-built AppImage).
