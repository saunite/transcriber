## Why

A release page lists 15 assets in one flat, alphabetical list, and GitHub offers no folders or ordering. Platforms interleave (`transcriber-cli_…linux`, `…macos`, `…windows`, then the `.dmg`, then the AppImage, then the `.deb`), and three of the rows — `InRelease`, `Packages`, `Packages.gz` — exist for apt, not for people. A visitor has to know the project's file names to find their download.

## What Changes

- **The release notes gain a "which download do I need?" table**, generated with the draft release. GitHub renders notes above the assets, so most readers never scan the list. The table names each platform's choices, says what each is for, and says plainly that the three repository index files are for package managers and can be ignored.
- **Assets are named with a platform prefix**, so the alphabetical list groups by platform: `linux-…`, `macos-…`, `windows-…`. The case rule decided on 2026-09-18 is unchanged: `.deb` and `.rpm` names stay lowercase, and the AppImage and the Windows and macOS artifacts keep their capitalised `Transcriber`.
- The README's three download tables follow the new names.
- **The package-split backlog item is corrected**, not started: it claims a typical upgrade would fall to "a few megabytes", which is wrong. The frozen engine is rebuilt on every release, so only the model (~142 MB of the 269 MB `.deb`) is stable. A split would halve upgrades, not shrink them to a few MB.

Not in scope, decided on 2026-09-19: moving the apt index off the release page. apt requires the index and the `.deb` to share one base URL, so the index can only move if the packages move with it, which would break `releases/latest/download/` links and contradict `linux-package-repos`'s "rather than being copied to a second location". The notes table explains those files instead.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `release-build`: adds a requirement that a release's downloads are named so the list groups by platform, and that the notes tell a reader which one to take.

## Impact

- `.github/workflows/release.yml`: the draft-release notes, and the asset staging in all three platform jobs.
- `README.md` (the Linux, Windows and macOS tables), and `docs/building.md` where it lists artifact names.
- `openspec/backlog.md`: the corrected package-split entry.
- No change to the repositories, the packages themselves, or any published release. The new names apply from the next release; v0.1.0's assets stay as they are, since the live apt index references them by name.
