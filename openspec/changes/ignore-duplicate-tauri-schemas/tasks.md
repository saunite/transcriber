## 1. Untrack the duplicates

- [ ] 1.1 Before removing anything, confirm the four schemas are still byte-identical (`sha256sum src-tauri/gen/schemas/*-schema.json`), and that `git grep -n "linux-schema\|windows-schema\|macOS-schema"` finds no reference outside `openspec/`. If either check fails, stop and report instead of continuing.
- [ ] 1.2 Add `/gen/schemas/linux-schema.json`, `/gen/schemas/windows-schema.json` and `/gen/schemas/macOS-schema.json` to `src-tauri/.gitignore`, and run `git rm --cached` on those three files. Verify:
  - `git ls-files src-tauri/gen/schemas` lists only `acl-manifests.json`, `capabilities.json` and `desktop-schema.json`;
  - the three files still exist on disk;
  - `git check-ignore` reports each of the three as ignored.
- [ ] 1.3 Run a local Linux Tauri build, which regenerates the schemas, and verify `git status --porcelain src-tauri/gen` prints nothing afterwards.
