## 1. Spec and config

- [x] 1.1 Add `specs/project-workflow/spec.md` delta with the two new requirements (platform split by change, ordered numbering) and verify `openspec validate 01-adopt-platform-split-requirements --strict` passes
- [x] 1.2 Add both new rules to `openspec/config.yaml`'s `rules:` block for `proposal`, `specs`, `design`, and `tasks`, matching the existing ponytail-rule pattern
- [x] 1.3 Verify the rules surface end-to-end: run `openspec instructions tasks --change 01-adopt-platform-split-requirements --json` and confirm the new rules appear in the `rules` array (already confirmed while drafting this change)

## 2. Apply

- [x] 2.1 Run `/opsx:archive` (or equivalent) once this change is approved, so `openspec/specs/project-workflow/spec.md` picks up the two new requirements
