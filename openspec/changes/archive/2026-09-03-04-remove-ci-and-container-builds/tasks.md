## 1. Verify replacements land first

- [x] 1.1 Confirm `02-add-wsl-linux-build` and `03-add-wsl-windows-build` are both archived (or at minimum, their end-to-end verification tasks pass) before proceeding with any deletion in this change

  Verified: both present under `openspec/changes/archive/` (`2026-09-03-02-add-wsl-linux-build`, `2026-09-03-03-add-wsl-windows-build`).

## 2. Delete CI and container files

- [x] 2.1 Delete `.github/workflows/build-gui.yml`; delete `.github/` entirely if it is left empty, and verify with `git status` that nothing else under it was tracked

  Done. `.github/` was *not* fully empty — `.github/hooks/impeccable.json` (unrelated design-skill hook config, reviewed earlier this session) remains — so only `build-gui.yml` and the now-empty `workflows/` dir were removed, per this task's own conditional. `git status` confirmed only the one file deleted.
- [x] 2.2 Delete `docker/build.ps1` and `docker/tauri-build.Dockerfile`; delete the `docker/` directory

  Done — those were the only two files in `docker/`, confirmed before deleting; whole directory removed.
- [x] 2.3 Delete `.dockerignore`

  Done.
- [x] 2.4 Grep the repo for any remaining reference to `docker/`, `.github/workflows`, or `tauri-build.Dockerfile` outside `openspec/changes/archive/` (historical records are fine to leave) and fix or remove each live reference found (e.g. `build_portable.py`'s error message mentioning `docker/build.ps1`, `src-tauri/.cargo/config.toml`'s comment)

  Both examples named in this task fixed: `build_portable.py`'s error message now points to "README.md's WSL build section" instead of `docker/build.ps1`; `src-tauri/.cargo/config.toml`'s comment now points to the same. Full grep sweep afterward found no other live references outside: this change's own delta specs/artifacts (expected — they describe the removal), other in-flight changes' artifacts (historical/contextual, e.g. `05`'s "instead of docker/build.ps1"), and `openspec/changes/archive/`.

## 3. Update documentation

- [x] 3.1 Rewrite `README.md`'s build instructions to describe the WSL-native path from `02`/`03` (toolchain install, `CARGO_TARGET_DIR`, the interop sidecar freeze for Windows) in place of the Docker instructions

  Done. Removed the Docker-specific "Building it yourself" intro and PowerShell code block entirely; kept a short native-toolchain fallback for macOS/other platforms; simplified the `02`/`03`-added subsection headers from "(no Docker, no container)" to plain "Linux build" / "Windows build (from WSL)" since there's no longer a Docker path to contrast against.
- [x] 3.2 Verify no README section still tells a reader to run `docker/build.ps1` or references a GitHub Actions workflow for building

  Verified: `grep -niE "docker|github actions|workflow_dispatch|build-gui\.yml" README.md` returns nothing.

## 4. Spec cleanup verification

- [x] 4.1 Run `openspec validate 04-remove-ci-and-container-builds --strict` and confirm the `docker-build` REMOVED delta and `linux-sidecar-build` REMOVED delta both validate cleanly

  Verified: `Change '04-remove-ci-and-container-builds' is valid`.
- [x] 4.2 After archiving, confirm `openspec/specs/docker-build/` no longer exists and `openspec/specs/linux-sidecar-build/spec.md` retains only the standalone-binary requirement

  Verified: `openspec/specs/docker-build/` no longer exists (confirmed via `ls`, both requirements removed, directory deleted entirely by the sync). `openspec/specs/linux-sidecar-build/spec.md` retains exactly one requirement, "Frozen Linux sidecar runs standalone," with both of its original scenarios intact. Also fixed the spec's Purpose text post-sync (flagged by the sync agent as stale): it referenced "the CI mechanism," which no longer exists — reworded to describe the requirement in CI-independent terms (the binary must run standalone regardless of what built it).
