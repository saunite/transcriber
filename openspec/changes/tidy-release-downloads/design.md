## Context

See `proposal.md` for why. What decides how a release page reads:

- The hosting service sorts assets alphabetically, case-insensitively, with no folders and no ordering control. `-` sorts before `_`, which is why `transcriber-cli_…` lands between the `.rpm` and the `.dmg` today.
- Release notes render above the asset list. They are written once, in `release.yml`'s "Create draft release" step, which already builds a heredoc for the GPL source directions.
- Each platform job stages its artifacts in `out/` and uploads with `gh release upload … out/*`. The Linux job already renames there: `.deb` and `.rpm` are lowercased, the AppImage is not (`fix-linux-native-window-frame`).
- The apt index is rebuilt for each release from that release's own assets, so a name change needs no migration. A published release's assets must not be renamed, though: v0.1.0's live index names them.

## Goals / Non-Goals

**Goals:** a visitor finds their download without knowing the project's file names; the list groups by platform; the machine-only files are identified as such.

**Non-Goals:** moving the apt index (see the proposal); changing what is built, or any published release.

## Decisions

**1. Rename in the CI staging step, not in the build scripts.**
Each job renames inside `out/`, just before upload, as the Linux job already does. `build_portable.py` and the Tauri bundler keep their names, so a local build and the developer documentation are unaffected, and each job's naming lives in one visible place.
- *Rename at the source:* it would spread the naming over `build_portable.py`, the bundler's config and the CLI packaging, and change what local builds produce for no gain.

**2. Prefix only, keeping the existing names and case rule.**

| Platform | Assets |
|---|---|
| Linux | `linux-Transcriber_<v>_amd64.AppImage`, `linux-transcriber_<v>_amd64.deb`, `linux-transcriber-<v>-1.x86_64.rpm`, `linux-transcriber-cli_<v>_linux-x64.tar.gz` |
| macOS | `macos-Transcriber_<v>_aarch64.dmg`, `macos-Transcriber_<v>_macos-arm64.zip`, `macos-transcriber-cli_<v>_macos-arm64.tar.gz` |
| Windows | `windows-Transcriber_<v>_x64-setup.exe`, `windows-Transcriber_<v>_windows-x64.zip`, `windows-transcriber-cli_<v>_windows-x64.zip` |

The case rule from 2026-09-18 is unchanged, confirmed by the user on 2026-09-19: `.deb` and `.rpm` lowercase, everything else capitalised.
- **Accepted redundancy:** the CLI archives read `linux-transcriber-cli_<v>_linux-x64.tar.gz`. Removing the second platform word would mean renaming inside `build_portable.py`, which Decision 1 keeps out of scope.
- *A leading `01-`, `02-` to force an order:* it groups but tells the reader nothing, and the prefix already sorts correctly.

**3. The notes table is written in the draft-release step, with the version substituted.**
The step already composes notes in a heredoc; the table joins it, above the existing GPL section, with `${GITHUB_REF_NAME#v}` filled in so each row names a real file. It has a row per platform choice (installer or package, portable, CLI), and a closing line that `InRelease`, `Packages` and `Packages.gz` are for apt and can be ignored.
- *A static file in the repository, linked from the notes:* one click further from the reader, and it would drift from the real names.
- *Generating the table from the uploaded assets:* the notes are written before the platform jobs upload anything, and reopening them afterwards adds a step for a table we can write plainly.

**4. Nothing changes for v0.1.0 or for the repositories.**
Renaming a published release's assets would break the live apt index, which names them. The new names apply from the next release, whose index is generated from the new names.

## Risks / Trade-offs

- [A saved link to `releases/latest/download/<old name>` stops resolving after the next release] → Those links are version-specific downloads people took by hand, not the update path: apt uses the index, dnf uses the Pages metadata, and the app's update check reads the release's version, never an asset name. The README's tables are updated in the same change.
- [The table drifts from the real names] → It lives in the same file as the staging steps that produce those names, and task 3.1 checks the built names against it at the next release.
- [The prefix makes names longer] → The grouping is worth it, and the version and platform stay readable.
