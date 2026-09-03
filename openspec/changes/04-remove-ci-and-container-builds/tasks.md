## 1. Verify replacements land first

- [ ] 1.1 Confirm `02-add-wsl-linux-build` and `03-add-wsl-windows-build` are both archived (or at minimum, their end-to-end verification tasks pass) before proceeding with any deletion in this change

## 2. Delete CI and container files

- [ ] 2.1 Delete `.github/workflows/build-gui.yml`; delete `.github/` entirely if it is left empty, and verify with `git status` that nothing else under it was tracked
- [ ] 2.2 Delete `docker/build.ps1` and `docker/tauri-build.Dockerfile`; delete the `docker/` directory
- [ ] 2.3 Delete `.dockerignore`
- [ ] 2.4 Grep the repo for any remaining reference to `docker/`, `.github/workflows`, or `tauri-build.Dockerfile` outside `openspec/changes/archive/` (historical records are fine to leave) and fix or remove each live reference found (e.g. `build_portable.py`'s error message mentioning `docker/build.ps1`, `src-tauri/.cargo/config.toml`'s comment)

## 3. Update documentation

- [ ] 3.1 Rewrite `README.md`'s build instructions to describe the WSL-native path from `02`/`03` (toolchain install, `CARGO_TARGET_DIR`, the interop sidecar freeze for Windows) in place of the Docker instructions
- [ ] 3.2 Verify no README section still tells a reader to run `docker/build.ps1` or references a GitHub Actions workflow for building

## 4. Spec cleanup verification

- [ ] 4.1 Run `openspec validate 04-remove-ci-and-container-builds --strict` and confirm the `docker-build` REMOVED delta and `linux-sidecar-build` REMOVED delta both validate cleanly
- [ ] 4.2 After archiving, confirm `openspec/specs/docker-build/` no longer exists and `openspec/specs/linux-sidecar-build/spec.md` retains only the standalone-binary requirement
