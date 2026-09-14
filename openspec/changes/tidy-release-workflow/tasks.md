## 1. Workflow edits

- [x] 1.1 In `.github/workflows/release.yml`'s "Create draft release" step, remove the `SOURCE-PROVENANCE.txt` argument, and add a `--notes` section built in `run:` with a heredoc (design.md Decision 1). The section names FFmpeg, x264 and x265, links to `https://github.com/${{ github.repository }}/blob/$GITHUB_REF_NAME/SOURCE-PROVENANCE.txt`, and says the file is also inside every download. Keep `--generate-notes`. Verify:
  - the YAML parses with PyYAML;
  - `gh release create` in the step no longer has a file argument;
  - an extracted copy of the step's script, run locally with `GITHUB_REF_NAME=v0.1.0` and `gh` replaced by `echo`, prints the expected `--notes` text with the tag in the URL.

  **Done 2026-09-14.** The step now builds `notes` from a heredoc in `run:` and calls `gh release create "$GITHUB_REF_NAME" --draft --verify-tag --title "$GITHUB_REF_NAME" --notes "$notes" --generate-notes`. The repository comes in through `env: REPO: ${{ github.repository }}` instead of being inlined in the heredoc; the URL is the same. Checks: PyYAML parses the workflow, and the `gh release create` line has no file argument. Running the step's script from the parsed YAML with `gh` stubbed as `printf` and `GITHUB_REF_NAME=v0.1.0` printed the flags in order and the notes Markdown, blank line kept, with `https://github.com/saunite/transcriber/blob/v0.1.0/SOURCE-PROVENANCE.txt`. That URL returns HTTP 200 on GitHub today.
- [x] 1.2 Replace the three `actions/upload-artifact@v4` with `actions/upload-artifact@v7`. Verify `grep -c 'upload-artifact@v7' .github/workflows/release.yml` prints 3, and `@v4` no longer appears.

  **Done 2026-09-14.** `grep -c 'upload-artifact@v7'` prints 3, and `@v4` prints 0.
- [x] 1.3 In README's "Releasing" licensing paragraph, change "the workflow attaches `SOURCE-PROVENANCE.txt` to the release" to say the workflow links it from the release notes at the release's tag. Verify that README no longer claims the file is attached.

  **Done 2026-09-14.** README's licensing paragraph now reads "…and every release's notes link to `SOURCE-PROVENANCE.txt` as it was at that release's tag, instead of attaching it among the downloads." The "attaches `SOURCE-PROVENANCE.txt` to the release" wording is gone.

## 2. Verification runs

- [ ] 2.1 Manual `workflow_dispatch` run on `dev` (only when the user asks for it). Verify all four jobs pass, each `Upload run artifacts` step succeeds, the run shows no "Node.js 20 is deprecated" annotation, and the `linux`, `windows` and `macos` artifacts are listed and downloadable.
- [ ] 2.2 Tagged verification (design.md Decision 3). **Ask the user** whether to re-tag `v0.1.0` (delete the stale draft and tag with `gh release delete v0.1.0 --cleanup-tag`, then push `v0.1.0` at the change's commit) or to wait for the real next release. On the chosen draft, verify:
  - its notes begin with the provenance section;
  - the link opens `SOURCE-PROVENANCE.txt` at that tag;
  - the asset list has no `SOURCE-PROVENANCE.txt`, but still has every platform's packages.
