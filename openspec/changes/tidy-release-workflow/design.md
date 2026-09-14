## Context

See proposal.md - Why. The current step, in the `preflight` job of `.github/workflows/release.yml`:

```yaml
- name: Create draft release
  if: github.ref_type == 'tag'
  env:
    GH_TOKEN: ${{ github.token }}
  run: gh release create "$GITHUB_REF_NAME" --draft --verify-tag --title "$GITHUB_REF_NAME" --generate-notes SOURCE-PROVENANCE.txt
```

`gh release create` treats trailing file arguments as assets. Per `gh release create --help`, "Additional release notes can be prepended to automatically generated notes by using the `--notes` flag."

The three `actions/upload-artifact@v4` steps upload `out/*` under the names `linux`, `windows` and `macos`, on non-tag runs only.

## Goals / Non-Goals

**Goals:**
- No provenance file among release assets, while the directions stay one click away on the release page and always match that release.
- No Node 20 deprecation warning from our own steps.

**Non-Goals:**
- Fixing the stale PyAV versions in `SOURCE-PROVENANCE.txt` (a separate change).
- Changing artifact contents, names, or the manual-run artifact layout.

## Decisions

### 1. Prepend a notes section with `--notes`, linking at the tag

The step drops the `SOURCE-PROVENANCE.txt` argument and passes `--notes` before `--generate-notes`:

```
## Source code for bundled GPL components

These downloads include FFmpeg, x264 and x265 (GPL-licensed) through PyAV.
Where to get their exact source: [SOURCE-PROVENANCE.txt](https://github.com/<repo>/blob/<tag>/SOURCE-PROVENANCE.txt).
The same file is also inside every download.
```

- **The URL is built from `${{ github.repository }}` and `$GITHUB_REF_NAME`**, so it points at the file **as tagged**. A later edit on `main` can't change what an old release links to, which matters because `licensing` requires each release's directions to name that release's versions.
- **The notes go in through a shell variable in `run:`**, holding a heredoc, so the multi-line Markdown needs no YAML escaping.

**Rejected: `--notes-file SOURCE-PROVENANCE.txt`.** It would paste 158 lines of plain text into every release page, which is worse to read than a link and still a wall of text next to the downloads.

**Rejected: a `blob/main/...` link.** It would drift from what was actually bundled in older releases.

### 2. `@v7`, not `@v6`

Both run on Node 24. v7.0.1 is the latest, and its only behaviour change is the opt-in `archive: false`, which we don't set, so archives stay zipped exactly as today. There's no reason to pin an older major.

### 3. Verification

- **The `@v7` update:** a manual run on `dev`. All three `Upload run artifacts` steps pass, the run page shows no Node 20 annotation, and the three artifacts download.
- **The notes:** a tagged run is the only thing that executes the step. The tag must equal the project version (`0.1.0`, enforced by "Release version matches the tag"). Options for the maintainer at that point:
  - **Re-tag `v0.1.0`.** `gh release delete v0.1.0 --cleanup-tag` removes the stale draft from 2026-09-12 and its tag, then push `v0.1.0` at the new commit. This also clears a draft built from outdated code, which the backlog's "real release" item already calls for.
  - **Wait for the real next release** and check the notes then. The task stays open until that happens.
  Both actions are outward-facing, so the task asks before either.

## Risks / Trade-offs

- **[Risk]** A typo in the heredoc or URL makes a broken link on a real release. → The tagged verification opens the link from the draft's notes and confirms it lands on the file at that tag.
- **[Risk]** Someone reads `licensing`'s "alongside the distributed artifact" as requiring an attached file. → The directions sit on the same page as the downloads, and in every download. The maintainer chose this reading on 2026-09-14. Legal advice would be the tiebreaker if it's ever questioned.
- **[Trade-off]** A user who only looks at the asset list no longer sees a provenance file there. That's intended: they see it in the notes directly above, and inside what they download.
