# Tasks

## 1. Release workflow

- [x] 1.1 In `.github/workflows/release.yml`, stage the Linux, Windows and macOS assets under the platform prefixes from design.md Decision 2, keeping the existing lowercase rename for `.deb` and `.rpm`. Verify each job's rename with a dry run on that platform's real file names (touch the files, run the loop, list the result), including that nothing is renamed twice and the CLI archive keeps its own name after the prefix.
- [x] 1.2 Add the "which download do I need?" table to the draft-release notes, above the GPL section, with the tag's version substituted and a closing line that `InRelease`, `Packages` and `Packages.gz` are for package managers. Verify by running the step's script locally with `GITHUB_REF_NAME=v0.1.1` and checking the rendered Markdown: one row per download, every file name matching what 1.1 produces.

## 2. Documentation and backlog

- [x] 2.1 Update the README's Linux, Windows and macOS tables to the new names, and `docs/building.md` where it lists artifact names, marking those as the names of the *local build* if they stay unprefixed. Run the no-ai-slop skill in detect mode on the changed prose and fix what it flags. Verify with `grep -n "linux-\|macos-\|windows-" README.md`.
- [x] 2.2 Correct the package-split entry in `openspec/backlog.md`: the frozen engine is rebuilt on every release, so only the model (~142 MB of the 269 MB `.deb`) is stable and a split would halve a typical upgrade rather than reduce it to a few megabytes. Leave the item parked. Verify with `grep -n "few megabytes" openspec/backlog.md` finding nothing.

  **Done 2026-09-19.** The entry is now "Split the bundled model into its own package", with a correction paragraph: the frozen engine is rebuilt every release, so only the model is stable, and splitting it takes a typical upgrade from ~269 MB to ~127 MB rather than to a few megabytes. It also records the two costs (one more asset per format, and a manual `.deb` install needing the model package alongside). The item stays parked. **The check as written ("grep finds nothing") does not hold:** the phrase survives once, inside the correction, quoting what the old text claimed. That is deliberate.

## 3. Verification

- [ ] 3.1 **With the user's go-ahead, since CI runs are theirs to start:** a manual `release.yml` run on `dev`, whose per-job run artifacts carry the staged names. Verify every uploaded name matches design.md Decision 2 and the notes table from 1.2. A manual run creates no release, so the notes themselves are checked from the rendered text in 1.2.
- [x] 3.2 Run `openspec validate tidy-release-downloads --strict` and verify it passes.
- [ ] 3.3 **At the next release, by the user:** open the published release page and confirm the notes table reads correctly above the assets, the assets group by platform, and the three index files are explained. Record the result here.
