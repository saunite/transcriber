## 1. Workflow edits

- [ ] 1.1 In `.github/workflows/release.yml`'s "Create draft release" step, remove the `SOURCE-PROVENANCE.txt` argument, and add a `--notes` section built in `run:` with a heredoc (design.md Decision 1). The section names FFmpeg, x264 and x265, links to `https://github.com/${{ github.repository }}/blob/$GITHUB_REF_NAME/SOURCE-PROVENANCE.txt`, and says the file is also inside every download. Keep `--generate-notes`. Verify:
  - the YAML parses with PyYAML;
  - `gh release create` in the step no longer has a file argument;
  - an extracted copy of the step's script, run locally with `GITHUB_REF_NAME=v0.1.0` and `gh` replaced by `echo`, prints the expected `--notes` text with the tag in the URL.
- [ ] 1.2 Replace the three `actions/upload-artifact@v4` with `actions/upload-artifact@v7`. Verify `grep -c 'upload-artifact@v7' .github/workflows/release.yml` prints 3, and `@v4` no longer appears.
- [ ] 1.3 In README's "Releasing" licensing paragraph, change "the workflow attaches `SOURCE-PROVENANCE.txt` to the release" to say the workflow links it from the release notes at the release's tag. Verify that README no longer claims the file is attached.

## 2. Verification runs

- [ ] 2.1 Manual `workflow_dispatch` run on `dev` (only when the user asks for it). Verify all four jobs pass, each `Upload run artifacts` step succeeds, the run shows no "Node.js 20 is deprecated" annotation, and the `linux`, `windows` and `macos` artifacts are listed and downloadable.
- [ ] 2.2 Tagged verification (design.md Decision 3). **Ask the user** whether to re-tag `v0.1.0` (delete the stale draft and tag with `gh release delete v0.1.0 --cleanup-tag`, then push `v0.1.0` at the change's commit) or to wait for the real next release. On the chosen draft, verify:
  - its notes begin with the provenance section;
  - the link opens `SOURCE-PROVENANCE.txt` at that tag;
  - the asset list has no `SOURCE-PROVENANCE.txt`, but still has every platform's packages.
