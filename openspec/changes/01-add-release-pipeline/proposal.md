## Why

Releases are built by hand today. Windows and Linux come from one WSL machine, and macOS can't be built at all because no Mac is available. Users get one no-install artifact per OS and nothing else: no installer, no package-manager install, and no standalone CLI, even though every build already produces a frozen CLI binary (the sidecar). Pushing a version tag should produce a draft GitHub release that contains portable, installer, and CLI artifacts for all three platforms.

## What Changes

- **Installers are back, alongside the portable artifacts.** This reverses `remove-installer-packaging`'s "SHALL NOT be distributed as an installer package". Every portable artifact stays: the Windows zip, the AppImage, and the zipped `.app`. Native installers are added next to them: `.deb` and `.rpm` in this change, NSIS in `02`, and `.dmg` in `03`.
- **GitHub Actions returns as a release pipeline.** It's a new `.github/workflows/release.yml`, not a revival of the CI that `04-remove-ci-and-container-builds` deleted. Pushing a `v*` tag runs a preflight (the tag must match the app version, and every URL in `SOURCE-PROVENANCE.txt` must resolve), builds each platform leg, and uploads everything to a **draft** release. A manual `workflow_dispatch` run builds the same things and creates no release.
- **Linux leg (`ubuntu-22.04`):** AppImage, `.deb`, and `.rpm`. The `.rpm` declares its dependencies by shared-library name, so one package resolves on both Fedora and openSUSE. Container install checks cover Debian, Ubuntu, Fedora, and openSUSE.
- **A standalone CLI archive in every release, same version as the GUI:** the frozen sidecar renamed to `transcriber`, the bundled `base` model and its license, the platform's launcher script(s), and the notice files. `build_portable.py` assembles it next to the GUI artifact.
- **The standalone CLI uses its bundled model automatically.** When the frozen binary finds `model/` next to itself and `--model` is `base` (the default), it loads the model from there instead of downloading it.
- **Launchers prefer the bundled binary.** When `transcriber` sits next to the script, the launcher runs it; otherwise it falls back to `python transcriber.py` as today. The Linux launcher changes here; the Windows launchers change in `02` and the macOS launcher in `03`.
- **Every leg smoke-tests the frozen sidecar before packaging.**
- **README:** a download section covering every artifact, and a "Releasing" section.

**Split:** the Windows leg is `02-add-release-pipeline-windows` and the macOS leg is `03-add-release-pipeline-macos`. The Linux leg lives here rather than in a change of its own, because the platform-agnostic pipeline can't be verified without at least one real leg. Linux is the only leg the development machine can verify end to end, including installing the packages.

## Capabilities

### New Capabilities
- `release-build`: how a release is triggered, gated, built, and published, and what every release must contain (including the standalone CLI archive and the Linux artifacts).

### Modified Capabilities
- `desktop-gui`: "Single no-install artifact per platform" is replaced by a requirement for a portable artifact per platform, with native installers offered alongside it. "Bundled resources resolve identically" and "Launches without a console" extend to installed layouts and menu launchers.
- `cli`: "Accept an explicit local model path" gains a scenario where the standalone binary uses its bundled model when no path is given.
- `teams-launcher`: a new requirement that launchers run the bundled standalone binary when one sits next to them.

## Impact

- **New**: `.github/workflows/release.yml`.
- **Changed**:
  - `build_portable.py`: versioned, platform-named artifact files, plus the CLI archive.
  - `transcriber.py`: bundled-model default when frozen.
  - `src-tauri/tauri.conf.json`: `bundle.linux.rpm.depends`.
  - `linux-start-transcription.sh`.
  - `README.md`.
- **Unchanged**: the local WSL/Linux build path and its specs (`wsl-linux-build`, `wsl-windows-build`). CI builds natively on each OS; local builds keep working as documented.
- **Cost**: none. The repository is public, so GitHub-hosted runner minutes are free.
- **Ordering**: apply `01` first. `02` and `03` add their legs to the workflow this change creates.
