## Why

Two things in `.github/workflows/release.yml` were raised on 2026-09-14.

- **`SOURCE-PROVENANCE.txt` appears among the downloads.** `preflight`'s "Create draft release" step attaches it as a release asset (`gh release create … --generate-notes SOURCE-PROVENANCE.txt`), so the draft `v0.1.0` release lists an 8 KB `.txt` next to the installers and packages. The maintainer wants the download list to hold only things users download.
  - The file exists for GPLv3 §6(d): the artifacts bundle GPL-licensed FFmpeg, x264 and x265 through PyAV, and `licensing` requires directions to their source "alongside the distributed artifact".
  - A copy already ships inside every package (`build_portable.py`'s `NOTICE_FILES`, `tauri.conf.json`'s `bundle.resources`).
  - The maintainer chose to keep the directions on the release page by linking the file from the release notes, instead of attaching it (option B of the 2026-09-14 exploration).
- **GitHub warns that `actions/upload-artifact@v4` targets Node.js 20**, which is deprecated and currently forced onto Node.js 24. It is used 3 times, in the Linux, Windows and macOS jobs. v6 is the first release built for Node 24 (`runs.using: node24`); the latest is v7.0.1. The other actions already run on Node 24: `actions/checkout@v5`, `actions/setup-python@v6`, `Swatinem/rust-cache@v2`.

## What Changes

- **Release notes link to the provenance file** instead of the release attaching it. The draft release's notes open with a short section naming the bundled GPL components and linking to `SOURCE-PROVENANCE.txt` in the repository **at the release's tag**. GitHub's generated notes follow. The file is still copied into every package, and `preflight` still checks that its source links resolve.
- **`actions/upload-artifact@v4` → `@v7`** in all three jobs. The default behaviour is unchanged: v7's only addition is an opt-in `archive: false`, which is not used.
- **README's "Releasing" licensing paragraph** says the workflow links the file from the release notes, not that it attaches it.
- **Not in scope:**
  - `SOURCE-PROVENANCE.txt` is stale: it records `av == 16.0.1`, while the venv resolves PyAV 18.1.0, which is unpinned. That is a licensing fix needing research, left for a separate change.
  - Per-file uploads for manual runs.
  - Deleting the old draft `v0.1.0` for its own sake. It is only touched if the maintainer chooses to re-tag it to verify this change.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `release-build`: "Source-provenance directions are verified and attached" changes from attaching the file as a release asset to linking it from the release notes, at the release's tag. The link check is unchanged. `licensing` is unchanged: a link on the release page still puts the directions alongside the download, and the in-package copy stays.

## Impact

- **Changed:** `.github/workflows/release.yml` (the "Create draft release" step, and three `upload-artifact` lines), `README.md`.
- **Unchanged:** `SOURCE-PROVENANCE.txt` and its link check, `build_portable.py`, `tauri.conf.json`, and every artifact's contents.
- **Verification:**
  - A manual run shows the three uploads working with no Node 20 warning.
  - Checking the release notes needs a tagged run, which creates a private draft release. The maintainer decides which tag at that point.
