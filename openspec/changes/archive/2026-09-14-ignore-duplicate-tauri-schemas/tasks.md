## 1. Untrack the duplicates

- [x] 1.1 Before removing anything, confirm the four schemas are still byte-identical (`sha256sum src-tauri/gen/schemas/*-schema.json`), and that `git grep -n "linux-schema\|windows-schema\|macOS-schema"` finds no reference outside `openspec/`. If either check fails, stop and report instead of continuing.

  **Done 2026-09-14.** All four `*-schema.json` hash to `0b57b9068cc886bd…`, and `git grep` for the three platform names outside `openspec/` finds nothing.
- [x] 1.2 Add `/gen/schemas/linux-schema.json`, `/gen/schemas/windows-schema.json` and `/gen/schemas/macOS-schema.json` to `src-tauri/.gitignore`, and run `git rm --cached` on those three files. Verify:
  - `git ls-files src-tauri/gen/schemas` lists only `acl-manifests.json`, `capabilities.json` and `desktop-schema.json`;
  - the three files still exist on disk;
  - `git check-ignore` reports each of the three as ignored.

  **Done 2026-09-14.** Three ignore lines, with a comment saying why `desktop-schema.json` stays tracked, are appended to `src-tauri/.gitignore`, and the three files are removed from the index. `git ls-files` now lists only `acl-manifests.json`, `capabilities.json` and `desktop-schema.json`; all six files remain on disk; `git check-ignore -v` attributes each of the three to its `src-tauri/.gitignore` line.
- [x] 1.3 Run a local Linux Tauri build, which regenerates the schemas, and verify `git status --porcelain src-tauri/gen` prints nothing afterwards.

  **Done 2026-09-14.** A local Linux build of the AppImage and `.rpm` ran with the change in place. Afterwards, `git status --porcelain src-tauri/gen` showed only the three intended staged deletions, with nothing untracked or modified. Tauri left all six schema files untouched (their dates stayed 2026-09-02/05/11), because their content hadn't changed, so the build never rewrote an ignored file. The ignore rule itself is proven by `git check-ignore` in 1.2.
